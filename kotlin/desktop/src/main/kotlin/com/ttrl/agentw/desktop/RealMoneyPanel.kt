package com.ttrl.agentw.desktop
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import com.ttrl.agentw.core.BrokerAccountSnapshot

@Composable fun RealMoneyPanel(snapshot:BrokerAccountSnapshot?){TerminalPanel("Real-money account data"){if(snapshot==null){Text("Broker account: NOT CONNECTED");Text("Balances/positions: unavailable — no synthetic values shown");Text("Live execution: DISABLED")}else{Text("Provider: ${snapshot.provider}");Text("Account: ••••${snapshot.accountId.takeLast(4)}");Text("Equity: ${snapshot.equity.currency} ${"%.2f".format(snapshot.equity.amount)}");Text("Cash: ${snapshot.cash.currency} ${"%.2f".format(snapshot.cash.amount)}");Text("Buying power: ${snapshot.buyingPower.currency} ${"%.2f".format(snapshot.buyingPower.amount)}");Text("Realized P&L: ${snapshot.realizedPnl.currency} ${"%.2f".format(snapshot.realizedPnl.amount)}");Text("Unrealized P&L: ${snapshot.unrealizedPnl.currency} ${"%.2f".format(snapshot.unrealizedPnl.amount)}");Text("Account mode: ${if(snapshot.isLiveAccount)"LIVE DATA" else "PAPER DATA"}");Text("Trading permission: SEPARATE / DISABLED")}}}
