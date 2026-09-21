package com.ttrl.agentw.core

/** Broker-sourced account data. No fabricated balances are permitted. */
data class Money(val amount:Double,val currency:String){init{require(amount.isFinite());require(currency.isNotBlank())}}
data class BrokerAccountSnapshot(val accountId:String,val equity:Money,val cash:Money,val buyingPower:Money,val realizedPnl:Money,val unrealizedPnl:Money,val observedAtEpochMs:Long,val provider:String,val isLiveAccount:Boolean){init{require(accountId.isNotBlank());require(provider.isNotBlank());require(equity.currency==cash.currency&&cash.currency==buyingPower.currency)}}
data class BrokerPosition(val symbol:String,val quantity:Double,val averagePrice:Money,val marketPrice:Money,val unrealizedPnl:Money){init{require(symbol.isNotBlank());require(quantity.isFinite())}}
interface AccountDataProvider{fun account():BrokerAccountSnapshot;fun positions():List<BrokerPosition>}
class AccountDataGuard(private val maxAgeMs:Long=5_000){fun verify(s:BrokerAccountSnapshot,nowMs:Long):BrokerAccountSnapshot{require(nowMs>=s.observedAtEpochMs){"future account snapshot"};require(nowMs-s.observedAtEpochMs<=maxAgeMs){"stale account snapshot"};require(s.equity.amount>=0&&s.cash.amount>=0&&s.buyingPower.amount>=0){"invalid broker account values"};return s}}
