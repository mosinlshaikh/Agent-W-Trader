# Agent-W-Trader Multi-Market Architecture

## Objective
Build one safety-critical Agent-W core with four isolated market domains:
- INDIA
- FOREX
- CRYPTO
- INTERNATIONAL

Market domains share infrastructure but never silently share execution rules, calendars, instruments, leverage limits, or broker credentials.

## Core nervous system
Every external input becomes an immutable evidence-bearing event:

Market/News/Broker Event -> Evidence Validation -> Specialized Agents -> Strategy Council -> Deterministic Risk Firewall -> OMS -> Broker -> Fill -> Ledger -> Reconciliation -> Learning Journal

The AI layer is advisory. It cannot bypass the risk firewall or submit directly to a live broker.

## Evidence contract
Every trade-relevant claim must carry:
- source/provider identity
- observed timestamp
- ingestion timestamp
- market domain
- instrument identity
- freshness status
- provenance/reference
- deterministic values when applicable
- confidence only when meaningful

Missing, stale, contradictory, or unverifiable evidence fails closed.

## Market isolation

### INDIA
NSE/BSE, Indian indices, equity/F&O/options-chain intelligence, Indian sessions/holidays, India-specific cost and execution rules.

### FOREX
Currency pairs, sessions, spread-aware execution, macro-event intelligence, currency correlation and rollover awareness.

### CRYPTO
24x7 sessions, spot/derivatives separation, funding/open-interest/liquidation intelligence and exchange-specific controls.

### INTERNATIONAL
US and other explicitly enabled venues, exchange calendars, earnings/corporate events, currency-aware valuation and venue-specific rules.

## Agent teams
Each domain owns specialized agents. Shared services may include:
- Evidence verifier
- News ingestion
- Candle/indicator calculations
- Memory
- Audit
- Health
- Portfolio accounting

A supervisor can compare agent evidence but cannot override deterministic execution controls.

## UI strategy
T Traders (mosinlshaikh/agentic-traders) is the visual reference for the Agent-W desktop design system. Reuse concepts, layout language and owned assets only after asset/license review. Do not copy unsafe trading behavior, browser-side secrets, mock financial values, or synthetic execution.

Target UI stack:
- Kotlin
- Compose Multiplatform/Desktop
- reusable T Traders design-system module
- Windows packaging as an installer/executable

Top-level market workspaces:
INDIA | FOREX | CRYPTO | INTERNATIONAL

## Migration rule
The existing Python operational paper-trading branch remains the reference/certification engine while Kotlin modules are introduced. Kotlin replacements require behavioral parity tests before replacing certified Python components.

## Live-money boundary
Paper and live execution must be separate capabilities. Live execution requires an explicit live broker adapter, credential isolation, stronger risk policy, reconciliation, monitoring, auditability and controlled activation. No LLM or agent may directly possess unrestricted broker execution authority.
