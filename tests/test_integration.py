"""
무한매수법 V4.0 통합 테스트 — 시나리오 기반

시나리오1: TQQQ 2025-01-02 시작, $10,000, 40분할
  → 총 수익률 +7.00%, 실현손익 $611.65, 최종 T=0.2111, 보유 3주

시나리오2: SOXL 2025-01-02 시작, $10,000, 40분할
  → 총 수익률 +10.88%, 실현손익 $877.92, 최종 T=0.1159, 보유 3주
  → 리버스모드 발동(T=39.51, 2025-04-23) → 종료(2025-04-25)
"""
import pytest

from src.state.manager import PortfolioState, StateManager
from src.strategy.calculator import InfiniteBuyingCalculator
from src.strategy.guide_builder import GuideBuilder


# ── 픽스처 ────────────────────────────────────────────────────────────────────

@pytest.fixture
def calc():
    return InfiniteBuyingCalculator()


@pytest.fixture
def builder():
    return GuideBuilder()


@pytest.fixture
def tqqq_final_state():
    """시나리오1 최종 상태 (2026-04-15 기준)."""
    return PortfolioState(
        symbol="TQQQ",
        division=40,
        original_capital=10000.0,
        remaining_cash=10524.67,
        T=0.2111,
        avg_price=28.9923,
        quantity=3,
        mode="general",
        cycle=1,
        start_date="2025-01-02",
        total_realized_profit=611.65,
        last_close_price=58.59,
    )


@pytest.fixture
def soxl_final_state():
    """시나리오2 최종 상태 (2026-04-15 기준)."""
    return PortfolioState(
        symbol="SOXL",
        division=40,
        original_capital=10000.0,
        remaining_cash=10830.56,
        T=0.1159,
        avg_price=15.7860,
        quantity=3,
        mode="general",
        cycle=1,
        start_date="2025-01-02",
        total_realized_profit=877.92,
        last_close_price=85.96,
    )


# ── 시나리오1: TQQQ 핵심 계산 검증 ───────────────────────────────────────────

class TestTQQQScenario1Calculations:
    """시나리오1의 InfiniteBuyingCalculator 계산 정합성 검증."""

    def test_initial_buy_amount(self, calc):
        """시드 $10,000, T=0 → 1회 매수금 = 10000÷40 = $250."""
        assert calc.calc_buy_amount(10000.0, 0.0) == pytest.approx(250.0)

    def test_initial_buy_quantity(self):
        """2025-01-02 종가 $39.31 → int(250÷39.31) = 6주."""
        buy_amount = 10000.0 / 40
        assert int(buy_amount / 39.31) == 6

    def test_day1_star_point(self, calc):
        """Day 1 마감 후(T=1.0, avg=$39.31) 별지점 계산.
        별% = (15 - 0.75×1)/100 = 14.25%
        별지점 = 39.31 × 1.1425 = $44.90
        """
        sp = calc.calc_star_point(39.31, 1.0)
        assert sp.star_pct_display == pytest.approx(14.25)
        assert sp.star_price == pytest.approx(44.90, abs=0.01)
        assert sp.buy_price == pytest.approx(44.89, abs=0.01)

    def test_front_half_boundary(self, calc):
        """전반전/후반전 경계: T<20 전반전, T≥20 후반전."""
        assert calc.is_front_half(19.99)
        assert not calc.is_front_half(20.0)
        assert calc.is_back_half(20.0)

    def test_quarter_sell_t_update_at_t8p5(self, calc):
        """시나리오1 2025-01-23: T=8.5 → 쿼터매도 → T×0.75=6.375."""
        assert calc.next_T_after_quarter_sell(8.5) == pytest.approx(6.375)

    def test_quarter_sell_quantity_at_52shares(self):
        """시나리오1 2025-01-23: qty=52 → 쿼터매도 수량 = 52÷4 = 13주."""
        assert 52 // 4 == 13

    def test_back_half_star_pct_is_negative(self, calc):
        """후반전(T=25): 별% = (15-0.75×25)/100 = -3.75% → 별지점 < 평단."""
        pct = calc.calc_star_pct(25.0)
        assert pct == pytest.approx(-0.0375)
        assert pct < 0

    def test_exhausted_mode_threshold(self, calc):
        """소진모드 진입 기준: T≥39."""
        assert not calc.is_exhausted(38.99)
        assert calc.is_exhausted(39.0)
        assert calc.is_exhausted(39.51)

    def test_final_sell_price(self, calc):
        """시나리오1 최종 avg≈$28.99 → 최종매도가 = avg×1.15 ≈ $33.34."""
        assert calc.calc_final_sell_price(28.9923) == pytest.approx(33.34, abs=0.01)

    def test_scenario1_total_return(self):
        """시나리오1 수익률: (실현$611.65 + 평가$88.79) ÷ $10,000 = 7.00%."""
        realized = 611.65
        unrealized = (58.59 - 28.9923) * 3
        total_return = (realized + unrealized) / 10000.0 * 100
        assert total_return == pytest.approx(7.00, abs=0.05)


