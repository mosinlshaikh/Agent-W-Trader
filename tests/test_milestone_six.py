from datetime import date, datetime, timezone

import pytest

from costs.trading_cost_engine import (
    FeeSchedule,
    InstrumentSegment,
    MissingFeeScheduleError,
    OverlappingFeeScheduleError,
    SQLiteFeeScheduleStore,
    TradeCostInput,
    TradeSide,
    TradingCostEngine,
)


def schedule(**overrides):
    values = dict(
        schedule_id="equity-2026",
        segment=InstrumentSegment.EQUITY_INTRADAY,
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        brokerage_rate=0.0003,
        brokerage_cap=20.0,
        stt_buy_rate=0.0,
        stt_sell_rate=0.00025,
        exchange_rate=0.00003,
        sebi_rate=0.000001,
        gst_rate=0.18,
        stamp_buy_rate=0.00003,
        stamp_sell_rate=0.0,
        slippage_bps=2.0,
    )
    values.update(overrides)
    return FeeSchedule(**values)


def trade(**overrides):
    values = dict(
        trade_id="trade-1",
        segment=InstrumentSegment.EQUITY_INTRADAY,
        side=TradeSide.SELL,
        quantity=100,
        execution_price=101.0,
        reference_price=100.8,
        traded_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
        gross_pnl=500.0,
    )
    values.update(overrides)
    return TradeCostInput(**values)


def test_true_net_pnl_deducts_all_cost_components(tmp_path):
    store = SQLiteFeeScheduleStore(tmp_path / "fees.db")
    store.add(schedule())
    result = TradingCostEngine(store).calculate(trade())

    assert result.schedule_id == "equity-2026"
    assert result.turnover == pytest.approx(10_100)
    assert result.brokerage == pytest.approx(3.03)
    assert result.stt == pytest.approx(2.525)
    assert result.exchange_charges == pytest.approx(0.303)
    assert result.sebi_charges == pytest.approx(0.0101)
    assert result.gst == pytest.approx((3.03 + 0.303 + 0.0101) * 0.18)
    assert result.stamp_duty == 0
    assert result.observed_slippage == pytest.approx(20.0)
    assert result.total_costs > 0
    assert result.net_pnl == pytest.approx(result.gross_pnl - result.total_costs)


def test_brokerage_cap_is_enforced(tmp_path):
    store = SQLiteFeeScheduleStore(tmp_path / "fees.db")
    store.add(schedule(brokerage_rate=0.01, brokerage_cap=20.0))
    result = TradingCostEngine(store).calculate(trade(quantity=10_000))
    assert result.brokerage == 20.0


def test_buy_and_sell_side_specific_levies(tmp_path):
    store = SQLiteFeeScheduleStore(tmp_path / "fees.db")
    store.add(schedule(stt_buy_rate=0.001, stt_sell_rate=0.002, stamp_buy_rate=0.003))
    engine = TradingCostEngine(store)
    buy = engine.calculate(trade(side=TradeSide.BUY))
    sell = engine.calculate(trade(side=TradeSide.SELL))
    assert buy.stt < sell.stt
    assert buy.stamp_duty > 0
    assert sell.stamp_duty == 0


def test_observed_slippage_cannot_be_hidden_by_lower_model(tmp_path):
    store = SQLiteFeeScheduleStore(tmp_path / "fees.db")
    store.add(schedule(slippage_bps=0.1))
    result = TradingCostEngine(store).calculate(
        trade(execution_price=102.0, reference_price=100.0, quantity=10)
    )
    assert result.observed_slippage == 20.0
    assert result.total_costs >= 20.0


def test_modeled_slippage_is_used_when_larger(tmp_path):
    store = SQLiteFeeScheduleStore(tmp_path / "fees.db")
    store.add(schedule(slippage_bps=100.0))
    result = TradingCostEngine(store).calculate(
        trade(execution_price=100.0, reference_price=99.99, quantity=100)
    )
    assert result.modeled_slippage == pytest.approx(100.0)
    assert result.total_costs >= 100.0


def test_schedule_is_resolved_by_trade_date(tmp_path):
    store = SQLiteFeeScheduleStore(tmp_path / "fees.db")
    store.add(schedule(schedule_id="h1", effective_to=date(2026, 6, 30)))
    store.add(
        schedule(
            schedule_id="h2",
            effective_from=date(2026, 7, 1),
            effective_to=date(2026, 12, 31),
            brokerage_rate=0.0005,
        )
    )
    result = TradingCostEngine(store).calculate(
        trade(traded_at=datetime(2026, 8, 1, tzinfo=timezone.utc))
    )
    assert result.schedule_id == "h2"


def test_missing_schedule_fails_closed(tmp_path):
    store = SQLiteFeeScheduleStore(tmp_path / "fees.db")
    with pytest.raises(MissingFeeScheduleError):
        TradingCostEngine(store).calculate(trade())


def test_overlapping_schedules_are_rejected(tmp_path):
    store = SQLiteFeeScheduleStore(tmp_path / "fees.db")
    store.add(schedule())
    with pytest.raises(OverlappingFeeScheduleError):
        store.add(schedule(schedule_id="overlap", effective_from=date(2026, 6, 1)))


def test_invalid_schedule_dates_and_rates_are_rejected():
    with pytest.raises(ValueError):
        schedule(effective_from=date(2026, 2, 1), effective_to=date(2026, 1, 1))
    with pytest.raises(ValueError):
        schedule(gst_rate=-0.01)


def test_timezone_naive_trade_is_rejected():
    with pytest.raises(ValueError):
        trade(traded_at=datetime(2026, 6, 1, 10, 0))
