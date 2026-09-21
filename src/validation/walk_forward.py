from __future__ import annotations
from pydantic import BaseModel
from .performance import PerformanceReport

class ValidationWindow(BaseModel):
    name:str
    in_sample:PerformanceReport
    out_of_sample:PerformanceReport

class WalkForwardReport(BaseModel):
    passed:bool
    windows:int
    failed_windows:list[str]
    reason:str

class WalkForwardValidator:
    """Requires out-of-sample success; in-sample profit alone cannot certify a strategy."""
    def certify(self,windows:list[ValidationWindow])->WalkForwardReport:
        if not windows: return WalkForwardReport(passed=False,windows=0,failed_windows=[],reason="no walk-forward windows")
        failed=[w.name for w in windows if not w.out_of_sample.passed]
        return WalkForwardReport(passed=not failed,windows=len(windows),failed_windows=failed,reason="all out-of-sample windows passed" if not failed else "out-of-sample validation failed")
