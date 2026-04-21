"""run_regen_log — 상태 변경 없이 로그 재생성 기능 테스트."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from src.runner import InfiniteBuyingRunner, _log_matches_state
from src.state.manager import PortfolioState, StateManager
from src.strategy.guide_builder import GuideBuilder
from src.report.daily_logger import DailyLogger


TARGET_DATE = "2026-04-21"

BASE_STATE = dict(
    symbol="TQQQ",
    division=40,
    original_capital=10000.0,
    remaining_cash=9767.68,
    T=1.0,
    avg_price=58.08,
    quantity=4,
    mode="general",
    cycle=1,
    start_date="2026-04-20",
    last_run_date=TARGET_DATE,
    total_realized_profit=0.0,
    last_close_price=58.08,
)


@pytest.fixture
def setup(tmp_path):
    s = PortfolioState(**BASE_STATE)
    mgr = StateManager(
        state_file=str(tmp_path / "state.json"),
        log_dir=str(tmp_path / "logs"),
    )
    mgr.save_state(s)
    log_dir = str(tmp_path / "logs")
    os.makedirs(log_dir, exist_ok=True)
    r = InfiniteBuyingRunner(state_mgr=mgr, symbol="TQQQ", division=40, default_capital=10000.0)
    r.daily_logger.log_dir = log_dir
    return r, mgr, s, tmp_path


def _make_matching_log(log_dir: str, state: PortfolioState) -> str:
    """state와 일치하는 로그 파일을 생성하고 경로를 반환한다."""
    guide = GuideBuilder().build(
        remaining_cash=state.remaining_cash,
        T=state.T,
        avg_price=state.avg_price,
        quantity=state.quantity,
        close_price=state.last_close_price,
    )
    logger = DailyLogger(log_dir=log_dir)
    return logger.log(TARGET_DATE, state, state.last_close_price, [], guide)


# ── 정상 생성 ──────────────────────────────────────────────────────────────────

def test_creates_log_when_missing(setup):
    r, mgr, s, tmp_path = setup
    inputs = iter([TARGET_DATE, "58.08", "n"])
    with patch("builtins.input", side_effect=inputs):
        r.run_regen_log()

    assert (tmp_path / "logs" / f"{TARGET_DATE}.md").exists()


def test_does_not_modify_state(setup):
    r, mgr, s, tmp_path = setup
    inputs = iter([TARGET_DATE, "58.08", "n"])
    with patch("builtins.input", side_effect=inputs):
        r.run_regen_log()

    reloaded = mgr.load_state()
    assert reloaded.T == s.T
    assert reloaded.remaining_cash == s.remaining_cash
    assert reloaded.quantity == s.quantity
    assert reloaded.avg_price == s.avg_price


def test_uses_default_date_when_empty_input(setup):
    r, mgr, s, tmp_path = setup
    inputs = iter(["", "58.08", "n"])
    with patch("builtins.input", side_effect=inputs):
        r.run_regen_log()

    assert (tmp_path / "logs" / f"{TARGET_DATE}.md").exists()


def test_includes_trade_record_in_log(setup):
    r, mgr, s, tmp_path = setup
    inputs = iter([TARGET_DATE, "58.08", "b", "4", "58.08", "n"])
    with patch("builtins.input", side_effect=inputs):
        r.run_regen_log()

    content = (tmp_path / "logs" / f"{TARGET_DATE}.md").read_text()
    assert "매수" in content
    assert "58.08" in content


# ── 제약 1: state 날짜 불일치 ─────────────────────────────────────────────────

def test_blocked_when_state_date_differs(setup):
    r, _, _, tmp_path = setup
    other_date = "2026-04-22"
    inputs = iter([other_date])
    with patch("builtins.input", side_effect=inputs):
        r.run_regen_log()

    assert not (tmp_path / "logs" / f"{other_date}.md").exists()


# ── 제약 2: 로그와 state 일치 여부 ───────────────────────────────────────────

def test_blocked_when_log_matches_state(setup):
    r, mgr, s, _ = setup
    log_path = _make_matching_log(r.daily_logger.log_dir, s)
    original = open(log_path).read()

    inputs = iter([TARGET_DATE])
    with patch("builtins.input", side_effect=inputs):
        r.run_regen_log()

    assert open(log_path).read() == original  # 파일 그대로


def test_regenerates_when_log_mismatches_state(setup):
    r, mgr, s, tmp_path = setup
    log_file = tmp_path / "logs" / f"{TARGET_DATE}.md"
    log_file.write_text("# 무한매수법 V4.0\n| 잔금 | $1.00 |\n| 평균단가 | $1.00 |\n| 보유수량 | 0주 |\n| T값 | 0.0 / 40 |\n| 누적 실현손익 | $0.00 |")

    inputs = iter([TARGET_DATE, "58.08", "n"])
    with patch("builtins.input", side_effect=inputs):
        r.run_regen_log()

    content = log_file.read_text()
    assert "9,767.68" in content  # 올바른 잔금으로 갱신됨


# ── _log_matches_state 단위 테스트 ────────────────────────────────────────────

def test_log_matches_state_true(setup):
    r, _, s, _ = setup
    log_path = _make_matching_log(r.daily_logger.log_dir, s)
    assert _log_matches_state(log_path, s) is True


def test_log_matches_state_false_on_wrong_values(setup):
    _, _, s, tmp_path = setup
    log_file = tmp_path / "logs" / f"{TARGET_DATE}.md"
    log_file.write_text("| 잔금 | $1.00 |\n| 평균단가 | $1.00 |\n| 보유수량 | 0주 |\n| T값 | 0.0 / 40 |\n| 누적 실현손익 | $0.00 |")
    assert _log_matches_state(str(log_file), s) is False


def test_log_matches_state_false_on_missing_fields(setup):
    _, _, s, tmp_path = setup
    log_file = tmp_path / "logs" / f"{TARGET_DATE}.md"
    log_file.write_text("불완전한 로그 내용")
    assert _log_matches_state(str(log_file), s) is False
