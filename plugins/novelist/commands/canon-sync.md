---
description: 確定した章から新事実を canon/state/台帳へ昇格させる(章確定のたびに必須)
argument-hint: "<章番号>"
---

第 $ARGUMENTS 章の内容を正典に反映する。**本文で書いた事実そのものが新しい設定になる** — この昇格を怠ると、次章以降のコンテキストパックに新事実が載らず、必ず矛盾の種になる。

# 手順

1. 対象章の原稿が存在することを確認する。直前の `/novelist:write` の会話に writer の「確定事実リスト」「【新規】固有名詞リスト」があれば控えておく。
2. Agent tool で `novelist:canon-updater` を起動し、章番号・原稿パス・(あれば)writer のリストを渡す。
3. 完了後、更新記録をユーザーに提示する。特に:
   - **要人間判断**(canon と本文の食い違い)が挙がっていたら、ユーザーに選択を求め、決定に従って canon か原稿を修正する
   - 原稿を直す場合は writer エージェント経由で行い、保存時の自動 lint に通す
4. 反映後の確認:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lint_manuscript.py" <この章の原稿> --project <プロジェクトルート>
   ```
   新規固有名詞が glossary に登録されたので、未登録警告が消えているはず。残っていれば canon-updater の登録漏れ — 追加登録させる。
5. git 管理下なら `git status` / `git diff --stat` で変更ファイルを見せ、コミットを提案する(勝手にコミットしない)。
