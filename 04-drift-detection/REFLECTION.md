# 04 — Drift Detection Reflection

## Which Statistical Test Fits Each Feature Type

### PSI (Population Stability Index) — Continuous / Binned Features

PSI bins both distributions into buckets and measures how much the population shifted between baseline and current. It is ideal for:

- **Continuous numerical features** that can be meaningfully discretized (e.g., `prompt_length`, `embedding_norm`, `response_length`)
- Production monitoring where you want a single scalar number that is easy to threshold and alert on (PSI > 0.1 = moderate shift, PSI > 0.2 = significant drift)
- Use when you need **comparability across time windows** — PSI values are comparable as long as the binning strategy is fixed

PSI is less suitable for features with very few unique values or heavy-tailed distributions where bin edges are hard to choose.

### KL Divergence — Discretized Distribution Comparison

KL(P_ref || P_cur) measures how much information is lost when the current distribution is used to approximate the reference. It is ideal for:

- **Discrete or discretized features** where the support can be enumerated (e.g., binned `response_quality`, categorical token IDs)
- Scenarios where you care about **directional divergence** — KL is asymmetric, so it tells you whether the shift is toward lower or higher probability regions
- Use when the two distributions should be similar and you want to penalize **unexpected new patterns** in current data

KL is sensitive to zero bins (requires smoothing) and can blow up when the current distribution has support the reference never had.

### KS (Kolmogorov-Smirnov) Test — Non-Parametric Distribution Comparison

The two-sample KS test compares the entire empirical CDFs without binning. It is ideal for:

- **Continuous features where you want a rigorous statistical test** (e.g., `prompt_length`, `response_quality`)
- When you need a **p-value** to make a formal accept/reject decision rather than a soft threshold
- KS is **non-parametric** — it makes no assumptions about the distribution shape, so it works for any continuous distribution

KS does not tell you *where* the drift occurred, only that the distributions differ. It is also less sensitive to small shifts in the tails compared to PSI.

### MMD (Maximum Mean Discrepancy) — Kernel-Based Distribution Comparison

MMD measures the distance between mean embeddings of the two distributions in a Reproducing Kernel Hilbert Space (RKHS). It is ideal for:

- **High-dimensional or structured data** (e.g., embedding vectors, image feature spaces)
- When you need a **general-purpose, kernelized** test that works without binning or distribution assumptions
- Use with a **universal kernel** (e.g., RBF) when you want to detect any type of distributional shift, not just shifts in specific moments

MMD requires choosing a kernel and its hyperparameters, which can be non-trivial. It is also computationally heavier than PSI or KS for large datasets.

## Summary Table

| Test | Feature Type | Threshold | Output | Best For |
|---|---|---|---|---|
| PSI | Continuous (binned) | > 0.2 drift | Scalar | Production monitoring, Prometheus alerting |
| KL | Discrete/discretized | Context-dependent | Scalar | Directional divergence, information loss |
| KS | Continuous | p-value < 0.05 | Statistic + p-value | Rigorous hypothesis testing |
| MMD | High-dimensional / embeddings | Kernel-dependent | Scalar | Kernel-based all-purpose comparison |

## Results from This Run

- `prompt_length` (continuous, large shift): PSI = 3.461, KS p-value = 0.0 → **drift detected** by all tests
- `embedding_norm` (continuous, no shift): PSI = 0.019 → **no drift**
- `response_length` (continuous, no shift): PSI = 0.016 → **no drift**
- `response_quality` (continuous, beta distribution shifted): PSI = 8.849, KS p-value = 0.0 → **drift detected** by all tests

PSI and KS agreed on which features drifted. KL amplified the shift magnitude because the shifted beta distribution had essentially zero overlap with the reference in certain bins.
