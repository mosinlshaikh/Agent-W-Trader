# Agent-W-Trader — Sovereign Quant Architecture

## Mission
Build a deterministic, auditable, paper-first multi-agent trading platform for Indian cash and derivatives markets. AI may analyse and rank opportunities, but no LLM may bypass deterministic risk, cost, compliance, data-quality, session, or execution controls.

## Non-negotiable safety boundary
- Live-money execution remains disabled until paper validation, broker certification, credential security, reconciliation, monitoring, deployment hardening, and operator approval are complete.
- The platform must not implement manipulative behaviour such as spoofing, layering, wash trading, quote stuffing, coordinated stop triggering, or deceptive liquidity placement.
- “Liquidity sweep” and “stop-hunt” features are analytical detectors only. They may identify probable liquidity events but must never attempt to cause them.
- Naked option selling is never an automatic default. Undefined-risk strategies require explicit policy approval, margin stress tests, tail hedges, and hard loss limits.
- Taxes, fees, exchange charges, expiry calendars, and regulations must be versioned configuration, never hard-coded assumptions.
- Profit is never guaranteed. Promotion to live mode requires statistically defensible out-of-sample performance after all costs.

## Core event pipeline
1. Ingest market, order-book, derivatives, news, calendar, and portfolio events.
2. Validate timestamp, schema, sequence, source, and freshness.
3. Build normalized market state across symbols and timeframes.
4. Run independent specialist agents.
5. Aggregate signals into a deterministic decision schema.
6. Estimate costs, slippage, margin, correlation, and tail risk.
7. Apply portfolio and account risk policy.
8. Simulate or route the approved order.
9. Reconcile broker and local state.
10. Record complete audit evidence and post-trade outcome.

## Intelligence planes

### 1. Microstructure and order-book intelligence
Inputs:
- Best bid/ask, spread, top-N depth, queue sizes, trade prints, cancellations, imbalance, microprice, latency, and volume profile.

Features:
- Spread in ticks and basis points.
- Top-5/top-20 depth imbalance.
- Order-flow imbalance and trade aggressor estimation.
- Queue depletion and replenishment.
- Iceberg suspicion score based on repeated replenishment and executed volume.
- VWAP, anchored VWAP, volume profile, point of control, value-area high, and value-area low.
- Liquidity-pool maps around swing highs/lows and prior session extremes.
- Liquidity-sweep detector based on penetration, absorption, close-back-inside, and follow-through.

Restrictions:
- No claim that hidden liquidity is known with certainty.
- Iceberg and stop-cluster outputs are probabilistic scores with evidence and confidence.

### 2. Derivatives and F&O intelligence
Inputs:
- Futures price, spot price, basis, volume, OI, change in OI, option-chain strikes, bid/ask, volume, OI, IV, Greeks, expiry, lot size, and margin.

Features:
- Long buildup, short buildup, short covering, and long liquidation classification.
- Put-call ratios by OI and volume.
- Strike-wise OI concentration and OI-change heatmap.
- Max-pain estimate with sensitivity and explicit “descriptive, not predictive” labeling.
- IV percentile, IV rank, skew, term structure, expected move, and event-risk regime.
- Greeks: delta, gamma, theta, vega, rho.
- Expiry and gamma-risk profiling.
- Strategy suitability ranking: defined-risk spreads before undefined-risk structures.

Risk controls:
- No automated naked short option strategy without explicit allow-list.
- Mandatory stress scenarios for gap, volatility expansion, liquidity loss, and margin increase.
- Position and portfolio Greeks limits.

### 3. Session and chronological behaviour
Session profiles are configurable and instrument-specific:
- 09:15–09:30: opening volatility; reduced size, stricter spread/slippage limits.
- 09:30–11:30: trend-establishment regime.
- 11:30–13:30: low-liquidity/chop regime; breakout threshold raised.
- 13:30–15:30: settlement, rebalancing, European overlap, and expiry gamma regime.

The session engine outputs:
- phase, expected liquidity, expected volatility, allowed strategies, size multiplier, and risk multiplier.

### 4. Cost, taxation, and execution friction
Every proposal requires a pre-trade net-expectancy report:
- Brokerage.
- STT and other statutory charges.
- Exchange transaction charges.
- GST.
- SEBI fees.
- Stamp duty.
- Bid-ask cost.
- Expected market impact.
- Expected slippage.
- Borrow, funding, and margin costs when applicable.

All rates are effective-dated and broker/instrument specific.