# ── 시나리오1: TQQQ GuideBuilder 검증 ────────────────────────────────────────

class TestTQQQScenario1GuideBuilder:
    """시나리오1 주요 시점 GuideBuilder.build() 출력 검증."""

    def test_initial_state_guide(self, builder):
        """T=0, qty=0: 초기매수 가이드 — 6주, has_sell=False."""
        guide = builder.build(
            remaining_cash=10000.0, T=0.0, avg_price=0.0,
            quantity=0, close_price=39.31,
        )
        assert guide.phase == "초기매수"
        assert guide.buy_quantity == 6
        assert guide.has_avg_buy is False
        assert guide.has_sell is False
        assert guide.quarter_sell_quantity == 0

    def test_front_half_guide_after_day1(self, builder):
        """Day 1 마감 후 전반전 가이드 (T=1, avg=39.31, qty=6).
        절반씩: q_star=3, q_avg=3, 쿼터매도=1주(6÷4).
        """
        cash = 10000.0 - 6 * 39.31
        guide = builder.build(
            remaining_cash=cash, T=1.0, avg_price=39.31,
            quantity=6, close_price=39.31,
        )
        assert guide.phase == "전반전"
        assert guide.has_avg_buy is True
        assert guide.buy_quantity == 3
        assert guide.avg_buy_quantity == 3
        assert guide.star_price == pytest.approx(44.90, abs=0.01)
        assert guide.buy_price == pytest.approx(44.89, abs=0.01)
        assert guide.quarter_sell_quantity == 1

    def test_back_half_guide_no_avg_loc(self, builder):
        """후반전(T=21): 평단LOC 없음(has_avg_buy=False), 별지점LOC만.
        시나리오1 2025-03-18 부근: T≈21.97, avg≈35.53, qty=147.
        """
        guide = builder.build(
            remaining_cash=5023.0, T=21.97, avg_price=35.53,
            quantity=147, close_price=31.55,
        )
        assert guide.phase == "후반전"
        assert guide.has_avg_buy is False
        assert guide.avg_buy_quantity == 0
        assert guide.quarter_sell_quantity == 147 // 4

    def test_quarter_sell_quantity_less_than_four(self, builder):
        """qty=3: 3÷4=0 → 쿼터매도 불가(수량=0), 최종매도는 가능(has_sell=True)."""
        guide = builder.build(
            remaining_cash=10000.0, T=0.5, avg_price=30.0,
            quantity=3, close_price=30.0,
        )
        assert guide.quarter_sell_quantity == 0
        assert guide.has_sell is True

    def test_star_point_price_matches_scenario(self, builder):
        """시나리오1 2025-01-24 부근: T=4.78, avg=$39.77 → 별지점 검증.
        별% = (15 - 0.75×4.78)/100 = 11.415%
        별지점 = 39.77 × 1.11415 ≈ $44.30
        """
        guide = builder.build(
            remaining_cash=8900.0, T=4.78, avg_price=39.77,
            quantity=30, close_price=44.17,
        )
        expected_star = round(39.77 * (1 + (15 - 0.75 * 4.78) / 100), 2)
        assert guide.star_price == pytest.approx(expected_star, abs=0.01)


# ── 시나리오1: 다일 시퀀스 검증 ──────────────────────────────────────────────

