package com.ttrl.agentw.core
import kotlin.test.*
class TradingTerminalStateTest{
 private class M:LiveMarketDataProvider{override fun quote(domain:MarketDomain,symbol:String)=LiveQuote(domain,symbol,99.0,101.0,100.0,1000,"feed","q1")}
 private class A:AccountDataProvider{override fun account()=BrokerAccountSnapshot("acct",Money(100000.0,"INR"),Money(50000.0,"INR"),Money(80000.0,"INR"),Money(0.0,"INR"),Money(0.0,"INR"),1000,"broker",true);override fun positions()=emptyList<BrokerPosition>()}
 private fun health(state:ProviderState=ProviderState.CONNECTED,last:Long=1000)=listOf(ProviderHealth("broker",ProviderKind.BROKER_ACCOUNT,state,1000,last),ProviderHealth("feed",ProviderKind.MARKET_DATA,state,1000,last))
 @Test fun healthyRealDataLoadsButLiveExecutionStaysOff(){val s=TradingTerminalService(M(),A()).load(MarketDomain.INDIA,"NIFTY",2000,health());assertTrue(s.dataReady);assertFalse(s.liveExecutionEnabled);assertTrue(s.safeMode)}
 @Test fun disconnectedProviderBlocksTerminal(){assertFails{TradingTerminalService(M(),A()).load(MarketDomain.INDIA,"NIFTY",2000,health(ProviderState.DISCONNECTED))}}
 @Test fun staleProviderBlocksTerminal(){assertFails{TradingTerminalService(M(),A()).load(MarketDomain.INDIA,"NIFTY",7001,health())}}
}
