"""GuideBuilder 단위 테스트."""
import pytest
from src.strategy.guide_builder import GuideBuilder


@pytest.fixture
def builder():
    return GuideBuilder()


def test_front_half_guide(builder):
    """전반전: 별지점 LOC + 평단 LOC 각 절반."""
    guide = builder.build(
        remaining_cash=19500.0,
        T=1.0,
        avg_price=45.93,
        quantity=10,
        close_price=45.93,
    )
    assert guide.phase == "전반전"
    assert guide.has_avg_buy is True
    assert guide.avg_buy_price == pytest.approx(45.93, abs=0.01)
    # 매수금 = 19500/39 / 2 = 250
    assert guide.buy_amount == pytest.approx(250.0, rel=1e-3)
    assert guide.buy_quantity == int(250.0 / 45.93)
    assert guide.has_sell is True
    assert guide.quarter_sell_quantity == 10 // 4


def test_back_half_guide(builder):
    """후반전: 별지점 LOC 전체."""
    guide = builder.build(
        remaining_cash=10000.0,
        T=20.0,
        avg_price=45.93,
        quantity=50,
        close_price=46.0,
    )
    assert guide.phase == "후반전"
    assert guide.has_avg_buy is False
    # 매수금 = 10000/(40-20) = 500
    assert guide.buy_amount == pytest.approx(500.0, rel=1e-3)
    assert guide.buy_quantity == int(500.0 / 46.0)


def test_initial_state_guide(builder):
    """초기 상태 (T=0, avg=0): 별지점 없음."""
    guide = builder.build(
        remaining_cash=20000.0,
        T=0.0,
        avg_price=0.0,
        quantity=0,
        close_price=45.0,
    )
    assert guide.star_price == 0.0
    assert guide.has_sell is False
    # avg=0이면 has_avg_buy=False, 전체 매수금으로 수량 계산
    assert guide.buy_quantity == int(20000.0 / 40 / 45.0)


def test_quarter_sell_quantity(builder):
    guide = builder.build(
        remaining_cash=15000.0,
        T=5.0,
        avg_price=45.0,
        quantity=20,
        close_price=45.0,
    )
    assert guide.quarter_sell_quantity == 5  # 20 // 4


def test_final_sell_price(builder):
    guide = builder.build(
        remaining_cash=10000.0,
        T=10.0,
        avg_price=50.0,
        quantity=30,
        close_price=50.0,
    )
    assert guide.final_sell_price == pytest.approx(50.0 * 1.15, abs=0.01)
    assert guide.final_sell_quantity == 23  # 30 - (30 // 4)
