# AtCoder学習システム（Claude Code スキル群）

![CI](https://github.com/skpk1732/atcoder-learning-system/actions/workflows/ci.yml/badge.svg)

AtCoderのレート向上（茶色 → 緑 → 水色）を目的に、**Claude Code のスキル＋Pythonツール**で構築した個人用学習システム。Obsidianボルト（PKM）の上で動作し、問題提案 → 演習 → 精進記録 → コードレビューのサイクルを半自動化している。

> このリポジトリはObsidianボルトのシステム部分（スキル・ツール）のみをホワイトリスト方式で管理したもの。学習ノート本体はローカル専用（`.gitignore` 参照）。

## システム構成

3つのスキル＋1ツールのパイプライン：

```
/atcoder-daily ──→ 問題を解く ──→ /atcoder-record（精進記録作成）
      │                                  ↕
      └─ 実測Diff照会                /atcoder-review ←─ tools/fetch_submission.py
         （提案前に必須）            （3レンズ並行レビュー）      （提出コード取得）
```

| コンポーネント | 役割 |
|---|---|
| `.claude/skills/atcoder-daily` | 現在のレート・フェーズに合う問題を提案。**テーマ・解法は伏せる**（型を見抜く訓練のため）。AC済み問題の重複提案を回避し、提案前に実測Difficultyを必ず照会 |
| `.claude/skills/atcoder-record` | 精進記録ノートを作成。提出コード・実行時間・実測Diff・レビュー結果まで一括記録 |
| `.claude/skills/atcoder-review` | 提出コードを複数エージェントで並行レビュー（正確性 / 計算量 / 簡略化の3レンズ）。バグ指摘はリファレンス実装とのストレステストで裏取りしてから確定 |
| `.claude/skills/english-inbox-process` | （おまけ）英語学習のInbox処理。未知の表現に意味・例文を付けて語彙集へ追記 |
| `.claude/skills/paper-read` | （おまけ）arXiv論文の逐語訳HTML（対訳ページ）を生成 |
| `2_Areas/AtCoder/tools/fetch_submission.py` | AtCoder Problems API / 公式APIから提出・Difficulty・レート履歴を取得するCLIツール |
| `2_Areas/AtCoder/snippets.py` | コンテスト用コピペスニペット集（Union-Find・BFS/DFS・二分探索など） |

## fetch_submission.py の機能

```powershell
$env:PYTHONIOENCODING = "utf-8"   # Windows環境での文字化け対策
python 2_Areas/AtCoder/tools/fetch_submission.py                    # 最新の提出を取得
python 2_Areas/AtCoder/tools/fetch_submission.py --problem abc129_c --ac  # 問題指定でAC提出を取得
python 2_Areas/AtCoder/tools/fetch_submission.py --list --ac        # AC済み問題ID一覧（重複提案の回避）
python 2_Areas/AtCoder/tools/fetch_submission.py --diff abc129_c    # 実測Difficulty照会（7日キャッシュ）
python 2_Areas/AtCoder/tools/fetch_submission.py --url <提出URL>    # API未反映時に提出詳細ページから直接取得
python 2_Areas/AtCoder/tools/fetch_submission.py --rating           # レート履歴（公式API・Rated回）
```

実装上の工夫：

- **APIラグ対策**: AtCoder Problems APIは提出直後の反映に数十分〜数時間かかるため、提出詳細ページ（公開）から直接取得する `--url` フォールバックを用意
- **WAF対策**: kenkoooo.com は `Accept-Encoding: gzip` が無いと403を返すため、ブラウザ相当のヘッダを送信
- **推定Diffの排除**: LLMの記憶によるDifficulty推定は±200以上ズレた実績があるため、提案前の実測照会をスキル側で強制

## 開発プロセス（バイブコーディング＋クロスレビュー）

このシステムは **Claude Code との対話（バイブコーディング）** で構築し、品質担保に**独立レビュアーとのクロスレビュー体制**を採用している：

1. Claude Code がスキル・ツールを実装 → 日本語メッセージでcommit
2. 別のAIエージェント（Codex）が `git show HEAD` をレビュー
3. 指摘の妥当性を検証（鵜呑みにしない。バグ指摘はストレステストで再現確認）
4. 妥当な指摘のみ修正してcommit

コミット履歴にこの往復（`Codexレビュー第N弾の指摘を修正` 等）がそのまま残っている。

## セットアップ

```powershell
# 個人設定（AtCoder ID）は雛形からコピーして作成（config.json はgit管理外）
cp 2_Areas/AtCoder/tools/config.example.json 2_Areas/AtCoder/tools/config.json
# config.json の "user_id" を自分のAtCoder IDに書き換える
```

- 必要環境: Python 3.x（標準ライブラリのみ・外部依存なし）＋ Claude Code
- スキルが参照するObsidianノート（レート目標・ロードマップ・精進記録）はローカル専用。新規クローン環境ではスキルが新規作成から始める仕様

## 運用ルール

- **git管理はホワイトリスト方式**：スキル・ツールなどシステム部分のみを公開し、学習ノート・個人設定はローカル専用
- **PRワークフロー＋CI**：システム変更はブランチ → PR → CI（py_compile＋pytest）通過 → マージで運用
- **クロスレビュー体制**：Claude Codeが実装し、独立レビュアー（Codex）が `git show HEAD` ベースでレビュー。レビュアー向け指示は [AGENTS.md](AGENTS.md) を参照
- Claude Code向けの指示書（CLAUDE.md）は個人の学習状況・進行中プロジェクトの情報を含むため**ローカル専用**とし、このリポジトリには含めていない
