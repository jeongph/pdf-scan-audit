#!/usr/bin/env python3
"""의심 페이지 PNG 추출. 전체 페이지(--mode full) 또는 헤더/푸터만(--mode header).

usage:
  extract_pages.py <pdf> <out_dir> --pages "1,5,10-12" [--mode full|header] [--dpi 110]
"""

import argparse
import os
import sys

import fitz


def parse_pages(spec):
    pages = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            for p in range(int(a), int(b) + 1):
                pages.add(p)
        else:
            pages.add(int(part))
    return sorted(pages)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("out_dir")
    ap.add_argument("--pages", required=True, help="쉼표·하이픈 (예: 1,5,10-12)")
    ap.add_argument("--mode", choices=["full", "header"], default="full")
    ap.add_argument("--dpi", type=int, default=None)
    args = ap.parse_args()

    dpi = args.dpi or (220 if args.mode == "header" else 110)
    os.makedirs(args.out_dir, exist_ok=True)
    pages = parse_pages(args.pages)

    doc = fitz.open(args.pdf)
    n = len(doc)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    saved = []
    for p in pages:
        if p < 1 or p > n:
            continue
        page = doc[p - 1]
        rect = page.rect
        if args.mode == "full":
            pix = page.get_pixmap(matrix=mat, alpha=False)
            out = os.path.join(args.out_dir, f"p{p:04d}.png")
            pix.save(out)
            saved.append(out)
        else:
            top = fitz.Rect(0, 0, rect.width, rect.height * 0.10)
            bot = fitz.Rect(0, rect.height * 0.90, rect.width, rect.height)
            pix_t = page.get_pixmap(matrix=mat, clip=top, alpha=False)
            pix_b = page.get_pixmap(matrix=mat, clip=bot, alpha=False)
            ot = os.path.join(args.out_dir, f"p{p:04d}_top.png")
            ob = os.path.join(args.out_dir, f"p{p:04d}_bot.png")
            pix_t.save(ot)
            pix_b.save(ob)
            saved.extend([ot, ob])
    doc.close()

    for s in saved:
        print(s)


if __name__ == "__main__":
    main()