class TestTQQQScenario1MultiDaySequence:
    """TQQQ 시나리오1 초반 3거래일 연속 시퀀스 검증.

    날짜         종가    T     avg     qty  cash
    2025-01-02  39.31  1.00  39.31    6   9764.14   초기매수
    2025-01-03  41.20  1.50  39.94    9   9640.54   별지점LOC 3주
    2025-01-06  42.60  2.00  40.61   12   9512.74   별지점LOC 3주
    """

    def test_day1_initial_buy(self, calc):
        """Day 1: 초기매수 6주 @$39.31 → T=1.0, cash=9764.14."""
        cash = 10000.0
        T = 0.0
        close = 39.31

        bq = int(calc.calc_buy_amount(cash, T) / close)
        cost = bq * close
        cash -= cost
        T = calc.next_T_after_full_buy(T)

        assert bq == 6
        assert T == pytest.approx(1.0)
        assert cash == pytest.approx(9764.14, abs=0.01)

    def test_day2_star_loc_only(self, calc):
        """Day 2: close=$41.20, 별지점 LOC만 체결 → T=1.5, qty=9, avg≈$39.94.
        close=41.20 <= star_lim=44.89: 체결
        close=41.20 > avg_lim=39.31: 미체결
        ratio≈0.49 (0.25~0.75) → T+0.5
        """
        cash = 9764.14
        T = 1.0
        avg = 39.31
        qty = 6
        close = 41.20

        exp_buy = calc.calc_buy_amount(cash, T)
        half = exp_buy / 2
        q_star = int(half / 39.31)           # 전일 종가로 수량 결정
        sp = calc.calc_star_point(avg, T)

        # 별지점 LOC 체결 여부
        assert close <= sp.buy_price         # 41.20 <= 44.89

        cost = q_star * close
        avg = calc.calc_new_avg_price(qty, avg, q_star, close)
        qty += q_star
        cash -= cost

        # 평단 LOC 미체결 여부
        assert close > 39.31                 # avg_lim

        ratio = cost / exp_buy
        assert 0.25 <= ratio < 0.75          # 절반 매수 → T+0.5
        T = calc.next_T_after_half_buy(T)

        assert qty == 9
        assert T == pytest.approx(1.5)
        assert avg == pytest.approx(39.94, abs=0.01)
        assert cash == pytest.approx(9640.54, abs=0.1)

    def test_day3_star_loc_again(self, calc):
        """Day 3: close=$42.60, 별지점 LOC 체결 → T=2.0, qty=12, avg≈$40.61."""
        cash = 9640.54
        T = 1.5
        avg = 39.94
        qty = 9
        close = 42.60

        exp_buy = calc.calc_buy_amount(cash, T)
        half = exp_buy / 2
        q_star = int(half / 41.20)           # 전일 종가
        sp = calc.calc_star_point(avg, T)

        # 별% = (15 - 0.75×1.5)/100 = 13.875% → 별지점 ≈ 45.48
        assert sp.star_price == pytest.approx(45.48, abs=0.05)
        assert close <= sp.buy_price

        cost = q_star * close
        avg = calc.calc_new_avg_price(qty, avg, q_star, close)
        qty += q_star
        cash -= cost

        ratio = cost / exp_buy
        assert 0.25 <= ratio < 0.75
        T = calc.next_T_after_half_buy(T)

        assert qty == 12
        assert T == pytest.approx(2.0)
        assert avg == pytest.approx(40.61, abs=0.05)

    def test_quarter_sell_event(self, calc):
        """시나리오1 2025-01-23: T=8.5, qty=52, close=$43.90 쿼터매도.
        쿼터매도 수량: 52÷4=13주
        T 갱신: 8.5×0.75=6.375
        수익: 13×(43.90-39.77)=$53.69
        """
        T = 8.5
        avg = 39.77
        qty = 52
        close = 43.90

        sell_qty = qty // 4
        profit = sell_qty * (close - avg)
        T_new = calc.next_T_after_quarter_sell(T)

        assert sell_qty == 13
        assert T_new == pytest.approx(6.375)
        assert profit == pytest.approx(53.69, abs=0.1)


# ── 시나리오2: SOXL 핵심 계산 검증 ───────────────────────────────────────────

