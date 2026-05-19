# Brain Data Feature Engineering & Implementation
**Dataset**: analyst47  
**Region**: USA  
**Delay**: 1

## Field Decomposition

### `anl47_indicator` (indicator)
- **Meaning**: Composite alpha indicator that synthesises multiple analyst inputs into a 1–10 scale, where higher values denote a stronger buy consensus.
- **What**: A numeric rating representing the aggregate opinion of sell-side analysts.
- **When/How**: Updated daily based on the latest analyst reports, recommendations, and target prices; reflects the current snapshot of consensus.
- **Why**: Serves as a convenient summary of collective analyst sentiment, often used as a standalone signal or as a building block in multi-factor models.
- **Reliability**: Moderately reliable; can be influenced by herd behaviour and may lag behind price movements. Its scaling from 1 to 10 implies a deliberate weighting scheme that can dampen extreme views.

### `anl47_rawalphadecay` (rawalphadecay)
- **Meaning**: Measures the impact of idea age or the decay of alpha signal strength over time.
- **What**: A continuous raw component that penalises older recommendations or forecasts, assuming that information freshness is positively correlated with predictive power.
- **When/How**: Computed daily by tracking how long ago a particular analyst insight was published; newer insights receive a higher score.
- **Why**: Captures the time value of information in financial markets, where stale ideas lose edge as they become priced in.
- **Reliability**: Generally high because the relationship between staleness and predictive power is intuitive and empirically supported, but it can fail during prolonged trending markets where old calls remain valid.

### `anl47_rawexperts` (rawexperts)
- **Meaning**: Contribution of an individual analyst or author’s historical performance to the raw signal.
- **What**: A weight based on past accuracy, calibration, or profitability of the analyst’s prior recommendations; higher values indicate a stronger track record.
- **When/How**: Recalculated periodically using a rolling window of previous forecasts and outcomes; the mapping from performance to the raw input can be linear or rank-based.
- **Why**: Adopts a “wisdom of the crowds – but filtered by expertise” philosophy, boosting signals from consistently accurate participants.
- **Reliability**: Can be robust if the track record is long enough and the performance metric is well designed; however, it may overfit to past episodic skill and can decay if the analyst changes coverage or style.

### `anl47_rawsentiment` (rawsentiment)
- **Meaning**: Raw component reflecting bullish/bearish idea counts and the open/closed status of those ideas.
- **What**: Aggregates the number of long vs. short outstanding recommendations and may account for recently closed positions; a positive value implies net bullishness.
- **When/How**: Computed daily by counting active analyst ideas, adjusting for their directional flags and possibly their recency or conviction.
- **Why**: Provides a direct measure of the prevailing market narrative among analysts, which can act as a contrarian or momentum indicator depending on market regime.
- **Reliability**: Highly volatile and subject to rapid swings around news events; its raw form may contain noise, but it captures real-time shifts in market sentiment.

### `anl47_totalrawsignal` (totalrawsignal)
- **Meaning**: Simple sum of the four raw components: sentiment, alpha decay, earnings, and experts.
- **What**: A composite raw value before any smoothing or final transformation; it amalgamates different facets of the analyst information set.
- **When/How**: Calculated daily as an arithmetic sum; each component may be linearly additive.
- **Why**: Acts as the base multi-dimensional signal from which final indicators are derived.
- **Reliability**: Because it mixes signals of varying nature and predictive horizon, it can be more stable than any single component, but the equal weighting may not be optimal.

### `earnings_event_signal_component` (event_signal_component)
- **Meaning**: Raw component that quantifies the proximity of analyst ideas to upcoming or recent earnings events.
- **What**: A score that increases when the analyst’s note is close to an earnings release date, capturing the heightened attention and information flow during earnings periods.
- **When/How**: Evaluated daily by comparing the idea date to the nearest earnings announcement; a value peaks on the announcement day and decays around it.
- **Why**: Earnings events are known to be critical information junctures, often accompanied by large price moves and analyst revisions; this component isolates event-driven informativeness.
- **Reliability**: Event proximity alone is a weak signal, but its interaction with the content of the idea can be powerful; the raw component is reliable in dating events but may not distinguish between positive and negative surprises.

## Academic Paper Pre-Search

The search on arXiv for “analyst revision”, “earnings forecast”, “recommendation change”, “alternative”, “analyst”, “investment” returned two highly relevant papers published after 2020. These two papers form the primary academic foundation for the feature concepts below.

- **“ChatGPT as a Time Capsule: The Limits of Price Discovery” (Lehner & Lopez-Lira, 2026).** The study extracts sector‑neutral LLM outlook scores from frozen language model checkpoints and finds that these scores are positively associated with analyst revisions, target‑price changes and cross‑sectional one‑month returns. This implies that changes in the aggregate analyst indicator – and the information freshness captured by alpha decay – contain forward‑looking information that can be turned into systematic features (e.g., momentum in the composite indicator).

