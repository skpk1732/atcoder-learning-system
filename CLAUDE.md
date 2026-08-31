# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## このリポジトリは何か

kyosuke（大学生）の**Obsidianボルト**。PARA法（`1_Projects`／`2_Areas`／`3_Resources`／`4_Archives`）で構成され、ノートはすべて日本語。役割分担：

- **Claude Code（あなた）** = ビルダー兼学習コーチ。システム構築・AtCoder学習支援・ノート作成
- **Codex** = 独立レビュアー（`AGENTS.md` 参照）。Claudeが作ったシステムをレビューする

中心は `2_Areas/AtCoder/` の**AtCoder学習システム**（緑→水色レートが目標）。ユーザーはPython使用・提出はPyPy。学習の現在地は `2_Areas/AtCoder/レート目標と現状.md` が正、フェーズ計画は `緑水 最短ロードマップ.md`。**提案や助言の前に必ずこの2つを読む**。

## AtCoder学習システムの構造

3つのスキル＋1ツールのパイプライン：

```
/atcoder-daily → 問題を解く → /atcoder-record（精進記録作成）
                                   ↕
/atcoder-review latest ← tools/fetch_submission.py（提出コード取得）
```

- `.claude/skills/atcoder-daily` — レベルに合う問題提案。**テーマ・解法・ヒントは伏せる**（ユーザーの強い要望。型を見抜く練習のため。答え合わせは記録時）
- `.claude/skills/atcoder-record` — 精進記録ノートを `2_Areas/AtCoder/精進記録/` に作成
- `.claude/skills/atcoder-review` — 提出コードを複数エージェント（正確性/計算量/簡略化の3レンズ）で並行レビュー

### fetch_submission.py（提出取得ツール）

```powershell
# 日本語出力が化けるので毎回この環境変数を付ける
$env:PYTHONIOENCODING = "utf-8"
python 2_Areas/AtCoder/tools/fetch_submission.py                    # 最新の提出
python 2_Areas/AtCoder/tools/fetch_submission.py --problem abc129_c --ac  # 問題指定
python 2_Areas/AtCoder/tools/fetch_submission.py --index 1          # 1つ前
python 2_Areas/AtCoder/tools/fetch_submission.py --list --ac        # AC済み問題ID一覧（重複提案の回避に使う）
python 2_Areas/AtCoder/tools/fetch_submission.py --diff abc129_c    # 実測Difficulty照会（提案前に必ず）
python 2_Areas/AtCoder/tools/fetch_submission.py --url <提出URL>    # API未反映時の復旧（詳細ページから直接取得）
python 2_Areas/AtCoder/tools/fetch_submission.py --rating          # レート履歴（AtCoder公式API・Rated回）
```

既知の挙動（ハマりどころ）：
- **AtCoder Problems APIは提出直後の反映にラグがある**（数十分〜数時間）。直近の提出が見つからないときは、ユーザーに提出詳細ページのURLを貼ってもらい **`--url <提出URL>`** で直接取る（詳細ページは公開。**一覧ページはログイン必須**なのでスクレイピング不可）
- kenkoooo.comのWAFは `Accept-Encoding: gzip` が無いと403（対処済み・`BROWSER_HEADERS` 参照）
- 古いABC（〜126あたり）のC/DはARCと共有で problem_id が `arc086_a` 形式のことがある
- 検証は `python -m py_compile` ＋ 実通信テスト

## Obsidianノートの規約（違反すると表示が壊れる）

1. **フロントマターの tags に `#` を付けない**：`tags: [精進, AtCoder]`。`#` はYAMLコメント開始でDataview集計が壊れる（過去に30ノート修正した事故あり）
2. **地の文に裸の `==` を書かない**：Obsidianでは `==text==` がハイライト記法。`d==1` 等のコードは必ずバッククォートで囲む（意図的な蛍光ペンとしてのみ `==重要==` を使う）
3. wikilink `[[名前]]` はノートのファイル名と一致させる。`アルゴリズム` はフォルダでありノートではない（リンクにしない）
4. 精進記録の形式：テンプレ準拠＋「実際の提出コード（日付・結果・実行時間・提出URL）」＋「コードレビュー（3レンズ）」を末尾に追記。`#精進` タグでMOCのDataviewに集計される
5. 日付は `{{date}}` のまま残さず実日付に置換する（`テンプレート集.md` のコードブロック内のテンプレ定義は例外）
6. 末尾に `*最終更新: YYYY-MM-DD*` 行があるノートを編集したら、**その行も実日付に更新する**（放置しがちな箇所。ユーザー指摘済み 2026-07-29）

## Claude Codeの編集安定化ルール