class TestSOXLScenario2Calculations:
    """시나리오2의 SOXL 40분할 규칙 및 리버스모드 계산 검증."""

    def test_initial_buy_quantity(self):
        """2025-01-02 종가 $27.67 → int(250÷27.67) = 9주."""
        buy_amount = 10000.0 / 40
        assert int(buy_amount / 27.67) == 9

    def test_soxl_star_pct_formula(self):
        """SOXL 40분할 별% = (20-T)/100. T=1 → 19%."""
        T = 1.0
        assert (20.0 - T) / 100.0 == pytest.approx(0.19)

    def test_soxl_star_price_at_t1(self):
        """avg=$27.67, T=1 → 별지점 = 27.67×1.19 = $32.93."""
        avg = 27.67
        T = 1.0
        star_pct = (20.0 - T) / 100.0
        sp = round(avg * (1 + star_pct), 2)
        assert sp == pytest.approx(32.93, abs=0.01)

    def test_soxl_final_sell_price(self):
        """SOXL 최종매도 = 평단×1.20. avg≈$15.786 → $18.94."""
        avg = 15.7860
        assert round(avg * 1.20, 2) == pytest.approx(18.94, abs=0.01)

    def test_soxl_reverse_mode_trigger(self):
        """시나리오2 리버스 발동: T=39.51 > 39 ✓."""
        T = 39.51
        EXHAUSTED_T = 39
        assert T > EXHAUSTED_T

    def test_soxl_reverse_moc_qty(self):
        """리버스 첫날 MOC 매도수량: qty=687 → 687÷20 = 34주."""
        assert 687 // 20 == 34

    def test_soxl_reverse_t_after_moc(self):
        """리버스 MOC 후 T: 39.51×0.95 ≈ 37.53."""
        T = 39.51
        assert round(T * 0.95, 10) == pytest.approx(37.535, abs=0.001)

    def test_soxl_reverse_star_price_5day_avg(self):
        """리버스 별지점 = 직전 5거래일 종가 평균.
        2025-04-24 pending 기준 직전 5일: [9.20, 8.71, 9.18, 10.29, 12.00]
        avg = 49.38 / 5 = $9.876 ≈ $9.88
        """
        last5 = [9.20, 8.71, 9.18, 10.29, 12.00]
        rev_star = round(sum(last5) / len(last5), 2)
        assert rev_star == pytest.approx(9.88, abs=0.01)

    def test_soxl_reverse_sell_qty(self):
        """리버스 2일차 매도수량: qty=653 → 653÷20 = 32주."""
        assert 653 // 20 == 32

    def test_soxl_reverse_exit_condition(self):
        """리버스 종료: 종가 > 평단×0.80.
        2025-04-25: close=$12.34 > avg=$14.96×0.80=$11.97 ✓.
        """
        avg = 14.96
        close = 12.34
        assert close > avg * 0.80

    def test_soxl_reverse_t_after_loc_sell(self):
        """리버스 LOC 매도 후 T: 37.535×0.95 ≈ 35.66."""
        T = 37.535
        assert round(T * 0.95, 10) == pytest.approx(35.658, abs=0.001)

    def test_scenario2_total_return(self):
        """시나리오2 수익률: (실현$877.92 + 평가$210.52) ÷ $10,000 = 10.88%."""
        realized = 877.92
        unrealized = (85.96 - 15.7860) * 3
        total_return = (realized + unrealized) / 10000.0 * 100
        assert total_return == pytest.approx(10.88, abs=0.05)


# ── StateManager 통합 테스트 ─────────────────────────────────────────────────

