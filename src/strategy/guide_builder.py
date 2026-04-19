"""내일 매매 가이드라인 생성 (브로커 없이 계산만 수행)."""
from __future__ import annotations

from dataclasses import dataclass

from .calculator import InfiniteBuyingCalculator


@dataclass
class TradeGuide:
    phase: str
    T: float

    # 별 정보
    star_pct_display: float   # % 단위 (예: 13.5)
    star_price: float

    # 매수 가이드 (전반전: 별지점 LOC 절반)
    buy_price: float           # LOC 지정가 (별지점 - 0.01)
    buy_amount: float          # 투입 금액
    buy_quantity: int          # 수량 (buy_amount / close_price)

    # 전반전 추가 매수 (평단 LOC 절반) — has_avg_buy=False 면 0
    avg_buy_price: float
    avg_buy_amount: float
    avg_buy_quantity: int
    has_avg_buy: bool

    # 매도 가이드
    quarter_sell_price: float
    quarter_sell_quantity: int
    final_sell_price: float
    final_sell_quantity: int
    has_sell: bool             # quantity > 0 이면 True


class GuideBuilder:
    def __init__(self) -> None:
        self._calc = InfiniteBuyingCalculator()

    def build(
        self,
        remaining_cash: float,
        T: float,
        avg_price: float,
        quantity: int,
        close_price: float,
    ) -> TradeGuide:
        calc = self._calc
        phase = calc.phase_label(T, quantity)
        buy_amount = calc.calc_buy_amount(remaining_cash, T)

        if avg_price > 0:
            sp = calc.calc_star_point(avg_price, T)
            star_pct_display = sp.star_pct_display
            star_price = sp.star_price
            buy_price = sp.buy_price
        else:
            star_pct_display = (15.0 - 0.75 * T)
            star_price = 0.0
            buy_price = 0.0

        ref = close_price if close_price > 0 else 1.0

        if calc.is_front_half(T) and avg_price > 0:
            half = buy_amount / 2
            buy_qty = int(half / ref)
            avg_buy_price = round(avg_price, 2)
            avg_buy_qty = int(half / ref)
            has_avg_buy = True
            guide_buy_amount = half
        else:
            buy_qty = int(buy_amount / ref)
            avg_buy_price = 0.0
            avg_buy_qty = 0
            has_avg_buy = False
            guide_buy_amount = buy_amount

        # 보유량 4주 미만이면 전량을 쿼터매도 수량으로 처리
        quarter_qty = quantity if quantity < 4 else quantity // 4
        final_sell_price = calc.calc_final_sell_price(avg_price) if avg_price > 0 else 0.0

        return TradeGuide(
            phase=phase,
            T=T,
            star_pct_display=star_pct_display,
            star_price=star_price,
            buy_price=buy_price,
            buy_amount=guide_buy_amount,
            buy_quantity=buy_qty,
            avg_buy_price=avg_buy_price,
            avg_buy_amount=buy_amount / 2,
            avg_buy_quantity=avg_buy_qty,
            has_avg_buy=has_avg_buy,
            quarter_sell_price=star_price,
            quarter_sell_quantity=quarter_qty,
            final_sell_price=final_sell_price,
            final_sell_quantity=quantity,
            has_sell=quantity > 0,
        )
