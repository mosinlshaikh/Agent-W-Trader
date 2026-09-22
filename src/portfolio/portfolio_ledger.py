"""Authoritative event-sourced portfolio truth engine."""

from __future__ import annotations

from copy import deepcopy

from portfolio.event_store import SQLiteLedgerEventStore
from portfolio.ledger_models import (
    LedgerEvent,
    LedgerEventType,
    PortfolioState,
    PositionState,
)


class InsufficientCashError(RuntimeError):
    pass


class InsufficientPositionError(RuntimeError):
    pass


class PortfolioLedger:
    """Rebuilds financial state exclusively from an append-only event stream."""

    def __init__(self, store: SQLiteLedgerEventStore) -> None:
        self.store = store
        self._state = self._replay(store.read_all())

    @property
    def state(self) -> PortfolioState:
        return deepcopy(self._state)

    def record(self, event: LedgerEvent) -> PortfolioState:
        candidate = deepcopy(self._state)
        self._apply(candidate, event)
        self.store.append(event)
        self._state = candidate
        return self.state

    def rebuild(self) -> PortfolioState:
        self._state = self._replay(self.store.read_all())
        return self.state

    def _replay(self, events: list[LedgerEvent]) -> PortfolioState:
        state = PortfolioState()
        for event in events:
            self._apply(state, event)
        return state

    def _apply(self, state: PortfolioState, event: LedgerEvent) -> None:
        if event.event_type == LedgerEventType.CASH_DEPOSIT:
            state.cash_balance += event.amount

        elif event.event_type == LedgerEventType.CASH_WITHDRAWAL:
            if event.amount > state.cash_balance:
                raise InsufficientCashError("cash withdrawal exceeds available balance")
            state.cash_balance -= event.amount

        elif event.event_type == LedgerEventType.FEE:
            if event.amount > state.cash_balance:
                raise InsufficientCashError("fee exceeds available cash")
            state.cash_balance -= event.amount
            state.fees_paid += event.amount
            state.realized_pnl -= event.amount

        elif event.event_type == LedgerEventType.BUY_FILL:
            assert event.symbol is not None
            cost = event.quantity * event.price
            if cost > state.cash_balance:
                raise InsufficientCashError("buy fill exceeds available cash")
            position = state.positions.get(event.symbol) or PositionState(symbol=event.symbol)
            total_cost = position.quantity * position.average_price + cost
            position.quantity += event.quantity
            position.average_price = total_cost / position.quantity
            state.positions[event.symbol] = position
            state.cash_balance -= cost

        elif event.event_type == LedgerEventType.SELL_FILL:
            assert event.symbol is not None
            position = state.positions.get(event.symbol)
            if position is None or event.quantity > position.quantity:
                raise InsufficientPositionError("sell fill exceeds long position")
            proceeds = event.quantity * event.price
            pnl = (event.price - position.average_price) * event.quantity
            position.quantity -= event.quantity
            position.realized_pnl += pnl
            state.realized_pnl += pnl
            state.cash_balance += proceeds
            if position.quantity == 0:
                del state.positions[event.symbol]
            else:
                state.positions[event.symbol] = position

        state.last_event_id = event.event_id
