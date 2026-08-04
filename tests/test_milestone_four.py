import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from portfolio.event_store import (
    DuplicateLedgerEventError,
    LedgerIntegrityError,
    SQLiteLedgerEventStore,
)
from portfolio.ledger_models import LedgerEvent, LedgerEventType
from portfolio.portfolio_ledger import (
    InsufficientCashError,
    InsufficientPositionError,
    PortfolioLedger,
)
from portfolio.valuation import (
    MarkToMarketEngine,
    MissingPriceError,
    ReferencePrice,
    SQLiteValuationSnapshotStore,
    StalePriceError,
)


def make_ledger(tmp_path: Path) -> PortfolioLedger:
    return PortfolioLedger(SQLiteLedgerEventStore(tmp_path / "portfolio.db"))


def funded_position(tmp_path: Path) -> PortfolioLedger:
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
    return ledger


def test_ledger_rebuilds_authoritative_state_after_restart(tmp_path):
    ledger = funded_position(tmp_path)
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


def test_duplicate_external_reference_is_rejected(tmp_path):
    store = SQLiteLedgerEventStore(tmp_path / "portfolio.db")
    store.append(
        LedgerEvent(
            event_type=LedgerEventType.BUY_FILL,
            symbol="TCS",
            quantity=1,
            price=3_500,
            reference_id="broker-fill-42",
        )
    )
    with pytest.raises(DuplicateLedgerEventError):
        store.append(
            LedgerEvent(
                event_type=LedgerEventType.BUY_FILL,
                symbol="TCS",
                quantity=1,
                price=3_500,
                reference_id="broker-fill-42",
            )
        )
    assert store.count() == 1


def test_tampered_financial_event_is_detected(tmp_path):
    path = tmp_path / "portfolio.db"
    store = SQLiteLedgerEventStore(path)
    store.append(LedgerEvent(event_type=LedgerEventType.CASH_DEPOSIT, amount=10_000))

    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE portfolio_events SET payload = REPLACE(payload, '10000.0', '90000.0')"
        )

    with pytest.raises(LedgerIntegrityError):
        store.read_all()


def test_returned_state_is_not_mutable_authority(tmp_path):
    ledger = make_ledger(tmp_path)
    ledger.record(LedgerEvent(event_type=LedgerEventType.CASH_DEPOSIT, amount=5_000))
    external_copy = ledger.state
    external_copy.cash_balance = 999_999
    assert ledger.state.cash_balance == 5_000


def test_mark_to_market_calculates_unrealized_and_nlv(tmp_path):
    ledger = funded_position(tmp_path)
    now = datetime.now(timezone.utc)
    valuation = MarkToMarketEngine().value(
        ledger.state,
        {"RELIANCE": ReferencePrice("reliance", 2_620, now)},
        valued_at=now,
    )

    assert valuation.cash_balance == pytest.approx(75_000)
    assert valuation.gross_market_value == pytest.approx(26_200)
    assert valuation.unrealized_pnl == pytest.approx(1_200)
    assert valuation.net_liquidation_value == pytest.approx(101_200)
    assert valuation.positions[0].market_price == pytest.approx(2_620)


def test_mark_to_market_blocks_missing_price(tmp_path):
    ledger = funded_position(tmp_path)
    with pytest.raises(MissingPriceError):
        MarkToMarketEngine().value(ledger.state, {})


def test_mark_to_market_blocks_stale_price(tmp_path):
    ledger = funded_position(tmp_path)
    now = datetime.now(timezone.utc)
    stale = ReferencePrice("RELIANCE", 2_620, now - timedelta(seconds=16))
    with pytest.raises(StalePriceError):
        MarkToMarketEngine(max_price_age=timedelta(seconds=15)).value(
            ledger.state,
            {"RELIANCE": stale},
            valued_at=now,
        )


def test_valuation_snapshot_survives_restart(tmp_path):
    ledger = funded_position(tmp_path)
    now = datetime.now(timezone.utc)
    valuation = MarkToMarketEngine().value(
        ledger.state,
        {"RELIANCE": ReferencePrice("RELIANCE", 2_610, now)},
        valued_at=now,
    )
    path = tmp_path / "valuations.db"
    SQLiteValuationSnapshotStore(path).append(valuation)

    latest = SQLiteValuationSnapshotStore(path).latest()
    assert latest is not None
    assert latest["net_liquidation_value"] == pytest.approx(101_100)
    assert latest["positions"][0]["symbol"] == "RELIANCE"
