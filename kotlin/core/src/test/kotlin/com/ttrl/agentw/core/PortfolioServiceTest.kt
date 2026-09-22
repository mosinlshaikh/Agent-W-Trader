package com.ttrl.agentw.core
import kotlin.test.*
class PortfolioServiceTest{
 private class A:AccountDataProvider{override fun account()=BrokerAccountSnapshot("a",Money(100000.0,"INR"),Money(50000.0,"INR"),Money(80000.0,"INR"),Money(0.0,"INR"),Money(0.0,"INR"),1000,"broker",true);override fun positions()=listOf(BrokerPosition("ABC",10.0,Money(100.0,"INR"),Money(0.0,"INR"),Money(0.0,"INR")))}
 private class M(private val t:Long=1000):LiveMarketDataProvider{override fun quote(domain:MarketDomain,symbol:String)=LiveQuote(domain,symbol,109.0,111.0,110.0,t,"market-feed","quote-1")}
 @Test fun realQuoteMarksPortfolio(){val p=PortfolioService(A(),M()).snapshot(MarketDomain.INDIA,2000);assertEquals(1100.0,p.positions.single().marketValue.amount);assertEquals(100.0,p.positions.single().unrealizedPnl.amount)}
 @Test fun staleQuoteBlocksPortfolio(){assertFails{PortfolioService(A(),M()).snapshot(MarketDomain.INDIA,7001)}}
}
