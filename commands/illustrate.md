---
description: 挿絵プランを作成する(キャラ設定画=三面図のプロンプト + シーン挿絵のプロンプトを挿入場所付きで出力)
argument-hint: "[章番号|all|characters] [多め|少なめ]"
---

挿絵用の画像生成プロンプト一式を作成する。画像そのものは生成せず、画像生成AIに渡せるプランを納品する。

# 手順

## 1. 対象と設定の確認

- 対象: $ARGUMENTS から読み取る。指定が無ければ執筆済みの全章(`all`)。`characters` ならキャラ設定画のみ
- 初回(`illustrations/style.yaml` が無い)なら AskUserQuestion で**1回だけ**聞く:
  1. **枚数**: 多め(1章に1〜2枚) / 少なめ(2〜3章に1枚)
  2. **画風**: アニメ調 / 水彩・淡彩 / 劇画・リアル寄り / おまかせ(作品のトーンから提案)
  3. **想定ツール**(任意): Stable Diffusion系 / NovelAI / Midjourney / 特に決めてない — タグの書き方を最適化するため
- 回答から `illustrations/style.yaml` を作成する:
  ```yaml
  density: 少なめ            # 多め / 少なめ
  target_tool: ""
  art_style: ""              # 画風の言語化
  common_prompt: ""          # 全プロンプト共通の先頭タグ(画風・クオリティタグ)
  common_negative: ""        # 共通ネガティブプロンプト
  aspect:
    character_sheet: "3:2"
    scene: "2:3"             # 挿絵は縦長が基本(書籍想定)
  ```
- 2回目以降は style.yaml を読んで質問せずに進む(密度変更などの指示が $ARGUMENTS にあれば style.yaml を更新)

## 2. illustrator エージェントを起動

Agent tool で `novelist:illustrator` を起動し、対象・密度・style.yaml のパスを渡す。出力先:
- `illustrations/characters/<id>.md` — キャラクター設定画(三面図 + 表情集)のプロンプト。対象範囲の登場キャラ全員分
- `illustrations/scenes/chNN.md` — シーン挿絵のプロンプト。各項目に**挿入場所(章 + 本文引用 + 直前/直後)**を明記

## 3. マーカー挿入の確認

完了後、ユーザーに「原稿にマーカー(`<!-- illust: ID -->`)を挿入するか」を確認する。挿入すると:
- 表示には影響しない(HTMLコメント)
- `/novelist:compile` 時、`illustrations/` に同名の画像ファイル(ch03-1.png 等)が置いてあれば納品ファイルに自動で画像が埋め込まれる

## 4. 報告

- 設定画: キャラ一覧とファイルパス
- シーン挿絵: ID / 章 / 場面 / 挿入場所 の一覧表
- 生成した画像の置き場所の案内: 「`illustrations/ch03-1.png` のように ID 名で保存すれば compile が拾う」
- illustrator が「canon に外見情報が不足」と報告した場合は、canon への追記を提案する(外見の canon 未登録は挿絵と本文の矛盾リスクなので放置しない)
