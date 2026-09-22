package com.ttrl.agentw.core

enum class MarketDomain { INDIA, FOREX, CRYPTO, INTERNATIONAL }
enum class EvidenceStatus { VERIFIED, STALE, CONFLICTED, INSUFFICIENT, BLOCKED }
data class EvidenceRef(val id:String,val domain:MarketDomain,val instrument:String,val status:EvidenceStatus,val provenance:String) {
    init { require(id.isNotBlank()); require(instrument.isNotBlank()); require(provenance.isNotBlank()) }
    val executable:Boolean get()=status==EvidenceStatus.VERIFIED
}
