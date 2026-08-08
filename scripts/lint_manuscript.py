#!/usr/bin/env python3
"""novelist 原稿 lint — canon(正典)と原稿を機械照合する決定論チェッカー。

LLM の注意力に依存しないチェックをここに集約する:
  1. 表記ゆれ        glossary.yaml の variants に一致        → ERROR
  2. 禁止語彙        world.yaml の banned_words に一致        → ERROR
  3. キャラ属性違反  characters/*.yaml の lint.forbid に一致  → ERROR
  4. 未登録カタカナ語 canon 側に存在しないカタカナ語           → WARN
  5. 死亡キャラ発話  status: dead のキャラ名直後に鉤括弧      → WARN

usage: lint_manuscript.py <manuscript.md> [more.md ...] [--project DIR]
exit code: 0 = 指摘なし / 2 = 指摘あり(内容は stdout)
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yamlish import load_yaml, ParseError

KATAKANA_RE_TMPL = r"[ァ-ヶー]{%d,}"
NEAR_WINDOW = 120  # lint.forbid の near 判定窓(前後の文字数)
SPEECH_WINDOW = 40  # 死亡キャラ名→鉤括弧の距離


def find_project_root(start):
    d = os.path.abspath(start)
    if os.path.isfile(d):
        d = os.path.dirname(d)
    while True:
        if os.path.exists(os.path.join(d, "novel.config.yaml")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def safe_load(path, findings):
    if not os.path.exists(path):
        return None
    try:
        return load_yaml(path)
    except ParseError as e:
        findings.append(("error", "parse", 0, "canon が読めない: %s: %s" % (path, e)))
    except Exception as e:  # PyYAML 側のエラーも報告する
        findings.append(("error", "parse", 0, "canon が読めない: %s: %s" % (path, e)))
    return None


def line_of(text, idx):
    return text.count("\n", 0, idx) + 1


def collect_known_katakana(root, cfg, min_len):
    """canon/plot/state 配下の全テキストに出現するカタカナ語 + 許可リストを既知集合とする。"""
    kata = re.compile(KATAKANA_RE_TMPL % min_len)
    known = set()
    paths = cfg.get("paths", {})
    # 生成物(コンテキストパック)は既知語の根拠にしない
    # (前章末尾が混入していて、未登録語が「既知」扱いになるのを防ぐ)
    pack_dir = os.path.abspath(os.path.join(
        root,
        (cfg.get("context_pack", {}) or {}).get(
            "output_dir", os.path.join(paths.get("state", "state"), "context-pack")),
    ))
    dirs = [paths.get("canon", "canon"), paths.get("plot", "plot"), paths.get("state", "state")]
    for d in dirs:
        full = os.path.join(root, d)
        for dirpath, _dirnames, filenames in os.walk(full):
            if os.path.abspath(dirpath).startswith(pack_dir):
                continue
            for fn in filenames:
                if fn.endswith((".yaml", ".yml", ".md", ".txt")):
                    try:
                        with open(os.path.join(dirpath, fn), encoding="utf-8") as f:
                            known.update(kata.findall(f.read()))
                    except OSError:
                        pass
    # プラグイン同梱の一般カタカナ語リスト
    common = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "common_katakana.txt")
    for path in (common, os.path.join(root, paths.get("state", "state"), "lint-allowlist.txt")):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    w = line.split("#")[0].strip()
                    if w:
                        known.add(w)
    return known


def load_characters(root, cfg, findings):
    chars = []
    cdir = os.path.join(root, cfg.get("paths", {}).get("canon", "canon"), "characters")
    if not os.path.isdir(cdir):
        return chars
    for fn in sorted(os.listdir(cdir)):
        if not fn.endswith((".yaml", ".yml")) or fn.startswith("_"):
            continue
        data = safe_load(os.path.join(cdir, fn), findings)
        if isinstance(data, dict):
            data.setdefault("id", os.path.splitext(fn)[0])
            data["_file"] = os.path.join("canon", "characters", fn)
            chars.append(data)
    return chars


def lint_file(path, root, cfg, chars, glossary, world, dead_names, known_kata):
    findings = []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lint_cfg = cfg.get("lint", {}) or {}
    min_len = int(lint_cfg.get("min_katakana_len", 3))

    # 1. 表記ゆれ (canonical に含まれる variant の誤検出は除外)
    for term in (glossary or {}).get("terms", []) or []:
        canonical = term.get("canonical")
        if not canonical:
            continue
        spans = [m.span() for m in re.finditer(re.escape(canonical), text)]
        for var in term.get("variants", []) or []:
            if not var:
                continue
            for m in re.finditer(re.escape(str(var)), text):
                if any(a <= m.start() and m.end() <= b for a, b in spans):
                    continue
                findings.append((
                    "error", "glossary_variant", line_of(text, m.start()),
                    "表記ゆれ:「%s」→ 正典表記「%s」 (canon/glossary.yaml)" % (var, canonical),
                ))

    # 2. 禁止語彙
    for item in (world or {}).get("banned_words", []) or []:
        if isinstance(item, str):
            item = {"word": item}
        word = item.get("word")
        if not word:
            continue
        for m in re.finditer(re.escape(str(word)), text):
            findings.append((
                "error", "banned_word", line_of(text, m.start()),
                "禁止語彙:「%s」%s (canon/world.yaml banned_words)"
                % (word, " — " + item["reason"] if item.get("reason") else ""),
            ))

    # 3. キャラ属性違反 (lint.forbid)
    for ch in chars:
        for rule in ((ch.get("lint") or {}).get("forbid") or []):
            if isinstance(rule, str):
                rule = {"pattern": rule}
            pat = rule.get("pattern")
            if not pat:
                continue
            try:
                rx = re.compile(pat)
            except re.error as e:
                findings.append(("error", "parse", 0,
                                 "lint.forbid の正規表現が不正: %s (%s): %s" % (pat, ch["_file"], e)))
                continue
            near = rule.get("near")
            for m in rx.finditer(text):
                if near:
                    lo = max(0, m.start() - NEAR_WINDOW)
                    hi = m.end() + NEAR_WINDOW
                    if str(near) not in text[lo:hi]:
                        continue
                findings.append((
                    "error", "character_forbid", line_of(text, m.start()),
                    "キャラ属性違反:「%s」%s%s (%s)" % (
                        m.group(0),
                        ("〔近傍: %s〕" % near) if near else "",
                        " — " + rule["reason"] if rule.get("reason") else "",
                        ch["_file"],
                    ),
                ))

    # 4. 未登録カタカナ語
    kata = re.compile(KATAKANA_RE_TMPL % min_len)
    seen = {}
    for m in kata.finditer(text):
        tok = m.group(0)
        if tok in known_kata:
            continue
        if tok not in seen:
            seen[tok] = [0, line_of(text, m.start())]
        seen[tok][0] += 1
    for tok, (count, first_line) in sorted(seen.items(), key=lambda kv: kv[1][1]):
        findings.append((
            "warn", "unknown_entity", first_line,
            "未登録カタカナ語:「%s」(%d回) — 固有名詞なら canon/glossary.yaml か characters/ に登録、"
            "一般語なら state/lint-allowlist.txt に1行追加" % (tok, count),
        ))

    # 5. 死亡キャラ発話疑い
    for name, src in dead_names:
        for m in re.finditer(re.escape(name), text):
            tail = text[m.end():m.end() + SPEECH_WINDOW]
            if "「" in tail.split("\n")[0]:
                findings.append((
                    "warn", "dead_speaker", line_of(text, m.start()),
                    "死亡キャラ発話疑い:「%s」の直後に鉤括弧 — status: dead (%s)。"
                    "回想・幻覚など意図的なら無視してよいが、意図を確認すること" % (name, src),
                ))
                break  # 同一キャラは1回だけ報告
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--project", default=None)
    args = ap.parse_args(argv)

    root = args.project or find_project_root(args.files[0])
    if root is None:
        print("novel.config.yaml が見つからない: %s" % args.files[0], file=sys.stderr)
        return 1

    findings = []
    cfg = safe_load(os.path.join(root, "novel.config.yaml"), findings) or {}
    canon_dir = cfg.get("paths", {}).get("canon", "canon")
    glossary = safe_load(os.path.join(root, canon_dir, "glossary.yaml"), findings)
    world = safe_load(os.path.join(root, canon_dir, "world.yaml"), findings)
    state = safe_load(
        os.path.join(root, cfg.get("paths", {}).get("state", "state"), "character-state.yaml"),
        findings,
    )
    chars = load_characters(root, cfg, findings)

    # 死亡キャラ: characters の status: dead、または state の condition に「死亡」
    dead_names = []
    state_chars = (state or {}).get("characters", {}) or {}
    for ch in chars:
        st = state_chars.get(ch.get("id"), {}) or {}
        is_dead = ch.get("status") == "dead" or "死亡" in str(st.get("condition", ""))
        if is_dead:
            for name in [ch.get("name")] + (ch.get("aliases") or []):
                if name:
                    dead_names.append((str(name), ch["_file"]))

    min_len = int((cfg.get("lint", {}) or {}).get("min_katakana_len", 3))
    known_kata = collect_known_katakana(root, cfg, min_len)

    total_err = total_warn = 0
    for path in args.files:
        fs = findings + lint_file(path, root, cfg, chars, glossary, world, dead_names, known_kata)
        findings = []  # canon 読み込みエラーは最初のファイルにだけ付ける
        if not fs:
            continue
        rel = os.path.relpath(path, root)
        print("== novelist lint: %s ==" % rel)
        for sev, _cat, line, msg in sorted(fs, key=lambda f: f[2]):
            tag = "[ERROR]" if sev == "error" else "[WARN] "
            loc = ("L%d " % line) if line else ""
            print("%s %s%s" % (tag, loc, msg))
            if sev == "error":
                total_err += 1
            else:
                total_warn += 1
    if total_err or total_warn:
        print("計: error %d / warn %d" % (total_err, total_warn))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
