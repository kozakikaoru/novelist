---
description: 作品プロジェクトの雛形(canon/plot/state/manuscript)を現在のディレクトリに生成する
---

novelist の作品プロジェクトを初期化する。

1. 次を実行する(既存ファイルは上書きされない):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init_project.py" --project <プロジェクトのルート>
   ```
   プロジェクトのルートは、ユーザーが指定していなければカレントディレクトリ。
2. 生成されたファイル一覧をユーザーに見せ、構成を簡潔に説明する:
   - `canon/` = 正典(世界観・キャラ・用語・制約・タイムライン)
   - `plot/` = 章構成と伏線台帳
   - `state/` = 可変状態(現在地・負傷・知識)と lint 許可リスト
   - `manuscript/` = 原稿(保存のたびに自動 lint がかかる)
3. PyYAML の有無を確認する: `python3 -c "import yaml"` — 無ければ「YAML はテンプレートの書式(サブセット)を守る必要がある。`pip install pyyaml` を推奨」と伝える。
4. 次のステップとして `/novelist:interview`(設定の打ち合わせ)を案内する。
