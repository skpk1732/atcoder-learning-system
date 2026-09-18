---
name: paper-read
description: 論文（主にarXiv）の逐語訳HTML（対訳ページ）を作成し、論文読みを効率化する。ユーザーが「この論文を対訳にして」「論文の逐語訳HTMLを作って」「論文読むの手伝って」などと言ったとき、または /paper-read で起動。引数としてarXivのURL・ID、またはローカルPDFのパスを受け取れる。
---

# 論文の逐語訳HTML作成

英語論文を、原文ブロック＋日本語逐語訳を縦に積んだHTMLに変換するスキル。
**訳すだけで、解釈はしない**——要約・解釈・重要度判断はすべてユーザー（人間）が行う。これはユーザーの明示的な要望（2026-07-21合意）。

## 🔴 絶対条件（ユーザー合意済み・変更しない）

1. **逐語訳**：全文を文単位で忠実に訳す。要約・省略・意訳・補足コメント・重要マーク（`==` 蛍光ペン等）は一切加えない
2. **図表はそのまま**：図の画像は原文のまま埋め込む。表も原文の内容のまま再現。キャプションのみ「原文＋訳」を併記
3. **主要な専門用語は英語のまま**：benchmark / annotator / prompt / fine-tuning / hallucination 等の術語は訳さず英語表記で埋め込む（一般語は日本語に訳す）。論文固有のキー概念（提案手法名・データセット名・評価指標名）も英語のまま
4. **レイアウトはブロック縦積み**：適当な長さのブロック（基本は原文の1段落。長すぎれば文境界で2〜3分割）ごとに、原文→訳の順で縦に並べる。左右2カラムにはしない

## 入力と保存先

- 入力：arXiv URL / arXiv ID / ローカルPDFパス。無ければ「どの論文ですか?（arXiv URLかPDFパス）」と1つだけ質問
- 保存先：`1_Projects/<研究プロジェクト>/06_論文対訳/<arxiv_id または短いslug>/index.html`（実際のプロジェクト名はローカルの CLAUDE.md を参照）
  - 別プロジェクトの論文だと分かる場合はそのプロジェクト配下の `論文対訳/` に置く
  - 画像は同フォルダの `figs/`、取得したソースHTMLも同フォルダに残す（再翻訳・検証用）
- 一時ファイル（動作確認など）はscratchpadに作る。ボルトには成果物以外を残さない

## 手順

### 1. ソース取得

```powershell
$env:PYTHONIOENCODING = "utf-8"
python .claude/skills/paper-read/tools/fetch_arxiv.py <arXiv ID or URL> --out "1_Projects/<研究プロジェクト>/06_論文対訳/<id>"
```

- arxiv.org/html → ar5iv の順で試し、画像を `figs/` にローカル保存、翻訳用の `source_clean.html` を生成する
- スクリプトが最後に出す**見出し一覧は完了チェックに使うので控えておく**
- HTML版が無い論文（両方404）は PDF で作業：
  - `python .claude/skills/paper-read/tools/fetch_arxiv.py --pdf <PDFパス> --out <出力フォルダ>` で図を抽出（要 pymupdf）
  - 本文は Read ツールでPDFを直接読む（20ページずつ）。PDFは `03_論文PDF/` にあるか、arXivの `/pdf/<id>` から取得

### 2. 出力ファイルの初期化

`.claude/skills/paper-read/assets/template.html` をコピーして `index.html` を作り、`{{TITLE}}`（原題）・`{{AUTHORS}}`・`{{URL}}`・`{{DATE}}`（実日付）を置換する。
本文ブロックは `<!-- END_OF_CONTENT -->` マーカーの**直前**に追記していく。

### 3. セクション単位で翻訳して追記

`source_clean.html` をセクションごとに読み、以下のマークアップで `index.html` に追記する。長い論文は TaskCreate でセクションの進捗を管理する。

```html
<section>
<h2><span class="en-head">3 Experimental Setup</span><span class="ja-head">3 実験設定</span></h2>
<div class="block">
  <p class="en">We presented 120 reasoning tasks to five LLMs ...</p>
  <p class="ja">我々は5つのLLMに120件のreasoningタスクを提示し…</p>
</div>
</section>
```

- 見出しは h2/h3 に原文＋訳を併記（テンプレートのCSS・目次生成がこの構造に依存）
- 数式は原文の `<math>` 要素（MathML）をそのままコピーして訳文中の対応位置に埋め込む。変数名・記号は一切変えない
- 図：`<figure><img src="figs/fig_XX.png"><figcaption><span class="en">原文キャプション</span><span class="ja">訳</span></figcaption></figure>`。本文中の元の位置に置く
- 表：`<div class="table-wrap"><table>…</table></div>` で原文のまま再現（数値・ヘッダとも訳さない）。キャプションのみ figcaption と同様に対訳
- 脚注は該当ブロックの直後に `<p class="en">` / `<p class="ja">` で小さく入れる
- **References は訳さない**。`<details class="references"><summary>References（原文のまま）</summary>…</details>` に原文リストを格納
- **Appendix はデフォルトで訳さない**。末尾に「Appendix A〜C は未訳（必要なら指示してください）」と明記する。ユーザーが求めたら追記
- インラインの引用番号 `[12]` や図表参照 `(Figure 2)` は原文の形のまま残す

### 4. 長い論文はサブエージェントに分担させてよい

セクション数が多い場合、general-purpose エージェントに「source_clean.html の該当セクションを読み、上記マークアップのHTML断片だけを返す」タスクを並行で投げてよい。その際：
- 本スキルの「🔴 絶対条件」と手順3のマークアップ規則を**プロンプトに全文コピーする**
- 一時ファイルを作るならscratchpadを使うよう指示する
- 返ってきた断片は必ず自分で抜き取り確認（原文段落の欠落・要約化がないか）してから追記する

### 5. 完了チェック（必ずやる）

1. 手順1で控えた**見出し一覧のすべて**が index.html に存在するか照合する（Grepで確認）
2. `figs/` の画像枚数と `index.html` 内の `<img` の数が一致するか確認する
3. ブラウザで開いて表示確認：`Invoke-Item <index.htmlのパス>`（少なくとも1回は開いて崩れがないか見る）
4. 訳し残し（`.en` だけで `.ja` が無いブロック）が無いか確認する

### 6. 完了報告

- index.html のフルパスと、未訳部分（References / Appendix）の明示
- `02_論文リスト/references.bib`・`論文リスト.xlsx` への登録は**しない**（ユーザー管理）。未登録らしければ一言添えるだけ

## 方針

- 訳注は原則付けない。多義語でどうしても決められない場合のみ `〔訳注: 原語 laughter は…〕` 形式で最小限（解釈は書かない）
- 品質より完走を優先しない：**段落の欠落は事故**。迷ったら必ず原文を残す
- コンテキストが苦しくなったら、途中まで追記済みの index.html と残セクション一覧を報告してから続きを別ターンで行う（ファイルに追記済みなので再開可能）
