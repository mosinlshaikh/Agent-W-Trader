package com.ttrl.agentw.core

enum class AgentAction { BUY, SELL, HOLD, ABSTAIN }
data class AgentProposal(val agentId:String,val role:String,val domain:MarketDomain,val instrument:String,val action:AgentAction,val confidence:Double,val evidence:List<EvidenceRef>,val invalidation:String?=null){init{require(confidence in 0.0..1.0)}}
data class CouncilDecision(val domain:MarketDomain,val instrument:String,val action:AgentAction,val confidence:Double,val agentIds:List<String>,val evidenceIds:List<String>,val quorumMet:Boolean,val riskAuthorized:Boolean=false)
class StrategyCouncil(private val minAgents:Int=2){
 fun decide(proposals:List<AgentProposal>):CouncilDecision{
  require(proposals.isNotEmpty());val domain=proposals.first().domain;val instrument=proposals.first().instrument.trim().uppercase();val gate=EvidenceGate()
  val valid=proposals.filter{p->p.domain==domain&&p.instrument.trim().uppercase()==instrument&&runCatching{gate.requireVerified(domain,instrument,p.evidence);if(p.action in setOf(AgentAction.BUY,AgentAction.SELL))require(!p.invalidation.isNullOrBlank());true}.getOrDefault(false)}
  val directional=valid.filter{it.action==AgentAction.BUY||it.action==AgentAction.SELL};val grouped=directional.groupBy{it.action};val top=grouped.maxByOrNull{it.value.size};val tied=top!=null&&grouped.values.count{it.size==top.value.size}>1
  val winners=if(top==null||tied) emptyList() else top.value;val roles=winners.map{it.role}.toSet();val quorum=winners.size>=minAgents&&roles.size>=2
  if(!quorum)return CouncilDecision(domain,instrument,AgentAction.ABSTAIN,0.0,valid.map{it.agentId},emptyList(),false,false)
  return CouncilDecision(domain,instrument,top!!.key,winners.map{it.confidence}.average(),winners.map{it.agentId},winners.flatMap{it.evidence.map(EvidenceRef::id)}.distinct().sorted(),true,false)
 }
}
