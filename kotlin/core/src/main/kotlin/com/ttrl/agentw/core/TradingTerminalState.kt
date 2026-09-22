package com.ttrl.agentw.core

data class TradingTerminalState(val domain:MarketDomain,val symbol:String,val quote:LiveQuote?,val account:BrokerAccountSnapshot?,val providerHealth:List<ProviderHealth>,val liveExecutionEnabled:Boolean=false){
 val dataReady:Boolean get()=quote!=null&&account!=null&&providerHealth.isNotEmpty()&&providerHealth.all{it.state==ProviderState.CONNECTED}
 val safeMode:Boolean get()=!liveExecutionEnabled
}
class TradingTerminalService(private val market:LiveMarketDataProvider,private val account:AccountDataProvider){
 fun load(domain:MarketDomain,symbol:String,nowMs:Long,health:List<ProviderHealth>):TradingTerminalState{
  require(health.isNotEmpty()){"provider health required"}
  require(health.all{ProviderHealthGuard().executable(it,nowMs)}){"provider unhealthy or stale"}
  val q=LiveQuoteGuard().verify(market.quote(domain,symbol),nowMs)
  val a=AccountDataGuard().verify(account.account(),nowMs)
  return TradingTerminalState(domain,symbol,q,a,health,false)
 }
}
