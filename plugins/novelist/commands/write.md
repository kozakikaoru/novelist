---
description: 1章分の執筆パイプラインを実行する(パック生成 → writer 執筆 → 3監査並列 → 改稿)
argument-hint: "<章番号> [追加指示]"
---

第 $ARGUMENTS 章の執筆パイプラインをオーケストレーションする。あなた(メインエージェント)は執筆せず、進行役に徹する。

# パイプライン

## 1. コンテキストパック生成
```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/build_context_pack.py" <章番号> --project <プロジェクトルート>
```
- outline に章が無い/キャラ id 未登録の警告が出たら、**執筆に進まず**ユーザーに確認するか `/novelist:outline` を案内する。
- `state/character-state.yaml` の `as_of_chapter` が「前章の番号」より小さい場合は canon-sync 忘れ。先に `/novelist:canon-sync` を実行するようユーザーに提案する。

## 2. 執筆 — writer エージェントを起動
Agent tool で `novelist:writer` を起動(run_in_background: false)。プロンプトに渡すもの:
- コンテキストパックのパス / 原稿の出力先(config の manuscript_pattern に従う)
- 章番号と、ユーザーからの追加指示($ARGUMENTS の2つ目以降)
保存時に hook の自動 lint が走り、機械検出できる矛盾は writer がその場で直す。

## 3. 監査 — 3エージェントを並列起動
writer 完了後、**1つのメッセージで3つ同時に** Agent tool を呼ぶ:
- `novelist:continuity-auditor` — 章番号・原稿パスのみ渡す(**writer の意図や報告は渡さない**。本文と canon だけで判断させる)
- `novelist:style-auditor` — 章番号・原稿パス
- `novelist:foreshadow-keeper` — 章番号・原稿パス

## 4. 差し戻し判定
3つの監査報告を集約し、重複を除いて重大度順に並べる。
- 指摘(重大・中・口調・視点・伏線の未実施/先バラシ/予定外)があれば → writer に SendMessage で指摘一覧を渡して改稿させ、**改稿後に該当監査だけ再実行**する。このループは最大2周。2周して解消しない指摘は「未解決」としてユーザーに委ねる。
- 監査が「canon への疑義」を挙げた場合は、原稿の問題と区別してユーザーに報告する(canon の修正は人間の判断)。

## 5. ユーザーへの報告
以下をまとめて提示する:
- 章のあらすじと文字数、原稿パス
- 監査結果の要約(解消済み / 未解決)
- writer の **確定事実リスト** と **【新規】固有名詞リスト**
- 次のアクション: 内容を確認して問題なければ `/novelist:canon-sync <章番号>` を実行するよう案内(**canon-sync するまで、この章の新事実は canon に反映されず、次章で矛盾の種になる**ことを明記する)

# 注意

- 手順を省略しない。特に監査3体の並列起動と、指摘があるときの差し戻しは必須。
- あなた自身が原稿を直接書き換えない(修正は必ず writer 経由。監査の独立性を保つため)。
