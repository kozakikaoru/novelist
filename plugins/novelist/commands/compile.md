---
description: 執筆済みの全章を1つの納品ファイル(build/<タイトル>.md)に結合する
---

原稿を納品形式に結合する。

1. 実行:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/compile_manuscript.py" --project <プロジェクトルート>
   ```
2. 出力(収録章・合計文字数・欠けている章の警告)をユーザーに報告する。
3. 欠けている章が警告されたら、`/novelist:write <章番号>` で執筆できることを案内する。
