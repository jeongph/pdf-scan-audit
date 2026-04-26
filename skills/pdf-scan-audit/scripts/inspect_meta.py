#!/usr/bin/env python3
"""PDF 페이지 메타·크기·DPI·회전·빈페이지 검사."""

import json
import os
import sys
from collections import Counter

import fitz


def inspect(path):
    doc = fitz.open(path)
    n = len(doc)
    rows = []
    sizes = []
    rotations = []
    dpis_x = []
    dpis_y = []
    has_image_count = 0
    blank_pages = []

    for i in range(n):
        page = doc[i]
        rect = page.rect
        w, h = rect.width, rect.height
        rot = page.rotation
        orientation = "portrait" if h >= w else "landscape"

        images = page.get_images(full=True)
        imgs_info = []
        for img in images:
            xref = img[0]
            try:
                info = doc.extract_image(xref)
                iw = info.get("width", 0)
                ih = info.get("height", 0)
                imgs_info.append((iw, ih, info.get("ext")))
            except Exception:
                pass

        dpi_x = dpi_y = None
        if imgs_info:
            has_image_count += 1
            iw, ih, _ = max(imgs_info, key=lambda x: x[0] * x[1])
            dpi_x = round(iw / (w / 72), 1) if w else None
            dpi_y = round(ih / (h / 72), 1) if h else None
            if dpi_x:
                dpis_x.append(dpi_x)
            if dpi_y:
                dpis_y.append(dpi_y)

        text = page.get_text("text") or ""
        text_len = len(text.strip())
        if not imgs_info and text_len < 5:
            blank_pages.append(i + 1)

        sizes.append((round(w, 2), round(h, 2)))
        rotations.append(rot)

        rows.append({
            "page": i + 1,
            "w": round(w, 2),
            "h": round(h, 2),
            "orient": orientation,
            "rot": rot,
            "n_images": len(imgs_info),
            "main_img": f"{imgs_info[0][0]}x{imgs_info[0][1]}" if imgs_info else None,
            "dpi_x": dpi_x,
            "dpi_y": dpi_y,
            "text_len": text_len,
        })

    size_counter = Counter(sizes)
    rot_counter = Counter(rotations)
    orient_counter = Counter(r["orient"] for r in rows)
    dominant_size = size_counter.most_common(1)[0] if size_counter else None
    dominant_orient = orient_counter.most_common(1)[0][0] if orient_counter else None

    off_size_pages = []
    if dominant_size:
        (dw, dh), _ = dominant_size
        tol = 0.05
        for r in rows:
            if abs(r["w"] - dw) / dw > tol or abs(r["h"] - dh) / dh > tol:
                off_size_pages.append(r["page"])

    off_rot_pages = [r["page"] for r in rows if r["rot"] != 0]
    off_orient_pages = [r["page"] for r in rows if r["orient"] != dominant_orient]

    dpi_mode = Counter([round(d / 10) * 10 for d in dpis_x]).most_common(1)
    dpi_mode_val = dpi_mode[0][0] if dpi_mode else None

    no_image_pages = [r["page"] for r in rows if r["n_images"] == 0]

    summary = {
        "file": os.path.basename(path),
        "total_pages": n,
        "metadata": doc.metadata,
        "size_distribution": [
            {"size": f"{s[0]}x{s[1]}", "count": c}
            for s, c in size_counter.most_common()
        ],
        "dominant_size": f"{dominant_size[0][0]}x{dominant_size[0][1]} ({dominant_size[1]}pages)"
        if dominant_size else None,
        "rotation_distribution": dict(rot_counter),
        "orientation_distribution": dict(orient_counter),
        "dominant_orientation": dominant_orient,
        "off_size_pages": off_size_pages,
        "off_size_count": len(off_size_pages),
        "off_rotation_pages": off_rot_pages,
        "off_orientation_pages": off_orient_pages,
        "blank_pages": blank_pages,
        "no_image_pages": no_image_pages,
        "dpi_x_min": min(dpis_x) if dpis_x else None,
        "dpi_x_max": max(dpis_x) if dpis_x else None,
        "dpi_x_mode_bucket": dpi_mode_val,
        "pages_with_text": sum(1 for r in rows if r["text_len"] > 0),
        "pages_with_image": has_image_count,
    }
    doc.close()
    return summary, rows


def main():
    if len(sys.argv) < 2:
        print("usage: inspect_meta.py <pdf> [<pdf>...]", file=sys.stderr)
        sys.exit(2)
    out = {}
    for p in sys.argv[1:]:
        s, rows = inspect(p)
        out[os.path.basename(p)] = {"summary": s, "rows": rows}
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
