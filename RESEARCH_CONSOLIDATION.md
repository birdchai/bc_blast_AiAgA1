# Research Consolidation Pass

This document freezes terminology, feature definitions, evaluation protocol, and
train/validation/test philosophy before entering Step 9: Hybrid Temporal AI
Epidemiology.

The goal is to prevent ambiguity, temporal leakage, inconsistent naming, and
uncontrolled complexity when moving from explainable mechanistic analysis toward
hybrid temporal forecasting.

---

## 1. Research Phase Definition

The project is no longer a simple forecasting script. It is now a computational
plant epidemiology platform with multiple explainable layers:

- weather-driven infection favorability
- temporal accumulation
- leaf wetness proxy
- host susceptibility
- spatial neighbor pressure
- directional wind-mediated connectivity
- regional heterogeneity
- temporal sequence preparation
- AI-assisted research orchestration

Step 9 should therefore be framed as:

```text
Hybrid Temporal AI Epidemiology
```

It should not be framed as simply "trying LSTM."

---

## 2. Frozen Terminology

### Core Units

| Term | Definition |
|---|---|
| province-week | One province observed at one weekly timestamp |
| target week | The week for which blast occurrence is evaluated |
| previous week | One week before the target week |
| future label | Blast occurrence shifted forward from the current feature week |
| region | Broad Thai geographic grouping: North, Northeast, Central, East, West, South |

### Disease Labels

| Term | Definition |
|---|---|
| `blast_any` | Binary weekly blast occurrence; 1 if blast value is positive during the week |
| `blast_days` | Count of positive blast days within a week |
| `blast_t_plus_1` | Future blast label one province-week ahead |
| `blast_t_plus_2` | Future blast label two province-weeks ahead |

### Model Families

| Term | Definition |
|---|---|
| weather-only | Risk features derived only from local weather |
| host-weighted | Weather risk modified by rice variety susceptibility |
| spatial-host-weather | Host-weighted risk combined with neighboring province pressure |
| directional wind alignment | Neighbor blast pressure filtered by wind direction alignment |
| region-aware temporal | Regional rolling pressure features used for future forecasting |

---

## 3. Frozen Feature Definitions

### Weather Infection Features

| Feature | Definition |
|---|---|
| `temp_favorable` | Hourly temperature in broad favorable range |
| `temp_optimal` | Hourly temperature in optimal range |
| `humidity_favorable` | Hourly relative humidity above favorable threshold |
| `humidity_optimal` | Hourly relative humidity above optimal threshold |
| `favorable_hour` | Hour with favorable temperature and humidity |
| `optimal_hour` | Hour with optimal temperature and humidity |
| `infection_ratio` | `favorable_hours / observed_hours` |
| `optimal_ratio` | `optimal_hours / observed_hours` |
| `risk_score` | Explainable weather-only weekly risk score |

### Leaf Wetness and Temporal Accumulation

| Feature | Definition |
|---|---|
| `leaf_wet_hour` | Favorable temperature and optimal humidity |
| `leaf_wet_hours` | Weekly count of `leaf_wet_hour` |
| `leaf_wet_ratio` | `leaf_wet_hours / observed_hours` |
| `rolling_2w_risk` | Two-week rolling sum of `risk_score` |
| `rolling_3w_risk` | Three-week rolling sum of `risk_score` |
| `rolling_2w_leaf_wet_hours` | Two-week rolling sum of `leaf_wet_hours` |
| `rolling_3w_leaf_wet_hours` | Three-week rolling sum of `leaf_wet_hours` |

### Host Susceptibility

| Feature | Definition |
|---|---|
| `susceptibility_score` | Province-week area-weighted rice variety susceptibility |
| `host_modifier` | `1 + (susceptibility_score - 0.50)` |
| `host_weighted_risk` | `risk_score * host_modifier` |
| `host_weighted_rolling_2w` | `rolling_2w_risk * host_modifier` |
| `host_weighted_rolling_3w` | `rolling_3w_risk * host_modifier` |

Frozen susceptibility v0 weights:

| Season | Variety | Weight |
|---|---|---:|
| default | unknown / unstable | 0.50 |
| offseason | `พิษณุโลก2,60-2` | 0.70 |
| inseason | `กข15` | 0.65 |
| inseason | `ขาวดอกมะลิ105` | 0.65 |
| any | `กข6` | 0.50 |

Do not change susceptibility weights during Step 9 baseline experiments.

### Spatial Features

| Feature | Definition |
|---|---|
| `neighbor_prevweek_risk` | Mean previous-week neighbor risk among top 5 nearest provinces |
| `neighbor_prevweek_blast` | Mean previous-week neighbor `blast_any` among top 5 nearest provinces |
| `spatial_host_weather_risk` | `0.7 * host_weighted_risk + 0.3 * neighbor_prevweek_risk` |

Neighbor definition is frozen as top 5 nearest provinces by centroid distance
until a specific spatial sensitivity study is designed.

### Wind Features

