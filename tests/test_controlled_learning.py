import pytest
from learning.journal import LearningJournal,OutcomeRecord
from learning.promotion import CandidateChange,PromotionGate,PromotionStatus
from market_domains.models import MarketDomain

def outcome(id="d1",pnl=100,fees=10,slippage=5):return OutcomeRecord(decision_id=id,domain=MarketDomain.INDIA,instrument="NIFTY",strategy_id="trend-v1",agent_ids=["trend","news"],evidence_ids=["e1"],order_id="o1",fill_ids=["f1"],gross_pnl=pnl,fees=fees,slippage=slippage)
def test_journal_attributes_net_outcome():
 j=LearningJournal();j.append(outcome());a=j.attribution("trend-v1");assert a.observations==1;assert a.net_pnl==85;assert a.wins==1
def test_duplicate_outcome_cannot_train_twice():
 j=LearningJournal();j.append(outcome());
 with pytest.raises(ValueError,match="duplicate"):j.append(outcome())
def test_unvalidated_learning_change_is_blocked():
 c=CandidateChange(candidate_id="c1",strategy_id="trend-v2",description="new threshold",evidence_refs=["e1"]);d=PromotionGate().evaluate(c);assert d.status==PromotionStatus.BLOCKED;assert not d.production_applied
def test_validated_candidate_still_requires_review_not_auto_production():
 c=CandidateChange(candidate_id="c2",strategy_id="trend-v2",description="validated candidate",backtest_passed=True,walk_forward_passed=True,paper_validation_passed=True,evidence_refs=["e1"]);d=PromotionGate().evaluate(c);assert d.status==PromotionStatus.READY_FOR_HUMAN_REVIEW;assert d.production_applied is False
def test_risk_limit_change_never_self_applies():
 c=CandidateChange(candidate_id="c3",strategy_id="risk-v2",description="raise risk",changes_risk_limits=True,backtest_passed=True,walk_forward_passed=True,paper_validation_passed=True,evidence_refs=["e1"]);d=PromotionGate().evaluate(c);assert d.status==PromotionStatus.READY_FOR_HUMAN_REVIEW;assert "human approval" in " ".join(d.reasons);assert not d.production_applied
