#!/usr/bin/env python3
"""콘텐츠 기반 검사: 빈 페이지, 회전 의심, 이미지 커버리지."""

import json
import os
import sys

import fitz


def orientation_hint(page):
    d = page.get_text("dict")
    widths = heights = 0
    n = 0
    for block in d.get("blocks", []):
        if block.get("type") == 0:
            for line in block.get("lines", []):
                bbox = line.get("bbox")
                if bbox:
                    w = bbox[2] - bbox[0]
                    h = bbox[3] - bbox[1]
                    widths += w
                    heights += h
                    n += 1
    if n == 0:
        return None
    return "normal" if widths > heights * 1.5 else "maybe_rotated"


def image_coverage(page):
    rect = page.rect
    page_area = rect.width * rect.height
    if page_area == 0:
        return None
    try:
        info = page.get_image_info()
    except Exception:
        info = []
    if not info:
        return None
    total = 0
    max_bbox = None
    for im in info:
        bbox = im.get("bbox")
        if not bbox:
            continue
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        a = w * h
        total += a
        if max_bbox is None or a > (max_bbox[2] - max_bbox[0]) * (max_bbox[3] - max_bbox[1]):
            max_bbox = bbox
    coverage = round(total / page_area, 3)
    if max_bbox:
        left = max_bbox[0] / rect.width
        right = (rect.width - max_bbox[2]) / rect.width
        top = max_bbox[1] / rect.height
        bottom = (rect.height - max_bbox[3]) / rect.height
        return {
            "coverage": coverage,
            "margins": {
                "l": round(left, 3),
                "r": round(right, 3),
                "t": round(top, 3),
                "b": round(bottom, 3),
            },
        }
    return {"coverage": coverage}


def inspect(path):
    doc = fitz.open(path)
    n = len(doc)
    no_text_pages = []
    orient_flags = []
    coverage_issues = []

    for i in range(n):
        page = doc[i]
        text = page.get_text("text") or ""
        if len(text.strip()) < 5:
            no_text_pages.append(i + 1)
        orient = orientation_hint(page)
        if orient == "maybe_rotated":
            orient_flags.append(i + 1)
        cov = image_coverage(page)
        if cov:
            margins = cov.get("margins") or {}
            bad = False
            for v in margins.values():
                if v < -0.01 or v > 0.08:
                    bad = True
                    break
            if bad:
                coverage_issues.append({"page": i + 1, **cov})

    doc.close()
    return {
        "file": os.path.basename(path),
        "total_pages": n,
        "no_text_pages_count": len(no_text_pages),
        "no_text_pages": no_text_pages,
        "maybe_rotated_pages": orient_flags,
        "coverage_issues_count": len(coverage_issues),
        "coverage_issues_sample": coverage_issues[:30],
    }


def main():
    if len(sys.argv) < 2:
        print("usage: inspect_content.py <pdf> [<pdf>...]", file=sys.stderr)
        sys.exit(2)
    out = [inspect(p) for p in sys.argv[1:]]
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