### 5. Candlestick and price-action intelligence
Features:
- OHLC anatomy, body and wick ratios, true range, gap, close location value.
- Hammer, shooting star, engulfing, doji, morning/evening star and configurable patterns.
- Rejection, absorption, displacement, fair-value-gap candidates.
- Swing points, break of structure, and change of character.
- Every pattern requires trend, volatility, volume, and higher-timeframe context.

### 6. Technical and mathematical intelligence
- EMA 9/21/50/200.
- MACD and histogram dynamics.
- RSI and divergence.
- SuperTrend.
- Bollinger bandwidth, squeeze, and expansion.
- ATR and realized volatility.
- VWAP and anchored VWAP.
- Regime detection rather than unconditional indicator voting.

### 7. Multi-timeframe, sector, and macro context
- 1m/5m execution context aligned with 15m/1h/daily structure.
- Index, sector, stock, futures, and volatility correlation.
- Breadth, sector strength, beta, rolling correlation, and factor exposure.
- Corporate action, earnings, policy, budget, and macro event calendar.

### 8. Execution and order management
- Market, limit, stop, stop-limit, bracket, and staged execution abstractions.
- Partial fills, modify/cancel, timeout, retry, and idempotency.
- Trailing stop and partial exit policies.
- Participation-rate and maximum-impact controls.
- Market-making research remains simulation-only until exchange/broker permissions, inventory controls, and latency infrastructure are validated.

### 9. Risk and survival circuitry
Account controls:
- Fixed-fractional sizing as default.
- Kelly only as a capped research signal, never raw full Kelly.
- Maximum per-trade risk.
- Maximum daily and weekly drawdown.
- Consecutive-loss circuit breaker.
- Maximum gross and net exposure.
- Sector, factor, symbol, expiry, and strategy concentration limits.
- Correlation-aware risk aggregation.
- Portfolio delta/gamma/vega/theta limits.
- Emergency kill switch and cool-down lock.

### 10. Self-learning and memory
Storage layers:
- Relational database for authoritative orders, fills, positions, costs, and P&L.
- Time-series storage for ticks, bars, order book, and features.
- Vector memory for post-trade case retrieval only.

Learning policy:
- No uncontrolled online self-modification of live strategy weights.
- Candidate updates are trained offline, walk-forward tested, compared to champion models, reviewed, versioned, and deployed through approval gates.
- Prevent look-ahead bias, leakage, survivorship bias, and repeated-test overfitting.

### 11. Latency engineering and co-location readiness
Purpose:
- Measure and reduce end-to-end delay across market-data ingest, normalization, strategy evaluation, risk approval, order submission, broker acknowledgement, and reconciliation.

Capabilities:
- Nanosecond-capable monotonic timestamps where infrastructure permits.
- Per-stage latency histograms: p50, p95, p99, and worst-case.
- Clock synchronization monitoring and timestamp-quality flags.
- Feed-to-decision, decision-to-order, order-to-ack, and ack-to-fill measurements.
- Venue and provider latency comparison.
- Simulation of co-located, cloud, and retail-internet environments.
- Latency budget enforcement: stale decisions are cancelled rather than submitted.

Boundary:
- Co-location is an infrastructure and regulatory capability, not a software switch.
- No claim of microsecond advantage without exchange-authorized access, certified connectivity, synchronized clocks, and measured production evidence.
- Latency-arbitrage research remains simulation/shadow mode until legal, exchange, broker, and market-data permissions are verified.

### 12. Cross-asset, basis, and parity arbitrage
Research relationships:
- Cash-futures fair value and annualized basis.
- Calendar spreads across futures expiries.
- Put-call parity and conversion/reversal relationships.
- Box-spread and synthetic-forward consistency checks.
- Index-versus-basket dislocation.
- ETF-versus-NAV or related-instrument spreads where data and execution permissions exist.

Execution requirements:
- Atomic or coordinated multi-leg order intent.
- Leg-risk limits, timeout, unwind policy, and partial-fill recovery.
- Borrow availability, margin, funding, taxes, corporate actions, dividends, lot sizes, and settlement rules included.
- Net edge must remain positive after spread, slippage, impact, fees, and worst-case legging cost.

Boundary:
- No arbitrage is labelled “guaranteed.” Execution risk, basis persistence, liquidity, margin changes, and leg failure can create losses.

### 13. Advanced Greeks and volatility-surface modeling
Capabilities:
- Per-position and portfolio delta, gamma, theta, vega, and rho.
- Volatility smile/skew and expiry term structure.
- Surface interpolation with arbitrage checks.
- Forward-volatility and event-premium decomposition.
- Sticky-strike and sticky-delta scenario analysis.
- Delta-hedging simulator with transaction costs and discrete rebalancing.
- Gamma-scalping and volatility-risk-premium research.
- Stress cubes across spot, IV, skew, time decay, rates, and liquidity shocks.

