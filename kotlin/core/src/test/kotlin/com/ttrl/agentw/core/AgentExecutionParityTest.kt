package com.ttrl.agentw.core
import kotlin.test.*
class AgentExecutionParityTest{
 private val e=EvidenceRef("e1",MarketDomain.INDIA,"NIFTY",EvidenceStatus.VERIFIED,"feed")
 private fun p(id:String,role:String,action:AgentAction=AgentAction.BUY)=AgentProposal(id,role,MarketDomain.INDIA,"NIFTY",action,.8,listOf(e),"stop invalidates")
 @Test fun diverseGroundedCouncilCanReachConsensusButNotRiskAuthorize(){val d=StrategyCouncil().decide(listOf(p("a","trend"),p("b","news")));assertEquals(AgentAction.BUY,d.action);assertTrue(d.quorumMet);assertFalse(d.riskAuthorized)}
 @Test fun sameRoleCannotFormQuorum(){assertEquals(AgentAction.ABSTAIN,StrategyCouncil().decide(listOf(p("a","trend"),p("b","trend"))).action)}
 @Test fun disagreementAbstains(){assertEquals(AgentAction.ABSTAIN,StrategyCouncil().decide(listOf(p("a","trend"),p("b","news",AgentAction.SELL))).action)}
 private fun intent(live:Boolean=false)=ExecutionIntent("i1","d1",MarketDomain.INDIA,"NIFTY",ExecutionSide.BUY,10.0,25000.0,"r1",listOf("e1"),live)
 private class Broker:ExecutionBroker{override fun submit(intent:ExecutionIntent)=BrokerSnapshot("b1",intent.intentId,BrokerState.ACKNOWLEDGED,0.0)}
 @Test fun liveMoneyDisabledByDefault(){assertFailsWith<LiveMoneyDisabled>{ExecutionGateway(Broker()).submit(intent(true))}}
 @Test fun duplicateIntentBlocked(){val g=ExecutionGateway(Broker());g.submit(intent());assertFailsWith<DuplicateExecutionIntent>{g.submit(intent())}}
 @Test fun unknownBrokerStateBlocks(){val i=intent();val s=BrokerSnapshot("b",i.intentId,BrokerState.UNKNOWN,0.0);assertEquals(ReconciliationState.BLOCKED,ExecutionReconciler().reconcile(i,s).state)}
}
