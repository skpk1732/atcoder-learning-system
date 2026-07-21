#!/usr/bin/env python3
"""arXiv論文のHTML版を取得し、対訳HTML作成の下ごしらえをするツール。

やること:
1. arXiv ID/URLから HTML版（arxiv.org/html → ar5iv の順）を取得
2. 本文中の画像を figs/ にローカル保存し、参照をローカルパスに書き換え
3. 翻訳作業用に属性を削ぎ落とした source_clean.html を生成（MathMLは保持）
4. タイトル・見出し一覧・画像枚数のサマリを表示

使い方:
    python fetch_arxiv.py 2402.01234 --out <出力フォルダ>
    python fetch_arxiv.py https://arxiv.org/abs/2402.01234 --out <出力フォルダ>
    python fetch_arxiv.py --pdf paper.pdf --out <出力フォルダ>   # HTML版が無い論文の図抽出

注意: 日本語出力が化けるので $env:PYTHONIOENCODING = "utf-8" を付けて実行する。
"""

import argparse
import gzip
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
}

ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")


def normalize_arxiv_id(text: str) -> str:
    """URLやIDの文字列から arXiv ID（バージョン付き可）を取り出す。"""
    m = ARXIV_ID_RE.search(text)
    if not m:
        raise ValueError(f"arXiv IDを認識できません: {text}")
    return m.group(1) + (m.group(2) or "")


def fetch(url: str, timeout: int = 60) -> tuple[bytes, str]:
    """URLを取得し (データ, リダイレクト後の最終URL) を返す。"""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
        return data, resp.geturl()


def fetch_html(arxiv_id: str) -> tuple[str, str]:
    """HTML版を取得。(最終URL, HTML文字列) を返す。"""
    candidates = [
        f"https://arxiv.org/html/{arxiv_id}",
        f"https://ar5iv.labs.arxiv.org/html/{arxiv_id}",
    ]
    errors = []
    for url in candidates:
        try:
            data, final_url = fetch(url)
            html = data.decode("utf-8", errors="replace")
            # ar5ivは論文が無いとトップページ的なHTMLを返すことがあるので本文の存在を確認
            if "ltx_page_main" in html or "ltx_document" in html or "<article" in html:
                return final_url, html
            errors.append(f"{url}: 論文本文が見つからない応答")
        except urllib.error.HTTPError as e:
            errors.append(f"{url}: HTTP {e.code}")
        except urllib.error.URLError as e:
            errors.append(f"{url}: {e.reason}")
    raise RuntimeError(
        "HTML版を取得できませんでした:\n  " + "\n  ".join(errors)
        + "\nこの論文はHTML版が無い可能性があります。PDFから作業してください（--pdf モード）。"
    )


def download_images(html: str, base_url: str, out_dir: Path) -> tuple[str, int]:
    """imgのsrcをローカル保存してパスを書き換えたHTMLと、保存枚数を返す。"""
    figs_dir = out_dir / "figs"
    srcs = re.findall(r'<img[^>]*?src="([^"]+)"', html)
    mapping: dict[str, str] = {}
    count = 0
    for src in dict.fromkeys(srcs):  # 順序を保って重複除去
        if src.startswith("data:"):
            continue
        # arxiv.org/html のsrcは「ページURLを基準ファイルとみなした」相対パス
        # （例: 1706.03762v7/x1.png）。ダメなら末尾スラッシュ付き基準でも試す
        abs_url = urllib.parse.urljoin(base_url, src)
        ext = Path(urllib.parse.urlparse(abs_url).path).suffix or ".png"
        local_name = f"fig_{count + 1:02d}{ext}"
        try:
            data, _ = fetch(abs_url)
        except (urllib.error.URLError, OSError):
            try:
                abs_url = urllib.parse.urljoin(base_url + "/", src)
                data, _ = fetch(abs_url)
            except (urllib.error.URLError, OSError) as e:
                print(f"  [警告] 画像取得失敗 {abs_url}: {e}")
                continue
        figs_dir.mkdir(parents=True, exist_ok=True)
        (figs_dir / local_name).write_bytes(data)
        mapping[src] = f"figs/{local_name}"
        count += 1

    def replace_src(m: re.Match) -> str:
        src = m.group(1)
        return m.group(0).replace(f'src="{src}"', f'src="{mapping[src]}"') if src in mapping else m.group(0)

    html = re.sub(r'<img[^>]*?src="([^"]+)"', replace_src, html)
    return html, count


