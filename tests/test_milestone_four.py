from pathlib import Path

import pytest

from portfolio.event_store import DuplicateLedgerEventError, SQLiteLedgerEventStore
from portfolio.ledger_models import LedgerEvent, LedgerEventType
from portfolio.portfolio_ledger import (
    InsufficientCashError,
    InsufficientPositionError,
    PortfolioLedger,
)


def make_ledger(tmp_path: Path) -> PortfolioLedger:
    return PortfolioLedger(SQLiteLedgerEventStore(tmp_path / "portfolio.db"))


def test_ledger_rebuilds_authoritative_state_after_restart(tmp_path):
    ledger = make_ledger(tmp_path)
    ledger.record(LedgerEvent(event_type=LedgerEventType.CASH_DEPOSIT, amount=100_000))
    ledger.record(
        LedgerEvent(
            event_type=LedgerEventType.BUY_FILL,
            symbol="RELIANCE",
            quantity=10,
            price=2_500,
            reference_id="fill-1",
        )
    )
    ledger.record(
        LedgerEvent(
            event_type=LedgerEventType.SELL_FILL,
            symbol="RELIANCE",
            quantity=4,
            price=2_600,
            reference_id="fill-2",
        )
    )
    ledger.record(LedgerEvent(event_type=LedgerEventType.FEE, amount=50))

    restarted = make_ledger(tmp_path)
    state = restarted.state
    assert state.cash_balance == pytest.approx(85_350)
    assert state.realized_pnl == pytest.approx(350)
    assert state.fees_paid == pytest.approx(50)
    assert state.positions["RELIANCE"].quantity == 6
    assert state.positions["RELIANCE"].average_price == pytest.approx(2_500)


def test_buy_cannot_exceed_available_cash(tmp_path):
    ledger = make_ledger(tmp_path)
    ledger.record(LedgerEvent(event_type=LedgerEventType.CASH_DEPOSIT, amount=1_000))
    with pytest.raises(InsufficientCashError):
        ledger.record(
            LedgerEvent(
                event_type=LedgerEventType.BUY_FILL,
                symbol="TCS",
                quantity=2,
                price=600,
            )
        )
    assert ledger.store.count() == 1


def test_sell_cannot_exceed_position(tmp_path):
    ledger = make_ledger(tmp_path)
    ledger.record(LedgerEvent(event_type=LedgerEventType.CASH_DEPOSIT, amount=10_000))
    ledger.record(
        LedgerEvent(
            event_type=LedgerEventType.BUY_FILL,
            symbol="INFY",
            quantity=5,
            price=1_000,
        )
    )
    with pytest.raises(InsufficientPositionError):
        ledger.record(
            LedgerEvent(
                event_type=LedgerEventType.SELL_FILL,
                symbol="INFY",
                quantity=6,
                price=1_100,
            )
        )
    assert ledger.state.positions["INFY"].quantity == 5


def test_duplicate_event_is_rejected(tmp_path):
    store = SQLiteLedgerEventStore(tmp_path / "portfolio.db")
    event = LedgerEvent(event_type=LedgerEventType.CASH_DEPOSIT, amount=1_000)
    store.append(event)
    with pytest.raises(DuplicateLedgerEventError):
        store.append(event)


def test_returned_state_is_not_mutable_authority(tmp_path):
    ledger = make_ledger(tmp_path)
    ledger.record(LedgerEvent(event_type=LedgerEventType.CASH_DEPOSIT, amount=5_000))
    external_copy = ledger.state
    external_copy.cash_balance = 999_999
    assert ledger.state.cash_balance == 5_000