| Feature | Definition |
|---|---|
| `mean_wind_speed` | Weekly mean wind speed |
| `max_wind_speed` | Weekly maximum wind speed |
| `prevailing_wind_direction` | Circular weekly mean wind direction |
| `wind_direction_variability` | Circular variability proxy |
| `high_wind_hours` | Hours with wind speed above conservative threshold |
| `humid_wind_hours` | Humid hours with nonzero wind |
| `leaf_wet_wind_hours` | Leaf-wet hours with nonzero wind |

Simple wind speed should not modify risk score yet.

### Directional Wind Alignment

| Feature | Definition |
|---|---|
| `bearing_neighbor_to_province` | Bearing from neighbor province to target province |
| `wind_alignment_angle` | Angular difference between wind direction and neighbor-to-target bearing |
| `wind_aligned_neighbor_blast` | Previous-week neighbor blast aligned with wind direction |
| `wind_aligned_neighbor_count` | Number of aligned neighbors |

Alignment tolerance is frozen at 45 degrees for exploratory baselines.

### Region-Aware Temporal Features

| Feature | Definition |
|---|---|
| `regional_neighbor_pressure_2w` | Two-week regional rolling neighbor pressure |
| `regional_neighbor_pressure_3w` | Three-week regional rolling neighbor pressure |
| `regional_leaf_wet_accumulation` | Regional rolling accumulated leaf wetness |
| `regional_host_pressure` | Regional mean susceptibility pressure |
| `regional_wind_alignment_frequency` | Regional mean wind-aligned neighbor blast pressure |

---

## 4. Evaluation Protocol

### Required Metrics

Every validation table should report:

- joined rows
- disease weeks
- precision
- recall
- F1
- false positives
- false negatives

For exploratory feature analysis, report:

- mean feature value in disease weeks
- mean feature value in non-disease weeks
- effect difference
- effect ratio where appropriate
- correlation
- direction stability across years

### Required Comparisons

When evaluating a new feature family, compare against:

- weather-only
- host-weighted
- spatial-host-weather where relevant
- region-aware temporal features where relevant

### Required Caveats

All exploratory feature effects are associations, not causal effects.

Years with weak labels must be interpreted carefully:

- 2015: no disease weeks
- 2016: very few disease weeks

---

## 5. Train / Validation / Test Philosophy

Step 9 must avoid temporal leakage.

### Recommended Split Philosophy

Use chronological splits, not random province-week splits.

Recommended first split:

| Set | Years | Purpose |
|---|---|---|
| train | 2017-2019 | Fit or calibrate temporal models |
| validation | 2020 | Select thresholds, windows, or model settings |
| test | 2021 | Final held-out evaluation |

Rationale:

- 2015 has no disease signal.
- 2016 has too few disease weeks.
- 2017-2019 provide multiple disease years for training.
- 2020 is high-disease and useful for validation stress testing.
- 2021 is a meaningful held-out robustness year.

### Alternative Sensitivity Split

If the model requires more training data:

| Set | Years |
|---|---|
| train | 2017-2020 |
| test | 2021 |

This should be clearly labeled as a reduced validation design.

### Regional Split Philosophy

Do not randomly mix region-year dynamics without reporting regional metrics.

Every Step 9 result should include:

- national metric
- regional metric
- region-year coverage
- disease-week counts

### Province Leakage Warning

Sequence windows must be built within province boundaries. A sequence for one
province must not use future labels or future features from the same province.

### Feature Leakage Warning

Allowed for current-week `t` prediction of `t+1`:

- features up to week `t`
- previous-week neighbor disease
- current-week weather summaries if the forecasting use case assumes week-end
  risk assessment

Not allowed:

- `blast_t_plus_1` or `blast_t_plus_2` as input features
- future weather
- future neighbor blast
- rolling windows that include future weeks

---

## 6. Normalization Philosophy

Before ML, feature normalization rules must be fixed.

Recommended:

- fit scalers on training years only
- apply the same scaler to validation and test years
- keep binary labels unscaled
- preserve raw explainable features in exported audit datasets

For tree-based transparent baselines, normalization may not be required.

For LSTM/GRU models, normalization is required and must be documented.

---

## 7. Imbalance Philosophy

Blast occurrence is imbalanced.

Do not rely on accuracy.

Primary metrics:

- recall
- precision
- F1
- false positives
- false negatives

Secondary metrics for ML phase:

- precision-recall AUC
- region-specific recall
- year-specific recall

Any class weighting or resampling must be reported explicitly.

---

## 8. Explainability Requirements for Step 9

Any future ML model must be compared to explainable baselines.

Minimum baselines:

- previous-week blast baseline
- weather-only temporal baseline
- host-weighted temporal baseline
- regional neighbor pressure baseline
- directional wind-alignment baseline

ML is only useful if it improves on these baselines while preserving
epidemiological interpretability.

---

## 9. Current Frozen Research Position

The project is entering the next phase as:

```text
Hybrid Temporal AI Epidemiology
```

The immediate goal is not to maximize F1 aggressively. The immediate goal is to
test whether explainable temporal epidemiological structure can support robust
future forecasting.

Step 9 should therefore begin with transparent temporal baselines before LSTM or
other sequence models.