def clean_html(html: str) -> str:
    """翻訳作業で読む用に、レイアウト系の属性やヘッダを削ぎ落とす。

    MathML（<math>〜</math>）の中身と alttext（元のLaTeX）は保持する。
    """
    # 論文本文は <article> に包まれている（arxiv/html・ar5ivとも）。
    # サイトのバナー・ロゴ等を排除するため、あれば <article> だけを残す
    m = re.search(r"<article\b.*</article>", html, flags=re.S | re.I)
    if m:
        html = m.group(0)
    html = re.sub(r"<head\b.*?</head>", "", html, flags=re.S | re.I)
    html = re.sub(r"<script\b.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<style\b.*?</style>", "", html, flags=re.S | re.I)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    # ar5iv/arxiv-htmlのヘッダ・フッタ・ナビ（サイトの飾り）は翻訳対象外
    html = re.sub(r"<footer\b.*?</footer>", "", html, flags=re.S | re.I)
    html = re.sub(r"<nav\b.*?</nav>", "", html, flags=re.S | re.I)
    html = re.sub(r"<header\b.*?</header>", "", html, flags=re.S | re.I)
    # class/style/id は大量に付くので除去（img/mathのsrc・alttext等は残る）
    html = re.sub(r'\s+(?:class|style|id)="[^"]*"', "", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html


def extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.S | re.I)
    if not m:
        return ""
    title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return re.sub(r"\s+", " ", title)


def extract_headings(html: str) -> list[str]:
    heads = []
    for level, inner in re.findall(r"<(h[1-4])[^>]*>(.*?)</\1>", html, flags=re.S | re.I):
        text = re.sub(r"<[^>]+>", " ", inner)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            heads.append(f"{level}: {text}")
    return heads


def run_arxiv(arg: str, out_dir: Path) -> None:
    arxiv_id = normalize_arxiv_id(arg)
    print(f"arXiv ID: {arxiv_id}")
    url, html = fetch_html(arxiv_id)
    print(f"取得元: {url}")
    out_dir.mkdir(parents=True, exist_ok=True)

    # rawは取得時のまま保存。画像DLとパス書き換えは本文整形後（ロゴ等を拾わないため）
    (out_dir / "source_raw.html").write_text(html, encoding="utf-8")
    cleaned = clean_html(html)
    cleaned, n_imgs = download_images(cleaned, url, out_dir)
    (out_dir / "source_clean.html").write_text(cleaned, encoding="utf-8")

    title = extract_title(html)
    headings = extract_headings(cleaned)
    print(f"タイトル: {title}")
    print(f"画像: {n_imgs}枚 → figs/")
    print(f"保存: {out_dir / 'source_raw.html'}")
    print(f"保存: {out_dir / 'source_clean.html'}（翻訳作業はこちらを読む）")
    print(f"見出し（{len(headings)}件）——完了チェックに使うこと:")
    for h in headings:
        print(f"  {h}")


def run_pdf(pdf_path: Path, out_dir: Path) -> None:
    """PDFから埋め込み画像を figs/ に抽出する（本文はReadツールでPDFを直接読む）。"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("PyMuPDFが未インストールです。`pip install pymupdf` を実行してください。")
        sys.exit(1)
    figs_dir = out_dir / "figs"
    figs_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    count = 0
    seen_xrefs = set()
    for page_num, page in enumerate(doc, start=1):
        for img in page.get_images(full=True):
            xref = img[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            pix = fitz.Pixmap(doc, xref)
            if pix.n - pix.alpha >= 4:  # CMYK等はRGBに変換
                pix = fitz.Pixmap(fitz.csRGB, pix)
            count += 1
            pix.save(figs_dir / f"p{page_num:02d}_img{count:02d}.png")
    print(f"ページ数: {len(doc)} / 抽出画像: {count}枚 → {figs_dir}")
    print("注意: ベクター描画の図は画像として埋め込まれていないため抽出されない。")
    print("その場合は該当ページをスクリーンショット相当で切り出すか、図の参照だけ残す。")


def main() -> None:
    parser = argparse.ArgumentParser(description="arXiv論文HTML版の取得・画像ローカル化")
    parser.add_argument("target", nargs="?", help="arXiv ID または URL")
    parser.add_argument("--pdf", help="ローカルPDFから図を抽出するモード")
    parser.add_argument("--out", required=True, help="出力フォルダ")
    args = parser.parse_args()

    out_dir = Path(args.out)
    if args.pdf:
        run_pdf(Path(args.pdf), out_dir)
    elif args.target:
        run_arxiv(args.target, out_dir)
    else:
        parser.error("arXiv ID/URL か --pdf のどちらかを指定してください")


if __name__ == "__main__":
    main()
