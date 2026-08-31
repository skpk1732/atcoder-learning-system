"""fetch_submission.py のオフラインテスト（ネットワーク不要）。

外部通信する http_get / time.sleep は monkeypatch で差し替える。
実行: pytest 2_Areas/AtCoder/tools/ -q
"""

import json
import math

import pytest

import fetch_submission as fs


# ---------- pick_extension ----------

@pytest.mark.parametrize(
    ("language", "ext"),
    [
        ("Python (CPython 3.11.4)", ".py"),
        ("Python (PyPy 3.10-v7.3.12)", ".py"),
        ("C++ 20 (gcc 12.2)", ".cpp"),
        ("Rust (rustc 1.70.0)", ".rs"),
        ("COBOL (Free)", ".txt"),  # 未知言語はフォールバック
    ],
)
def test_pick_extension(language, ext):
    assert fs.pick_extension(language) == ext


# ---------- load_username ----------

def test_load_username_prefers_cli_arg():
    assert fs.load_username("someone") == "someone"


def test_load_username_reads_config(tmp_path, monkeypatch):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"username": "kyo"}), encoding="utf-8")
    monkeypatch.setattr(fs, "CONFIG_PATH", config)
    assert fs.load_username(None) == "kyo"


def test_load_username_rejects_placeholder(tmp_path, monkeypatch):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"username": "YOUR_ATCODER_ID"}), encoding="utf-8")
    monkeypatch.setattr(fs, "CONFIG_PATH", config)
    with pytest.raises(SystemExit):
        fs.load_username(None)


# ---------- fetch_code ----------

def test_fetch_code_extracts_and_unescapes(monkeypatch):
    page = (
        "<html><body>"
        '<pre id="submission-code" class="prettyprint">'
        "print(1 &lt; 2 &amp;&amp; 3 &gt; 2)"
        "</pre></body></html>"
    )
    monkeypatch.setattr(fs, "http_get", lambda url: page.encode("utf-8"))
    assert fs.fetch_code("abc999", 123) == "print(1 < 2 && 3 > 2)"


def test_fetch_code_exits_when_pre_missing(monkeypatch):
    monkeypatch.setattr(fs, "http_get", lambda url: b"<html>login please</html>")
    with pytest.raises(SystemExit):
        fs.fetch_code("abc999", 123)


# ---------- fetch_submissions ----------

def _sub(epoch, sid):
    return {"epoch_second": epoch, "id": sid}


def test_fetch_submissions_sorts_newest_first(monkeypatch):
    data = [_sub(100, 1), _sub(300, 3), _sub(200, 2)]
    monkeypatch.setattr(fs, "http_get", lambda url: json.dumps(data).encode())
    result = fs.fetch_submissions("user")
    assert [s["id"] for s in result] == [3, 2, 1]


def test_fetch_submissions_paginates_until_short_page(monkeypatch):
    # 1ページ目: ちょうど500件（=続きあり） / 2ページ目: 1件（=打ち切り）
    page1 = [_sub(i, i) for i in range(500)]
    page2 = [_sub(1000, 1000)]
    calls = []

    def fake_get(url):
        calls.append(url)
        return json.dumps(page1 if len(calls) == 1 else page2).encode()

    monkeypatch.setattr(fs, "http_get", fake_get)
    monkeypatch.setattr(fs.time, "sleep", lambda s: None)
    result = fs.fetch_submissions("user", from_second=0)
    assert len(result) == 501
    assert len(calls) == 2
    # 2ページ目のカーソルは「1ページ目の最大epoch+1」
    assert "from_second=500" in calls[1]


# ---------- get_difficulty ----------

@pytest.fixture
def models_cache(tmp_path, monkeypatch):
    """TOOLS_DIRをtmpに向け、モデルJSONをキャッシュとして配置する。"""
    models = {
        "abc999_a": {"difficulty": -1000},  # 補正対象（400未満）
        "abc999_c": {"difficulty": 550},    # 実測そのまま（round）
        "abc999_d": {},                     # difficultyキーなし
    }
    monkeypatch.setattr(fs, "TOOLS_DIR", tmp_path)
    (tmp_path / "problem_models_cache.json").write_text(
        json.dumps(models), encoding="utf-8"
    )
    # キャッシュが新しいので http_get は呼ばれないはず（呼ばれたら失敗させる）
    monkeypatch.setattr(
        fs, "http_get", lambda url: pytest.fail("キャッシュがあるのに通信した")
    )
    return models


def test_get_difficulty_applies_low_end_correction(models_cache):
    result = fs.get_difficulty(["abc999_a"])
    raw = models_cache["abc999_a"]["difficulty"]
    assert result["abc999_a"] == round(400 / math.exp(1.0 - raw / 400))


def test_get_difficulty_rounds_normal_values(models_cache):
    assert fs.get_difficulty(["abc999_c"]) == {"abc999_c": 550}


def test_get_difficulty_returns_none_for_uncalculated(models_cache):
    # difficultyキーが無い問題・モデルに存在しない問題はどちらもNone
    result = fs.get_difficulty(["abc999_d", "abc000_x"])
    assert result == {"abc999_d": None, "abc000_x": None}


def test_get_difficulty_is_case_insensitive(models_cache):
    assert fs.get_difficulty(["ABC999_C"]) == {"ABC999_C": 550}
