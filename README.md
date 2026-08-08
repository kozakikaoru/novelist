# novelist — 設定矛盾を防ぐ小説執筆支援プラグイン

Claude Code 用プラグイン。作品設定を綿密にヒアリングして **canon(正典)** として書き起こし、それを基に**複数エージェント**(執筆・整合性監査・文体監査・伏線管理・正典更新)と**決定論的 lint(hook)** を組み合わせて執筆する。

「序盤で青い目と紹介したキャラが後半で赤い目になる」「口調が章ごとに変わる」「伏線の回収忘れ」——AI 執筆で起きがちな設定矛盾を、仕組みで防ぐことが目的。

## 設計思想: 3層防御

「設定ファイルを用意しても AI は全部に目を通すとは限らない」という前提に立ち、単一の仕組みに頼らない。

| 層 | 手段 | 効くもの | LLM 依存 |
|---|---|---|---|
| 1 | コンテキストパック(章ごとに canon を機械抽出) | 読み落とし全般 | 低 |
| 2 | hook + lint スクリプト(保存のたび必ず発火) | 表記ゆれ・禁止語彙・属性違反・未登録固有名詞・死亡キャラ発話 | **ゼロ** |
| 3 | 監査エージェント3体(執筆者とは独立) | 文脈依存の矛盾・口調・視点・伏線 | 高 |

### 「絞る」のではなく「解像度を変える」

コンテキストパックは登場キャラだけに範囲を切るのではない。**全キャラの1行サマリ(表記・生死・現在地・特筆能力)と、制約(禁じ手)・用語集は常時フルロード**し、その章で使わない“詳細”(生い立ちの長文など)だけを畳む。登場しないキャラが会話に出てきても、表記や生死は崩れない。

さらに canon 合計が閾値(既定 60,000 字)未満のうちは絞り込み自体を行わず**全文投入**する(full モード)。絞り込みは canon が育ってからの最適化。

### 制約(禁じ手リスト) — `canon/constraints.yaml`

「登場しないキャラ A が存在すると起こりえない事象」はキャラシートを何行にしても防げない。これは A の属性ではなく**世界にかかる制約**なので、独立した台帳に否定形で書く:

```yaml
- id: C001
  rule: "レンは嘘を見抜ける。レンが同席する場面で、欺瞞が成功する展開は成立しない"
  holds_while: "レンがその場に同席している間"
  involves: [ren]
```

これはパックに常時フルロードされ、writer は場面を書く前に、continuity-auditor は監査時に全件照合する。

### 執筆者と監査者でコンテキスト戦略を逆にする

- **writer**: パックだけを読む(生成の精度優先)。自分の書いた本文を正しいと思い込む自己整合バイアスを避けるため、監査は行わない
- **continuity-auditor**: **canon 全体を読む**(見落としの回収優先)。確定した本文に実際に出た固有名詞から canon を**逆引き**するので、予定外に登場したものも捕捉できる。執筆意図は知らされない

### 本文 → canon の還流(canon-sync)

矛盾の半分は「設定に書いてないことを本文で書き、それが記録されない」ことから生まれる。**書いた本文そのものが新しい設定**なので、章が確定するたび canon-updater が新事実(負傷・移動・誰が何を知ったか・新固有名詞・伏線の回収)を canon / state / 台帳へ昇格させる。これを怠ると次章のパックに新事実が載らない。`/novelist:status` が sync 忘れを検出する。

## インストール

```
/plugin marketplace add kozakikaoru/novelist
/plugin install novelist@novelist
```

YAML の読み込みに PyYAML があると堅牢(無ければテンプレートの書式サブセットのみ対応の内蔵パーサで動く)。推奨: `pip install pyyaml`

## 使い方(ワークフロー)

```
/novelist:init        # 作品プロジェクトの雛形生成
/novelist:interview   # 設定の打ち合わせ → canon に書き起こし(対話)
/novelist:outline     # 章構成・伏線設計(対話)
/novelist:write 1     # 第1章の執筆パイプライン
/novelist:canon-sync 1  # 承認後、新事実を canon へ昇格
/novelist:write 2     # 以下繰り返し
/novelist:status      # 進捗・伏線期限・sync忘れの診断
/novelist:check 3     # 既存章の監査だけ実行(執筆なし)
```

`/novelist:write N` の内部パイプライン:

```
① build_context_pack.py N   canon から章のパックを機械生成
② writer                    パックだけを見て執筆
③ hook (自動)               保存のたび lint。機械検出できる矛盾は即差し戻し
④ 監査3体を並列起動          continuity / style / foreshadow(独立・読み取り専用)
⑤ 指摘を writer に戻して改稿(最大2周)
⑥ ユーザー確認 → /novelist:canon-sync N
```

## 作品側のファイル構成

```
novel.config.yaml         # パス・閾値・lint 設定
canon/                    # 正典(不変の事実)
  world.yaml              #   世界観・絶対ルール・禁止語彙
  style.yaml              #   文体・視点ルール
  characters/<id>.yaml    #   1キャラ1ファイル。invariants / speech / 1行summary / lint.forbid
  glossary.yaml           #   固有名詞の正典表記 + 誤表記(variants)
  constraints.yaml        #   禁じ手リスト(常時フルロード)
  timeline.yaml           #   確定した時系列
plot/
  outline.yaml            #   章構成(pov / 登場キャラ / 仕込み・回収する伏線)
  foreshadowing.yaml      #   伏線台帳(planted / due_by / resolved)
state/                    # 可変状態(canon-sync で更新)
  character-state.yaml    #   現在地・負傷・所持品(as_of_chapter で sync 忘れ検出)
  knowledge.yaml          #   誰が何を知っているか(情報の非対称性)
  lint-allowlist.txt      #   作品固有の一般カタカナ語の許可リスト
  context-pack/           #   生成物(パック)
manuscript/chNN.md        # 原稿(保存のたび自動 lint)
```

## lint が機械検出するもの(hook で保存のたび必ず実行)

| 検出 | 根拠 | 重大度 |
|---|---|---|
| 表記ゆれ(誤表記の使用) | glossary の variants | ERROR |
| 禁止語彙(世界観外の語) | world の banned_words | ERROR |
| キャラ属性違反(例: 近傍に「アオイ」がある「赤い瞳」) | characters の lint.forbid(正規表現 + near) | ERROR |
| 未登録カタカナ語(canon に無い固有名詞の混入) | canon 全文 + 同梱一般語リスト + allowlist | WARN |
| 死亡キャラの発話疑い | status: dead + 直後の鉤括弧 | WARN |

未登録カタカナ語の運用: 意図した新固有名詞なら `canon/glossary.yaml` に登録、一般名詞なら `state/lint-allowlist.txt` に1行追加。

## 制限事項

- 漢字の固有名詞(人名・地名)の「未登録検出」は機械的には行えない(カタカナのみ)。漢字名の検証は continuity-auditor の逆引き監査が担う
- 内蔵 YAML パーサはテンプレートの書式サブセットのみ対応。凝った YAML を書くなら PyYAML を入れること
- lint は決定論ゆえに文脈を読まない(回想シーンでの死亡キャラ発話も警告する)。WARN は「確認せよ」であって「必ず誤り」ではない
