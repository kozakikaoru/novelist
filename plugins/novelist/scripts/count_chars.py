#!/usr/bin/env python3
"""原稿の文字数を実測し、目標字数と照合する。

writer の自己申告は不正確(実測比 +20% の過大申告が観測されている)なので、
文字数の報告は必ずこのスクリプトの出力を使うこと。

目標は plot/outline.yaml に書く:
  target_total_chars: 20000   # トップレベル: 全体目標
  chapters:
    - n: 1
      target_chars: 4000      # 章ごとの目標(任意)

usage: count_chars.py [章番号...] [--project DIR]  (章番号省略で全章)
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yamlish import load_yaml


def try_load(path):
    try:
        return load_yaml(path)
    except Exception:
        return None


def count(text):
    no_ws = len(re.sub(r"\s", "", text))
    return no_ws, len(text)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("chapters", nargs="*", type=int)
    ap.add_argument("--project", default=os.getcwd())
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project)

    cfg = try_load(os.path.join(root, "novel.config.yaml"))
    if cfg is None:
        print("ERROR: novel.config.yaml が見つからない", file=sys.stderr)
        return 1
    p = cfg.get("paths", {}) or {}
    ms_dir = os.path.join(root, p.get("manuscript", "manuscript"))
    pattern = cfg.get("manuscript_pattern", "ch{n:02d}.md")
    outline = try_load(os.path.join(root, p.get("plot", "plot"), "outline.yaml")) or {}
    by_n = {c.get("n"): c for c in (outline.get("chapters") or []) if isinstance(c, dict)}

    ns = args.chapters
    if not ns:
        ns = sorted(k for k in by_n if isinstance(k, int))
        if not ns and os.path.isdir(ms_dir):
            ns = sorted(
                int(m.group(1))
                for fn in os.listdir(ms_dir)
                for m in [re.search(r"(\d+)", fn)]
                if fn.endswith(".md") and m
            )

    total_nws = total_all = 0
    print("章   文字数(空白除く)  (含む)   目標      差分")
    for n in ns:
        path = os.path.join(ms_dir, pattern.format(n=n))
        if not os.path.exists(path):
            print("%-4d (原稿なし)" % n)
            continue
        with open(path, encoding="utf-8") as f:
            nws, full = count(f.read())
        total_nws += nws
        total_all += full
        target = (by_n.get(n) or {}).get("target_chars")
        if target:
            diff = nws - int(target)
            print("{:<4} {:>12,}  {:>10,}  {:>8,}  {:+,} ({:+.0f}%)".format(
                n, nws, full, int(target), diff, diff * 100.0 / int(target)))
        else:
            print("{:<4} {:>12,}  {:>10,}".format(n, nws, full))

    print("合計 {:>12,}  {:>10,}".format(total_nws, total_all))
    goal = outline.get("target_total_chars")
    if goal:
        diff = total_nws - int(goal)
        print("全体目標 {:,} に対して {:+,} ({:+.0f}%)".format(
            int(goal), diff, diff * 100.0 / int(goal)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
