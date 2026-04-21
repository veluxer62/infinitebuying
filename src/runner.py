"""
무한매수법 V4.0 가이드 도구 — 메인 오케스트레이터.

매일 `python main.py` 실행 시 아래 순서로 동작한다:
  1. 오늘 종가 입력
  2. 현재 포트폴리오 상태 출력
  3. 오늘 체결된 매매 내역 입력 (없으면 건너뜀)
  4. 상태 갱신 (평단, 잔금, T값 등)
  5. 내일 매매 가이드라인 출력
  6. 일별 로그 저장
  7. 회전 완료 시 최종 보고서 생성
"""
from __future__ import annotations

from datetime import date

from .report.daily_logger import DailyLogger, TradeRecord
from .report.final_report import FinalReportGenerator
from .state.manager import PortfolioState, StateManager
from .strategy.calculator import InfiniteBuyingCalculator
from .strategy.guide_builder import GuideBuilder, TradeGuide

_SEP = "─" * 60


class InfiniteBuyingRunner:
    def __init__(
        self,
        state_mgr: StateManager,
        symbol: str = "TQQQ",
        division: int = 40,
        default_capital: float = 0.0,
    ) -> None:
        self.state_mgr = state_mgr
        self.symbol = symbol
        self.division = division
        self.default_capital = default_capital
        self.calc = InfiniteBuyingCalculator()
        self.guide_builder = GuideBuilder()
        self.daily_logger = DailyLogger()
        self.final_reporter = FinalReportGenerator()

    # ══════════════════════════════════════════════════════════════════════════
    # 메인 진입점
    # ══════════════════════════════════════════════════════════════════════════

    def run(self) -> None:
        _header(f"무한매수법 V4.0 가이드 도구  |  {self.symbol} {self.division}분할")

        state = self._load_or_init_state()
        today = date.today().isoformat()

        # ── STEP 1: 오늘 종가 입력 ──
        close_price = _input_float("오늘 종가(USD)를 입력하세요: $")
        state.last_close_price = close_price

        # ── STEP 2: 현재 포트폴리오 출력 ──
        self._print_status(state, close_price)

        # ── STEP 3: 소진모드 체크 ──
        if self.calc.is_exhausted(state.T):
            _warn("소진모드(T≥39) 진입. 소진모드 방법론을 별도로 수행하세요.")
            self.state_mgr.save_state(state)
            return

        # ── STEP 4: 오늘 체결 내역 입력 ──
        trades = self._input_trades(state, close_price)

        # ── STEP 5: 상태 갱신 ──
        if trades:
            self._apply_trades(state, trades, close_price)
            self.state_mgr.save_state(state)
            _info("상태 갱신 완료")
            print()
            self._print_status(state, close_price)

        # ── STEP 6: 내일 가이드라인 ──
        if self.calc.is_exhausted(state.T):
            _warn("T가 39에 도달했습니다. 소진모드 방법론을 수행하세요.")
            self.state_mgr.save_state(state)
            return

        guide = self.guide_builder.build(
            remaining_cash=state.remaining_cash,
            T=state.T,
            avg_price=state.avg_price,
            quantity=state.quantity,
            close_price=close_price,
        )
        self._print_guide(guide)

        # ── STEP 7: 상태 저장 ──
        state.last_run_date = today
        self.state_mgr.save_state(state)

        # ── STEP 8: 일별 로그 ──
        log_path = self.daily_logger.log(today, state, close_price, trades, guide)
        _info(f"일별 로그 저장 → {log_path}")

        # ── STEP 9: 회전 완료 체크 (최종매도 후 수량=0) ──
        if state.quantity == 0 and state.T > 0:
            self._handle_cycle_complete(state, close_price)

    def run_regen_log(self) -> None:
        """--regen-log: 상태 변경 없이 지정 날짜의 로그 파일만 재생성.

        제약조건:
        - state.last_run_date 가 target_date 와 일치해야 한다.
          일치하지 않으면 state가 아직 갱신되지 않은 것이므로 일반 실행을 안내한다.
        - 로그 파일이 존재하고 state 와 일치하면 재생성을 거부한다.
          로그가 없거나 불일치할 때만 재생성을 진행한다.
        """
        import os

        state = self.state_mgr.load_state()
        if state is None:
            print("  상태 파일 없음. 먼저 일반 실행으로 초기화하세요.")
            return

        default_date = state.last_run_date or date.today().isoformat()
        date_input = input(f"  재생성할 날짜 (YYYY-MM-DD) [{default_date}]: ").strip()
        target_date = date_input if date_input else default_date

        # ── 제약 1: state가 해당 날짜로 갱신되어 있어야 한다 ──
        if state.last_run_date != target_date:
            _warn(
                f"state 마지막 실행일({state.last_run_date})이 "
                f"요청 날짜({target_date})와 다릅니다."
            )
            print("  해당 날짜의 데이터가 state에 반영되지 않았습니다.")
            print("  python main.py 를 실행하여 먼저 데이터를 입력하세요.")
            return

        # ── 제약 2: 로그가 존재하고 state와 일치하면 재생성 불필요 ──
        log_path = os.path.join(self.daily_logger.log_dir, f"{target_date}.md")
        if os.path.exists(log_path):
            if _log_matches_state(log_path, state):
                _info("로그 파일이 이미 state와 일치합니다. 재생성 불필요.")
                return
            _warn("로그 파일의 내용이 state와 불일치합니다. 재생성을 진행합니다.")

        close_price = _input_float("종가(USD)를 입력하세요: $")
        trades = self._input_trades_readonly(state)

        guide = self.guide_builder.build(
            remaining_cash=state.remaining_cash,
            T=state.T,
            avg_price=state.avg_price,
            quantity=state.quantity,
            close_price=close_price,
        )

        saved = self.daily_logger.log(target_date, state, close_price, trades, guide)
        _info(f"로그 재생성 완료 → {saved}")

    def _input_trades_readonly(self, state: PortfolioState) -> list[TradeRecord]:
        """상태를 변경하지 않고 체결 내역만 입력받는다."""
        trades: list[TradeRecord] = []

        print(f"\n{_SEP}")
        print("  체결된 매매가 있으면 입력하세요.")
        print("  [b] 매수  [q] 쿼터매도  [f] 최종매도  [n] 없음 (Enter)")
        print(f"{_SEP}")

        while True:
            cmd = input("  선택: ").strip().lower()
            if cmd in ("", "n"):
                break
            elif cmd == "b":
                t = self._input_buy_trade(state, 0.0)
                if t:
                    trades.append(t)
            elif cmd == "q":
                t = self._input_quarter_sell_trade(state)
                if t:
                    trades.append(t)
            elif cmd == "f":
                t = self._input_final_sell_trade(state)
                if t:
                    trades.append(t)
                break
            else:
                print("  b / q / f / n 중에 입력하세요.")
                continue

            more = input("  추가 입력? (y/n): ").strip().lower()
            if more != "y":
                break

        return trades

    def run_status_only(self) -> None:
        """--status: 포트폴리오 현황만 출력 (상태 변경 없음)."""
        state = self.state_mgr.load_state()
        if state is None:
            print("  상태 파일 없음. 첫 실행 시 자동 생성됩니다.")
            return
        close_price = _input_float("현재가(USD)를 입력하세요: $")
        self._print_status(state, close_price)

    # ══════════════════════════════════════════════════════════════════════════
    # 체결 내역 입력
    # ══════════════════════════════════════════════════════════════════════════

    def _input_trades(self, state: PortfolioState, close_price: float) -> list[TradeRecord]:
        trades: list[TradeRecord] = []

        print(f"\n{_SEP}")
        print("  오늘 체결된 매매가 있으면 입력하세요.")
        print("  [b] 매수  [q] 쿼터매도  [f] 최종매도  [n] 없음 (Enter)")
        print(f"{_SEP}")

        while True:
            cmd = input("  선택: ").strip().lower()
            if cmd in ("", "n"):
                break
            elif cmd == "b":
                t = self._input_buy_trade(state, close_price)
                if t:
                    trades.append(t)
            elif cmd == "q":
                t = self._input_quarter_sell_trade(state)
                if t:
                    trades.append(t)
            elif cmd == "f":
                t = self._input_final_sell_trade(state)
                if t:
                    trades.append(t)
                break
            else:
                print("  b / q / f / n 중에 입력하세요.")

            more = input("  추가 입력? (y/n): ").strip().lower()
            if more != "y":
                break

        return trades

    def _input_buy_trade(self, state: PortfolioState, close_price: float) -> TradeRecord | None:
        try:
            qty = int(input("    매수 수량(주): ").strip())
            price = _input_float("    매수 체결가: $")
            if qty <= 0 or price <= 0:
                print("    올바른 값을 입력하세요.")
                return None
            return TradeRecord(side="매수", quantity=qty, price=price)
        except ValueError:
            print("    숫자를 입력하세요.")
            return None

    def _input_quarter_sell_trade(self, state: PortfolioState) -> TradeRecord | None:
        if state.quantity == 0:
            print("    보유 수량이 없습니다.")
            return None
        suggested = state.quantity // 4
        try:
            qty_input = input(f"    쿼터매도 수량(주) [기본: {suggested}]: ").strip()
            qty = int(qty_input) if qty_input else suggested
            price = _input_float("    쿼터매도 체결가: $")
            if qty <= 0 or price <= 0:
                print("    올바른 값을 입력하세요.")
                return None
            return TradeRecord(side="쿼터매도", quantity=qty, price=price)
        except ValueError:
            print("    숫자를 입력하세요.")
            return None

    def _input_final_sell_trade(self, state: PortfolioState) -> TradeRecord | None:
        if state.quantity == 0:
            print("    보유 수량이 없습니다.")
            return None
        try:
            qty_input = input(f"    최종매도 수량(주) [전량: {state.quantity}]: ").strip()
            qty = int(qty_input) if qty_input else state.quantity
            price = _input_float("    최종매도 체결가: $")
            if qty <= 0 or price <= 0:
                print("    올바른 값을 입력하세요.")
                return None
            return TradeRecord(side="최종매도", quantity=qty, price=price)
        except ValueError:
            print("    숫자를 입력하세요.")
            return None

    # ══════════════════════════════════════════════════════════════════════════
    # 상태 갱신
    # ══════════════════════════════════════════════════════════════════════════

    def _apply_trades(
        self, state: PortfolioState, trades: list[TradeRecord], close_price: float
    ) -> None:
        buy_trades = [t for t in trades if t.side == "매수"]
        sell_trades = [t for t in trades if t.side in ("쿼터매도", "최종매도")]

        # ── 매수 처리 ──
        if buy_trades:
            expected_buy = self.calc.calc_buy_amount(state.remaining_cash, state.T)
            total_bought = sum(t.amount for t in buy_trades)

            for t in buy_trades:
                state.avg_price = self.calc.calc_new_avg_price(
                    state.quantity, state.avg_price, t.quantity, t.price
                )
                state.quantity += t.quantity
                state.remaining_cash = max(0.0, state.remaining_cash - t.amount)

            ratio = total_bought / expected_buy if expected_buy > 0 else 0.0
            if ratio >= 0.75:
                state.T = self.calc.next_T_after_full_buy(state.T)
                _info(f"매수 비율 {ratio*100:.1f}% → T+1  (T={state.T:.4f})")
            elif ratio >= 0.25:
                state.T = self.calc.next_T_after_half_buy(state.T)
                _info(f"매수 비율 {ratio*100:.1f}% → T+0.5  (T={state.T:.4f})")
            else:
                _info(f"매수 비율 {ratio*100:.1f}% → T 변동 없음")

        # ── 매도 처리 ──
        for t in sell_trades:
            revenue = t.amount
            cost_basis = t.quantity * state.avg_price
            profit = revenue - cost_basis
            state.total_realized_profit += profit
            state.remaining_cash += revenue
            state.quantity = max(0, state.quantity - t.quantity)

            if t.side == "쿼터매도":
                state.T = self.calc.next_T_after_quarter_sell(state.T)
                _info(f"쿼터매도 체결 → T×0.75  (T={state.T:.4f})  수익: ${profit:,.2f}")
            elif t.side == "최종매도":
                _info(f"최종매도 체결 → 보유={state.quantity}주  실현손익+${profit:,.2f}")

    # ══════════════════════════════════════════════════════════════════════════
    # 회전 완료 처리
    # ══════════════════════════════════════════════════════════════════════════

    def _handle_cycle_complete(self, state: PortfolioState, close_price: float) -> None:
        print(f"\n{'=' * 60}")
        print(f"  {state.cycle}회전 완료!")
        profit = state.total_realized_profit
        pct = profit / state.original_capital * 100 if state.original_capital else 0
        print(f"  실현 수익: ${profit:,.2f}  ({pct:.2f}%)")

        report_path = self.final_reporter.generate(state, close_price)
        _info(f"최종 보고서 → {report_path}")

        if _confirm("다음 회전을 복리로 시작하시겠습니까? (아니면 원래 원금 유지)"):
            new_capital = state.original_capital + state.total_realized_profit
        else:
            new_capital = state.original_capital

        new_state = self.state_mgr.create_initial_state(state.symbol, state.division, new_capital)
        new_state.cycle = state.cycle + 1
        self.state_mgr.save_state(new_state)
        print(f"  {new_state.cycle}회전 시작. 원금: ${new_capital:,.2f}")

    # ══════════════════════════════════════════════════════════════════════════
    # 출력 헬퍼
    # ══════════════════════════════════════════════════════════════════════════

    def _load_or_init_state(self) -> PortfolioState:
        state = self.state_mgr.load_state()
        if state is None:
            print("\n초기 설정을 시작합니다.")
            print(f"  종목: {self.symbol}  |  분할수: {self.division}")
            default_hint = f" [{self.default_capital:,.0f}]" if self.default_capital > 0 else ""
            while True:
                try:
                    raw = input(f"  투자 원금 (USD){default_hint}: $").strip()
                    capital = float(raw) if raw else self.default_capital
                    if capital > 0:
                        break
                    print("  0보다 큰 값을 입력하세요.")
                except ValueError:
                    print("  숫자를 입력하세요.")
            state = self.state_mgr.create_initial_state(self.symbol, self.division, capital)
            self.state_mgr.save_state(state)
            _info(f"초기 상태 생성 완료. {self.symbol} {self.division}분할  원금=${capital:,.2f}")
        return state

    def _print_status(self, state: PortfolioState, close_price: float) -> None:
        phase = self.calc.phase_label(state.T, state.quantity)
        star = (
            self.calc.calc_star_point(state.avg_price, state.T)
            if state.avg_price > 0 else None
        )
        market_val = state.market_value(close_price)
        unrealized = state.unrealized_pnl(close_price)
        ret_pct = state.total_return_pct(close_price)
        pct_T = state.T / state.division * 100

        print(f"\n{_SEP}")
        print(f"  포트폴리오 현황  [{phase}]  T={state.T:.4f}/{state.division} ({pct_T:.1f}%)")
        print(f"{_SEP}")
        print(f"  원금:       ${state.original_capital:>12,.2f}   잔금:  ${state.remaining_cash:>12,.2f}")
        print(f"  평단:       ${state.avg_price:>12.4f}   종가:  ${close_price:>12.2f}")
        print(f"  보유:       {state.quantity:>12}주     평가:  ${market_val:>12,.2f}")
        sign = "+" if unrealized >= 0 else ""
        print(f"  평가손익:  {sign}${unrealized:>11,.2f}   수익률: {sign}{ret_pct:>10.2f}%")
        print(f"  실현손익:   ${state.total_realized_profit:>12,.2f}")
        if star:
            print(f"  별%:        {star.star_pct_display:>11.4f}%   별지점: ${star.star_price:>10.2f}")
        print(f"{_SEP}")

    def _print_guide(self, guide: TradeGuide) -> None:
        print(f"\n{_SEP}")
        print(f"  내일 매매 가이드라인  [{guide.phase}]")
        print(f"{_SEP}")
        print(f"  별%: {guide.star_pct_display:.4f}%    별지점: ${guide.star_price:.2f}")
        print()

        print("  [매수]")
        print(f"    LOC 지정가:   ${guide.buy_price:.2f}  (별지점 - $0.01)")
        print(f"    매수 금액:    ${guide.buy_amount:,.2f}")
        print(f"    매수 수량:    {guide.buy_quantity}주")
        if guide.has_avg_buy:
            print(f"    평단 LOC:     ${guide.avg_buy_price:.2f}  (평균단가)")
            print(f"    평단 금액:    ${guide.avg_buy_amount:,.2f}")
            print(f"    평단 수량:    {guide.avg_buy_quantity}주")

        if guide.has_sell:
            print()
            print("  [매도]")
            print(f"    쿼터매도 LOC: ${guide.quarter_sell_price:.2f}  (별지점)  {guide.quarter_sell_quantity}주")
            print(f"    최종매도:     ${guide.final_sell_price:.2f}  (평단×1.15)  {guide.final_sell_quantity}주")

        print(f"{_SEP}")


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def _header(msg: str) -> None:
    print(f"\n{'═' * 60}")
    print(f"  {msg}")
    print(f"{'═' * 60}")


