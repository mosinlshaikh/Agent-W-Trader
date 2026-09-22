package com.ttrl.agentw.core

enum class ProviderKind { BROKER_ACCOUNT, MARKET_DATA, NEWS }
enum class ProviderState { CONNECTED, DEGRADED, DISCONNECTED, STALE, BLOCKED }
data class ProviderHealth(val provider:String,val kind:ProviderKind,val state:ProviderState,val checkedAtEpochMs:Long,val lastDataAtEpochMs:Long?,val message:String="")
class ProviderHealthGuard(private val maxDataAgeMs:Long=5_000){
 fun executable(h:ProviderHealth,nowMs:Long):Boolean {
  if(h.state!=ProviderState.CONNECTED)return false
  val last=h.lastDataAtEpochMs?:return false
  if(nowMs<last)return false
  return nowMs-last<=maxDataAgeMs
 }
}
