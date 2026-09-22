package com.ttrl.agentw.core

enum class ExecutionSide { BUY, SELL }
data class ExecutionIntent(val intentId:String,val decisionId:String,val domain:MarketDomain,val instrument:String,val side:ExecutionSide,val quantity:Double,val expectedPrice:Double,val riskAuthorizationId:String,val evidenceIds:List<String>,val liveMoney:Boolean=false){init{require(quantity>0);require(expectedPrice>0);require(evidenceIds.isNotEmpty())}}
enum class BrokerState { ACKNOWLEDGED, PARTIAL, FILLED, REJECTED, CANCELLED, UNKNOWN }
data class BrokerSnapshot(val brokerOrderId:String,val clientIntentId:String,val state:BrokerState,val filledQuantity:Double,val averageFillPrice:Double?=null)
interface ExecutionBroker { fun submit(intent:ExecutionIntent):BrokerSnapshot }
class LiveMoneyDisabled:IllegalStateException("live-money execution disabled")
class DuplicateExecutionIntent:IllegalStateException("duplicate execution intent")
class BrokerFailure(message:String):IllegalStateException(message)
class ExecutionGateway(private val broker:ExecutionBroker,private val allowLiveMoney:Boolean=false){private val submitted=mutableSetOf<String>();fun submit(i:ExecutionIntent):BrokerSnapshot{if(i.liveMoney&&!allowLiveMoney)throw LiveMoneyDisabled();if(i.intentId in submitted)throw DuplicateExecutionIntent();val s=try{broker.submit(i)}catch(e:Exception){throw BrokerFailure("broker submission failed")};if(s.clientIntentId!=i.intentId)throw BrokerFailure("broker acknowledgement identity mismatch");submitted+=i.intentId;return s}}
enum class ReconciliationState { MATCHED, PENDING, BLOCKED }
data class ReconciliationResult(val state:ReconciliationState,val reasons:List<String>)
class ExecutionReconciler{fun reconcile(i:ExecutionIntent,s:BrokerSnapshot):ReconciliationResult{val r=mutableListOf<String>();if(s.clientIntentId!=i.intentId)r+="broker/client intent mismatch";if(s.filledQuantity>i.quantity)r+="broker overfill detected";if(s.state==BrokerState.UNKNOWN)r+="unknown broker order state";if(s.state==BrokerState.FILLED&&s.filledQuantity!=i.quantity)r+="filled state quantity mismatch";if(r.isNotEmpty())return ReconciliationResult(ReconciliationState.BLOCKED,r);if(s.state in setOf(BrokerState.ACKNOWLEDGED,BrokerState.PARTIAL))return ReconciliationResult(ReconciliationState.PENDING,listOf("awaiting final broker state"));return ReconciliationResult(ReconciliationState.MATCHED,emptyList())}}
