# Agent-W-Trader Production Readiness Roadmap

This roadmap measures readiness for a constrained, supervised real-money pilot—not completion of every speculative research idea.

## Progress method
Each milestone has acceptance tests. Percentage increases only when code, tests, operational evidence, and required external integrations are complete. Documentation-only research features do not increase real-money readiness.

## Current baseline
- Milestone 1: deterministic safety core — complete
- Milestone 2: persistent paper execution — complete
- Milestone 3: operational safeguards — complete
- Milestone 4: authoritative portfolio truth engine — in progress

Estimated production readiness at Milestone 4 start: **18%**.

## Remaining major milestones
4. Authoritative portfolio truth engine and event-sourced ledger.
5. Effective-dated brokerage, tax, fee, slippage, and net-P&L engine.
6. Independent symbolic risk kernel and signed policy configuration.
7. Full order/fill/position reconciliation and broker failure laboratory.
8. Event-driven exchange simulator with partial fills, queues, latency, and market impact.
9. Strategy registry, experiment lineage, drift and edge-decay controls.
10. Immutable digital flight recorder, audit evidence, and incident replay.
11. Security hardening: secrets, permissions, signed builds, dependency and supply-chain controls.
12. Operational command center, alerts, runbooks, backup, recovery, and kill-switch drills.
13. Official live market-data and broker sandbox adapters with compliance controls.
14. Extended shadow/paper validation with statistically meaningful evidence.
15. Independent review and constrained supervised live pilot.

## Current milestone 4 acceptance criteria
- Append-only, idempotent financial events.
- Restart-safe replay into authoritative portfolio state.
- Cash, position, average-price, realized-P&L, and fee accounting.
- Fail-closed insufficient cash and insufficient position controls.
- State cannot be mutated outside the ledger.
- CI passes on supported Python versions.

## Reporting format
Every milestone report will include:
- production readiness percentage;
- milestones completed and remaining;
- CI/test status;
- unresolved risks;
- what becomes possible after the milestone;
- what remains prohibited for real money.