- ファイル編集前は、直前に必ず対象ファイルをReadする。「前に読んだ文脈にある」は不可
- Editの `old_string` は短く、現在ファイルに確実に存在する連続部分にする。巨大なセクション丸ごと置換しない
- Editが失敗したら、同じ内容で再試行せず、対象ファイルをReadし直して小さい差分でやり直す
- 存在しないスクリプトや過去の設計を推測で実行しない。`rg --files` やReadで存在確認してから使う
- ツール呼び出し用のXMLやJSONをユーザー向け本文に貼らない。必要な変更はClaude Codeの実ツールで実行する

## 学習コーチとしての運用ルール（ユーザーと合意済み）

- **問題を解いた/コンテスト参加の報告があったら、言われなくても必ず①精進記録を残す ②`--diff`で実測Diffを取得 ③参加回なら`--rating`で新レートを取得してログ追記 ④ACコードのコードレビュー（3レンズ）を実施して記録に追記**（ユーザーの強い要望。①〜③は2026-07-19、④は2026-08-02に明示）
- **現フェーズはPhase 2（D中心期）**。2026-07-25にPhase 1（C完璧化）を卒業して移行済み（ABC468で初4完・茶色484・本人合意。経緯は `緑水 最短ロードマップ.md`）。主軸はD問題 Diff 400〜800＋緑コアアルゴ（BFS/DFS・Union-Find・EDPC）、計測付きC（Diff 400〜600・15分）は早解き磨き。フェーズを飛ばした水色帯の武器（セグ木・応用DP等）へは急がせない
- 問題提案時にテーマを明かさない（上述）。詰まったら**段階ヒント方式**（ヒント1=制約への着目 → ヒント2=道具 → ヒント3=骨組み）で、いきなり解説しない
- 解けなかった問題は翌日upsolve（自力で書き直し）を促す
- レビューのバグ指摘は**リファレンス実装とのストレステストで裏を取ってから**確定と呼ぶ。再現できないものは「要確認」
- **検証用の一時ファイルはscratchpadに作る**。ボルト（作業フォルダ）に何も残さない（エージェントへの指示にも明記する）

## Git運用

- `.gitignore` は**ホワイトリスト方式**：システム部分のみ管理（`.claude/`、`2_Areas/AtCoder/tools/`、`AGENTS.md`、`CLAUDE.md`）。Obsidianノートは管理外
- スキルが参照するObsidianノート（`2_Areas/AtCoder/` のノート類・`2_Areas/English/` など）は**意図的にローカル専用**。新規クローン環境ではスキルだけ存在し参照先ノートが無い、はこのボルトの仕様（ノートが無ければスキルは新規作成から始める）
- 一回限りのWorkflowスクリプトを `.claude/workflows/` に残さない（`.claude/` は管理対象なので誤コミットしやすい。使い捨てはscratchpadに置くか、役目を終えたら削除する）
- ローカル専用（コミット禁止）：`.claude/settings.local.json`、`tools/config.json`（個人のAtCoder ID。雛形は `config.example.json`）
- **Codexクロスレビューのフロー**：システムを変更 → commit → ユーザーがCodexに `git show HEAD` をレビューさせる → 指摘が貼られたら妥当性を検証（鵜呑みにしない）→ 妥当なものだけ修正 → commit
- コミットメッセージは日本語

## 英語学習システム（2_Areas/English/）

AtCoderと同じくInbox処理型で運用する。ユーザーが `2_Areas/English/英語Inbox.md` の `## 未処理` にある用途別欄へ書く:

- `### 知らない単語・表現`: 英単語・英語フレーズ。`#llm` があればカテゴリ `LLM/AI`
- `### 英語で言いたいこと`: 日本語で書いた「英語で言いたい内容」

処理は `/english-inbox-process` スキルで行う。常駐監視や自動実行ではない。Claude自身が意味・例文・自然な英訳を作り、`2_Areas/English/語彙・イディオム集.md` へ**チェックボックス行**として追記し、Inboxの処理済み行を削除する。

- 状態は2値のみ：チェックなし `- [ ]` = 未、チェックあり `- [x]` = 済（2026-07-26に旧4値の練習中/定着/要確認を廃止。怪しいものは行末メモに「要確認」と書く）
- 行形式: `- [ ] **表現**｜意味｜例: 例文｜カテゴリ｜メモ`（言いたいことは `- [ ] **言いたいこと**｜英: 自然な英語｜別: 代替表現｜カテゴリ｜メモ`）。区切りは全角 `｜`
- `未の表現一覧.md` がDataviewのTASKクエリで未チェック行だけを表示する。そこでチェックしても元ファイルに反映される
- `LLM英語用語集.md` は統合済みの案内ノート。新規追加先は常に `語彙・イディオム集.md`
- `英語学習ログTemplate.md` は廃止し `4_Archives/` へ移動済み（2026-07-26）
- English関連ノート以外は触らない

## その他

- `1_Projects/hit-u_help_AI/` は独立プロジェクトで専用の `CLAUDE.md` を持つ。そちらの作業ではそちらに従う
- ユーザーへの応答は日本語。競プロのコード例はPython（PyPy前提）
