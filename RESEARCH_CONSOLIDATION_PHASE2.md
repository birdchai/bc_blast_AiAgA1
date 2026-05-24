# Research Consolidation Phase 2

## Corrected-Label Rice Blast Epidemiology Phase

This document consolidates the corrected-label research phase from Step 9.7 through Step 9.15. It is intended for thesis writing, proposal refinement, publication planning, and project memory.

The central change in this phase is the replacement of the previous blast disease label source with corrected `rice_blast_outbreak_weekly` labels. From Step 9.7 onward, corrected labels become the official outcome source for model development and evaluation.

## 1. Phase Overview

Step 9.7 marks the beginning of the corrected-label era. The project rebuilt the temporal epidemiology dataset using updated data sources and replaced the old blast label source with corrected weekly outbreak labels.

Important interpretation:

- Step 9.2 to Step 9.6 remain useful as methodological experiments.
- They show how the research workflow developed:
  - classical ML,
  - DNN baseline,
  - LSTM baseline,
  - calibration,
  - decision governance.
- However, their model scores should not be treated as final performance claims because they used the older label source.

The corrected-label phase is therefore the more credible basis for final thesis and publication claims.

## 2. Updated Data Foundation

The corrected-label phase uses four updated data layers.

### Updated Weather Hourly

`weather_hourly` becomes the default weather source going forward.

It provides:

- temperature,
- humidity,
- precipitation,
- dew point,
- wind speed,
- wind gust,
- wind direction,
- cloud cover,
- sea-level pressure,
- coordinates and address metadata.

The updated weather structure is cleaner than the earlier source, while sample comparisons showed that the underlying weather values remain consistent with the previous data.

### Updated POV Rice Monthly

`pov_rice_monthly` replaces earlier daily-expanded POV handling.

Key interpretation:

- The updated POV source is monthly.
- Province-month variety ratios must be rebuilt from monthly area data.
- Raw area totals should not be directly compared against old daily-expanded POV totals.
- Host susceptibility should be recomputed from updated monthly variety ratios.

### Corrected Rice Blast Outbreak Weekly

`rice_blast_outbreak_weekly` becomes the official corrected label source.

It is used to construct:

- `blast_any`,
- `blast_t_plus_1`,
- `blast_t_plus_2`,
- `label_source_available`,
- `label_observed`.

This source replaces the previous blast disease label source.

### BUS Daily Values

`bus_value_daily` is treated as an external mechanistic reference.

BUS interpretation:

- BUS is a weather-based disease suitability index.
- Critical BUS is defined as BUS >= 2.25.
- BUS is not a target label.
- BUS should not be a required national model dependency because coverage is limited.

### Terrain / Elevation Availability

The updated weather source does not contain direct terrain or elevation fields.

Weather audit findings:

- No `elevation`, `altitude`, `station elevation`, `height above sea level`, `terrain`, or DEM field exists.
- Only `sealevelpressure` is available as a pressure field.
- `sealevelpressure` is adjusted to sea level and should not be used as an elevation proxy.

Terrain/elevation must be introduced through an external province-level or raster-derived terrain table.

## 3. Corrected Label Impact

Corrected labels changed the interpretation of prior results.

Major effect:

- Some positives in the old label source were removed or corrected.
- The 2020 outbreak structure changed materially under the corrected weekly outbreak label.
- Previous high model performance must be interpreted cautiously because the target changed.

Research implication:

- Old-label Step 9.2 to Step 9.6 results remain valuable for workflow development.
- Corrected-label Step 9.7 onward results become the official evidence base.
- The corrected labels reduce overclaim risk and make the evaluation more conservative.

The corrected-label phase showed that performance is lower but more credible.

## 4. BUS Benchmark

Step 9.7B evaluated BUS as an external mechanistic benchmark and optional feature.

Findings:

- BUS coverage is limited, mainly to 2020-2021 and selected provinces in the current rebuilt dataset.
- BUS-only rule baselines are not strong enough as standalone national outbreak predictors.
- BUS can provide useful mechanistic context, but not enough historical coverage for a full nationwide supervised model.
- `core_no_BUS` models can operate without BUS.

