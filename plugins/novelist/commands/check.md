---
description: 既存原稿の監査だけを実行する(執筆なし)。章番号指定または all
argument-hint: "<章番号|all>"
---

既存の原稿に対して監査を実行する。執筆・修正は行わず、報告のみ。

# 手順

1. 対象を決める: $ARGUMENTS が数値ならその章、`all` なら manuscript/ にある全章。
2. **機械 lint** を先に回す:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lint_manuscript.py" <対象ファイル...> --project <プロジェクトルート>
   ```
3. **監査エージェント4体を並列起動**(1メッセージで同時に):
   `novelist:continuity-auditor` / `novelist:style-auditor` / `novelist:foreshadow-keeper` / `novelist:plausibility-auditor`
   それぞれに対象章番号と原稿パスを渡す。`all` の場合も一括で全章分を各監査に渡してよい(章ごとに分けて報告させる)。
4. 結果を集約して報告する:
   - lint の指摘(機械検出)と監査の指摘(文脈検出)を分けて、重大度順に列挙。説得力監査の指摘は「要確認」として別枠にする(主観的判断を含むため)
   - 修正するかはユーザーの判断に委ねる。修正指示が出たら `/novelist:write` の差し戻しと同様に writer エージェント経由で行う
5. 何も指摘が無ければ「全チェック通過」と報告する。

原稿・canon を一切編集しないこと。
