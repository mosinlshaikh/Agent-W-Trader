package com.ttrl.agentw.desktop
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application
import com.ttrl.agentw.core.*

@Composable fun AgentWShell(){ var domain by remember{mutableStateOf(MarketDomain.INDIA)}; MaterialTheme { Column(Modifier.fillMaxSize().padding(20.dp),verticalArrangement=Arrangement.spacedBy(TTradersTokens.Gap)){ Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){ Column{Text("Agent-W Trader",style=MaterialTheme.typography.headlineMedium);Text("Evidence-grounded autonomous trading research terminal")} SafetyBadge("LIVE MONEY",false) }; Row(horizontalArrangement=Arrangement.spacedBy(8.dp)){MarketDomain.entries.forEach{d->FilterChip(selected=domain==d,onClick={domain=d},label={Text(d.name)})}}; Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(TTradersTokens.Gap)){ Box(Modifier.weight(1f)){TerminalPanel("Execution Safety"){Text("Mode: PAPER / SAFE");SafetyBadge("EVIDENCE GATE",true);SafetyBadge("RISK BRAIN",true)}};Box(Modifier.weight(1f)){TerminalPanel("Market Brain"){Text("Domain: ${domain.name}");EvidenceBadge(EvidenceStatus.VERIFIED);Text("No synthetic market values displayed")}} }; TerminalPanel("Agent Council"){Text("Supervisor: advisory only");Text("Risk authorization: deterministic");Text("Broker access: gated by execution contracts")};TerminalPanel("T Traders SDK Migration"){Text("Design tokens · terminal panels · evidence badges · safety states");Text("Unsafe simulated execution behavior excluded")}} } }
fun main()=application{Window(onCloseRequest=::exitApplication,title="Agent-W Trader"){AgentWShell()}}
