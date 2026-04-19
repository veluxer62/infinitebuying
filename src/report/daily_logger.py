"""날짜별 운용 로그 생성 (data/logs/YYYY-MM-DD.md)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime

from ..state.manager import PortfolioState
from ..strategy.calculator import InfiniteBuyingCalculator
from ..strategy.guide_builder import TradeGuide


@dataclass
class TradeRecord:
    side: str        # "매수" | "쿼터매도" | "최종매도"
    quantity: int
    price: float

    @property
    def amount(self) -> float:
        return self.quantity * self.price


class DailyLogger:
    def __init__(self, log_dir: str = "data/logs") -> None:
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self._calc = InfiniteBuyingCalculator()

    def log(
        self,
        run_date: str,
        state: PortfolioState,
        close_price: float,
        trades: list[TradeRecord],
        guide: TradeGuide,
    ) -> str:
        path = os.path.join(self.log_dir, f"{run_date}.md")
        with open(path, "w", encoding="utf-8") as f:
            self._write(f, run_date, state, close_price, trades, guide)
        return path

    def _write(self, f, run_date, state, close_price, trades, guide):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        market_val = state.market_value(close_price)
        unrealized = state.unrealized_pnl(close_price)
        total_ret_pct = state.total_return_pct(close_price)
        star = (
            self._calc.calc_star_point(state.avg_price, state.T)
            if state.avg_price > 0 else None
        )

        f.write(f"# 무한매수법 V4.0 — {run_date}\n\n")
        f.write(f"> 기록시각: {now}  |  페이즈: **{guide.phase}**  |  T={state.T:.4f}\n\n")
        f.write("---\n\n")

        # ── 포트폴리오 현황 ──
        f.write("## 포트폴리오 현황\n\n")
        f.write("| 항목 | 값 |\n|------|----|\n")
        f.write(f"| 종목 | {state.symbol} ({state.division}분할) |\n")
        f.write(f"| 원금 | ${state.original_capital:,.2f} |\n")
        f.write(f"| 잔금 | ${state.remaining_cash:,.2f} |\n")
        f.write(f"| 종가 | ${close_price:.2f} |\n")
        f.write(f"| 평균단가 | ${state.avg_price:.4f} |\n")
        f.write(f"| 보유수량 | {state.quantity}주 |\n")
        f.write(f"| 평가금액 | ${market_val:,.2f} |\n")
        sign = "+" if unrealized >= 0 else ""
        f.write(f"| 평가손익 | {sign}${unrealized:,.2f} |\n")
        f.write(f"| 수익률(원금대비) | {sign}{total_ret_pct:.2f}% |\n")
        f.write(f"| 누적 실현손익 | ${state.total_realized_profit:,.2f} |\n")
        f.write(f"| T값 | {state.T:.6f} / {state.division} ({state.T/state.division*100:.1f}%) |\n")
        if star:
            f.write(f"| 별% | {star.star_pct_display:.4f}% |\n")
            f.write(f"| 별지점 | ${star.star_price:.2f} |\n")
        f.write(f"| 진행회차 | {state.cycle}회전 |\n")
        f.write("\n")

        # ── 금일 체결 내역 ──
        f.write("## 금일 체결 내역\n\n")
        if trades:
            f.write("| 구분 | 수량 | 체결가 | 금액 |\n")
            f.write("|------|------|--------|------|\n")
            for t in trades:
                f.write(f"| {t.side} | {t.quantity}주 | ${t.price:.2f} | ${t.amount:,.2f} |\n")
        else:
            f.write("체결 없음\n")
        f.write("\n")

        # ── 내일 가이드라인 ──
        f.write("## 내일 매매 가이드라인\n\n")
        f.write(f"> 페이즈: **{guide.phase}**  |  별%: {guide.star_pct_display:.4f}%  |  별지점: ${guide.star_price:.2f}\n\n")

        f.write("### 매수\n\n")
        f.write("| 항목 | 값 |\n|------|----|\n")
        f.write(f"| LOC 지정가 | ${guide.buy_price:.2f} (별지점 - $0.01) |\n")
        f.write(f"| 매수 금액 | ${guide.buy_amount:,.2f} |\n")
        f.write(f"| 매수 수량 | {guide.buy_quantity}주 |\n")
        if guide.has_avg_buy:
            f.write(f"| 평단 LOC 지정가 | ${guide.avg_buy_price:.2f} |\n")
            f.write(f"| 평단 매수 금액 | ${guide.avg_buy_amount:,.2f} |\n")
            f.write(f"| 평단 매수 수량 | {guide.avg_buy_quantity}주 |\n")
        f.write("\n")

        if guide.has_sell:
            f.write("### 매도\n\n")
            f.write("| 항목 | 값 |\n|------|----|\n")
            f.write(f"| 쿼터매도 LOC 지정가 | ${guide.quarter_sell_price:.2f} (별지점) |\n")
            f.write(f"| 쿼터매도 수량 | {guide.quarter_sell_quantity}주 |\n")
            f.write(f"| 최종매도 지정가 | ${guide.final_sell_price:.2f} (평단 × 1.15) |\n")
            f.write(f"| 최종매도 수량 | {guide.final_sell_quantity}주 |\n")
            f.write("\n")

        f.write("---\n\n")
        f.write("*자동생성 — 무한매수법 V4.0 가이드 도구*\n")
