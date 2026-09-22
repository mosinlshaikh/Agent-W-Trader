package com.ttrl.agentw.desktop
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.ttrl.agentw.core.*

@Composable fun TradingTerminalPanel(s:TradingTerminalState?){TerminalPanel("Trading Terminal"){if(s==null){Text("Waiting for verified broker + market providers");Text("Orders: BLOCKED");return@TerminalPanel};Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text("${s.domain.name} · ${s.symbol}");SafetyBadge("LIVE EXECUTION",s.liveExecutionEnabled)};s.quote?.let{Text("Last: ${"%.2f".format(it.last)}");Text("Bid/Ask: ${it.bid ?: "—"} / ${it.ask ?: "—"}");Text("Market source: ${it.provider}")};s.account?.let{Text("Account equity: ${it.equity.currency} ${"%.2f".format(it.equity.amount)}")};Spacer(Modifier.height(8.dp));Text("Provider health");s.providerHealth.forEach{Text("${it.kind}: ${it.state} · ${it.provider}")};Text("Execution policy: ${if(s.safeMode)"PAPER / SAFE MODE" else "LIVE AUTHORIZED"}")}}
