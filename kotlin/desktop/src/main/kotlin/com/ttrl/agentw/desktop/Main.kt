package com.ttrl.agentw.desktop
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application
import com.ttrl.agentw.core.MarketDomain

@Composable fun AgentWShell(){ var domain by remember{mutableStateOf(MarketDomain.INDIA)}; MaterialTheme { Column(Modifier.fillMaxSize().padding(20.dp)){ Text("Agent-W Trader",style=MaterialTheme.typography.headlineMedium); Text("Evidence-grounded multi-market autonomous trading research terminal"); Spacer(Modifier.height(16.dp)); Row(horizontalArrangement=Arrangement.spacedBy(8.dp)){ MarketDomain.entries.forEach{ d-> FilterChip(selected=domain==d,onClick={domain=d},label={Text(d.name)}) } }; Spacer(Modifier.height(20.dp)); Card(Modifier.fillMaxWidth()){ Column(Modifier.padding(16.dp)){ Text("Market: ${domain.name}"); Text("Execution: PAPER / SAFE MODE"); Text("Evidence gate: ACTIVE"); Text("Live money: DISABLED") } } } } }
fun main()=application { Window(onCloseRequest=::exitApplication,title="Agent-W Trader"){ AgentWShell() } }
