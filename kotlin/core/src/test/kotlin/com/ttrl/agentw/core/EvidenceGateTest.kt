package com.ttrl.agentw.core
import kotlin.test.*
class EvidenceGateTest {
 @Test fun verifiedEvidencePasses(){ val e=EvidenceRef("e1",MarketDomain.INDIA,"NIFTY",EvidenceStatus.VERIFIED,"feed"); assertEquals(1,EvidenceGate().requireVerified(MarketDomain.INDIA,"NIFTY",listOf(e)).size) }
 @Test fun staleEvidenceFailsClosed(){ val e=EvidenceRef("e1",MarketDomain.INDIA,"NIFTY",EvidenceStatus.STALE,"feed"); assertFailsWith<EvidenceRejected>{EvidenceGate().requireVerified(MarketDomain.INDIA,"NIFTY",listOf(e))} }
 @Test fun crossMarketEvidenceFailsClosed(){ val e=EvidenceRef("e1",MarketDomain.CRYPTO,"BTCUSD",EvidenceStatus.VERIFIED,"feed"); assertFailsWith<EvidenceRejected>{EvidenceGate().requireVerified(MarketDomain.FOREX,"BTCUSD",listOf(e))} }
}
