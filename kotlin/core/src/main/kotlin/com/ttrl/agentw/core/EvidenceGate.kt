package com.ttrl.agentw.core

class EvidenceRejected(message:String):IllegalStateException(message)
class EvidenceGate {
    fun requireVerified(domain:MarketDomain,instrument:String,evidence:List<EvidenceRef>):List<EvidenceRef> {
        if(evidence.isEmpty()) throw EvidenceRejected("evidence required")
        val normalized=instrument.trim().uppercase()
        evidence.forEach {
            if(!it.executable) throw EvidenceRejected("non-verified evidence: ${it.id}")
            if(it.domain!=domain) throw EvidenceRejected("cross-domain evidence blocked")
            if(it.instrument.trim().uppercase()!=normalized) throw EvidenceRejected("cross-instrument evidence blocked")
        }
        return evidence
    }
}
