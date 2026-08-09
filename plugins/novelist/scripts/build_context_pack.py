#!/usr/bin/env python3
"""章ごとのコンテキストパックを生成する。

設計方針(重要):
- 「範囲を切る」のではなく「解像度を変える」。全キャラ・全制約・全用語は
  どのモードでも必ず載る。削るのはその章で使わない“詳細”だけ。
- canon 全体が閾値(full_load_threshold_chars)未満なら、絞り込み自体を行わず
  全文投入する(full モード)。絞り込みは canon が育ってからの最適化。
- 制約(constraints = 禁じ手リスト)と全キャラ1行サマリは常時フルロード。
  「登場しないキャラの存在が世界にかける制約」はここで担保する。

usage: build_context_pack.py <chapter_n> [--project DIR] [--stdout]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yamlish import load_yaml

PREV_TAIL_CHARS = 1500


def read_text(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return None


def try_load(path):
    try:
        return load_yaml(path)
    except Exception as e:
        print("WARNING: %s を読めない: %s" % (path, e), file=sys.stderr)
        return None


def canon_total_chars(root, paths, exclude_dir):
    total = 0
    for d in (paths["canon"], paths["plot"], paths["state"]):
        for dirpath, _dn, filenames in os.walk(os.path.join(root, d)):
            if os.path.abspath(dirpath).startswith(exclude_dir):
                continue
            for fn in filenames:
                if fn.endswith((".yaml", ".yml", ".md", ".txt")):
                    t = read_text(os.path.join(dirpath, fn))
                    if t:
                        total += len(t)
    return total


def load_characters(root, paths):
    out = []
    cdir = os.path.join(root, paths["canon"], "characters")
    if not os.path.isdir(cdir):
        return out
    for fn in sorted(os.listdir(cdir)):
        if not fn.endswith((".yaml", ".yml")) or fn.startswith("_"):
            continue
        path = os.path.join(cdir, fn)
        data = try_load(path)
        if isinstance(data, dict):
            data.setdefault("id", os.path.splitext(fn)[0])
            data["_path"] = path
            out.append(data)
    return out


def find_chapter(outline, n):
    for ch in (outline or {}).get("chapters", []) or []:
        if ch.get("n") == n:
            return ch
    return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("chapter", type=int)
    ap.add_argument("--project", default=os.getcwd())
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args(argv)
    n = args.chapter
    root = os.path.abspath(args.project)

    cfg = try_load(os.path.join(root, "novel.config.yaml"))
    if cfg is None:
        print("ERROR: novel.config.yaml が見つからない(/novelist:init を先に実行)", file=sys.stderr)
        return 1
    p = cfg.get("paths", {}) or {}
    paths = {
        "canon": p.get("canon", "canon"),
        "plot": p.get("plot", "plot"),
        "state": p.get("state", "state"),
        "manuscript": p.get("manuscript", "manuscript"),
    }
    cp_cfg = cfg.get("context_pack", {}) or {}
    threshold = int(cp_cfg.get("full_load_threshold_chars", 60000))
    pattern = cfg.get("manuscript_pattern", "ch{n:02d}.md")

    outline = try_load(os.path.join(root, paths["plot"], "outline.yaml"))
    chapter = find_chapter(outline, n)
    if chapter is None:
        print("ERROR: plot/outline.yaml に第%d章がない(/novelist:outline で追加)" % n, file=sys.stderr)
        return 1

    pack_dir = os.path.abspath(
        os.path.join(root, cp_cfg.get("output_dir", os.path.join(paths["state"], "context-pack")))
    )
    total = canon_total_chars(root, paths, pack_dir)
    mode = "full" if total < threshold else "layered"

    chars = load_characters(root, paths)
    by_id = {c["id"]: c for c in chars}
    present_ids = chapter.get("characters") or []
    missing = [cid for cid in present_ids if cid not in by_id]

    state = try_load(os.path.join(root, paths["state"], "character-state.yaml")) or {}
    foreshadow = try_load(os.path.join(root, paths["plot"], "foreshadowing.yaml")) or {}

    out = []
    w = out.append
    w("# 第%d章 コンテキストパック (mode: %s)" % (n, mode))
    w("")
    w("> このパックは canon(正典)から機械生成された。ここに書かれた事実と矛盾する記述をしてはならない。")
    w("> パックに存在しない固有名詞(キャラ・地名・アイテム等)を新規に登場させる場合は、")
    w("> 本文中に出す前に必ず【新規: 名前 — 一言説明】としてマークし、最終報告に列挙すること。")
    w("")

    # --- 章情報 ---
    w("## この章の設計 (plot/outline.yaml)")
    w("```yaml")
    for k in ("n", "title", "pov", "characters", "locations", "summary",
              "foreshadowing_plant", "foreshadowing_resolve"):
        if k in chapter:
            w("%s: %s" % (k, chapter[k]))
    w("```")
    if missing:
        w("**警告: characters に canon 未登録の id がある: %s — 執筆前に登録すること**" % missing)
    w("")

    def dump(title, relpath, note=None):
        t = read_text(os.path.join(root, relpath))
        if t and t.strip():
            w("## %s (%s)" % (title, relpath))
            if note:
                w("> " + note)
            w("```yaml")
            w(t.rstrip())
            w("```")
            w("")

    if mode == "full":
        # 全文投入
        dump("世界観", os.path.join(paths["canon"], "world.yaml"))
        dump("制約・禁じ手リスト", os.path.join(paths["canon"], "constraints.yaml"),
             "登場しないキャラでも、その存在が展開を不可能にする。必ず全件確認すること。")
        dump("文体・作風", os.path.join(paths["canon"], "style.yaml"))
        for c in chars:
            dump("キャラクター: %s" % c.get("name", c["id"]),
                 os.path.relpath(c["_path"], root))
        dump("用語集", os.path.join(paths["canon"], "glossary.yaml"))
        dump("タイムライン", os.path.join(paths["canon"], "timeline.yaml"))
        dump("伏線台帳", os.path.join(paths["plot"], "foreshadowing.yaml"))
        dump("キャラクター現在状態", os.path.join(paths["state"], "character-state.yaml"))
        dump("情報の非対称性(誰が何を知っているか)", os.path.join(paths["state"], "knowledge.yaml"),
             "キャラがまだ知らないはずの事実を口にさせないこと。")
    else:
        # 解像度可変: 詳細はこの章の登場キャラのみ、それ以外は1行 + 常時ロード群
        dump("世界観", os.path.join(paths["canon"], "world.yaml"))
        dump("制約・禁じ手リスト【常時フルロード】", os.path.join(paths["canon"], "constraints.yaml"),
             "登場しないキャラでも、その存在が展開を不可能にする。必ず全件確認すること。")
        dump("文体・作風", os.path.join(paths["canon"], "style.yaml"))

        w("## 全キャラクター一覧【常時ロード・1行解像度】")
        w("> 登場予定がなくても、会話で言及される・存在が影響する可能性がある。表記と生死は必ずこれに従うこと。")
        st_chars = (state.get("characters") or {})
        for c in chars:
            st = st_chars.get(c["id"], {}) or {}
            parts = ["- **%s** (%s)" % (c.get("name", c["id"]), c["id"])]
            parts.append("[%s]" % c.get("status", "alive"))
            if st.get("location"):
                parts.append("現在地: %s" % st["location"])
            if c.get("summary"):
                parts.append("— %s" % c["summary"])
            w(" ".join(parts))
        w("")

        w("## この章の登場キャラクター【フル解像度】")
        for cid in present_ids:
            c = by_id.get(cid)
            if not c:
                continue
            w("### %s (%s)" % (c.get("name", cid), cid))
            w("```yaml")
            w((read_text(c["_path"]) or "").rstrip())
            w("```")
            st = (state.get("characters") or {}).get(cid)
            if st:
                w("現在状態 (state/character-state.yaml as_of_chapter: %s):" % state.get("as_of_chapter"))
                w("```yaml")
                for k, v in st.items():
                    w("%s: %s" % (k, v))
                w("```")
            w("")

        # 用語集はコンパクト形(正典表記の一覧)
        glossary = try_load(os.path.join(root, paths["canon"], "glossary.yaml")) or {}
        terms = glossary.get("terms") or []
        if terms:
            w("## 用語集【常時ロード・正典表記】")
            for t in terms:
                if t.get("canonical"):
                    line = "- %s" % t["canonical"]
                    if t.get("category"):
                        line += " (%s)" % t["category"]
                    if t.get("note"):
                        line += " — %s" % t["note"]
                    w(line)
            w("")

        # 伏線: 未回収のみ + この章で仕込む/回収する分
        items = foreshadow.get("items") or []
        touch = set((chapter.get("foreshadowing_plant") or []) + (chapter.get("foreshadowing_resolve") or []))
        open_items = [i for i in items if i.get("status") not in ("resolved", "dropped") or i.get("id") in touch]
        if open_items:
            w("## 伏線台帳(未回収 + この章で扱う分)")
            for i in open_items:
                mark = ""
                if i.get("id") in (chapter.get("foreshadowing_resolve") or []):
                    mark = " ← **この章で回収する**"
                elif i.get("id") in (chapter.get("foreshadowing_plant") or []):
                    mark = " ← **この章で仕込む**"
                w("- %s [%s] (仕込み: 第%s章 / 期限: 第%s章) %s%s"
                  % (i.get("id"), i.get("status"), i.get("planted_in"), i.get("due_by"),
                     i.get("description", ""), mark))
            w("")

        dump("情報の非対称性(誰が何を知っているか)", os.path.join(paths["state"], "knowledge.yaml"),
             "キャラがまだ知らないはずの事実を口にさせないこと。")

        # タイムライン: この章以前のみ
        timeline = try_load(os.path.join(root, paths["canon"], "timeline.yaml")) or {}
        events = [e for e in (timeline.get("events") or []) if (e.get("chapter") or 0) <= n]
        if events:
            w("## タイムライン(これまで)")
            for e in events[-15:]:
                w("- 第%s章 / %s: %s" % (e.get("chapter"), e.get("t", "?"), e.get("event", "")))
            w("")

    # 前章の末尾(文体・場面の連続性)
    if n > 1:
        prev = os.path.join(root, paths["manuscript"], pattern.format(n=n - 1))
        t = read_text(prev)
        if t:
            w("## 前章の末尾(連続性の参照用)")
            w("```")
            w(t[-PREV_TAIL_CHARS:].strip())
            w("```")
            w("")

    body = "\n".join(out) + "\n"
    if args.stdout:
        sys.stdout.write(body)
        return 0
    os.makedirs(pack_dir, exist_ok=True)
    out_path = os.path.join(pack_dir, "ch%02d.md" % n)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(body)
    print("パック生成: %s" % os.path.relpath(out_path, root))
    print("mode: %s (canon合計 %d 字 / 閾値 %d 字)" % (mode, total, threshold))
    print("パックサイズ: %d 字 / 登場キャラ: %s" % (len(body), present_ids or "(未指定)"))
    if missing:
        print("警告: canon 未登録のキャラ id: %s" % missing)
    return 0


if __name__ == "__main__":
    sys.exit(main())
