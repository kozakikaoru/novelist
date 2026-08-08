---
description: 章構成と伏線設計の打ち合わせ。plot/outline.yaml と plot/foreshadowing.yaml を作る
argument-hint: "[章番号や補足指示]"
---

ユーザーと章構成を設計し、`plot/outline.yaml` と `plot/foreshadowing.yaml` に書き起こす。

# 前提

- `canon/` が概ね埋まっていること。空同然なら先に `/novelist:interview` を案内する。
- 既に outline がある場合は読み込み、追加・修正だけを扱う。$ARGUMENTS があればそれに従う。

# 進め方

1. **全体構成**: 章数の目安、大きな流れ(起承転結・三幕など)、結末をユーザーと確認する。
2. **伏線の設計** → `plot/foreshadowing.yaml`:
   物語の核となる謎・どんでん返しを聞き出し、伏線として台帳化する。各項目に必ず:
   - `description`(何を匂わせるか)と `payoff`(どう回収するか)
   - `planted_in`(仕込む章)と `due_by`(回収期限の章)
   **due_by の無い伏線を作らない。** 回収忘れ検出はこの期限が頼り。
3. **各章の設計** → `plot/outline.yaml`: 章ごとに
   - `pov`(視点キャラ id)/ `characters`(**登場キャラの id を全部**。台詞が無くても居るなら書く)/ `locations`
   - `summary`(起きること・章の終わりの状態)
   - `foreshadowing_plant` / `foreshadowing_resolve`(台帳の id で)
4. **整合チェック**(書き終えたら必ず):
   - 台帳の全伏線が、どこかの章の plant に載っているか
   - due_by までに resolve する章が計画されているか
   - characters の id が canon/characters/ に実在するか
   - constraints に照らして不可能な展開が計画されていないか(例: 嘘を見抜くキャラの同席場面で騙し計画)
   問題があればユーザーに提示して解決してから確定する。

# 終了時

章一覧(番号・タイトル・視点・一言)と伏線の仕込み/回収マップを提示し、`/novelist:write <章番号>` で執筆開始できることを案内する。
