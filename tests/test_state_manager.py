"""StateManager 단위 테스트."""
import json
import os
import tempfile

import pytest

from src.state.manager import PortfolioState, StateManager


@pytest.fixture
def tmp_state_file(tmp_path):
    return str(tmp_path / "state.json")


@pytest.fixture
def mgr(tmp_state_file):
    return StateManager(state_file=tmp_state_file)


def test_load_state_returns_none_when_no_file(mgr):
    assert mgr.load_state() is None


def test_save_and_load_state(mgr):
    state = mgr.create_initial_state("TQQQ", 40, 20000.0)
    mgr.save_state(state)
    loaded = mgr.load_state()
    assert loaded is not None
    assert loaded.symbol == "TQQQ"
    assert loaded.original_capital == 20000.0
    assert loaded.T == 0.0
    assert loaded.quantity == 0


def test_create_initial_state(mgr):
    state = mgr.create_initial_state("TQQQ", 40, 15000.0)
    assert state.remaining_cash == 15000.0
    assert state.cycle == 1
    assert state.mode == "general"
    assert state.is_initial()


def test_reset_removes_file(mgr, tmp_state_file):
    state = mgr.create_initial_state("TQQQ", 40, 20000.0)
    mgr.save_state(state)
    assert os.path.exists(tmp_state_file)
    mgr.reset()
    assert not os.path.exists(tmp_state_file)


def test_portfolio_state_market_value():
    state = PortfolioState(
        symbol="TQQQ", division=40, original_capital=20000.0,
        remaining_cash=19500.0, T=1.0, avg_price=45.93, quantity=10,
        mode="general", cycle=1, start_date="2026-04-18",
    )
    assert state.market_value(50.0) == pytest.approx(500.0)
    assert state.unrealized_pnl(50.0) == pytest.approx((50.0 - 45.93) * 10, rel=1e-4)


def test_total_return_pct():
    state = PortfolioState(
        symbol="TQQQ", division=40, original_capital=20000.0,
        remaining_cash=19500.0, T=1.0, avg_price=45.93, quantity=10,
        mode="general", cycle=1, start_date="2026-04-18",
    )
    # unrealized = (50 - 45.93) * 10 = 40.7
    pct = state.total_return_pct(50.0)
    assert pct == pytest.approx(40.7 / 20000.0 * 100, rel=1e-3)
