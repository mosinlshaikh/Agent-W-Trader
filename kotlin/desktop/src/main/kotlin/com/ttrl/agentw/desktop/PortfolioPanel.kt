package com.ttrl.agentw.desktop
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import com.ttrl.agentw.core.PortfolioSnapshot

@Composable fun PortfolioPanel(p:PortfolioSnapshot?){TerminalPanel("Portfolio & Positions"){if(p==null){Text("Real broker portfolio: NOT CONNECTED");Text("No fabricated positions or prices are displayed")}else{Text("Positions: ${p.positions.size}");p.positions.forEach{r->HorizontalDivider();Text(r.symbol);Text("Qty ${r.quantity} · Live ${r.livePrice.currency} ${"%.2f".format(r.livePrice.amount)}");Text("Market value ${r.marketValue.currency} ${"%.2f".format(r.marketValue.amount)} · U-P&L ${"%.2f".format(r.unrealizedPnl.amount)}")}}}}