def _info(msg: str) -> None:
    print(f"  [i] {msg}")


def _warn(msg: str) -> None:
    print(f"  [!] {msg}")


def _confirm(msg: str) -> bool:
    return input(f"\n  {msg} (y/n): ").strip().lower() == "y"


def _log_matches_state(log_path: str, state: "PortfolioState") -> bool:
    """로그 파일의 핵심 수치가 state와 일치하는지 확인한다."""
    import re

    try:
        with open(log_path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return False

    def _extract(pattern: str) -> str | None:
        m = re.search(pattern, text)
        return m.group(1) if m else None

    def _close_enough(a: float, b: float, tol: float = 0.005) -> bool:
        return abs(a - b) <= tol

    raw_cash = _extract(r"\| 잔금 \| \$([\d,]+\.\d+)")
    raw_avg = _extract(r"\| 평균단가 \| \$([\d,]+\.\d+)")
    raw_qty = _extract(r"\| 보유수량 \| (\d+)주")
    raw_T = _extract(r"\| T값 \| ([\d.]+) /")
    raw_profit = _extract(r"\| 누적 실현손익 \| \$([\d,]+\.\d+)")

    if any(v is None for v in (raw_cash, raw_avg, raw_qty, raw_T, raw_profit)):
        return False

    try:
        log_cash = float(raw_cash.replace(",", ""))
        log_avg = float(raw_avg.replace(",", ""))
        log_qty = int(raw_qty)
        log_T = float(raw_T)
        log_profit = float(raw_profit.replace(",", ""))
    except (ValueError, AttributeError):
        return False

    return (
        _close_enough(log_cash, state.remaining_cash)
        and _close_enough(log_avg, state.avg_price)
        and log_qty == state.quantity
        and _close_enough(log_T, state.T)
        and _close_enough(log_profit, state.total_realized_profit)
    )


def _input_float(prompt: str) -> float:
    while True:
        try:
            val = float(input(f"  {prompt}").strip())
            if val > 0:
                return val
            print("  0보다 큰 값을 입력하세요.")
        except ValueError:
            print("  숫자를 입력하세요.")