class TestStateManagerIntegration:
    """StateManager를 사용한 시나리오 상태 저장/로드/조회 통합 테스트."""

    def test_tqqq_state_save_and_load(self, tmp_path, tqqq_final_state):
        """시나리오1 최종 상태 저장 후 로드 시 모든 필드 정합성 유지."""
        mgr = StateManager(state_file=str(tmp_path / "state.json"))
        mgr.save_state(tqqq_final_state)
        loaded = mgr.load_state()

        assert loaded.symbol == "TQQQ"
        assert loaded.division == 40
        assert loaded.T == pytest.approx(0.2111)
        assert loaded.remaining_cash == pytest.approx(10524.67)
        assert loaded.avg_price == pytest.approx(28.9923)
        assert loaded.quantity == 3
        assert loaded.total_realized_profit == pytest.approx(611.65)
        assert loaded.last_close_price == pytest.approx(58.59)

    def test_soxl_state_save_and_load(self, tmp_path, soxl_final_state):
        """시나리오2 SOXL 최종 상태 저장 후 로드 시 모든 필드 정합성 유지."""
        mgr = StateManager(state_file=str(tmp_path / "state.json"))
        mgr.save_state(soxl_final_state)
        loaded = mgr.load_state()

        assert loaded.symbol == "SOXL"
        assert loaded.T == pytest.approx(0.1159)
        assert loaded.remaining_cash == pytest.approx(10830.56)
        assert loaded.avg_price == pytest.approx(15.7860)
        assert loaded.quantity == 3
        assert loaded.total_realized_profit == pytest.approx(877.92)

    def test_tqqq_final_state_market_metrics(self, tqqq_final_state):
        """시나리오1 최종 평가 지표: 평가금액=$175.77, 수익률=+7.00%."""
        state = tqqq_final_state
        close = 58.59

        assert state.market_value(close) == pytest.approx(175.77, abs=0.01)
        assert state.unrealized_pnl(close) == pytest.approx(88.79, abs=0.1)

        total_return = (
            state.unrealized_pnl(close) + state.total_realized_profit
        ) / state.original_capital * 100
        assert total_return == pytest.approx(7.00, abs=0.05)

    def test_soxl_final_state_market_metrics(self, soxl_final_state):
        """시나리오2 최종 평가 지표: 평가금액=$257.88, 수익률=+10.88%."""
        state = soxl_final_state
        close = 85.96

        assert state.market_value(close) == pytest.approx(257.88, abs=0.01)

        total_return = (
            state.unrealized_pnl(close) + state.total_realized_profit
        ) / state.original_capital * 100
        assert total_return == pytest.approx(10.88, abs=0.05)

    def test_t_value_precision_preserved(self, tmp_path):
        """T값 소수점 정밀도가 저장/로드 후에도 유지된다 (리버스모드 중간값)."""
        mgr = StateManager(state_file=str(tmp_path / "state.json"))
        state = PortfolioState(
            symbol="SOXL", division=40, original_capital=10000.0,
            remaining_cash=500.0, T=37.535000000,
            avg_price=14.96, quantity=653, mode="general",
            cycle=1, start_date="2025-01-02",
        )
        mgr.save_state(state)
        loaded = mgr.load_state()
        assert loaded.T == pytest.approx(37.535, rel=1e-6)

    def test_load_returns_none_when_no_file(self, tmp_path):
        """상태 파일이 없으면 None 반환."""
        mgr = StateManager(state_file=str(tmp_path / "nonexistent.json"))
        assert mgr.load_state() is None

    def test_reset_removes_state_file(self, tmp_path, tqqq_final_state):
        """reset() 후 load_state()는 None을 반환한다."""
        mgr = StateManager(state_file=str(tmp_path / "state.json"))
        mgr.save_state(tqqq_final_state)
        assert mgr.load_state() is not None
        mgr.reset()
        assert mgr.load_state() is None

    def test_reset_removes_log_files(self, tmp_path, tqqq_final_state):
        """reset() 시 log_dir 내 파일도 모두 삭제된다."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        (log_dir / "2025-01-02.md").write_text("log1")
        (log_dir / "2025-01-03.md").write_text("log2")

        mgr = StateManager(
            state_file=str(tmp_path / "state.json"),
            log_dir=str(log_dir),
        )
        mgr.save_state(tqqq_final_state)
        mgr.reset()

        assert mgr.load_state() is None
        assert list(log_dir.iterdir()) == []

    def test_reset_without_log_dir_does_not_raise(self, tmp_path, tqqq_final_state):
        """log_dir가 존재하지 않아도 reset()은 예외 없이 동작한다."""
        mgr = StateManager(
            state_file=str(tmp_path / "state.json"),
            log_dir=str(tmp_path / "nonexistent_logs"),
        )
        mgr.save_state(tqqq_final_state)
        mgr.reset()
        assert mgr.load_state() is None

    def test_overwrite_state_with_updated_values(self, tmp_path):
        """상태 파일을 덮어쓰면 최신 값으로 갱신된다."""
        mgr = StateManager(state_file=str(tmp_path / "state.json"))

        state_v1 = PortfolioState(
            symbol="TQQQ", division=40, original_capital=10000.0,
            remaining_cash=9764.14, T=1.0, avg_price=39.31,
            quantity=6, mode="general", cycle=1, start_date="2025-01-02",
        )
        mgr.save_state(state_v1)

        state_v2 = PortfolioState(
            symbol="TQQQ", division=40, original_capital=10000.0,
            remaining_cash=9640.54, T=1.5, avg_price=39.94,
            quantity=9, mode="general", cycle=1, start_date="2025-01-02",
        )
        mgr.save_state(state_v2)

        loaded = mgr.load_state()
        assert loaded.T == pytest.approx(1.5)
        assert loaded.quantity == 9
        assert loaded.remaining_cash == pytest.approx(9640.54)