Governance decision:

- BUS is `accepted_reference`.
- BUS may support dashboards, mechanistic comparison, or external benchmark reporting.
- BUS should not be treated as a required dependency for the main national model.
- BUS should not be used as a target label.

## 5. Forward-Year Split

Step 9.9 introduced the stronger corrected-label chronological split:

- train: 2017-2020
- validation: 2021
- test: 2022

This split is more credible than the earlier corrected-label split:

- Previous split:
  - train: 2017-2019
  - validation: 2020
  - test: 2021
- New split:
  - adds outbreak year 2020 into training,
  - uses 2021 for validation,
  - preserves 2022 as a held-out future year.

Training positives increased substantially:

- previous train positives: 176
- forward-split train positives: 643

Interpretation:

- Adding 2020 gives the model outbreak-regime examples.
- The new split better represents forward-year forecasting.
- Test 2022 remains held out and must not be used for threshold selection.

## 6. Updated Baseline Models

Step 9.9 reran core `core_no_BUS` baselines using the corrected-label forward split.

Test 2022 model comparison:

| model | threshold | precision | recall | F1 | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| DNN no class weight | 0.20 | 0.3923 | 0.3168 | 0.3505 | 0.7818 | 0.2904 |
| Random Forest | 0.50 | 0.3662 | 0.3230 | 0.3432 | 0.7886 | 0.2407 |
| DNN class-weighted | 0.80 | 0.2906 | 0.3665 | 0.3242 | 0.7790 | 0.2450 |
| XGBoost | 0.65 | 0.2653 | 0.3230 | 0.2913 | 0.7755 | 0.2523 |

Current corrected-label forward baseline:

- best F1: DNN no-class-weight `core_no_BUS`
- best interpretable competitor: Random Forest `core_no_BUS`
- recall-oriented option: DNN class-weighted `core_no_BUS`

Feature importance continued to support the scientific narrative:

- regional neighbor pressure,
- host susceptibility,
- regional host pressure,
- wind alignment,
- regional leaf wet accumulation,
- weather and seasonal features.

## 7. Temporal Model Revisit

Step 9.10A revisited compact temporal models under the corrected-label forward split.

Models:

- GRU,
- TCN,
- Hybrid DNN + GRU,
- Hybrid DNN + TCN.

Sequence lengths:

- 2 weeks,
- 4 weeks.

Best temporal model:

- Hybrid DNN + TCN, 2-week sequence.

Comparison:

| model | F1 | ROC-AUC | PR-AUC |
|---|---:|---:|---:|
| Step 9.9 DNN no class weight | 0.3505 | 0.7818 | 0.2904 |
| Step 9.9 Random Forest | 0.3432 | 0.7886 | 0.2407 |
| Step 9.9 DNN class-weighted | 0.3242 | 0.7790 | 0.2450 |
| Best temporal: Hybrid DNN + TCN 2w | 0.3274 | 0.7844 | 0.2157 |

Interpretation:

- Temporal models do not beat the best tabular baseline.
- Hybrid temporal models are better than pure sequence-only models.
- Short memory remains more useful than longer memory.
- Hybrid DNN + TCN 2-week remains useful as temporal evidence and a Northeast-sensitive candidate, but not as the default model.

## 8. Decision Governance

Decision governance evaluates model behavior after validation-only threshold selection and calibration.

Principles:

- Select thresholds using validation data only.
- Apply selected thresholds to held-out test data.
- Do not use test data for threshold selection.
- Separate classification decisions from risk communication.

Operational modes:

- balanced default,
- high-precision field-alert mode,
- high-recall surveillance mode,
- calibrated alert-tier dashboard mode.

Calibration and alert tiers:

- Calibration improves interpretability of predicted risk.
- Calibrated tiers are useful for dashboards and staged monitoring.
- Calibration does not necessarily improve F1.

