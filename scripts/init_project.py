#!/usr/bin/env python3
"""作品プロジェクトの雛形を生成する(既存ファイルは絶対に上書きしない)。

usage: init_project.py [--project DIR]
"""

import argparse
import os
import shutil
import sys

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(PLUGIN_ROOT, "templates")

# (テンプレート名, 配置先)
FILES = [
    ("novel.config.yaml", "novel.config.yaml"),
    ("world.yaml", "canon/world.yaml"),
    ("style.yaml", "canon/style.yaml"),
    ("glossary.yaml", "canon/glossary.yaml"),
    ("constraints.yaml", "canon/constraints.yaml"),
    ("timeline.yaml", "canon/timeline.yaml"),
    ("character.yaml", "canon/characters/_template.yaml"),
    ("outline.yaml", "plot/outline.yaml"),
    ("foreshadowing.yaml", "plot/foreshadowing.yaml"),
    ("character-state.yaml", "state/character-state.yaml"),
    ("knowledge.yaml", "state/knowledge.yaml"),
    ("lint-allowlist.txt", "state/lint-allowlist.txt"),
]
DIRS = ["canon/characters", "plot", "state/context-pack", "manuscript"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=os.getcwd())
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project)

    created, skipped = [], []
    for d in DIRS:
        os.makedirs(os.path.join(root, d), exist_ok=True)
    for src, dst in FILES:
        src_path = os.path.join(TEMPLATES, src)
        dst_path = os.path.join(root, dst)
        if os.path.exists(dst_path):
            skipped.append(dst)
            continue
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        shutil.copyfile(src_path, dst_path)
        created.append(dst)

    print("プロジェクト: %s" % root)
    for f in created:
        print("  作成: %s" % f)
    for f in skipped:
        print("  スキップ(既存): %s" % f)
    if not created:
        print("すべて既存。何も変更していない。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
