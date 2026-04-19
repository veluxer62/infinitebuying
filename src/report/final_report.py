"""회전 종료 시 최종 보고서 생성 (reports/report_cycleN_YYYYMMDD.md)"""
from __future__ import annotations

import glob
import os
from datetime import datetime

from ..state.manager import PortfolioState


class FinalReportGenerator:
    def __init__(
        self,
        log_dir: str = "data/logs",
        report_dir: str = "reports",
    ) -> None:
        self.log_dir = log_dir
        self.report_dir = report_dir
        os.makedirs(report_dir, exist_ok=True)

    def generate(self, state: PortfolioState, final_price: float) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(
            self.report_dir,
            f"report_cycle{state.cycle}_{timestamp}.md",
        )
        with open(path, "w", encoding="utf-8") as f:
            self._write(f, state, final_price)
        return path

    def _write(self, f, state: PortfolioState, final_price: float) -> None:
        end_date = datetime.now().strftime("%Y-%m-%d")
        profit = state.total_realized_profit
        profit_pct = (profit / state.original_capital * 100) if state.original_capital else 0
        log_files = sorted(glob.glob(os.path.join(self.log_dir, "*.md")))
        days = len(log_files)

        f.write(f"# 무한매수법 V4.0 최종 보고서 — {state.cycle}회전\n\n")
        f.write(f"> 종목: **{state.symbol}** ({state.division}분할)  \n")
        f.write(f"> 시작일: {state.start_date}  |  종료일: {end_date}  |  운용일수: {days}일\n\n")
        f.write("---\n\n")

        # ── 수익 요약 ──
        f.write("## 수익 요약\n\n")
        f.write("| 항목 | 값 |\n|------|----|\n")
        f.write(f"| 원금 | ${state.original_capital:,.2f} |\n")
        f.write(f"| 실현 수익 | ${profit:,.2f} |\n")
        f.write(f"| 수익률 | {profit_pct:.2f}% |\n")
        f.write(f"| 잔여 현금 | ${state.remaining_cash:,.2f} |\n")
        next_capital = state.original_capital + profit
        f.write(f"| 복리 적용 시 다음 원금 | ${next_capital:,.2f} |\n\n")

        # ── 운용 통계 ──
        f.write("## 운용 통계\n\n")
        f.write(f"- 총 운용일수: {days}일\n")
        f.write(f"- 최종 T값: {state.T:.6f}\n")
        f.write(f"- 최종 평균단가: ${state.avg_price:.4f}\n")
        f.write(f"- 최종 보유수량: {state.quantity}주\n\n")

        # ── 일별 로그 목록 ──
        f.write("## 일별 로그 목록\n\n")
        for lf in log_files:
            fname = os.path.basename(lf)
            f.write(f"- [{fname}](../data/logs/{fname})\n")

        f.write("\n---\n\n")
        f.write("*자동생성 — 무한매수법 V4.0 자동화 도구*\n")
