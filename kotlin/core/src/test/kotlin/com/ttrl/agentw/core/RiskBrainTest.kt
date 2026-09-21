package com.ttrl.agentw.core
import kotlin.test.*
class RiskBrainTest{
 private fun request(kill:Boolean=false,stop:Double=500.0)=RiskRequest(MarketDomain.INDIA,"NIFTY",100000.0,20000.0,stop,0.0,10000.0,1.0,kill)
 @Test fun safeRequestPasses(){assertTrue(RiskBrain().authorize(request()).approved)}
 @Test fun killSwitchIsFinal(){assertFalse(RiskBrain().authorize(request(kill=true)).approved)}
 @Test fun tradeRiskCannotBeOverridden(){assertFalse(RiskBrain().authorize(request(stop=5000.0)).approved)}
}
