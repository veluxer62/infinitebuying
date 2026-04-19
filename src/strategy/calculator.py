"""
무한매수법 V4.0 핵심 계산 모듈 (TQQQ 40분할 기준).

모든 메서드는 순수 함수(Pure Function)로, 부작용 없이 계산만 수행한다.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StarPoint:
    """별지점 계산 결과"""
    star_pct: float    # 별% (소수점 기준, 예: 0.028 = 2.8%)
    star_price: float  # 별지점 = 평단 × (1 + 별%)
    buy_price: float   # 매수점 = 별지점 - 0.01

    @property
    def star_pct_display(self) -> float:
        return round(self.star_pct * 100, 4)


class InfiniteBuyingCalculator:
    """
    무한매수법 V4.0 계산기.

    종목: TQQQ
    분할: 40분할
    별% 공식: (15 - 0.75 × T) %
    최종 지정가 매도: 평단 × 1.15
    """

    DIVISION: int = 40
    SYMBOL: str = "TQQQ"
    FINAL_SELL_RATIO: float = 0.15   # +15% 지정가 매도
    HALF_T: float = DIVISION / 2     # 전반전/후반전 경계 (T=20)
    EXHAUSTED_T: float = DIVISION - 1  # 소진모드 진입 기준 (T=39)

    # ── 별지점 ────────────────────────────────────────────────────────────────

    def calc_star_pct(self, T: float) -> float:
        """40분할 TQQQ 별% = (15 - 0.75T) / 100"""
        return (15.0 - 0.75 * T) / 100.0

    def calc_star_point(self, avg_price: float, T: float) -> StarPoint:
        """별지점 및 매수점 계산"""
        pct = self.calc_star_pct(T)
        star = round(avg_price * (1 + pct), 2)
        return StarPoint(star_pct=pct, star_price=star, buy_price=round(star - 0.01, 2))

    # ── 매수금 ────────────────────────────────────────────────────────────────

    def calc_buy_amount(self, remaining_cash: float, T: float) -> float:
        """1회 매수금 = 잔금 / (40 - T)"""
        divisor = self.DIVISION - T
        if divisor <= 0:
            return 0.0
        return remaining_cash / divisor

    # ── 매도가 ────────────────────────────────────────────────────────────────

    def calc_final_sell_price(self, avg_price: float) -> float:
        """최종 지정가 매도가 = 평단 × 1.15"""
        return round(avg_price * (1 + self.FINAL_SELL_RATIO), 2)

    # ── T값 갱신 ──────────────────────────────────────────────────────────────

    def next_T_after_full_buy(self, T: float) -> float:
        return round(T + 1.0, 10)

    def next_T_after_half_buy(self, T: float) -> float:
        return round(T + 0.5, 10)

    def next_T_after_quarter_sell(self, T: float) -> float:
        return round(T * 0.75, 10)

    # ── 평균단가 갱신 ─────────────────────────────────────────────────────────

    def calc_new_avg_price(
        self,
        current_qty: int,
        current_avg: float,
        buy_qty: int,
        buy_price: float,
    ) -> float:
        """매수 후 새로운 평균단가"""
        total_cost = current_qty * current_avg + buy_qty * buy_price
        total_qty = current_qty + buy_qty
        return round(total_cost / total_qty, 6) if total_qty > 0 else 0.0

    # ── 페이즈 판별 ───────────────────────────────────────────────────────────

    def is_initial(self, T: float, quantity: int) -> bool:
        return quantity == 0 and T == 0.0

    def is_front_half(self, T: float) -> bool:
        """전반전: T < 20"""
        return T < self.HALF_T

    def is_back_half(self, T: float) -> bool:
        """후반전: 20 ≤ T < 39"""
        return self.HALF_T <= T < self.EXHAUSTED_T

    def is_exhausted(self, T: float) -> bool:
        """소진모드: T ≥ 39"""
        return T >= self.EXHAUSTED_T

    def phase_label(self, T: float, quantity: int) -> str:
        if self.is_initial(T, quantity):
            return "초기매수"
        if self.is_exhausted(T):
            return "소진모드"
        if self.is_front_half(T):
            return "전반전"
        return "후반전"
