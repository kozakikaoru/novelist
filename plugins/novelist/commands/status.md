---
description: 執筆状況ダッシュボード(進捗・伏線の期限・canon-sync 忘れ・健全性)
---

作品の現在状態を診断して報告する。ファイルは編集しない。

# 収集するもの

1. `plot/outline.yaml` と `manuscript/` を突き合わせ: 計画章数 / 執筆済み章数 / 次に書く章
2. `state/character-state.yaml` の `as_of_chapter` と執筆済み最新章を比較:
   **as_of_chapter < 最新章 なら canon-sync 忘れ。強調して警告し、`/novelist:canon-sync` を案内する**
3. `plot/foreshadowing.yaml`: 未回収伏線の一覧。とくに `due_by` が「次に書く章」以前のもの = **期限切れ・期限間近**として強調
4. `canon/characters/`: キャラ数、`summary` が空のキャラ(1行サマリ欠落は解像度可変モードの穴になる)、`speech.examples` が空のキャラ
5. `canon/constraints.yaml` が空なら「禁じ手リスト未整備」と警告(interview のフェーズ5を案内)
6. 執筆済み全章に機械 lint:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lint_manuscript.py" <全原稿> --project <ルート>
   ```
7. 文字数の実測(writer の自己申告ではなくこれを使う):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/count_chars.py" --project <ルート>
   ```
   outline に target_chars / target_total_chars があれば差分も出る
8. canon 合計文字数と閾値(novel.config.yaml)から、現在のパック mode(full / layered)を表示

# 報告フォーマット

```
# 執筆状況
- 進捗: 5/20章 (次: 第6章)
- パック mode: full (canon 24,300字 / 閾値 60,000字)

## ⚠ 要対応
- canon-sync 忘れ: state は第4章時点、原稿は第5章まで → /novelist:canon-sync 5
- 伏線 F002: 期限 第4章を超過(未回収)

## 伏線
- 未回収 3件 (F002 超過, F005 期限第8章, F007 期限第15章)

## canon 健全性
- summary 空: (なし) / speech.examples 空: mob_01
- lint: 全章クリーン
```
