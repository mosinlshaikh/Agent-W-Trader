plugins { kotlin("jvm"); id("org.jetbrains.compose"); id("org.jetbrains.kotlin.plugin.compose") }
kotlin { jvmToolchain(21) }
dependencies { implementation(project(":core")); implementation(compose.desktop.currentOs); implementation(compose.material3) }
compose.desktop { application { mainClass = "com.ttrl.agentw.desktop.MainKt"; nativeDistributions { targetFormats(org.jetbrains.compose.desktop.application.dsl.TargetFormat.Exe); packageName = "Agent-W Trader"; packageVersion = "0.1.0" } } }
