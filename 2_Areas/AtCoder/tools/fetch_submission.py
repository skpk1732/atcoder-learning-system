"""AtCoderの提出記録から最新の提出コードを取得するツール。

使い方:
    python fetch_submission.py                  # config.json のユーザー名で最新の提出を取得
    python fetch_submission.py --user kyosuke   # ユーザー名を指定
    python fetch_submission.py --ac             # 最新の「AC」提出に限定
    python fetch_submission.py --index 1        # 最新から1つ前の提出

動作:
    1. AtCoder Problems API から提出一覧を取得
    2. 最新（または指定）の提出の詳細ページからコード本文を抽出
    3. 提出コード/ フォルダに保存し、メタ情報とパスを表示
"""

import argparse
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

API_URL = "https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions?user={user}&from_second={from_second}"
SUBMISSION_URL = "https://atcoder.jp/contests/{contest_id}/submissions/{submission_id}"

# kenkoooo.com のWAFはブラウザ相当のヘッダを要求する。
# 特に Accept-Encoding が urllib 既定の identity だと 403 になる（gzip 必須）。
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip",
    "Accept-Language": "ja",
    "Referer": "https://kenkoooo.com/atcoder/",
}

TOOLS_DIR = Path(__file__).resolve().parent
CONFIG_PATH = TOOLS_DIR / "config.json"
SAVE_DIR = TOOLS_DIR.parent / "提出コード"

EXT_BY_LANGUAGE = {
    "python": ".py",
    "pypy": ".py",
    "c++": ".cpp",
    "rust": ".rs",
    "java": ".java",
    "c#": ".cs",
    "go": ".go",
    "ruby": ".rb",
    "kotlin": ".kt",
}


def http_get(url: str) -> bytes:
    headers = dict(BROWSER_HEADERS)
    if "atcoder.jp" in url:
        headers["Referer"] = "https://atcoder.jp/"
        headers["Accept"] = "text/html,application/xhtml+xml,*/*;q=0.8"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as res:
        body = res.read()
        if res.headers.get("Content-Encoding") == "gzip":
            import gzip
            body = gzip.decompress(body)
        return body


def load_username(cli_user: str | None) -> str:
    if cli_user:
        return cli_user
    if CONFIG_PATH.exists():
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        user = config.get("username", "").strip()
        if user and user != "YOUR_ATCODER_ID":
            return user
    sys.exit(
        "AtCoderのユーザー名が未設定です。\n"
        f"  {CONFIG_PATH} の username を設定するか、--user <ID> で指定してください。"
    )


def fetch_submissions(user: str, from_second: int = 0) -> list[dict]:
    """from_second 以降の提出を取得（新しい順に並べ替えて返す）。

    ページ数に上限を設けて提出数が極端に多いユーザーでも暴走しないようにする。
    """
    submissions: list[dict] = []
    cursor = from_second
    for _ in range(40):  # 最大 40ページ × 500件
        data = json.loads(http_get(API_URL.format(user=user, from_second=cursor)))
        if not data:
            break
        submissions.extend(data)
        if len(data) < 500:  # APIは1回最大500件
            break
        cursor = max(s["epoch_second"] for s in data) + 1
        time.sleep(1)  # API負荷への配慮
    submissions.sort(key=lambda s: s["epoch_second"], reverse=True)
    return submissions


def fetch_code(contest_id: str, submission_id: int) -> str:
    url = SUBMISSION_URL.format(contest_id=contest_id, submission_id=submission_id)
    page = http_get(url).decode("utf-8", errors="replace")
    m = re.search(r'<pre id="submission-code"[^>]*>(.*?)</pre>', page, re.DOTALL)
    if not m:
        sys.exit(f"コード本文を抽出できませんでした: {url}")
    return html.unescape(m.group(1))


def pick_extension(language: str) -> str:
    lang = language.lower()
    for key, ext in EXT_BY_LANGUAGE.items():
        if key in lang:
            return ext
    return ".txt"


def main() -> None:
    parser = argparse.ArgumentParser(description="AtCoderの最新提出コードを取得")
    parser.add_argument("--user", help="AtCoderユーザーID（省略時はconfig.json）")
    parser.add_argument("--ac", action="store_true", help="AC提出に限定する")
    parser.add_argument("--index", type=int, default=0, help="最新から何番目か（0=最新）")
    parser.add_argument("--problem", help="問題IDを指定（例: abc129_c）。その問題の最新提出を取る")
    parser.add_argument("--list", action="store_true", help="提出済み問題IDの一覧を表示して終了（コード取得はしない）")
    args = parser.parse_args()

    user = load_username(args.user)

    if args.list:
        # 全履歴から問題IDを列挙（--ac でAC済みに限定）。重複提案の回避などに使う
        subs = fetch_submissions(user)
        if args.ac:
            subs = [s for s in subs if s["result"] == "AC"]
        seen: dict[str, str] = {}
        for s in subs:  # 新しい順なので最初に見えたものが最新
            seen.setdefault(s["problem_id"], s["result"])
        for pid in sorted(seen):
            print(pid)
        return

    def matching(subs: list[dict]) -> list[dict]:
        if args.ac:
            subs = [s for s in subs if s["result"] == "AC"]
        if args.problem:
            subs = [s for s in subs if s["problem_id"] == args.problem.lower()]
        return subs

    # まず直近90日を検索し、条件に合う提出が足りなければ全履歴に遡る
    # （古い問題の --problem 指定でもフォールバックで見つかるように）
    submissions = matching(fetch_submissions(user, int(time.time()) - 90 * 24 * 3600))
    if len(submissions) <= args.index:
        time.sleep(1)  # API負荷への配慮
        submissions = matching(fetch_submissions(user))
    if not submissions:
        sys.exit(f"提出が見つかりませんでした（user={user}, ac_only={args.ac}, problem={args.problem}）")
    if args.index >= len(submissions):
        sys.exit(f"条件に合う提出は{len(submissions)}件しかありません（--index {args.index}）")

    sub = submissions[args.index]
    code = fetch_code(sub["contest_id"], sub["id"])

    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    ext = pick_extension(sub["language"])
    save_path = SAVE_DIR / f"{sub['problem_id']}_{sub['id']}{ext}"
    save_path.write_text(code, encoding="utf-8", newline="\n")

    meta = {
        "user": user,
        "problem_id": sub["problem_id"],
        "contest_id": sub["contest_id"],
        "problem_url": f"https://atcoder.jp/contests/{sub['contest_id']}/tasks/{sub['problem_id']}",
        "submission_url": SUBMISSION_URL.format(contest_id=sub["contest_id"], submission_id=sub["id"]),
        "result": sub["result"],
        "language": sub["language"],
        "execution_time_ms": sub.get("execution_time"),
        "code_length": sub["length"],
        "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(sub["epoch_second"])),
        "saved_to": str(save_path),
    }
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