Boundary:
- Delta-neutral does not mean risk-free. Gamma, vega, jump, skew, liquidity, model, and hedging risks remain.
- Portfolio neutrality is measured continuously and bounded by policy, never assumed.

### 14. Institutional execution algorithms
Supported execution policies:
- TWAP with configurable schedule and randomization.
- VWAP and volume-participation execution.
- POV/participation-rate control.
- Implementation-shortfall optimization.
- Arrival-price benchmarking.
- Limit-order slicing with queue and cancellation controls.
- Reserve/iceberg-style child-order abstractions only where the broker/venue explicitly supports them.

Controls:
- Maximum participation rate.
- Minimum child-order size and throttling.
- Price collars, spread limits, and adverse-selection checks.
- Cancel/replace rate limits.
- Market-impact and information-leakage monitoring.
- Full parent-child audit trail.

Boundary:
- The objective is lawful market-impact reduction, not deceptive liquidity display.
- Spoofing, layering, quote stuffing, or orders entered without genuine execution intent are prohibited.

### 15. Alternative data, news, and sentiment intelligence
Inputs may include only licensed, public, or explicitly authorized sources:
- Global and domestic news feeds.
- Economic calendars and official releases.
- Exchange publications and corporate announcements.
- FII/DII and other official market statistics.
- Public social-media data where terms permit.
- Earnings transcripts and regulatory filings.

Pipeline:
- Source identity, timestamp, license, and freshness validation.
- Deduplication and entity linking.
- Event classification and novelty scoring.
- Sentiment, uncertainty, relevance, and source-reliability scores.
- Cross-source confirmation before high-impact decisions.
- Event-time alignment to prevent look-ahead bias.

Controls:
- Robots.txt, platform terms, copyright, privacy, and data-retention rules must be respected.
- No bypassing authentication, paywalls, rate limits, or technical access controls.
- Social-media signals are low-trust by default and cannot independently authorize trades.
- News-derived signals must pass deterministic risk, cost, liquidity, and session controls.

## Multi-agent design
Specialist agents:
- MarketDataQualityAgent
- MicrostructureAgent
- CandleStructureAgent
- TechnicalRegimeAgent
- DerivativesAgent
- SessionContextAgent
- SectorCorrelationAgent
- NewsEventAgent
- AlternativeDataAgent
- LatencyTelemetryAgent
- ArbitrageRelationshipAgent
- VolatilitySurfaceAgent
- InstitutionalExecutionAgent
- CostModelAgent
- PortfolioRiskAgent
- ExecutionAgent
- ReconciliationAgent
- PostTradeReviewAgent

Decision hierarchy:
- Specialists produce typed observations, not broker commands.
- SignalAggregator combines evidence.
- PortfolioRiskAgent has veto authority.
- ExecutionAgent can execute only a signed, approved OrderIntent.
- ReconciliationAgent is authoritative after submission.

## Scale reality
The architecture may support tens or hundreds of concurrent strategy workers, but “1,000–10,000 daily micro-trades” is not a target by itself. Throughput is allowed only when market data rights, broker limits, exchange rules, infrastructure latency, net expectancy, and operational controls support it. Trade count never substitutes for edge.

## Promotion gates
### Gate A — deterministic unit correctness
All calculations, state transitions, and fail-closed controls tested.

### Gate B — historical research integrity
Walk-forward and out-of-sample tests with complete cost and slippage models.

### Gate C — event-driven simulation
Order book, partial fills, latency, disconnects, gaps, limit moves, and stale data.

### Gate D — shadow and paper trading
Real-time signals and simulated orders for a statistically meaningful period.

### Gate E — constrained live pilot
Small capital, allow-listed instruments, hard daily limits, manual kill switch, and continuous reconciliation.

### Gate F — controlled scale
Scale only after stability, capacity, and risk evidence.

## Planned implementation epics
1. Unified event and schema layer.
2. Authoritative portfolio ledger and P&L.
3. Cost/tax engine with effective-dated schedules.
4. Candle, technical, and multi-timeframe feature engine.
5. Order-book and liquidity analytics.
6. Derivatives chain, OI, IV, Greeks, and volatility-surface engine.
7. Session/regime policy engine.
8. Correlation and portfolio risk engine.
9. Execution simulator with partial fills, latency, and market impact.
10. Cross-asset arbitrage relationship engine with multi-leg simulation.
11. Institutional execution algorithms with parent-child order tracking.
12. Alternative-data ingestion, licensing registry, and event intelligence.
13. Post-trade analytics, experiment registry, and governed model promotion.
14. Live provider and low-latency adapters only after all promotion gates.
