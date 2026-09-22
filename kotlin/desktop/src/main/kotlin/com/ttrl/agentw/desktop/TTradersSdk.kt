package com.ttrl.agentw.desktop
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.ttrl.agentw.core.EvidenceStatus

object TTradersTokens { val CardRadius=18.dp; val Gap=12.dp; val PanelPadding=16.dp }
@Composable fun TerminalPanel(title:String,content:@Composable ColumnScope.()->Unit){ Card(Modifier.fillMaxWidth(),shape=RoundedCornerShape(TTradersTokens.CardRadius),border=BorderStroke(1.dp,MaterialTheme.colorScheme.outlineVariant)){ Column(Modifier.padding(TTradersTokens.PanelPadding)){ Text(title,style=MaterialTheme.typography.titleMedium); Spacer(Modifier.height(8.dp)); content() } } }
@Composable fun EvidenceBadge(status:EvidenceStatus){ AssistChip(onClick={},label={Text("EVIDENCE · ${status.name}")}) }
@Composable fun SafetyBadge(label:String,active:Boolean){ AssistChip(onClick={},label={Text("${if(active) "ACTIVE" else "OFF"} · $label")}) }
