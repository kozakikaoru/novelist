#!/usr/bin/env python3
"""執筆済みの全章を1つの納品ファイルに結合する。

usage: compile_manuscript.py [--project DIR] [--out PATH]
出力: build/<タイトル>.md (扉 + 目次 + 各章)。exit 1 = 原稿が1章も無い
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
    except Exception as e:
        print("WARNING: %s を読めない: %s" % (path, e), file=sys.stderr)
        return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=os.getcwd())
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project)

    cfg = try_load(os.path.join(root, "novel.config.yaml"))
    if cfg is None:
        print("ERROR: novel.config.yaml が見つからない", file=sys.stderr)
        return 1
    p = cfg.get("paths", {}) or {}
    ms_dir = os.path.join(root, p.get("manuscript", "manuscript"))
    pattern = cfg.get("manuscript_pattern", "ch{n:02d}.md")

    world = try_load(os.path.join(root, p.get("canon", "canon"), "world.yaml")) or {}
    outline = try_load(os.path.join(root, p.get("plot", "plot"), "outline.yaml")) or {}
    chapters = outline.get("chapters") or []
    titles = {c.get("n"): c.get("title", "") for c in chapters}

    # outline に載っている章 + パターンに合致する原稿を章番号順に収集
    ns = sorted({c.get("n") for c in chapters if isinstance(c.get("n"), int)})
    if not ns:
        rx = re.compile(r"(\d+)")
        found = []
        if os.path.isdir(ms_dir):
            for fn in os.listdir(ms_dir):
                m = rx.search(fn)
                if fn.endswith(".md") and m:
                    found.append(int(m.group(1)))
        ns = sorted(set(found))

    title = world.get("title") or "無題"
    parts = ["# %s" % title]
    if world.get("summary"):
        parts.append("")
        parts.append(str(world["summary"]).strip())
    toc = ["", "## 目次", ""]
    body = []
    total = 0
    included = []
    for n in ns:
        path = os.path.join(ms_dir, pattern.format(n=n))
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read().strip()
        if not text:
            continue
        ch_title = titles.get(n) or ""
        heading = "第%d章 %s" % (n, ch_title) if ch_title else "第%d章" % n
        toc.append("- %s" % heading)
        body.append("")
        body.append("---")
        body.append("")
        body.append("## %s" % heading)
        body.append("")
        body.append(text)
        total += len(text)
        included.append(n)

    if not included:
        print("ERROR: 結合できる原稿が1章も無い (%s)" % ms_dir, file=sys.stderr)
        return 1

    out_path = args.out or os.path.join(root, "build", "%s.md" % title)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts + toc + body) + "\n")

    print("納品ファイル: %s" % os.path.relpath(out_path, root))
    print("収録: %d章 (%s) / 本文合計 %d 字" % (len(included), included, total))
    missing = [n for n in ns if n not in included]
    if missing:
        print("警告: outline にあるが原稿が無い章: %s" % missing)
    return 0


if __name__ == "__main__":
    sys.exit(main())
