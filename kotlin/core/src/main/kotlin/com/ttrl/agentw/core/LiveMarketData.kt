package com.ttrl.agentw.core

data class LiveQuote(val domain:MarketDomain,val symbol:String,val bid:Double?,val ask:Double?,val last:Double,val observedAtEpochMs:Long,val provider:String,val sourceReference:String){init{require(symbol.isNotBlank());require(last>0);require(provider.isNotBlank());require(sourceReference.isNotBlank());require(bid==null||bid>0);require(ask==null||ask>0)}}
interface LiveMarketDataProvider{fun quote(domain:MarketDomain,symbol:String):LiveQuote}
class LiveQuoteGuard(private val maxAgeMs:Long=5_000){fun verify(q:LiveQuote,nowMs:Long):LiveQuote{require(nowMs>=q.observedAtEpochMs){"future quote"};require(nowMs-q.observedAtEpochMs<=maxAgeMs){"stale quote"};if(q.bid!=null&&q.ask!=null)require(q.bid<=q.ask){"crossed quote"};return q}}
