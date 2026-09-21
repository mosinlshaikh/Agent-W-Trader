from __future__ import annotations
from collections.abc import Mapping
from market_domains.models import EvidenceStatus,MarketEvidence
from .contracts import AgentAction,AgentProposal

class EvidenceFirewallRejected(RuntimeError): pass
class EvidenceFirewall:
    """Rejects AI proposals that cannot be tied to verified machine evidence."""
    def validate(self,proposal:AgentProposal,evidence:Mapping[str,MarketEvidence])->AgentProposal:
        if proposal.action in {AgentAction.BUY,AgentAction.SELL} and not proposal.evidence_ids:
            raise EvidenceFirewallRejected("directional action has no evidence")
        for eid in proposal.evidence_ids:
            item=evidence.get(eid)
            if item is None: raise EvidenceFirewallRejected(f"unknown evidence id: {eid}")
            if item.status!=EvidenceStatus.VERIFIED: raise EvidenceFirewallRejected(f"evidence not verified: {eid}")
            if item.domain!=proposal.domain: raise EvidenceFirewallRejected("cross-domain evidence blocked")
            if item.instrument!=proposal.instrument.strip().upper(): raise EvidenceFirewallRejected("cross-instrument evidence blocked")
        if proposal.action in {AgentAction.BUY,AgentAction.SELL} and not proposal.invalidation:
            raise EvidenceFirewallRejected("directional action requires invalidation condition")
        return proposal
