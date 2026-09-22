# T Traders UI/UX Reuse Audit

Source reviewed: mosinlshaikh/agentic-traders main.

## Strong reusable design concepts
- dark glass trading-terminal visual language
- sticky command header and ticker tape
- trading terminal workspace
- AI Agent Studio
- portfolio/position views
- backtesting workspace
- market-intelligence workspace
- visual strategy builder
- risk visualization and correlation matrix
- settings and emergency kill-switch placement
- Lucide-based icon vocabulary

## Required changes before Agent-W production reuse
1. Replace INDIAN/GLOBAL with four first-class workspaces: INDIA, FOREX, CRYPTO, INTERNATIONAL.
2. Remove remote stock/Unsplash imagery from core branding and package owned/local assets.
3. Never label the product "Zero Hallucination" as an unconditional guarantee. UI should show evidence state: VERIFIED, STALE, CONFLICTED, INSUFFICIENT, or BLOCKED.
4. Remove simulated/random order-book values from any production trading screen.
5. Never store broker/API secrets in browser/local storage.
6. Never treat UI state changes as broker execution.
7. Separate PAPER and LIVE visually and architecturally.
8. All P&L, risk, correlation and recommendation displays must expose provenance and calculation timestamps where relevant.

## Kotlin design-system target
Suggested modules:
- ttraders-design-tokens
- ttraders-icons
- ttraders-components
- ttraders-charts
- ttraders-terminal
- ttraders-agent-ui

The first Kotlin milestone should reproduce the shell/navigation and evidence-state components, not broker execution.
