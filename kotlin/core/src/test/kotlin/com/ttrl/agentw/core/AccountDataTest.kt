package com.ttrl.agentw.core
import kotlin.test.*
class AccountDataTest{
 private fun snap(t:Long)=BrokerAccountSnapshot("acct1234",Money(100000.0,"INR"),Money(50000.0,"INR"),Money(80000.0,"INR"),Money(1200.0,"INR"),Money(-200.0,"INR"),t,"broker",true)
 @Test fun freshBrokerAccountDataPasses(){assertEquals(100000.0,AccountDataGuard().verify(snap(1000),2000).equity.amount)}
 @Test fun staleBrokerAccountDataFailsClosed(){assertFails{AccountDataGuard().verify(snap(1000),7001)}}
 @Test fun liveAccountDataDoesNotImplyTradePermission(){val s=snap(1000);assertTrue(s.isLiveAccount);assertFailsWith<LiveMoneyDisabled>{ExecutionGateway(object:ExecutionBroker{override fun submit(intent:ExecutionIntent)=BrokerSnapshot("b",intent.intentId,BrokerState.ACKNOWLEDGED,0.0)}).submit(ExecutionIntent("i","d",MarketDomain.INDIA,"NIFTY",ExecutionSide.BUY,1.0,1.0,"r",listOf("e"),true))}}
}