- **“A kinetic theory approach to consensus formation in financial markets” (Attali & Salvarani, 2025).** The authors model the dynamics of sell‑side analysts’ opinions and find that, contrary to the intuition that analysts lead prices, analysts tend to set their target prices based on market prices. The model suggests that extreme consensus readings often reflect past price moves rather than future returns, and that reversal patterns can be exploited. This motivates features that measure the distance from recent consensus peaks or the divergence between raw sentiment and the consensus indicator.

No other directly relevant references were returned; where a concept is not explicitly covered by these two works, the economic rationale is provided.

## Feature Concept Generation

### 1. Analyst Consensus Momentum
**Reasoning:**
Lehner & Lopez-Lira (2026) show that analyst revisions are positively correlated with subsequent returns, indicating that consensus shifts contain momentum-like predictive content. Tracking the change in the composite indicator over a moderate lookback window captures whether analysts are collectively upgrading or downgrading a stock.

**Concept:** Analyst Consensus Momentum  
**Implementation Example:** `ts_delta({indicator}, 20)`

---

### 2. Raw Signal Purity Filter
**Reasoning:**
The `totalrawsignal` aggregates four diverse components, but `rawsentiment` can be noisy and driven by transient crowd behaviour. By subtracting the sentiment component, we extract a “clean” signal that reflects more fundamental factors: analyst track record (`rawexperts`), information timeliness (`rawalphadecay`), and earnings‑event proximity (`event_signal_component`). Lehner & Lopez-Lira (2026) suggest that LLM‑derived outlooks (which proxy for systematic textual signals) add value beyond raw sentiment; similarly, removing sentiment may enhance signal purity.

**Concept:** Raw Signal Purity Filter  
**Implementation Example:** `subtract({totalrawsignal}, {rawsentiment})`

---

### 3. Expert Track Record Strength
**Reasoning:**
The `rawexperts` component embodies the historical forecasting skill of the analysts. When this component is high relative to its own history, the current consensus is supported by analysts with proven ability. Drawing from the idea that “who said it” matters (Gleason & Lee, 2003, among others), we measure the deviation of the expert weight from its 60‑day mean. A positive deviation indicates that the market is currently receiving input from exceptionally skilled analysts, which could lead to more reliable signals.

**Concept:** Expert Track Record Strength  
**Implementation Example:** `ts_av_diff({rawexperts}, 60)`

---

### 4. Earnings Event Decay
**Reasoning:**
The `event_signal_component` peaks around earnings announcements, but the value of such event‑driven signals decays as the information is absorbed. The `rawalphadecay` component already measures general idea staleness. Multiplying the two creates a feature that is high only when both conditions hold: an analyst insight is close to an earnings event *and* that insight is relatively fresh. This isolates the most time‑sensitive, event‑driven alpha. No direct academic reference found from search for this specific interaction; the economic logic is that the intersection of event proximity and low staleness should contain the highest density of actionable information.

**Concept:** Earnings Event Decay  
**Implementation Example:** `multiply({event_signal_component}, {rawalphadecay})`

---

### 5. Consensus Reversal Potential
**Reasoning:**
Attali & Salvarani (2025) provide evidence that analyst consensus tends to follow market prices rather than lead them, implying that extreme consensus readings may mark the end of a trend. The number of days since the indicator reached its maximum over a 60‑day window serves as a contrarian gauge: a large value means the peak is far in the past, suggesting the consensus has softened and a reversal may be imminent; a small value (recent peak) indicates strong, potentially overbought consensus.

**Concept:** Consensus Reversal Potential  
**Implementation Example:** `ts_arg_max({indicator}, 60)`

---

### 6. Sentiment vs. Indicator Divergence
**Reasoning:**
`rawsentiment` reflects a simple count‑based, open‑close view of analyst positions, while the composite `indicator` folds in additional criteria such as accuracy and conviction. When short‑term sentiment and the broader composite point in opposite directions, there is disagreement within the analyst community. Such divergence can signal uncertainty or a turning point. We quantify this as the difference between sentiment and a trailing 20‑day average of the composite indicator. Attali & Salvarani (2025) support the idea that following raw consensus can be misleading; measuring internal disagreement is a natural extension.

**Concept:** Sentiment vs. Indicator Divergence  
**Implementation Example:** `subtract({rawsentiment}, ts_mean({indicator}, 20))`

---

### 7. Expert‑Weighted Indicator
**Reasoning:**
Combining the current consensus (`indicator`) with the strength of the analysts behind it (`rawexperts`) yields a refined signal that emphasises calls from historically accurate forecasters. This aligns with the broader academic finding that analyst forecast accuracy is persistent and that weighting signals by past accuracy improves portfolio performance (e.g., Stickel, 1992). Lehner & Lopez-Lira (2026) also touch on the importance of the quality of the textual signal, which is analogous to expert weighting.

**Concept:** Expert‑Weighted Indicator  
**Implementation Example:** `multiply({indicator}, {rawexperts})`