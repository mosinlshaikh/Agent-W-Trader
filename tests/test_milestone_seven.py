import pytest

from simulation.exchange import (
    BookLevel,
    ExchangeSimulator,
    Side,
    SimOrder,
    SimOrderStatus,
    SimOrderType,
    UnknownOrderError,
)


def test_market_order_waits_for_latency_then_fills():
    exchange = ExchangeSimulator(latency_ms=10)
    exchange.seed_book(bids=[BookLevel(99, 10)], asks=[BookLevel(101, 10)])
    order = SimOrder("TCS", Side.BUY, 5, SimOrderType.MARKET)
    exchange.submit(order)
    exchange.advance_to(9)
    assert order.status == SimOrderStatus.PENDING
    exchange.advance_to(10)
    assert order.status == SimOrderStatus.FILLED
    assert exchange.fills[0].price == pytest.approx(101)


def test_market_order_partially_fills_and_rejects_remainder():
    exchange = ExchangeSimulator(latency_ms=0)
    exchange.seed_book(bids=[], asks=[BookLevel(100, 3)])
    order = SimOrder("INFY", Side.BUY, 5, SimOrderType.MARKET)
    exchange.submit(order)
    exchange.advance_to(0)
    assert order.status == SimOrderStatus.PARTIALLY_FILLED
    assert order.remaining_quantity == 2
    assert order.rejection_reason == "INSUFFICIENT_LIQUIDITY"


def test_non_crossing_limit_order_rests():
    exchange = ExchangeSimulator(latency_ms=0)
    exchange.seed_book(bids=[BookLevel(99, 10)], asks=[BookLevel(101, 10)])
    order = SimOrder("RELIANCE", Side.BUY, 5, SimOrderType.LIMIT, limit_price=100)
    exchange.submit(order)
    exchange.advance_to(0)
    assert order.status == SimOrderStatus.OPEN
    assert any(event.event_type == "RESTING" for event in exchange.events)


def test_price_time_priority_fills_earlier_order_first():
    exchange = ExchangeSimulator(latency_ms=0)
    exchange.seed_book(bids=[], asks=[])
    first = SimOrder("SBIN", Side.BUY, 5, SimOrderType.LIMIT, limit_price=100)
    second = SimOrder("SBIN", Side.BUY, 5, SimOrderType.LIMIT, limit_price=100)
    exchange.submit(first)
    exchange.submit(second)
    exchange.advance_to(0)
    exchange.execute_external_trade(price=100, quantity=6, aggressor_side=Side.SELL)
    assert first.status == SimOrderStatus.FILLED
    assert second.status == SimOrderStatus.PARTIALLY_FILLED
    assert second.remaining_quantity == 4


def test_better_price_has_priority_over_earlier_order():
    exchange = ExchangeSimulator(latency_ms=0)
    exchange.seed_book(bids=[], asks=[])
    lower = SimOrder("HDFCBANK", Side.BUY, 5, SimOrderType.LIMIT, limit_price=99)
    higher = SimOrder("HDFCBANK", Side.BUY, 5, SimOrderType.LIMIT, limit_price=100)
    exchange.submit(lower)
    exchange.submit(higher)
    exchange.advance_to(0)
    exchange.execute_external_trade(price=99, quantity=5, aggressor_side=Side.SELL)
    assert higher.status == SimOrderStatus.FILLED
    assert lower.status == SimOrderStatus.OPEN


def test_halted_exchange_rejects_activation():
    exchange = ExchangeSimulator(latency_ms=5)
    exchange.set_halted(True)
    order = SimOrder("NIFTY", Side.BUY, 1, SimOrderType.MARKET)
    exchange.submit(order)
    exchange.advance_to(5)
    assert order.status == SimOrderStatus.REJECTED
    assert order.rejection_reason == "TRADING_HALTED"


def test_circuit_limit_rejects_limit_order():
    exchange = ExchangeSimulator(latency_ms=0)
    exchange.set_circuit_limits(90, 110)
    order = SimOrder("ABC", Side.BUY, 1, SimOrderType.LIMIT, limit_price=111)
    exchange.submit(order)
    exchange.advance_to(0)
    assert order.status == SimOrderStatus.REJECTED
    assert order.rejection_reason == "PRICE_OUTSIDE_CIRCUIT"


def test_cancel_fill_race_is_deterministic():
    exchange = ExchangeSimulator(latency_ms=10)
    exchange.seed_book(bids=[], asks=[BookLevel(100, 5)])
    order = SimOrder("ITC", Side.BUY, 5, SimOrderType.MARKET)
    exchange.submit(order)
    exchange.cancel(order.order_id)
    exchange.advance_to(10)
    assert order.status == SimOrderStatus.FILLED
    assert any(event.event_type == "CANCEL_REJECTED" for event in exchange.events)


def test_replace_resets_priority():
    exchange = ExchangeSimulator(latency_ms=0)
    exchange.seed_book(bids=[], asks=[])
    first = SimOrder("AXISBANK", Side.BUY, 5, SimOrderType.LIMIT, limit_price=100)
    second = SimOrder("AXISBANK", Side.BUY, 5, SimOrderType.LIMIT, limit_price=100)
    exchange.submit(first)
    exchange.submit(second)
    exchange.advance_to(0)
    exchange.replace(first.order_id, quantity=5, limit_price=100)
    exchange.advance_to(0)
    exchange.execute_external_trade(price=100, quantity=5, aggressor_side=Side.SELL)
    assert second.status == SimOrderStatus.FILLED


def test_market_impact_worsens_later_level_price():
    exchange = ExchangeSimulator(latency_ms=0, market_impact_bps_per_full_level=10)
    exchange.seed_book(bids=[], asks=[BookLevel(100, 1), BookLevel(101, 1)])
    order = SimOrder("MARUTI", Side.BUY, 2, SimOrderType.MARKET)
    exchange.submit(order)
    exchange.advance_to(0)
    assert len(exchange.fills) == 2
    assert exchange.fills[1].price > 101


def test_unknown_order_fails_closed():
    exchange = ExchangeSimulator()
    with pytest.raises(UnknownOrderError):
        exchange.cancel("missing")