Model role after governance:

- DNN no-class-weight `core_no_BUS`: stable default.
- DNN class-weighted: recall-sensitive surveillance candidate.
- Random Forest: interpretable comparator.
- Hybrid DNN + TCN 2-week: temporal support candidate, especially for Northeast sensitivity.

## 9. Province Analog Epidemiology

Step 9.11 investigated province similarity / analog epidemiology.

Goal:

- Test whether epidemiologically similar provinces provide useful signals beyond geographic adjacency.

Analog profile families:

- weather / moisture,
- host / POV,
- spatial / regional pressure,
- outbreak-history profile,
- combined epidemiological profile.

Findings:

- Analog similarity is partially distinct from geographic adjacency.
- Analog neighbors are often, but not always, geographically close.
- Analog outbreak-history features show measurable association with corrected outbreak labels.
- Analog features are most useful in Northeast-related outbreak behavior.
- Analog features do not solve North failures.

Scientific interpretation:

- Disease similarity is not identical to physical distance.
- Epidemiological analogs provide a complementary view of province relationships.

## 10. Analog Feature Ablation And Governance

Step 9.12 tested analog features in controlled model ablations.

Main finding:

- DNN no-class-weight + analog history improved F1 and recall relative to DNN `core_no_BUS`.

Key comparison:

- DNN `core_no_BUS` F1: 0.3505
- DNN `core_plus_analog_history` F1: 0.3704

Tradeoff:

- recall improves,
- false negatives decrease,
- false positives increase,
- PR-AUC does not improve for DNN analog history.

Random Forest finding:

- RF all-analog improves ranking metrics.
- It can increase false positives depending on threshold policy.

Step 9.13 decision governance found:

- Analog history remains useful after threshold governance.
- RF all-analog can be a strong ranking comparator.
- DNN analog history improves Northeast recall/F1.
- Analog history should not automatically replace `core_no_BUS` nationally.

Governance decision:

- `core_no_BUS`: stable default.
- `core_plus_analog_history`: accepted regional / governance candidate.
- RF all-analog: interpretable ranking or dashboard candidate.
- all-analog expansion: not default.

## 11. North-Focused Diagnostic

Step 9.14 diagnosed why North positives remain missed.

North test 2022 positives:

- total: 18
- Lamphun: 8
- Nan: 7
- Phichit: 2
- Nakhon Sawan: 1

All available models missed all North positive cases:

- DNN `core_no_BUS`,
- DNN `core_plus_analog_history`,
- RF `core_plus_all_analog`,
- RF `core_plus_analog_history`,
- Hybrid DNN + TCN 2-week.

Key interpretation:

- Lamphun shows a clear regime shift:
  - train positives: 1
  - test 2022 positives: 8
- Nan also increases strongly relative to train history.
- North positives have weaker weather, moisture, host, and spatial propagation signals than Northeast positives.
- `neighbor_prevweek_blast` is zero for North positives.
- `analog_prevweek_blast` is zero for North positives.

Failure type summary:

| failure type | cases |
|---|---:|
| no neighbor/analog outbreak signal | 18 |
| possible terrain/microclimate missing feature | 18 |
| low host susceptibility/risk signal | 4 |
| low weather-risk signal | 3 |
| unobserved label context | 1 |

Conclusion:

- North failure is not solved by analog history, temporal models, calibration, or threshold governance.
- North likely requires a separate diagnostic path.
- Terrain/elevation and microclimate remain plausible missing-data hypotheses.

## 12. Feature Agent And Data Scout Governance

Step 9.15 formalized feature lifecycle governance.

Documents:

- `FEATURE_AGENT_SPEC.md`
- `DATA_SCOUT_AGENT_SPEC.md`

Feature Agent roles:

- Feature Scientist Agent:
  - proposes biologically meaningful features and hypotheses.
- Feature Validation Agent:
  - tests feature effects, stability, missingness, and regional association.
- Feature Ablation Agent:
  - evaluates controlled model impact.
