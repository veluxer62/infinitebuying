"""포트폴리오 상태 영속화 (state.json)."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import date
from typing import Optional


@dataclass
class PortfolioState:
    symbol: str
    division: int
    original_capital: float
    remaining_cash: float
    T: float
    avg_price: float
    quantity: int
    mode: str                      # "general" | "exhausted"
    cycle: int
    start_date: str
    last_run_date: Optional[str] = None
    total_realized_profit: float = 0.0
    last_close_price: float = 0.0

    def is_initial(self) -> bool:
        return self.quantity == 0 and self.T == 0.0

    def invested_amount(self) -> float:
        return self.original_capital - self.remaining_cash

    def market_value(self, price: float) -> float:
        return self.quantity * price

    def unrealized_pnl(self, price: float) -> float:
        return (price - self.avg_price) * self.quantity

    def total_return_pct(self, price: float) -> float:
        """평가손익 / 원금 × 100"""
        if self.original_capital == 0:
            return 0.0
        return self.unrealized_pnl(price) / self.original_capital * 100


class StateManager:
    def __init__(
        self,
        state_file: str = "data/state.json",
        log_dir: str = "data/logs",
    ) -> None:
        self.state_file = state_file
        self.log_dir = log_dir
        os.makedirs(os.path.dirname(state_file), exist_ok=True)

    def load_state(self) -> Optional[PortfolioState]:
        if not os.path.exists(self.state_file):
            return None
        with open(self.state_file, encoding="utf-8") as f:
            data = json.load(f)
        return PortfolioState(**data)

    def save_state(self, state: PortfolioState) -> None:
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(asdict(state), f, ensure_ascii=False, indent=2)

    def create_initial_state(
        self, symbol: str, division: int, capital: float
    ) -> PortfolioState:
        return PortfolioState(
            symbol=symbol,
            division=division,
            original_capital=capital,
            remaining_cash=capital,
            T=0.0,
            avg_price=0.0,
            quantity=0,
            mode="general",
            cycle=1,
            start_date=date.today().isoformat(),
        )

    def reset(self) -> None:
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        if os.path.isdir(self.log_dir):
            for fname in os.listdir(self.log_dir):
                fpath = os.path.join(self.log_dir, fname)
                if os.path.isfile(fpath):
                    os.remove(fpath)
