#!/usr/bin/env python3
"""헤더/푸터에서 페이지번호 추출 후 연속성 분석.

상하단 10% 영역에서 숫자만으로 구성된 짧은 줄을 페이지번호 후보로 본다.
이전 페이지와의 일관성을 기준으로 가장 그럴듯한 시퀀스를 선택하고,
PDF↔책 페이지 오프셋의 mode를 추정한다.
"""

import json
import os
import re
import sys
from collections import Counter

import fitz

NUM_ONLY = re.compile(r"^[\s\-–—_•·\.]*(\d{1,4})[\s\-–—_•·\.]*$")


def header_footer_candidates(page, margin_ratio=0.10):
    rect = page.rect
    h = rect.height
    top_band = fitz.Rect(0, 0, rect.width, h * margin_ratio)
    bot_band = fitz.Rect(0, h * (1 - margin_ratio), rect.width, h)
    cands = set()
    for band in (top_band, bot_band):
        words = page.get_text("blocks", clip=band)
        for w in words:
            text = (w[4] or "").strip()
            if not text:
                continue
            for line in text.splitlines():
                line = line.strip()
                m = NUM_ONLY.match(line)
                if m:
                    n = int(m.group(1))
                    if 1 <= n <= 2000:
                        cands.add(n)
    return sorted(cands)


def inspect(path):
    doc = fitz.open(path)
    n = len(doc)
    by_page = []
    for i in range(n):
        cands = header_footer_candidates(doc[i])
        by_page.append({"page": i + 1, "cands": cands})
    doc.close()

    picked = [None] * n
    for i, entry in enumerate(by_page):
        cands = entry["cands"]
        prev_val = None
        for j in range(i - 1, -1, -1):
            if picked[j] is not None:
                prev_val = picked[j]
                gap = i - j
                target = prev_val + gap
                if target in cands:
                    picked[i] = target
                    break
        if picked[i] is None and cands and prev_val is None:
            picked[i] = cands[0]

    for i in range(n - 2, -1, -1):
        nxt_val = picked[i + 1]
        if nxt_val is None:
            continue
        target = nxt_val - 1
        cands = by_page[i]["cands"]
        if picked[i] is None and target in cands:
            picked[i] = target

    offsets = [(i + 1) - picked[i] for i in range(n) if picked[i] is not None]
    offset_mode = Counter(offsets).most_common(1)[0] if offsets else None

    chains = []
    cur = [(1, picked[0])]
    for i in range(1, n):
        prev = picked[i - 1]
        now = picked[i]
        if prev is not None and now is not None and now == prev + 1:
            cur.append((i + 1, now))
        else:
            chains.append(cur)
            cur = [(i + 1, now)]
    chains.append(cur)

    chain_summary = []
    for ch in chains:
        if all(x[1] is None for x in ch):
            chain_summary.append({
                "pdf_range": [ch[0][0], ch[-1][0]],
                "len": len(ch),
                "page_range": None,
                "gap_type": "no-pagenum-detected",
            })
            continue
        chain_summary.append({
            "pdf_range": [ch[0][0], ch[-1][0]],
            "len": len(ch),
            "page_range": [ch[0][1], ch[-1][1]] if ch[0][1] is not None else None,
            "gap_type": "ok",
        })

    suspicious_gaps = []
    pairs = [(i + 1, picked[i]) for i in range(n) if picked[i] is not None]
    for a, b in zip(pairs, pairs[1:]):
        pdf_gap = b[0] - a[0]
        num_gap = b[1] - a[1]
        if pdf_gap == num_gap:
            continue
        diff = num_gap - pdf_gap
        kind = "real-missing" if 1 <= abs(diff) <= 5 else "ocr-misread"
        suspicious_gaps.append({
            "between_pdf_pages": [a[0], b[0]],
            "picked_numbers": [a[1], b[1]],
            "expected_gap": pdf_gap,
            "actual_gap": num_gap,
            "kind": kind,
        })

    real_missing = [g for g in suspicious_gaps if g["kind"] == "real-missing"]
    ocr_misread = [g for g in suspicious_gaps if g["kind"] == "ocr-misread"]

    return {
        "file": os.path.basename(path),
        "total_pages": n,
        "pages_with_num_candidates": sum(1 for x in by_page if x["cands"]),
        "picked_coverage": sum(1 for p in picked if p is not None),
        "first_picked": next((p for p in picked if p is not None), None),
        "last_picked": next((p for p in reversed(picked) if p is not None), None),
        "offset_mode": {
            "value": offset_mode[0],
            "count": offset_mode[1],
        } if offset_mode else None,
        "chains_total": len(chain_summary),
        "chains_sample": chain_summary[:50],
        "real_missing_gaps": real_missing,
        "ocr_misread_gaps_count": len(ocr_misread),
        "ocr_misread_gaps_sample": ocr_misread[:20],
    }


def main():
    if len(sys.argv) < 2:
        print("usage: pagenum_check.py <pdf> [<pdf>...]", file=sys.stderr)
        sys.exit(2)
    out = [inspect(p) for p in sys.argv[1:]]
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
