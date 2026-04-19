"""InfiniteBuyingCalculator 단위 테스트."""
import pytest
from src.strategy.calculator import InfiniteBuyingCalculator


@pytest.fixture
def calc():
    return InfiniteBuyingCalculator()


def test_calc_star_pct(calc):
    assert calc.calc_star_pct(0) == pytest.approx(0.15)
    assert calc.calc_star_pct(20) == pytest.approx(0.0)
    assert calc.calc_star_pct(10) == pytest.approx(0.075)


def test_calc_star_point(calc):
    sp = calc.calc_star_point(45.93, 1.0)
    assert sp.star_pct_display == pytest.approx(14.25)
    assert sp.star_price == pytest.approx(45.93 * 1.1425, abs=0.01)
    assert sp.buy_price == pytest.approx(sp.star_price - 0.01, abs=0.01)


def test_calc_buy_amount(calc):
    # 잔금 20000, T=0 → 20000/40 = 500
    assert calc.calc_buy_amount(20000.0, 0) == pytest.approx(500.0)
    # 잔금 19500, T=1 → 19500/39 = 500
    assert calc.calc_buy_amount(19500.0, 1) == pytest.approx(500.0)


def test_calc_final_sell_price(calc):
    assert calc.calc_final_sell_price(45.93) == pytest.approx(45.93 * 1.15, abs=0.01)


def test_t_increments(calc):
    assert calc.next_T_after_full_buy(1.0) == pytest.approx(2.0)
    assert calc.next_T_after_half_buy(1.0) == pytest.approx(1.5)
    assert calc.next_T_after_quarter_sell(4.0) == pytest.approx(3.0)


def test_phase_detection(calc):
    assert calc.is_front_half(0)
    assert calc.is_front_half(19.9)
    assert not calc.is_front_half(20.0)
    assert calc.is_back_half(20.0)
    assert calc.is_back_half(38.9)
    assert not calc.is_back_half(39.0)
    assert calc.is_exhausted(39.0)
    assert calc.is_exhausted(40.0)


def test_calc_new_avg_price(calc):
    # 10주 @$45 + 5주 @$50 → avg = (10×45 + 5×50) / 15 = 700/15 ≈ 46.67
    avg = calc.calc_new_avg_price(10, 45.0, 5, 50.0)
    assert avg == pytest.approx(700 / 15, rel=1e-4)


def test_phase_label(calc):
    assert calc.phase_label(0, 0) == "초기매수"
    assert "전반전" in calc.phase_label(1, 10)
    assert "후반전" in calc.phase_label(20, 10)
    assert "소진모드" in calc.phase_label(39, 10)
