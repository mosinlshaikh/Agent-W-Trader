from validation.performance import PerformanceReport,PerformanceValidator,TradeResult,ValidationLimits
from validation.walk_forward import ValidationWindow,WalkForwardValidator

def test_costs_are_deducted_from_strategy_pnl():
 r=PerformanceValidator().evaluate([TradeResult(gross_pnl=100,fees=10,slippage=20)],10000,ValidationLimits(min_trades=1,min_profit_factor=.1));assert r.net_pnl==70

def test_large_drawdown_fails_even_if_later_profitable():
 ts=[TradeResult(gross_pnl=-2000),TradeResult(gross_pnl=3000)]
 r=PerformanceValidator().evaluate(ts,10000,ValidationLimits(min_trades=2,max_drawdown_pct=10,min_profit_factor=.1));assert not r.passed;assert "maximum drawdown exceeded" in r.reasons

def test_partial_fill_quality_is_enforced():
 ts=[TradeResult(gross_pnl=100,partial_fill_ratio=.2) for _ in range(3)]
 r=PerformanceValidator().evaluate(ts,10000,ValidationLimits(min_trades=3,min_profit_factor=.1,min_fill_ratio=.8));assert not r.passed

def report(passed): return PerformanceReport(trades=50,net_pnl=1000,max_drawdown_pct=5,profit_factor=1.5,avg_fill_ratio=.95,passed=passed,reasons=[] if passed else ["failed"])

def test_walk_forward_rejects_in_sample_only_success():
 w=ValidationWindow(name="2026-Q1",in_sample=report(True),out_of_sample=report(False));r=WalkForwardValidator().certify([w]);assert not r.passed;assert r.failed_windows==["2026-Q1"]

def test_all_out_of_sample_windows_must_pass():
 ws=[ValidationWindow(name="w1",in_sample=report(True),out_of_sample=report(True)),ValidationWindow(name="w2",in_sample=report(True),out_of_sample=report(True))];assert WalkForwardValidator().certify(ws).passed
