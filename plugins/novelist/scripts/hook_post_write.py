#!/usr/bin/env python3
"""PostToolUse hook — 原稿(manuscript 配下の .md)が保存されたら即 lint を回す。

エージェントの注意力に依存しない安全網。指摘があれば exit 2 で差し戻し、
Claude(メイン/サブエージェント問わず)がその場で修正する。
novelist プロジェクト外のファイル編集では何もしない。
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lint_manuscript import find_project_root
from yamlish import load_yaml


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        return 0
    path = (data.get("tool_input") or {}).get("file_path")
    if not path or not path.endswith(".md"):
        return 0
    path = os.path.abspath(path)
    if not os.path.exists(path):
        return 0

    root = find_project_root(path)
    if root is None:
        return 0
    try:
        cfg = load_yaml(os.path.join(root, "novel.config.yaml")) or {}
    except Exception:
        return 0
    ms_dir = os.path.abspath(os.path.join(root, (cfg.get("paths") or {}).get("manuscript", "manuscript")))
    if not path.startswith(ms_dir + os.sep):
        return 0

    lint = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lint_manuscript.py")
    proc = subprocess.run(
        [sys.executable, lint, path, "--project", root],
        capture_output=True, text=True, timeout=25,
    )
    if proc.returncode == 0:
        return 0
    sys.stderr.write(proc.stdout + proc.stderr)
    sys.stderr.write(
        "\n[novelist hook] 原稿が canon と矛盾している。上記を修正して保存し直すこと。\n"
        "- ERROR: 原稿側を正典に合わせて書き直す(正典が誤りなら人間に確認)\n"
        "- 未登録カタカナ語: 意図した固有名詞なら canon/glossary.yaml に登録してから続行。\n"
        "  一般名詞なら state/lint-allowlist.txt に1行追加。意図しない語なら原稿から除去\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
