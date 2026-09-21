package com.ttrl.agentw.core

data class RiskLimits(val maxTradeRiskPct:Double=1.0,val maxDailyLossPct:Double=2.0,val maxOrderValue:Double=500000.0,val maxGrossExposurePct:Double=100.0,val maxLeverage:Double=1.0)
data class RiskRequest(val domain:MarketDomain,val instrument:String,val accountEquity:Double,val orderValue:Double,val stopLossAmount:Double,val dailyPnl:Double=0.0,val currentGrossExposure:Double=0.0,val leverage:Double=1.0,val killSwitch:Boolean=false)
data class RiskDecision(val approved:Boolean,val reasons:List<String>,val maxPermittedRisk:Double,val projectedExposure:Double)
class RiskBrain {
 fun authorize(r:RiskRequest,l:RiskLimits=RiskLimits()):RiskDecision{
  require(r.accountEquity>0 && r.orderValue>0 && r.stopLossAmount>0)
  val reasons=mutableListOf<String>();val maxRisk=r.accountEquity*l.maxTradeRiskPct/100.0;val projected=r.currentGrossExposure+r.orderValue
  if(r.killSwitch)reasons+="kill switch active"
  if(r.stopLossAmount>maxRisk)reasons+="per-trade risk limit exceeded"
  if(r.dailyPnl<=-(r.accountEquity*l.maxDailyLossPct/100.0))reasons+="daily loss limit reached"
  if(r.orderValue>l.maxOrderValue)reasons+="maximum order value exceeded"
  if(projected>r.accountEquity*l.maxGrossExposurePct/100.0)reasons+="gross exposure limit exceeded"
  if(r.leverage>l.maxLeverage)reasons+="leverage limit exceeded"
  return RiskDecision(reasons.isEmpty(),reasons,maxRisk,projected)
 }
}