- Feature Governance Agent:
  - assigns final feature status and use case.
- Data Scout Agent:
  - escalates missing-data needs and evaluates external data sources.

Feature lifecycle statuses:

- `proposed`,
- `data_available`,
- `data_missing`,
- `audited`,
- `validated`,
- `ablated`,
- `governed`,
- `accepted_core`,
- `accepted_regional`,
- `accepted_dashboard`,
- `accepted_reference`,
- `rejected`,
- `future_data_needed`.

Registry outputs:

- `feature_registry_template.csv`
- `feature_registry_current.csv`

First official Data Scout case:

- province-level terrain/elevation data.

## 13. Current Model-Role Summary

| role | model / feature set | interpretation |
|---|---|---|
| stable default | DNN no-class-weight `core_no_BUS` | best corrected-label forward F1 baseline before analog governance |
| stable interpretable comparator | Random Forest `core_no_BUS` | strong ROC-AUC and explainable feature importance |
| recall-sensitive candidate | DNN class-weighted `core_no_BUS` | useful when missed outbreaks are costly |
| regional recall candidate | DNN `core_plus_analog_history` | improves Northeast recall/F1 but increases false positives |
| ranking comparator | RF all-analog | strong ranking metrics, useful for dashboard or prioritization analysis |
| temporal support model | Hybrid DNN + TCN 2-week | useful temporal evidence but not default |
| external reference | BUS features | benchmark/dashboard support, not national dependency |
| missing-data candidate | terrain/elevation | needed for North-focused diagnostic path |

## 14. Current Unresolved Gaps

Major unresolved gaps:

- North-region failures remain unsolved.
- Terrain/elevation is not available in current weather data.
- Microclimate variation is not captured by province-level weather summaries.
- Sub-provincial heterogeneity may be important.
- Reporting and label density may still affect observed outbreak patterns.
- Analog history helps Northeast but does not transfer to North.
- BUS coverage is insufficient for nationwide dependence.

Scientific caution:

- Corrected-label results are more credible than old-label results, but they remain constrained by province-level aggregation.
- Model behavior is regionally heterogeneous.
- A single nationwide threshold may hide region-specific risk patterns.

## 15. Next Directions

Recommended next steps:

1. Terrain/elevation data scouting.
   - Evaluate SRTM, Copernicus DEM, ASTER GDEM, Thai GIS/DEM sources, and commercial DEM options if needed.

2. Province terrain table preparation.
   - Expected fields:
     - province,
     - elevation_mean,
     - elevation_min,
     - elevation_max,
     - elevation_range,
     - elevation_std,
     - terrain_roughness,
     - source,
     - notes.

3. Controlled terrain-feature association.
   - Do not retrain models before auditing terrain coverage and province matching.

4. North-specific diagnostics.
   - Focus on Lamphun and Nan.
   - Compare terrain, microclimate, seasonality, host composition, and reporting density.

5. Similarity-augmented forecasting.
   - Keep analog history as a regional candidate.
   - Avoid all-analog default until false-positive behavior is governed.

6. Future agent automation.
   - Implement Feature Agent lifecycle checks.
   - Add registry updates after each validation or ablation.
   - Use Data Scout Agent workflow for missing-data escalation.

## Phase 2 Consolidated Interpretation

The corrected-label phase strengthens the scientific credibility of the project. It shows that rice blast forecasting requires more than weather-only modeling, but also that uncontrolled feature expansion is risky.

The strongest corrected-label evidence supports a governed, explainable system with:

- core mechanistic weather and leaf-wetness features,
- host susceptibility,
- regional/spatial pressure,
- short-term temporal accumulation,
- cautious use of analog history,
- BUS as an external reference,
- terrain/elevation as a missing-data research frontier.

The central unresolved scientific problem is North-region detection. Current features capture Northeast outbreak structure better than North outbreak structure. This suggests that the next research advance should come from missing environmental context, especially terrain and microclimate, rather than from simply adding larger neural architectures.
