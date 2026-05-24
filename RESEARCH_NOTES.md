✔ hypothesis
✔ ideas
✔ failures
✔ threshold reasoning
✔ epidemiology insights

## 2026-05-19 Temporal Accumulation Test

Implemented incremental temporal features in `tools/blast_model_v1.py`:

- `leaf_wet_hours`
- `leaf_wet_ratio`
- `rolling_2w_risk`
- `rolling_3w_risk`
- rolling infection/optimal/leaf-wet hours

Nationwide 2017 batch result:

- No score type reached recall >= 0.8.
- Best `risk_score`: lag 2, threshold 45, f1 0.0487, recall 0.2923.
- Best `rolling_2w_risk`: lag 1, threshold 90, f1 0.0453, recall 0.2462.
- Best `rolling_3w_risk`: lag 0, threshold 150, f1 0.0494, recall 0.1538.

Interpretation:

- Rolling accumulation can reduce false positives at higher thresholds.
- It also reduces recall sharply.
- Weather-only and temporal accumulation are still insufficient nationally.
- Next likely modifier is host susceptibility / POV integration, not another weather-only rule tweak.

## 2026-05-19 Multi-Year Feature Stability

Ran stability check for 2015-2021.

Coverage:

- 2015 has 0 disease weeks, so it does not provide useful effect direction.
- 2016 has only 2 disease weeks, so effect estimates are weak.
- 2017-2021 provide stronger signal.

Weather stability:

- Most stable positive weather indicators are humidity/leaf-wet related:
  - `humidity_optimal_hours`: positive 5/6 observed years.
  - `humidity_favorable_hours`: positive 5/6 observed years.
  - `rolling_3w_leaf_wet_hours`: positive 5/6 observed years.
  - `rolling_2w_leaf_wet_hours`: positive 5/6 observed years.
  - `leaf_wet_hours`: positive 5/6 observed years.
- Temperature and rainfall directions are mixed.

POV stability:

- Stable positive candidates:
  - offseason `พิษณุโลก2,60-2`: positive 5/6 observed years.
  - inseason `กข15`: positive 4/5 observed years.
  - inseason `ขาวดอกมะลิ105`: positive 4/5 observed years.
- `กข6` is unstable: positive 2/5 years and negative 3/5 years.

Interpretation:

- Susceptibility v0 should use only stable, modest weights.
- Avoid treating `กข6` as globally susceptible until province/season effects are checked.
- Host weighting should combine stable POV signals with humidity/leaf-wet weather signals.

## 2026-05-19 Susceptibility v0

Implemented experimental host susceptibility v0.

Weights:

- default / unknown / unstable varieties: 0.50
- offseason `พิษณุโลก2,60-2`: 0.70
- inseason `กข15`: 0.65
- inseason `ขาวดอกมะลิ105`: 0.65
- `กข6`: 0.50 because it is unstable across years.

Host weighting formula:

- `host_modifier = 1 + (susceptibility_score - 0.50)`
- default 0.50 leaves weather risk unchanged.
- 0.70 increases risk by 20%.
- 0.65 increases risk by 15%.

Nationwide 2017 validation:

- weekly susceptibility rows: 3344
- mean susceptibility: 0.5210
- min susceptibility: 0.5000
- max susceptibility: 0.6483

Best weather-only:

- `rolling_3w_risk`, lag 0, threshold 150
- precision 0.0294
- recall 0.1538
- f1 0.0494
- false positive 330
- false negative 55

Best host-weighted:

- `host_weighted_rolling_3w`, lag 1, threshold 150
- precision 0.0358
- recall 0.2154
- f1 0.0614
- false positive 377
- false negative 51

Interpretation:

- Susceptibility v0 improves f1 modestly in 2017.
- It increases true positives but also increases false positives.
- The gain is real enough to keep the host layer, but not strong enough to claim final model quality.
- Next step should test host-weighted validation across 2017-2021 before changing weights.

## 2026-05-19 Multi-Year Host-Weighted Robustness

Ran host-weighted validation for 2015-2021 without changing weights.

Outputs:

- `experiments/outputs/host_weighted_validation_2015_2021.csv`
- `experiments/outputs/host_weighted_validation_best_by_year.csv`
- `experiments/outputs/host_weighted_validation_improvement_summary.csv`

Best weather-only vs host-weighted by year:

| year | disease weeks | best weather-only f1 | best host-weighted f1 | f1 delta | host improves |
|---|---:|---:|---:|---:|---|
| 2015 | 0 | 0.0000 | 0.0000 | 0.0000 | no |
| 2016 | 2 | 0.0000 | 0.0000 | 0.0000 | no |
| 2017 | 65 | 0.0494 | 0.0614 | +0.0120 | yes |
| 2018 | 27 | 0.0360 | 0.0638 | +0.0278 | yes |
| 2019 | 143 | 0.0814 | 0.0865 | +0.0052 | yes |
| 2020 | 562 | 0.3016 | 0.3100 | +0.0084 | yes |
| 2021 | 345 | 0.1509 | 0.1497 | -0.0012 | no |

Summary:

- Host-weighted improved f1 in 4/7 years overall.
- If excluding weak-label years 2015 and 2016, host-weighted improved f1 in 4/5 years.
- Mean f1 delta across all years: +0.0075.
- Median f1 delta across all years: +0.0052.

Interpretation:

- Susceptibility v0 is directionally useful, especially 2017-2020.
- The improvement is modest and not universal.
- 2021 is a warning case: host weighting does not automatically improve robustness.
- Keep weights unchanged for now; next work should inspect 2021 failure and province/season behavior before tuning.

## 2026-05-19 Spatial Epidemiology v0

Implemented explainable spatial pressure layer.

Spatial construction:

- Province centroids computed from POV latitude/longitude.
- Province distances computed using haversine distance.
- Neighbor set = top 5 nearest provinces per province.

Spatial weekly features:

- `neighbor_prevweek_risk`: mean previous-week `host_weighted_risk` among top 5 neighbors.
- `neighbor_prevweek_blast`: mean previous-week `blast_any` among top 5 neighbors.

Combined score:

- `spatial_host_weather_risk = 0.7 * host_weighted_risk + 0.3 * neighbor_prevweek_risk`

Outputs:

- `experiments/outputs/spatial_host_weather_validation_2017_2021.csv`
- `experiments/outputs/spatial_host_weather_best_by_year.csv`
- `experiments/outputs/spatial_host_weather_comparison_summary.csv`
- `experiments/outputs/province_centroids_from_pov.csv`
- `experiments/outputs/province_distances.csv`
- `experiments/outputs/province_top5_neighbors.csv`

Best score comparison:

| year | disease weeks | weather f1 | host f1 | spatial f1 | spatial vs weather | spatial vs host |
|---|---:|---:|---:|---:|---:|---:|
| 2017 | 65 | 0.0494 | 0.0614 | 0.0647 | +0.0153 | +0.0033 |
| 2018 | 27 | 0.0360 | 0.0638 | 0.0396 | +0.0036 | -0.0242 |
| 2019 | 143 | 0.0814 | 0.0865 | 0.0814 | +0.0001 | -0.0051 |
| 2020 | 562 | 0.3016 | 0.3100 | 0.2974 | -0.0042 | -0.0126 |
| 2021 | 345 | 0.1509 | 0.1497 | 0.1587 | +0.0078 | +0.0090 |

Summary:

- Spatial-host-weather improves over weather-only in 4/5 years.
- Spatial-host-weather improves over host-weighted in 2/5 years.
- Mean f1 delta vs weather-only: +0.0045.
- Mean f1 delta vs host-weighted: -0.0059.

Interpretation:

- Neighbor pressure contains useful signal.
- The current conservative spatial score does not consistently beat host-weighted rolling features.
- Spatial signal may be more useful as an added feature or alert context than as a direct replacement score.
- Do not tune aggressively yet; next step should inspect whether `neighbor_prevweek_blast` has independent value and whether spatial effects differ by region.

## 2026-05-19 Wind Epidemiology Exploration

Implemented exploratory wind feature extraction.

Added weather columns to loader:

- `wspd`
- `wgust`
- `wdir`
- `dew`
- `cloudcover`
- `sealevelpressure`

Weekly wind features:

- `mean_wind_speed`
- `max_wind_speed`
- `mean_wind_gust`
- `prevailing_wind_direction`
- `wind_direction_variability`
- `high_wind_hours`
- `humid_wind_hours`
- `leaf_wet_wind_hours`
- `high_wind_ratio`
- `humid_wind_ratio`
- `leaf_wet_wind_ratio`

Conservative logic:

- `high_wind_hour`: `wspd >= 10`
- `humid_wind_hour`: RH favorable and wind speed > 0
- `leaf_wet_wind_hour`: leaf-wet condition and wind speed > 0

Outputs:

- `experiments/outputs/wind_feature_effects_2015_2021.csv`
- `experiments/outputs/wind_feature_stability_2015_2021.csv`
- `experiments/outputs/wind_feature_coverage_2015_2021.csv`

Coverage:

- 2015 has 0 disease weeks and is not useful for effect direction.
- 2016 has only 2 disease weeks and is weak.
- 2017-2021 provide stronger signal.

Wind stability results:

| feature | positive years | negative years | direction stability | mean correlation | mean abs correlation |
|---|---:|---:|---:|---:|---:|
| `wind_direction_variability` | 1 | 5 | 0.8333 | -0.0337 | 0.0381 |
| `mean_wind_speed` | 1 | 5 | 0.8333 | -0.0153 | 0.0372 |
| `high_wind_hours` | 2 | 4 | 0.6667 | -0.0118 | 0.0407 |
| `high_wind_ratio` | 2 | 4 | 0.6667 | -0.0137 | 0.0407 |
| `prevailing_wind_direction` | 2 | 4 | 0.6667 | -0.0183 | 0.0330 |
| `humid_wind_hours` | 3 | 3 | 0.5000 | 0.0146 | 0.0340 |
| `leaf_wet_wind_hours` | 3 | 3 | 0.5000 | 0.0108 | 0.0308 |

Comparison with existing features:

- `neighbor_prevweek_blast` remains the strongest stable comparison signal:
  - positive 5/6 observed years
  - mean correlation 0.1180
- Humidity/leaf-wet features remain more epidemiologically stable than most wind-speed features:
  - `humidity_optimal_hours`: positive 5/6
  - `humidity_favorable_hours`: positive 5/6
  - `rolling_3w_leaf_wet_hours`: positive 5/6

Interpretation:

- Simple wind-speed features do not show strong positive association with blast.
- Mean wind speed and wind direction variability are more often lower in disease weeks, but the signal is weak.
- Humid/leaf-wet wind features are mixed across years.
- Wind should not modify risk score yet.
- A Step 9 wind-mediated spatial model may still be worth exploring, but it should test directional transport from infected neighboring provinces rather than using wind speed alone.

Pre-Step 9 conclusion:

- Simple wind-speed epidemiology is insufficient.
- Future spatial modeling should focus on directional wind-mediated connectivity from infected neighboring provinces.

## 2026-05-20 Directional Wind Alignment Exploration

Implemented exploratory directional wind alignment without modifying risk scores.

Method:

- Compute bearing from each neighbor province to target province.
- Compare bearing with target province weekly `prevailing_wind_direction`.
- Neighbor is wind-aligned when angular difference <= 45 degrees.
- Use previous-week neighbor blast only.

New feature:

- `wind_aligned_neighbor_blast`

Outputs:

- `experiments/outputs/wind_directional_alignment_effects_2015_2021.csv`
- `experiments/outputs/wind_directional_alignment_stability_2015_2021.csv`
- `experiments/outputs/wind_directional_alignment_coverage_2015_2021.csv`
- `experiments/outputs/province_top5_neighbors_with_bearing.csv`

Coverage:

| year | disease weeks | wind-aligned nonzero weeks | mean wind-aligned neighbor blast |
|---|---:|---:|---:|
| 2015 | 0 | 0 | 0.0000 |
| 2016 | 2 | 2 | 0.0001 |
| 2017 | 65 | 110 | 0.0054 |
| 2018 | 27 | 26 | 0.0013 |
| 2019 | 148 | 215 | 0.0112 |
| 2020 | 573 | 675 | 0.0390 |
| 2021 | 359 | 393 | 0.0210 |

Directional effect:

| year | disease mean | no-disease mean | effect diff | correlation |
|---|---:|---:|---:|---:|
| 2016 | 0.0000 | 0.0001 | -0.0001 | -0.0005 |
| 2017 | 0.0031 | 0.0054 | -0.0024 | -0.0091 |
| 2018 | 0.0296 | 0.0011 | +0.0285 | 0.1374 |
| 2019 | 0.0162 | 0.0110 | +0.0052 | 0.0199 |
| 2020 | 0.0757 | 0.0330 | +0.0427 | 0.1558 |
| 2021 | 0.0373 | 0.0194 | +0.0180 | 0.0774 |

Stability:

- `wind_aligned_neighbor_blast`: positive 4/6 observed years.
- Mean correlation: 0.0635.
- Mean absolute correlation: 0.0667.
- Signal is much stronger than simple wind speed, but weaker than raw `neighbor_prevweek_blast`.

Interpretation:

- Directional wind-mediated neighbor infection has meaningful exploratory signal.
- The strongest years are 2018, 2020, and 2021.
- 2017 is a warning case where direction alignment is slightly negative.
- 2016 is too sparse to trust.
- This supports Step 9 exploration of wind-mediated spatial connectivity, but still does not justify modifying risk score yet.

## 2026-05-20 Regional Epidemiology v0

Implemented regional heterogeneity analysis.

Regions:

- North
- Northeast
- Central
- East
- West
- South

Outputs:

- `experiments/outputs/region_feature_effects.csv`
- `experiments/outputs/region_feature_stability.csv`
- `experiments/outputs/regional_validation_summary.csv`
- `experiments/outputs/regional_coverage.csv`
- `experiments/outputs/province_region_mapping.csv`

Disease-week coverage, 2017-2021:

| region | disease weeks |
|---|---:|
| Northeast | 458 |
| North | 350 |
| South | 152 |
| East | 126 |
| Central | 62 |
| West | 24 |

Best validation family counts for region-years with disease:

- host-weighted: 11
- weather-only: 8
- spatial-host-weather: 6

Mean f1 by region and score family:

| region | weather-only | host-weighted | spatial-host-weather |
|---|---:|---:|---:|
| Central | 0.0568 | 0.0555 | 0.0635 |
| East | 0.1606 | 0.1682 | 0.1481 |
| North | 0.1642 | 0.1660 | 0.1550 |
| Northeast | 0.1853 | 0.1911 | 0.1795 |
| South | 0.1740 | 0.1721 | 0.1541 |
| West | 0.2959 | 0.2930 | 0.1927 |

Host effect interpretation:

- Host susceptibility is strongest and most consistent in Northeast and East.
- Northeast `susceptibility_score`: positive 4/5 years, mean correlation 0.0982.
- East `susceptibility_score`: positive 3/5 years, mean correlation 0.1184.
- Central `susceptibility_score` is consistently negative in observed years, suggesting current national host weights may not transfer well there.
- West has too few disease years to trust despite high apparent correlations.

Spatial effect interpretation:

- Northeast has the clearest spatial pressure:
  - `neighbor_prevweek_blast`: positive 5/5 years, mean correlation 0.2036.
- North also shows moderate spatial signal:
  - `neighbor_prevweek_blast`: positive 4/6 years, mean correlation 0.0896.
- Central and South spatial signals are weak or inconsistent.
- Distance-only spatial score still does not consistently beat host-weighted rolling scores.

Wind-direction effect interpretation:

- Directional wind alignment differs strongly by region.
- Northeast `wind_aligned_neighbor_blast`: positive 4/5 years, mean correlation 0.0879.
- North `wind_aligned_neighbor_blast`: mixed 3/6 years, mean correlation 0.0420.
- East and South are mixed.
- Central `wind_aligned_neighbor_blast` is consistently negative/weak in observed years.

Scientific interpretation:

- Rice blast epidemiology is regionally heterogeneous.
- Northeast is the strongest candidate for spatial and wind-mediated connectivity modeling.
- East and Northeast are the best candidates for host-susceptibility refinement.
- South and West need caution because disease occurrence is sparse or behavior differs from national patterns.
- A single national mechanistic score is likely too coarse; future work should keep the national baseline but evaluate region-specific modifiers.

## 2026-05-20 Region-Aware Temporal Epidemiology Preparation

Implemented sequence-ready regional temporal epidemiology dataset preparation.

Goal:

- Prepare explainable temporal structure for future hybrid mechanistic + LSTM forecasting.
- No ML introduced.
- No score optimization performed.

New region-aware temporal features:

- `regional_neighbor_pressure_2w`
- `regional_neighbor_pressure_3w`
- `regional_leaf_wet_accumulation`
- `regional_host_pressure`
- `regional_wind_alignment_frequency`

Future target labels:

- `blast_t_plus_1`
- `blast_t_plus_2`

Outputs:

- `experiments/outputs/region_temporal_sequence_dataset_2015_2021.csv`
- `experiments/outputs/region_temporal_feature_effects.csv`
- `experiments/outputs/region_temporal_feature_consistency.csv`
- `experiments/outputs/region_temporal_feature_coverage.csv`

Sequence dataset:

- rows: 28,503
- columns: 38
- provinces: 77
- regions: 6
- `blast_t_plus_1` positives: 1,153
- `blast_t_plus_2` positives: 1,130

Coverage by year:

| year | rows | blast weeks | t+1 positives | t+2 positives |
|---|---:|---:|---:|---:|
| 2015 | 4081 | 0 | 0 | 0 |
| 2016 | 4081 | 2 | 2 | 2 |
| 2017 | 4077 | 65 | 65 | 65 |
| 2018 | 4077 | 27 | 27 | 27 |
| 2019 | 4081 | 148 | 146 | 143 |
| 2020 | 4081 | 573 | 568 | 562 |
| 2021 | 4025 | 359 | 345 | 331 |

Strongest t+1 temporal signals:

- Northeast:
  - `regional_wind_alignment_frequency`: mean corr 0.1960
  - `regional_neighbor_pressure_2w`: mean corr 0.1941
  - `regional_neighbor_pressure_3w`: mean corr 0.1908
  - `susceptibility_score`: mean corr 0.1062
- East:
  - `susceptibility_score`: mean corr 0.1257
  - `host_weighted_rolling_3w`: mean corr 0.0757
  - `rolling_3w_risk`: mean corr 0.0679
- North:
  - `regional_neighbor_pressure_2w`: mean corr 0.1044
  - `regional_wind_alignment_frequency`: mean corr 0.0967
  - `neighbor_prevweek_blast`: mean corr 0.0840
- South:
  - `regional_neighbor_pressure_2w`: positive 3/3 observed years, mean corr 0.1396
  - `regional_neighbor_pressure_3w`: positive 3/3 observed years, mean corr 0.1353
  - `regional_wind_alignment_frequency`: positive 3/3 observed years, mean corr 0.1200

Strongest t+2 temporal signals:

- Northeast:
  - `regional_neighbor_pressure_2w`: mean corr 0.1775
  - `regional_wind_alignment_frequency`: mean corr 0.1770
  - `regional_neighbor_pressure_3w`: mean corr 0.1662
  - `susceptibility_score`: mean corr 0.1073
- East:
  - `susceptibility_score`: mean corr 0.1285
  - `host_weighted_rolling_3w`: mean corr 0.0757
  - `rolling_3w_risk`: mean corr 0.0679
- North:
  - `regional_wind_alignment_frequency`: mean corr 0.0931
  - `regional_neighbor_pressure_2w`: mean corr 0.0852
  - `neighbor_prevweek_blast`: mean corr 0.0780

Interpretation:

- Region-aware temporal features preserve the main epidemiological insight: Northeast is dominated by regional spatial/wind-connected pressure.
- East appears more host-susceptibility driven.
- North has moderate regional neighbor and wind-alignment temporal signal.
- South shows regional pressure signal, but only across 3 observed disease years, so it needs caution.
- The sequence dataset is now ready for future hybrid mechanistic + LSTM experiments, but the next step should still start with transparent baselines before training sequence models.

## 2026-05-20 Step 9.1 ML/LSTM-ready Dataset Audit

Goal:

- Validate the region-aware temporal sequence dataset before entering Hybrid Temporal AI Epidemiology modeling.
- Treat this step as temporal epidemiological data governance, not model training.

Dataset audited:

- `experiments/outputs/region_temporal_sequence_dataset_2015_2021.csv`

Outputs:

- `experiments/outputs/dataset_audit_summary.csv`
- `experiments/outputs/temporal_sequence_integrity.csv`
- `experiments/outputs/label_distribution_summary.csv`
- `experiments/outputs/feature_integrity_summary.csv`
- `experiments/outputs/dataset_column_roles.csv`
- `experiments/outputs/temporal_leakage_risk_summary.csv`
- `experiments/outputs/train_val_test_split_summary.csv`

Dataset structure:

- rows: 28,503
- columns: 38
- provinces: 77
- regions: 6
- year coverage: 2015-2021
- week coverage: 1-53
- numeric columns: 29
- categorical columns: 2
- temporal columns: 3
- target columns: 2

Temporal integrity:

- Most provinces have near-complete weekly coverage across the sequence period.
- `Bueng Kan` has the strongest continuity issue:
  - rows: 359
  - estimated missing weeks: 3
  - duplicated province-week rows flagged: 10
  - sequence gap count: 6
  - max gap: 9 weeks
- Several provinces also show duplicated province-week rows around yearly/week boundaries and should be reviewed before formal ML training.
- Interpretation: the dataset is structurally usable for temporal learning, but sequence continuity policy must be fixed before Step 9 modeling.

Future label integrity:

Overall label distribution:

| target | available rows | positives | negatives | missing | positive rate |
|---|---:|---:|---:|---:|---:|
| `blast_t_plus_1` | 27,964 | 1,153 | 26,811 | 539 | 0.0405 |
| `blast_t_plus_2` | 27,425 | 1,130 | 26,295 | 1,078 | 0.0396 |

Yearly pattern:

- 2015 has no positive future blast labels.
- 2016 has extremely sparse positives.
- 2017-2019 contain low but usable positive signal.
- 2020 is the strongest outbreak year.
- 2021 remains outbreak-positive and is suitable as a chronological held-out test year.

Interpretation:

- Strong class imbalance remains and must be explicitly handled in future modeling design.
- Missing future labels are expected near sequence ends, especially for `t_plus_2`, and should not be imputed casually.

Feature integrity:

- No infinite values were detected.
- No major constant-column issue was detected.
- Minor missing values were detected in weather and wind-derived features:
  - `prevailing_wind_direction`: 29 missing
  - `wind_direction_variability`: 29 missing
  - `temperature_mean`: 28 missing
  - `humidity_mean`: 28 missing
  - `leaf_wet_ratio`: 28 missing
  - `risk_score`: 28 missing
  - `host_weighted_risk`: 28 missing
  - `spatial_host_weather_risk`: 28 missing
  - `mean_wind_speed`: 28 missing
  - rolling risk variants: 20-24 missing

Interpretation:

- Missingness is small relative to dataset size, but a transparent missing-value policy is required before ML.
- Do not normalize, impute, or rebalance yet; those decisions belong to the modeling protocol.

Temporal leakage risk:

- `blast_t_plus_1` is not included as a predictor.
- `blast_t_plus_2` is not included as a predictor.
- No explicitly future-named predictor columns were detected.
- Current disease labels are excluded from predictor roles.
- Rolling and regional temporal features require a historical-only definition to remain frozen.

Interpretation:

- Initial leakage audit passes for target-column exclusion.
- Rolling feature definitions should be frozen before sequence-window generation to prevent accidental future information leakage.

Chronological split summary:

| split | years | rows | t+1 positives | t+1 positive rate | t+2 positives | t+2 positive rate |
|---|---|---:|---:|---:|---:|---:|
| train | 2017-2019 | 12,081 | 238 | 0.0197 | 235 | 0.0195 |
| validation | 2020 | 4,235 | 582 | 0.1374 | 575 | 0.1358 |
| test | 2021 | 3,948 | 331 | 0.0838 | 318 | 0.0805 |

Interpretation:

- The chronological split is scientifically defensible for forecasting:
  - train: pre-major outbreak learning period
  - validation: high-outbreak year
  - test: later held-out year
- The distribution shift between train and validation/test is large and should be treated as an epidemiological realism challenge, not merely a model problem.

Conclusion:

- Step 9.1 confirms that the temporal sequence dataset is broadly ready for the next phase of Hybrid Temporal AI Epidemiology.
- The dataset is not yet ready for blind model training until the team freezes:
  - duplicate province-week handling
  - missing predictor policy
  - missing future-label policy
  - rolling-feature historical-only definitions
  - chronological evaluation protocol
- No ML training, normalization, or imbalance correction was performed in this step.

## 2026-05-20 Step 9.1B Spore-release-window Wind Feature Analysis

Goal:

- Test biologically informed wind features during likely rice blast conidia release windows before ML modeling.
- Use hourly weather data to separate general all-day wind from wind/moisture conditions during likely spore-release periods.
- Treat findings as exploratory association, not causal evidence.

Biological window definitions:

- Primary spore-release window: 02:00-06:00
- Broader exploratory window: 22:00-06:00

Implemented features:

- `spore_window_mean_wind_speed`
- `spore_window_prevailing_wind_direction`
- `spore_window_wind_direction_variability`
- `spore_window_leaf_wet_hours`
- `spore_window_humid_wind_hours`
- `spore_window_wind_aligned_neighbor_blast`
- `spore_window_wind_aligned_neighbor_count`
- `spore_window_min_wind_alignment_angle`
- `spore_window_mean_wind_alignment_angle`
- broader-window comparison features with `broad_spore_window_` prefix

Outputs:

- `experiments/outputs/spore_window_wind_features_2015_2021.csv`
- `experiments/outputs/spore_window_wind_effects_2015_2021.csv`
- `experiments/outputs/spore_window_wind_stability_2015_2021.csv`
- `experiments/outputs/spore_window_wind_comparison_2015_2021.csv`
- `experiments/outputs/spore_window_wind_coverage_2015_2021.csv`

Coverage:

| year | rows | provinces | blast weeks | mean primary-window observed hours | primary aligned nonzero weeks | all-day aligned nonzero weeks |
|---|---:|---:|---:|---:|---:|---:|
| 2015 | 4081 | 77 | 0 | 18.42 | 0 | 0 |
| 2016 | 4081 | 77 | 2 | 20.85 | 2 | 2 |
| 2017 | 4077 | 77 | 65 | 21.49 | 108 | 110 |
| 2018 | 4077 | 77 | 27 | 21.21 | 28 | 26 |
| 2019 | 4081 | 77 | 148 | 21.35 | 222 | 215 |
| 2020 | 4081 | 77 | 573 | 20.74 | 585 | 675 |
| 2021 | 4025 | 77 | 359 | 20.89 | 397 | 393 |

Main association findings:

- `spore_window_leaf_wet_hours` is the most stable biological-window feature.
  - For `blast_t_plus_1`: positive in 6/6 analyzable years, mean correlation 0.0360.
  - For `blast_t_plus_2`: positive in 6/6 analyzable years, mean correlation 0.0429.
- Broader-window leaf wet hours also remain stable.
  - For `blast_t_plus_1`: positive in 6/6 analyzable years, mean correlation 0.0350.
  - For `blast_t_plus_2`: positive in 6/6 analyzable years, mean correlation 0.0414.
- `spore_window_wind_aligned_neighbor_blast` shows weak-to-moderate association but mixed yearly stability.
  - For `blast_t_plus_1`: positive in 3/6 years, mean correlation 0.0383.
  - For `blast_t_plus_2`: positive in 4/6 years, mean correlation 0.0393.
- All-day `wind_aligned_neighbor_blast` remains comparable.
  - For `blast_t_plus_1`: positive in 3/6 years, mean correlation 0.0322.
  - For `blast_t_plus_2`: positive in 5/6 years, mean correlation 0.0426.
- Mean wind speed alone is mostly negative or unstable and should not be used as a direct risk amplifier.

Interpretation:

- The spore-release-window hypothesis adds biological interpretability, especially for leaf-wet and humid conditions during 02:00-06:00.
- Directional neighbor alignment during the spore-release window contains some signal, but it does not clearly dominate all-day directional alignment.
- The strongest evidence is not simple wind speed; it is moisture during biologically plausible release windows plus conservative directional neighbor context.
- This supports adding spore-window features to future ML-ready datasets as candidate predictors, but it does not justify changing the mechanistic risk score yet.

Limitations:

- The 02:00-06:00 release window is biologically informed but not locally calibrated.
- Weather station wind direction may not represent canopy-level airflow.
- Weekly aggregation may dilute short spore-release and deposition events.
- 2015 has no disease-positive weeks, so effect direction is evaluated from 2016-2021.

Conclusion:

- Step 9.1B confirms that biologically timed wind/moisture feature engineering is useful enough to carry forward into Step 9 feature governance.
- Spore-window leaf wetness is stable and interpretable.
- Spore-window directional alignment is promising but weak; it should remain an exploratory predictor, not a risk-score modifier.
- No ML training, normalization, imbalance correction, or risk-score change was performed.

## 2026-05-22 Step 9.2 Classical ML Epidemiology Baseline

Goal:

- Evaluate whether classical ML models can detect meaningful epidemiological structure from the mechanistic temporal dataset.
- Treat ML as epidemiological structure validation, not leaderboard optimization.
- Preserve explainability and compare against mechanistic score baselines.

Dataset:

- `experiments/outputs/region_temporal_sequence_dataset_2015_2021.csv`

Target:

- `blast_t_plus_1`

Chronological split:

| split | years | rows | positives | positive rate |
|---|---|---:|---:|---:|
| train | 2017-2019 | 11,927 | 238 | 0.0200 |
| validation | 2020 | 4,081 | 582 | 0.1426 |
| test | 2021 | 3,871 | 331 | 0.0855 |

Models:

- Random Forest
- XGBoost

Feature policy:

- Included mechanistic weather, rolling temporal, host susceptibility, spatial epidemiology, wind-alignment, regional metadata, and week seasonality features.
- Excluded future labels:
  - `blast_t_plus_1`
  - `blast_t_plus_2`
- Excluded direct leakage/current disease labels:
  - `blast_any`
  - `blast_days`
- Excluded identifiers and split metadata:
  - `province`
  - `datetime`
  - raw `year`
  - raw `week`
- Regional metadata was encoded using one-hot `region`.
- Imbalance was intentionally untreated.
- No SMOTE, no class weighting, no DNN, and no LSTM were used.

Outputs:

- `experiments/outputs/classical_ml_baseline_metrics.csv`
- `experiments/outputs/classical_ml_feature_importance.csv`
- `experiments/outputs/classical_ml_region_performance.csv`
- `experiments/outputs/classical_ml_prediction_errors.csv`
- `experiments/outputs/classical_ml_false_positives.csv`
- `experiments/outputs/classical_ml_false_negatives.csv`
- `experiments/outputs/classical_ml_mechanistic_baseline_comparison.csv`
- `experiments/outputs/classical_ml_test_comparison.csv`
- `experiments/outputs/classical_ml_feature_manifest.csv`
- `experiments/outputs/classical_ml_leakage_exclusions.csv`
- `experiments/outputs/classical_ml_model_status.csv`
- `experiments/outputs/classical_ml_split_summary.csv`

Test-set comparison:

| model | precision | recall | f1 | ROC-AUC | PR-AUC | false positive | false negative |
|---|---:|---:|---:|---:|---:|---:|---:|
| Random Forest | 0.1574 | 0.5589 | 0.2457 | 0.7118 | 0.2034 | 990 | 146 |
| XGBoost | 0.1873 | 0.2931 | 0.2285 | 0.7143 | 0.2048 | 421 | 234 |
| spatial-host-weather baseline | 0.0938 | 0.5317 | 0.1594 | 0.5080 | 0.0954 | 1701 | 155 |
| weather-only baseline | 0.0908 | 0.3958 | 0.1477 | 0.5022 | 0.0915 | 1312 | 200 |
| host-weighted baseline | 0.0888 | 0.3988 | 0.1452 | 0.5052 | 0.0967 | 1355 | 199 |

Interpretation:

- Classical ML improves substantially over mechanistic threshold baselines on ROC-AUC, PR-AUC, and F1.
- Random Forest gives the best test F1 and recall, but produces many false positives.
- XGBoost gives slightly better precision, ROC-AUC, and PR-AUC, but lower recall.
- This is consistent with the project hypothesis that the mechanistic temporal feature set contains learnable epidemiological structure.
- The large train-to-validation/test distribution shift remains important: train positives are around 2%, while validation/test positives are much higher.

Top feature importance:

Random Forest strongest features:

- `susceptibility_score`
- `wind_direction_variability`
- `regional_neighbor_pressure_3w`
- `regional_neighbor_pressure_2w`
- `regional_host_pressure`
- `regional_wind_alignment_frequency`
- `temperature_mean`
- `mean_wind_speed`
- `neighbor_prevweek_risk`
- `prevailing_wind_direction`

XGBoost strongest features:

- `regional_neighbor_pressure_2w`
- `regional_neighbor_pressure_3w`
- `region_Northeast`
- `susceptibility_score`
- `regional_wind_alignment_frequency`
- `humidity_mean`
- `week_cos`
- `region_South`
- `regional_host_pressure`
- `wind_direction_variability`

Regional performance on 2021 test:

- Random Forest recall is strongest in Northeast, North, South, and West but with high false positives.
- XGBoost performs best in South and Northeast, with fewer false positives than Random Forest.
- Central has no positive test labels, so positive-class metrics are not epidemiologically informative there.
- West has few positive rows, so region-level metrics are unstable.

Error pattern:

- Random Forest false positives are widespread because the validation-selected threshold is low.
- XGBoost false positives concentrate in provinces such as Phetchabun, Tak, Roi Et, Nakhon Si Thammarat, and Nakhon Sawan.
- XGBoost false negatives concentrate in Nan, Uthai Thani, Pattani, Phrae, Phayao, Ubon Ratchathani, and Nakhon Ratchasima.
- These errors suggest regional/province-specific outbreak regimes that may need region-adaptive thresholds or temporal sequence modeling later.

Conclusion:

- Step 9.2 confirms that classical ML can detect epidemiological structure beyond hand-thresholded mechanistic scores.
- The feature importance pattern supports earlier findings: host susceptibility, regional neighbor pressure, wind alignment/context, and temporal accumulation all carry signal.
- Because imbalance was intentionally untreated, the current metrics should be interpreted as baseline structure validation, not final forecasting performance.
- Next work should freeze the ML evaluation protocol and then test controlled improvements such as threshold policy, calibrated probabilities, region-aware evaluation, and later sequence learning.

## 2026-05-22 Step 9.3 DNN Baseline for Hybrid Temporal AI Epidemiology

Goal:

- Train a simple interpretable dense neural network baseline as a bridge between classical ML and future LSTM/sequence learning.
- Test whether a small DNN improves over Random Forest, XGBoost, and mechanistic baselines using the same chronological split.

Dataset:

- `experiments/outputs/region_temporal_sequence_dataset_2015_2021.csv`

Target:

- `blast_t_plus_1`

Chronological split:

| split | years | rows | positives | positive rate |
|---|---|---:|---:|---:|
| train | 2017-2019 | 11,927 | 238 | 0.0200 |
| validation | 2020 | 4,081 | 582 | 0.1426 |
| test | 2021 | 3,871 | 331 | 0.0855 |

Feature policy:

- Used the same leakage exclusions as Step 9.2.
- Excluded:
  - `blast_t_plus_1`
  - `blast_t_plus_2`
  - `blast_any`
  - `blast_days`
  - `datetime`
  - raw `year`
  - raw `week`
- Included numeric epidemiological predictors plus encoded categorical metadata:
  - `province`
  - `region`
- Added week seasonality as `week_sin` and `week_cos`.

Preprocessing:

- numeric predictors:
  - median imputation
  - standardization
- categorical predictors:
  - most-frequent imputation
  - one-hot encoding

Model:

- small dense neural network
- Dense 64 ReLU
- Dropout 0.25
- Dense 32 ReLU
- Dropout 0.15
- Sigmoid binary output
- Early stopping on validation PR-AUC

Runs:

- `dnn_no_class_weight`
- `dnn_class_weight`

Outputs:

- `experiments/outputs/dnn_baseline_metrics.csv`
- `experiments/outputs/dnn_baseline_test_predictions.csv`
- `experiments/outputs/dnn_baseline_confusion_matrix.csv`
- `experiments/outputs/dnn_baseline_training_history.csv`
- `experiments/outputs/dnn_baseline_model_comparison.csv`
- `experiments/outputs/dnn_baseline_feature_manifest.csv`
- `experiments/outputs/dnn_baseline_leakage_exclusions.csv`
- `experiments/outputs/dnn_baseline_split_summary.csv`

Validation results:

| model | threshold | precision | recall | f1 | ROC-AUC | PR-AUC | false positive | false negative |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DNN no class weight | 0.05 | 0.3313 | 0.3763 | 0.3524 | 0.7175 | 0.3323 | 442 | 363 |
| DNN class weight | 0.85 | 0.3849 | 0.5000 | 0.4350 | 0.7768 | 0.3811 | 465 | 291 |

Test comparison:

| model | precision | recall | f1 | ROC-AUC | PR-AUC | false positive | false negative |
|---|---:|---:|---:|---:|---:|---:|---:|
| DNN class weight | 0.3002 | 0.4290 | 0.3532 | 0.7303 | 0.2683 | 331 | 189 |
| DNN no class weight | 0.2495 | 0.4139 | 0.3114 | 0.7317 | 0.2573 | 412 | 194 |
| Random Forest | 0.1574 | 0.5589 | 0.2457 | 0.7118 | 0.2034 | 990 | 146 |
| XGBoost | 0.1873 | 0.2931 | 0.2285 | 0.7143 | 0.2048 | 421 | 234 |
| spatial-host-weather baseline | 0.0938 | 0.5317 | 0.1594 | 0.5080 | 0.0954 | 1701 | 155 |
| weather-only baseline | 0.0908 | 0.3958 | 0.1477 | 0.5022 | 0.0915 | 1312 | 200 |
| host-weighted baseline | 0.0888 | 0.3988 | 0.1452 | 0.5052 | 0.0967 | 1355 | 199 |

Interpretation:

- The simple DNN improves over Random Forest and XGBoost on test F1 and PR-AUC.
- The class-weighted DNN gives the best F1 and precision among all tested models.
- Random Forest still gives higher recall, but at the cost of many more false positives.
- The class-weighted DNN reduces false positives substantially compared with Random Forest while keeping moderate recall.
- This suggests nonlinear interactions among host, regional pressure, weather, and wind features are useful even before LSTM.

Limitations:

- This is still a tabular DNN, not a temporal sequence model.
- Province one-hot encoding may help capture regional/province effects but can reduce geographic generalization.
- The threshold was selected from validation data; threshold governance should be frozen before serious forecasting claims.
- Class weighting was tested conservatively, but no SMOTE or aggressive imbalance engineering was used.

Conclusion:

- Step 9.3 supports moving toward Hybrid Temporal AI Epidemiology.
- A simple dense neural baseline already improves over classical ML on test F1 and PR-AUC.
- The next scientific step should not jump directly to complex LSTM tuning; it should define sequence-window construction and compare tabular DNN vs temporal DNN/LSTM under the same leakage-safe protocol.

## 2026-05-22 Step 9.4 LSTM Temporal Sequence Model

Goal:

- Train an initial LSTM baseline using province-wise weekly temporal sequences.
- Test whether explicit 4-week temporal sequence learning improves over tabular DNN, classical ML, and mechanistic baselines.
- Preserve temporal integrity before any aggressive tuning.

Dataset:

- `experiments/outputs/region_temporal_sequence_dataset_2015_2021.csv`

Target:

- `blast_t_plus_1`

Sequence setup:

- sequence length: 4 weeks
- each sample uses the previous/current 4 weekly rows of epidemiological predictors
- prediction target is `blast_t_plus_1` at the sequence end week
- sequences are constructed within `province + year`
- no sequence crosses province boundaries
- no sequence crosses year boundaries

Feature policy:

- Same leakage exclusions as Step 9.3.
- Excluded:
  - `blast_t_plus_1`
  - `blast_t_plus_2`
  - `blast_any`
  - `blast_days`
  - `datetime`
  - raw `year`
  - raw `week`
- Included:
  - numeric epidemiological predictors
  - one-hot `province`
  - one-hot `region`
  - `week_sin`
  - `week_cos`

Preprocessing:

- numeric predictors:
  - median imputation
  - standardization
  - fitted on train years only
- categorical predictors:
  - most-frequent imputation
  - one-hot encoding
  - fitted on train years only

Model:

- LSTM 32 units
- recurrent dropout 0.10
- dropout 0.20
- dense 16 ReLU
- sigmoid binary output
- binary cross entropy
- early stopping on validation PR-AUC

Runs:

- `lstm_no_class_weight`
- `lstm_class_weight`

Outputs:

- `experiments/outputs/lstm_baseline_metrics.csv`
- `experiments/outputs/lstm_baseline_test_predictions.csv`
- `experiments/outputs/lstm_baseline_confusion_matrix.csv`
- `experiments/outputs/lstm_baseline_training_history.csv`
- `experiments/outputs/lstm_baseline_model_comparison.csv`
- `experiments/outputs/lstm_sequence_manifest.csv`
- `experiments/outputs/lstm_sequence_summary.csv`
- `experiments/outputs/lstm_baseline_feature_manifest.csv`

Sequence coverage:

| split | years | sequences | positives | positive rate | provinces | regions |
|---|---|---:|---:|---:|---:|---:|
| train | 2017-2019 | 11,311 | 229 | 0.0202 | 77 | 6 |
| validation | 2020 | 3,927 | 570 | 0.1451 | 77 | 6 |
| test | 2021 | 3,640 | 292 | 0.0802 | 77 | 6 |

Validation results:

| model | threshold | precision | recall | f1 | ROC-AUC | PR-AUC | false positive | false negative |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LSTM no class weight | 0.05 | 0.3646 | 0.1772 | 0.2385 | 0.6608 | 0.2580 | 176 | 469 |
| LSTM class weight | 0.80 | 0.3483 | 0.4895 | 0.4070 | 0.7670 | 0.3639 | 522 | 291 |

Test comparison:

| model | precision | recall | f1 | ROC-AUC | PR-AUC | false positive | false negative |
|---|---:|---:|---:|---:|---:|---:|---:|
| DNN class weight | 0.3002 | 0.4290 | 0.3532 | 0.7303 | 0.2683 | 331 | 189 |
| DNN no class weight | 0.2495 | 0.4139 | 0.3114 | 0.7317 | 0.2573 | 412 | 194 |
| LSTM class weight | 0.2528 | 0.3904 | 0.3069 | 0.7094 | 0.2087 | 337 | 178 |
| Random Forest | 0.1574 | 0.5589 | 0.2457 | 0.7118 | 0.2034 | 990 | 146 |
| XGBoost | 0.1873 | 0.2931 | 0.2285 | 0.7143 | 0.2048 | 421 | 234 |
| LSTM no class weight | 0.2116 | 0.1747 | 0.1914 | 0.6213 | 0.1685 | 190 | 241 |
| spatial-host-weather baseline | 0.0938 | 0.5317 | 0.1594 | 0.5080 | 0.0954 | 1701 | 155 |
| weather-only baseline | 0.0908 | 0.3958 | 0.1477 | 0.5022 | 0.0915 | 1312 | 200 |
| host-weighted baseline | 0.0888 | 0.3988 | 0.1452 | 0.5052 | 0.0967 | 1355 | 199 |

Interpretation:

- Class weighting is important for LSTM; without it, recall is too low.
- The class-weighted LSTM improves over mechanistic baselines and is competitive with classical ML.
- The class-weighted LSTM does not beat the tabular DNN baseline on test F1 or PR-AUC.
- This suggests the current 4-week LSTM setup is not yet extracting stronger temporal signal than the tabular DNN.
- The result is scientifically useful: temporal sequence modeling is feasible, but sequence design needs careful governance before stronger claims.

Limitations:

- Sequence length was fixed at 4 weeks and not tuned.
- Sequences were restricted within province-year to avoid leakage, which removes early-year weeks and reduces sample count.
- Province one-hot encoding helps baseline performance but may limit geographic generalization.
- The LSTM architecture is intentionally small and not optimized.
- Weekly aggregation may still hide shorter infection/spore-release dynamics.

Conclusion:

- Step 9.4 successfully establishes a leakage-aware LSTM baseline.
- Current LSTM does not yet outperform the simpler tabular DNN.
- The next research direction should be sequence governance rather than aggressive model tuning:
  - compare sequence lengths such as 2, 4, 6, and 8 weeks
  - test sequence construction with previous-only windows vs current-inclusive windows
  - evaluate region-specific sequence behavior
  - decide whether province should be one-hot, embedding, or excluded for generalization tests

## 2026-05-22 Step 9.4B LSTM Temporal Sequence Governance

Goal:

- Investigate how temporal sequence length and epidemiological feature grouping affect rice blast forecasting before building hybrid LSTM models.
- Treat this as sequence-governance research, not model optimization.
- Preserve temporal integrity and avoid province/year leakage.

Dataset:

- `experiments/outputs/region_temporal_sequence_dataset_2015_2021.csv`

Target:

- `blast_t_plus_1`

Split:

- train: 2017-2019
- validation: 2020
- test: 2021

Sequence design:

- sequence lengths tested:
  - 2 weeks
  - 4 weeks
  - 8 weeks
  - 12 weeks
- sequences are constructed within `province + year`
- no sequence crosses province boundaries
- no sequence crosses year boundaries
- target is evaluated at the sequence end week

Feature-group design:

- `temporal_only`
  - humidity
  - rainfall
  - leaf wetness
  - rolling risk
  - neighbor previous-week pressure
  - wind alignment
  - week seasonality
- `temporal_host`
  - temporal-only features
  - susceptibility and host-weighted risk features
- `temporal_host_spatial`
  - temporal + host features
  - spatial-host-weather and regional pressure features

Important design note:

- Province and region were not used as model inputs in this governance run.
- Region was used only for evaluation.
- This was intentional to test epidemiological temporal feature behavior without geographic one-hot memorization.

Model policy:

- same small LSTM architecture across all configurations
- class-weighted training
- early stopping on validation PR-AUC
- no aggressive tuning
- no hybrid gating
- no transformer

Outputs:

- `experiments/outputs/lstm_sequence_governance_metrics.csv`
- `experiments/outputs/lstm_sequence_length_comparison.csv`
- `experiments/outputs/lstm_feature_group_comparison.csv`
- `experiments/outputs/lstm_region_performance.csv`
- `experiments/outputs/lstm_sequence_governance_training_history.csv`
- `experiments/outputs/lstm_sequence_governance_manifest.csv`

Best test configurations:

| config | feature group | sequence length | precision | recall | f1 | ROC-AUC | PR-AUC |
|---|---|---:|---:|---:|---:|---:|---:|
| `temporal_host_2w` | temporal + host | 2 | 0.1539 | 0.6195 | 0.2466 | 0.7111 | 0.2171 |
| `temporal_host_spatial_2w` | temporal + host + spatial | 2 | 0.1702 | 0.3836 | 0.2357 | 0.7094 | 0.1782 |
| `temporal_only_2w` | temporal only | 2 | 0.1639 | 0.3459 | 0.2224 | 0.6699 | 0.1852 |
| `temporal_host_spatial_4w` | temporal + host + spatial | 4 | 0.1212 | 0.6610 | 0.2049 | 0.6727 | 0.1501 |
| `temporal_host_4w` | temporal + host | 4 | 0.1350 | 0.4212 | 0.2045 | 0.6765 | 0.1739 |

Sequence length effects:

| sequence length | best f1 | mean f1 | best PR-AUC | mean PR-AUC | best ROC-AUC |
|---:|---:|---:|---:|---:|---:|
| 2 | 0.2466 | 0.2349 | 0.2171 | 0.1935 | 0.7111 |
| 4 | 0.2049 | 0.2038 | 0.1739 | 0.1545 | 0.6765 |
| 8 | 0.1711 | 0.1660 | 0.1078 | 0.1059 | 0.6264 |
| 12 | 0.1687 | 0.1472 | 0.1080 | 0.0977 | 0.6247 |

Interpretation:

- Short memory performs best in this governance run.
- Two-week sequences outperform 4, 8, and 12 weeks on best F1, mean F1, PR-AUC, and ROC-AUC.
- Longer memory does not help under the current simple LSTM architecture and current weekly feature design.
- This suggests the weekly rice blast signal in this dataset may be more immediate/short-lag than long-memory, or that longer windows introduce noise and reduce usable sample count.

Feature-group effects:

| feature group | best f1 | mean f1 | best PR-AUC | mean PR-AUC | best ROC-AUC |
|---|---:|---:|---:|---:|---:|
| temporal + host | 0.2466 | 0.1968 | 0.2171 | 0.1437 | 0.7111 |
| temporal + host + spatial | 0.2357 | 0.1827 | 0.1782 | 0.1349 | 0.7094 |
| temporal only | 0.2224 | 0.1845 | 0.1852 | 0.1350 | 0.6699 |

Interpretation:

- Adding host susceptibility improves the best sequence result.
- Spatial/regional pressure features do not improve the best LSTM result in this run.
- Spatial features may still be useful, but the current simple LSTM may not use them effectively without better architecture or region-aware handling.

Regional behavior:

- Northeast remains the strongest and most interpretable region for sequence learning.
- The best region-level result was `temporal_host_spatial_2w` in Northeast:
  - precision 0.2143
  - recall 0.5192
  - f1 0.3034
  - ROC-AUC 0.7437
  - PR-AUC 0.2308
- `temporal_host_2w` in Northeast had high recall:
  - recall 0.8365
  - f1 0.2839
  - PR-AUC 0.3191
- West sometimes shows high ROC-AUC, but sample size and positive count are small, so interpretation should be cautious.
- North and South show usable but less stable sequence behavior.

Conclusion:

- Step 9.4B shows that temporal sequence governance matters substantially.
- Longer sequence memory does not automatically improve rice blast forecasting.
- Current evidence favors:
  - 2-week memory
  - temporal + host features
  - region-wise interpretation, especially Northeast
- The tabular DNN from Step 9.3 still outperforms these simple LSTM governance configurations overall, but the 2-week LSTM results provide a clearer direction for future hybrid temporal modeling.

Next direction:

- Use 2-week sequence length as the initial default for future hybrid LSTM work.
- Test previous-only windows versus current-inclusive windows.
- Consider region-aware LSTM evaluation, especially Northeast.
- Reintroduce region/province metadata carefully as embeddings or controlled inputs, not as unchecked memorization.
- Do not proceed to complex hybrid gating until sequence construction and regional behavior are frozen.

## 2026-05-22 Step 9.4C Advanced Statistical Epidemiology Features

Goal:

- Create advanced statistical temporal features to improve future ML/LSTM forecasting while preserving epidemiological interpretability.
- Add historical rolling, trend, EWMA, and province-relative anomaly features.
- Do not train ML in this step.

Dataset:

- Base dataset: `experiments/outputs/region_temporal_sequence_dataset_2015_2021.csv`
- Optional spore-window feature source: `experiments/outputs/spore_window_wind_features_2015_2021.csv`
- Enhanced output: `experiments/outputs/region_temporal_sequence_dataset_stat_features.csv`

Source features used:

- `humidity_mean`
- `leaf_wet_hours`
- `leaf_wet_ratio`
- `spore_window_leaf_wet_hours`
- `risk_score`
- `host_weighted_risk`
- `neighbor_prevweek_risk`
- `neighbor_prevweek_blast`
- `wind_aligned_neighbor_blast`
- `susceptibility_score`

Feature families created:

- historical rolling mean:
  - 2 weeks
  - 4 weeks
  - 8 weeks
- historical rolling standard deviation:
  - 2 weeks
  - 4 weeks
  - 8 weeks
- historical rolling max:
  - 2 weeks
  - 4 weeks
  - 8 weeks
- historical rolling min:
  - 2 weeks
  - 4 weeks
  - 8 weeks
- historical rolling sum:
  - 2 weeks
  - 4 weeks
  - 8 weeks
- historical rolling slope/trend:
  - 4 weeks
  - 8 weeks
- historical EWMA:
  - span 4
- province-relative historical anomaly:
  - current value minus prior province historical mean
  - historical z-score within province
  - historical percentile rank within province

Temporal safety policy:

- All rolling and EWMA features use `shift(1)` before aggregation.
- Current week values are excluded from historical rolling statistics.
- Future labels are not used.
- Province-relative mean, z-score, and percentile features use prior weeks only.

Outputs:

- `experiments/outputs/region_temporal_sequence_dataset_stat_features.csv`
- `experiments/outputs/statistical_temporal_feature_manifest.csv`
- `experiments/outputs/statistical_temporal_feature_integrity.csv`
- `experiments/outputs/statistical_temporal_leakage_audit.csv`
- `experiments/outputs/statistical_temporal_feature_summary.csv`

Summary:

| metric | value |
|---|---:|
| input rows | 28,503 |
| input columns after spore-window join | 41 |
| output rows | 28,503 |
| output columns | 251 |
| source features used | 10 |
| statistical features created | 210 |
| features with infinite values | 0 |
| constant features | 0 |
| low-variance features | 0 |
| leakage audit pass | 210/210 |

Integrity findings:

- No infinite values were detected.
- No constant features were detected.
- No low-variance features were detected.
- Higher missingness appears in historical z-score features for sparse binary pressure variables:
  - `wind_aligned_neighbor_blast_province_hist_zscore`
  - `neighbor_prevweek_blast_province_hist_zscore`
- Interpretation: this is expected because early province history and sparse binary values often have insufficient or zero historical standard deviation.

Interpretation:

- The enhanced dataset now contains interpretable temporal memory features without future leakage.
- These features should help test whether explicit statistical memory can improve tabular DNN or LSTM models.
- The feature count increased substantially but remains governed by a manifest.
- Statistical features are explainable and tied to epidemiological concepts:
  - moisture persistence
  - risk accumulation
  - host susceptibility anomaly
  - neighbor pressure trend
  - wind-aligned pressure history

Conclusion:

- Step 9.4C successfully creates a leakage-safe statistical temporal feature dataset.
- This prepares the next phase: test whether advanced statistical memory improves DNN and/or LSTM without changing the mechanistic risk score.
- No ML training was performed in this step.

## 2026-05-22 Step 9.4D ML/DNN with Advanced Statistical Temporal Features

Goal:

- Evaluate whether the leakage-safe statistical temporal features from Step 9.4C improve forecasting performance.
- Compare against previous RF, XGBoost, DNN, LSTM, and mechanistic baselines.
- Keep this as a controlled comparison, not aggressive optimization.

Dataset:

- `experiments/outputs/region_temporal_sequence_dataset_stat_features.csv`

Target:

- `blast_t_plus_1`

Split:

- train: 2017-2019
- validation: 2020
- test: 2021

Feature policy:

- same leakage exclusions as previous ML/DNN experiments
- excluded:
  - `blast_t_plus_1`
  - `blast_t_plus_2`
  - `blast_any`
  - `blast_days`
  - `datetime`
  - raw `year`
  - raw `week`
- included:
  - base mechanistic epidemiological features
  - statistical temporal features
  - host features
  - spatial features
  - wind/spore-window features
  - one-hot `province`
  - one-hot `region`

Feature set:

- numeric features: 244
- categorical features: `province`, `region`
- statistical features used: 210

Models:

- Random Forest
- XGBoost
- DNN without class weights
- DNN with class weights

Outputs:

- `experiments/outputs/stat_feature_ml_metrics.csv`
- `experiments/outputs/stat_feature_dnn_metrics.csv`
- `experiments/outputs/stat_feature_model_comparison.csv`
- `experiments/outputs/stat_feature_importance.csv`
- `experiments/outputs/stat_feature_importance_family_summary.csv`
- `experiments/outputs/stat_feature_confusion_matrix.csv`
- `experiments/outputs/stat_feature_test_predictions.csv`
- `experiments/outputs/stat_feature_manifest_used.csv`
- `experiments/outputs/stat_feature_dnn_training_history.csv`
- `experiments/outputs/stat_feature_split_summary.csv`

Test comparison:

| model | precision | recall | f1 | ROC-AUC | PR-AUC | false positive | false negative |
|---|---:|---:|---:|---:|---:|---:|---:|
| DNN class weight | 0.3002 | 0.4290 | 0.3532 | 0.7303 | 0.2683 | 331 | 189 |
| DNN no class weight | 0.2495 | 0.4139 | 0.3114 | 0.7317 | 0.2573 | 412 | 194 |
| LSTM class weight | 0.2528 | 0.3904 | 0.3069 | 0.7094 | 0.2087 | 337 | 178 |
| stat DNN class weight | 0.2249 | 0.4199 | 0.2929 | 0.7391 | 0.2235 | 479 | 192 |
| stat DNN no class weight | 0.2668 | 0.3112 | 0.2873 | 0.7038 | 0.2157 | 283 | 228 |
| Random Forest | 0.1574 | 0.5589 | 0.2457 | 0.7118 | 0.2034 | 990 | 146 |
| stat XGBoost | 0.1951 | 0.2870 | 0.2323 | 0.7173 | 0.2132 | 392 | 236 |
| XGBoost | 0.1873 | 0.2931 | 0.2285 | 0.7143 | 0.2048 | 421 | 234 |
| stat Random Forest | 0.1288 | 0.7221 | 0.2186 | 0.6696 | 0.1666 | 1617 | 92 |
| spatial-host-weather baseline | 0.0938 | 0.5317 | 0.1594 | 0.5080 | 0.0954 | 1701 | 155 |
| weather-only baseline | 0.0908 | 0.3958 | 0.1477 | 0.5022 | 0.0915 | 1312 | 200 |
| host-weighted baseline | 0.0888 | 0.3988 | 0.1452 | 0.5052 | 0.0967 | 1355 | 199 |

Interpretation:

- Statistical features improve XGBoost slightly over the previous XGBoost baseline:
  - F1: 0.2285 to 0.2323
  - ROC-AUC: 0.7143 to 0.7173
  - PR-AUC: 0.2048 to 0.2132
  - false positives decrease from 421 to 392
- Statistical features do not improve Random Forest F1; stat RF increases recall but produces too many false positives.
- Statistical features do not beat the original DNN class-weight baseline on F1 or PR-AUC.
- Stat DNN class weight has the highest ROC-AUC among tested models, but lower F1 and PR-AUC than the original DNN.
- This suggests statistical memory features contain useful signal, but the expanded feature space can dilute or destabilize baseline models without feature selection.

Top model signals:

Random Forest with statistical features:

- `province_Songkhla`
- `regional_neighbor_pressure_3w`
- `regional_neighbor_pressure_2w`
- `susceptibility_score_province_hist_percentile`
- `regional_wind_alignment_frequency`
- `regional_host_pressure`
- `wind_aligned_neighbor_blast_province_hist_zscore`
- `susceptibility_score_hist_ewma_span4`
- `susceptibility_score_hist_4w_max`
- `susceptibility_score_hist_2w_min`

XGBoost with statistical features:

- `regional_neighbor_pressure_2w`
- `regional_wind_alignment_frequency`
- `rolling_3w_risk`
- `regional_neighbor_pressure_3w`
- `host_weighted_rolling_3w`
- `province_Songkhla`
- `spore_window_leaf_wet_hours_hist_2w_min`
- `province_Tak`
- `rolling_2w_leaf_wet_hours`
- `neighbor_prevweek_blast_hist_4w_mean`

Feature family importance:

| model | top family by total importance | total importance |
|---|---|---:|
| stat Random Forest | rolling statistics | 0.4877 |
| stat XGBoost | rolling statistics | 0.4695 |
| stat Random Forest | base epidemiological | 0.1750 |
| stat XGBoost | base epidemiological | 0.2068 |
| stat Random Forest | province-relative | 0.1660 |
| stat XGBoost | province-relative | 0.1242 |

Epidemiological interpretation:

- Rolling statistics matter strongly, especially susceptibility, spore-window leaf wetness, neighbor pressure, and host-weighted risk history.
- Province-relative features add useful signal, especially for susceptibility and wind-aligned neighbor blast anomalies.
- EWMA and slope features are useful but less dominant than rolling statistics and base epidemiological features.
- Spore-window historical leaf wetness appears in XGBoost top features, supporting the biological timing hypothesis from Step 9.1B.

Conclusion:

- Step 9.4D shows that advanced statistical temporal features add interpretable signal, especially for tree-based models.
- However, adding all statistical features does not automatically improve the best overall model.
- The current best overall model remains the original DNN class-weight baseline from Step 9.3.
- Next work should focus on governed feature selection rather than adding more model complexity:
  - select top statistical feature families
  - compare base-only vs rolling-only vs province-relative subsets
  - test DNN with reduced statistical feature sets
  - avoid moving to hybrid gating until feature selection is controlled

## 2026-05-22 Step 9.4E Controlled Feature Selection for Statistical Temporal Features

Goal:

- Select compact, biologically interpretable feature sets from the statistical temporal feature dataset.
- Test whether controlled subsets improve ML/DNN performance compared with all statistical features and prior baselines.
- Avoid adding new features or tuning aggressively.

Dataset:

- `experiments/outputs/region_temporal_sequence_dataset_stat_features.csv`

Target:

- `blast_t_plus_1`

Split:

- train: 2017-2019
- validation: 2020
- test: 2021

Feature sets:

| feature set | total features | statistical features |
|---|---:|---:|
| `core_only` | 34 | 0 |
| `core_plus_top20_stat` | 54 | 20 |
| `core_plus_biological_stat` | 68 | 34 |
| `core_plus_top_family` | 64 | 30 |

Feature set definitions:

- `core_only`
  - original mechanistic weather
  - temporal rolling risk
  - host susceptibility
  - spatial pressure
  - wind/spore-window features
  - one-hot province and region
- `core_plus_top20_stat`
  - core features
  - top 20 statistical features ranked from RF/XGBoost importance
- `core_plus_biological_stat`
  - core features
  - biologically meaningful rolling leaf wetness, spore-window leaf wetness, host-weighted risk, neighbor blast, susceptibility anomaly, and wind-aligned anomaly features
- `core_plus_top_family`
  - core features
  - top rolling-statistic and province-relative features

Models:

- XGBoost
- DNN class-weighted

Outputs:

- `experiments/outputs/controlled_feature_selection_metrics.csv`
- `experiments/outputs/controlled_feature_sets_manifest.csv`
- `experiments/outputs/controlled_feature_importance.csv`
- `experiments/outputs/controlled_feature_test_predictions.csv`
- `experiments/outputs/controlled_feature_model_comparison.csv`

Test comparison:

| model | feature set | precision | recall | f1 | ROC-AUC | PR-AUC | false positive | false negative |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| controlled DNN class weight | `core_only` | 0.3157 | 0.4683 | 0.3771 | 0.7335 | 0.2722 | 336 | 176 |
| previous DNN class weight | reference | 0.3002 | 0.4290 | 0.3532 | 0.7303 | 0.2683 | 331 | 189 |
| controlled DNN class weight | `core_plus_top_family` | 0.2520 | 0.4804 | 0.3306 | 0.7207 | 0.2413 | 472 | 172 |
| controlled DNN class weight | `core_plus_biological_stat` | 0.2298 | 0.5166 | 0.3181 | 0.7371 | 0.2570 | 573 | 160 |
| controlled DNN class weight | `core_plus_top20_stat` | 0.2283 | 0.3897 | 0.2879 | 0.7191 | 0.2321 | 436 | 202 |
| controlled XGBoost | `core_only` | 0.2450 | 0.3323 | 0.2821 | 0.7282 | 0.2423 | 339 | 221 |
| controlled XGBoost | `core_plus_biological_stat` | 0.2082 | 0.3535 | 0.2620 | 0.7164 | 0.2310 | 445 | 214 |
| controlled XGBoost | `core_plus_top20_stat` | 0.2029 | 0.2991 | 0.2418 | 0.7179 | 0.2284 | 389 | 232 |
| controlled XGBoost | `core_plus_top_family` | 0.1869 | 0.2508 | 0.2142 | 0.7105 | 0.2084 | 361 | 248 |

Main finding:

- The compact `core_only` DNN is the best model so far.
- It improves over the previous DNN class-weight baseline:
  - F1: 0.3532 to 0.3771
  - precision: 0.3002 to 0.3157
  - recall: 0.4290 to 0.4683
  - PR-AUC: 0.2683 to 0.2722
  - false negatives: 189 to 176
  - false positives remain similar: 331 to 336

Interpretation:

- Controlled feature governance improves performance more than simply adding many statistical features.
- Statistical feature subsets did not improve over `core_only` in this run.
- The best result comes from a compact, biologically interpretable feature set that includes:
  - mechanistic weather
  - host susceptibility
  - spatial pressure
  - wind/spore-window context
  - regional/province metadata
- This suggests the original epidemiological feature engineering is strong, and excessive derived statistics can dilute signal or increase noise.

XGBoost interpretation:

- Controlled XGBoost with `core_only` outperforms previous XGBoost and stat XGBoost:
  - controlled XGBoost F1: 0.2821
  - previous XGBoost F1: 0.2285
  - stat XGBoost all-features F1: 0.2323
- This confirms that compact feature governance also benefits tree models.

Scientific interpretation:

- The statistical temporal features contain real signal, but they should not be added wholesale.
- The current best direction is not "more features"; it is biologically disciplined feature selection.
- The compact core feature set likely captures the strongest mechanistic, host, spatial, wind, and regional structure already.

Conclusion:

- Step 9.4E establishes the current best baseline:
  - controlled DNN class-weighted with `core_only`
  - test F1 0.3771
  - ROC-AUC 0.7335
  - PR-AUC 0.2722
- This becomes the new reference baseline before any hybrid model.
- Next work should freeze the `core_only` feature set and test:
  - threshold calibration
  - region-wise thresholds
  - probability calibration
  - region-aware evaluation
  - hybrid modeling only after feature-set governance is frozen

## 2026-05-22 Step 9.5 Hybrid Mechanistic-LSTM Baseline

Goal:

- Test whether combining compact core epidemiological features with short temporal memory improves forecasting beyond the best DNN baseline.
- Use the governed `core_only` feature set from Step 9.4E.
- Keep the model interpretable and conservative.

Current best reference before this step:

- controlled DNN class-weighted + `core_only`
- test F1: 0.3771
- ROC-AUC: 0.7335
- PR-AUC: 0.2722

Dataset:

- `experiments/outputs/region_temporal_sequence_dataset_2015_2021.csv`

Target:

- `blast_t_plus_1`

Split:

- train: 2017-2019
- validation: 2020
- test: 2021

Hybrid design:

- temporal branch:
  - 2-week sequence
  - compact LSTM
  - dropout
- current-week mechanistic branch:
  - current-week `core_only` feature vector
  - dense layers
- fusion:
  - concatenate LSTM representation and current-week representation
  - dense fusion layer
  - sigmoid output

Feature policy:

- used `core_only` governed features
- included one-hot province and region through the preprocessing pipeline
- no statistical all-features dataset
- no SMOTE
- class weighting enabled
- train-only imputation, scaling, and one-hot encoding

Temporal integrity:

- sequence length: 2 weeks
- sequences constructed within `province + year`
- no sequence crosses province boundaries
- no sequence crosses year boundaries

Outputs:

- `experiments/outputs/hybrid_lstm_metrics.csv`
- `experiments/outputs/hybrid_lstm_test_predictions.csv`
- `experiments/outputs/hybrid_lstm_confusion_matrix.csv`
- `experiments/outputs/hybrid_lstm_training_history.csv`
- `experiments/outputs/hybrid_lstm_model_comparison.csv`
- `experiments/outputs/hybrid_lstm_manifest.csv`
- `experiments/outputs/hybrid_lstm_sequence_summary.csv`

Sequence coverage:

| split | rows | positives | positive rate | provinces | regions |
|---|---:|---:|---:|---:|---:|
| train | 11,773 | 238 | 0.0202 | 77 | 6 |
| validation | 4,081 | 582 | 0.1426 | 77 | 6 |
| test | 3,794 | 318 | 0.0838 | 77 | 6 |

Hybrid results:

| split | precision | recall | f1 | ROC-AUC | PR-AUC | false positive | false negative |
|---|---:|---:|---:|---:|---:|---:|---:|
| validation | 0.3333 | 0.5189 | 0.4059 | 0.7645 | 0.3889 | 604 | 280 |
| test | 0.2097 | 0.4497 | 0.2860 | 0.6971 | 0.2305 | 539 | 175 |

Test comparison:

| model | precision | recall | f1 | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|
| controlled DNN core-only | 0.3157 | 0.4683 | 0.3771 | 0.7335 | 0.2722 |
| previous DNN class weight | 0.3002 | 0.4290 | 0.3532 | 0.7303 | 0.2683 |
| LSTM class weight | 0.2528 | 0.3904 | 0.3069 | 0.7094 | 0.2087 |
| hybrid mechanistic-LSTM | 0.2097 | 0.4497 | 0.2860 | 0.6971 | 0.2305 |
| controlled XGBoost core-only | 0.2450 | 0.3323 | 0.2821 | 0.7282 | 0.2423 |

Interpretation:

- The hybrid model performs reasonably on validation but drops on the 2021 test year.
- It does not improve over the controlled DNN core-only baseline.
- It slightly improves recall relative to some LSTM/classical baselines, but precision and F1 are weaker than the best DNN.
- The temporal branch may be adding noise or overfitting the 2020 validation outbreak pattern.
- Current-week compact epidemiological features remain more reliable than the initial fused temporal architecture.

Scientific interpretation:

- Hybrid modeling is feasible but not automatically superior.
- The best current evidence still favors a compact tabular representation of mechanistic, host, spatial, wind, and regional information.
- Temporal sequence information may require better design:
  - previous-only versus current-inclusive windows
  - region-specific temporal behavior
  - calibrated fusion
  - simpler temporal summaries before LSTM fusion

Conclusion:

- Step 9.5 establishes a first hybrid mechanistic-LSTM baseline.
- It does not beat the controlled DNN core-only reference.
- The project should not escalate to more complex hybrid architectures yet.
- Next work should focus on calibration and regional evaluation of the current best compact DNN baseline before further hybrid complexity.

## 2026-05-22 Step 9.5B Hybrid LSTM Generalization Error Analysis

Goal:

- Diagnose why the hybrid mechanistic-LSTM performed well on validation 2020 but dropped on test 2021.
- Compare hybrid errors against the best current controlled DNN `core_only` baseline.
- Focus on generalization and epidemiological interpretation.

Inputs:

- `experiments/outputs/hybrid_lstm_test_predictions.csv`
- `experiments/outputs/controlled_feature_test_predictions.csv`
- `experiments/outputs/hybrid_lstm_metrics.csv`
- `experiments/outputs/controlled_feature_selection_metrics.csv`
- `experiments/outputs/region_temporal_sequence_dataset_2015_2021.csv`

Outputs:

- `experiments/outputs/hybrid_lstm_error_overlap.csv`
- `experiments/outputs/hybrid_lstm_region_error_summary.csv`
- `experiments/outputs/hybrid_lstm_year_shift_summary.csv`
- `experiments/outputs/hybrid_lstm_failure_case_summary.csv`
- `experiments/outputs/hybrid_lstm_province_error_summary.csv`
- `experiments/outputs/hybrid_lstm_week_error_summary.csv`
- `experiments/outputs/hybrid_lstm_risk_context_error_summary.csv`
- `experiments/outputs/hybrid_lstm_validation_test_metric_shift.csv`

Important note:

- Row-level validation predictions were not exported in Step 9.5.
- Therefore this diagnostic compares row-level DNN vs hybrid predictions on test 2021 and uses aggregate validation/test metrics plus feature distribution summaries for year-shift analysis.

Test 2021 overlap summary:

| overlap type | rows |
|---|---:|
| both correct | 2,973 |
| both wrong | 391 |
| DNN correct / hybrid wrong | 323 |
| hybrid correct / DNN wrong | 107 |

Interpretation:

- The DNN has a clear advantage in disagreement cases.
- Hybrid produces about 3 times more unique mistakes than it uniquely corrects.
- This explains why hybrid recall remains moderate but F1 drops: the temporal branch adds many wrong positives.

Validation-to-test metric shift:

| model | split | precision | recall | f1 | ROC-AUC | PR-AUC | false positive | false negative |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| hybrid LSTM | validation | 0.3333 | 0.5189 | 0.4059 | 0.7645 | 0.3889 | 604 | 280 |
| hybrid LSTM | test | 0.2097 | 0.4497 | 0.2860 | 0.6971 | 0.2305 | 539 | 175 |
| controlled DNN core-only | validation | 0.3905 | 0.5481 | 0.4560 | 0.7971 | 0.4026 | 498 | 263 |
| controlled DNN core-only | test | 0.3157 | 0.4683 | 0.3771 | 0.7335 | 0.2722 | 336 | 176 |

Interpretation:

- Both models degrade from validation 2020 to test 2021.
- Hybrid degrades more sharply:
  - F1 drop: 0.4059 to 0.2860
  - PR-AUC drop: 0.3889 to 0.2305
  - precision drop: 0.3333 to 0.2097
- Controlled DNN remains more stable and better calibrated across years.

Regional error behavior on test 2021:

- Hybrid over-predicts in several regions:
  - Central: 29 false positives despite 0 positives in overlap rows
  - East: 60 false positives
  - North: 221 false positives
  - Northeast: 160 false positives
  - South: 69 false positives
- Hybrid has better recall than DNN in some regions, but this comes with high false positives.
- West has no predicted positives from either model and all 14 positives are missed.

Region-level interpretation:

- North is the largest hybrid failure area:
  - hybrid false positives: 221
  - hybrid false negatives: 59
  - hybrid F1: 0.2857
  - DNN F1: 0.3502
- Northeast remains epidemiologically informative but hybrid still over-predicts:
  - hybrid false positives: 160
  - DNN false positives: 148
  - DNN F1 remains higher.
- South has a stronger DNN precision advantage:
  - DNN precision 0.5385
  - hybrid precision 0.2737

Risk-context behavior:

| risk level | rows | positive rate | DNN F1 | hybrid F1 | hybrid false positive | hybrid false negative |
|---|---:|---:|---:|---:|---:|---:|
| High | 118 | 0.1356 | 0.4286 | 0.3571 | 30 | 6 |
| Moderate | 1,674 | 0.0902 | 0.3746 | 0.3142 | 246 | 77 |
| Low | 2,002 | 0.0754 | 0.3567 | 0.2495 | 263 | 92 |

Interpretation:

- Hybrid over-predicts even in low and moderate risk contexts.
- This supports the hypothesis that the temporal branch learned a broad outbreak-like pattern from validation 2020 that does not transfer cleanly to 2021.

Major hybrid false-positive provinces:

- Tak: 41
- Sukhothai: 38
- Surin: 35
- Si Sa Ket: 34
- Prachin Buri: 27
- Rayong: 25
- Lampang: 23
- Phrae: 21
- Phichit: 18
- Maha Sarakham: 17

Major hybrid false-negative provinces:

- Nan: 23
- Pattani: 22
- Nakhon Ratchasima: 17
- Phayao: 14
- Uthai Thani: 14
- Chachoengsao: 11
- Phetchaburi: 9
- Nakhon Si Thammarat: 8
- Yasothon: 7

Diagnostic conclusion:

- The hybrid LSTM is primarily over-predicting, not under-predicting.
- It is region-sensitive and year-sensitive.
- It appears to generalize worse than the DNN because it reacts too strongly to short temporal patterns that resemble 2020 outbreak conditions.
- The controlled DNN core-only baseline is more stable across validation/test and has better precision-F1 balance.

Implication:

- Do not increase hybrid architecture complexity yet.
- Prioritize:
  - probability calibration
  - regional threshold calibration
  - region-wise error governance
  - exporting validation predictions for future diagnostics
  - testing hybrid models only after calibration and regional behavior are understood

## 2026-05-22 Step 9.6 Calibration and Regional Threshold Governance

Goal:

- Improve decision quality of the current best rice blast forecasting model without changing model architecture.
- Use validation 2020 only for threshold selection and calibration.
- Preserve test 2021 as held-out evaluation.

Current reference model:

- controlled DNN class-weighted + `core_only`
- reference test F1: 0.3771
- reference ROC-AUC: 0.7335
- reference PR-AUC: 0.2722

Inputs:

- `experiments/outputs/controlled_feature_test_predictions.csv`
- `experiments/outputs/controlled_feature_validation_predictions.csv`
- `experiments/outputs/controlled_feature_selection_metrics.csv`
- `experiments/outputs/region_temporal_sequence_dataset_2015_2021.csv`

Implementation note:

- `controlled_stat_feature_selection.py` was updated to export:
  - `controlled_feature_validation_predictions.csv`
  - `controlled_feature_all_predictions.csv`
- No new model architecture was trained.
- Thresholds and calibration were selected from validation 2020 only.

Threshold policies:

- `global_f1`
- `global_high_recall`
- `global_high_precision`
- `region_f1`
- `region_high_recall`
- `platt_global_f1`

Outputs:

- `experiments/outputs/calibration_threshold_metrics.csv`
- `experiments/outputs/regional_thresholds.csv`
- `experiments/outputs/calibrated_test_predictions.csv`
- `experiments/outputs/calibration_region_performance.csv`
- `experiments/outputs/calibration_confusion_matrix.csv`
- `experiments/outputs/calibration_policy_comparison.csv`
- `experiments/outputs/calibration_reliability_summary.csv`

Selected thresholds from validation 2020:

| policy | region | threshold |
|---|---|---:|
| global F1 | all | 0.82 |
| global high recall | all | 0.43 |
| global high precision | all | 0.95 |
| region F1 | North | 0.92 |
| region F1 | Northeast | 0.78 |
| region F1 | Central | 0.45 |
| region F1 | East | 0.67 |
| region F1 | West | 0.05 |
| region F1 | South | 0.54 |
| region high recall | North | 0.53 |
| region high recall | Northeast | 0.53 |
| region high recall | Central | 0.22 |
| region high recall | East | 0.49 |
| region high recall | West | 0.05 |
| region high recall | South | 0.31 |

Test 2021 policy comparison:

| policy | precision | recall | f1 | ROC-AUC | PR-AUC | false positive | false negative |
|---|---:|---:|---:|---:|---:|---:|---:|
| global F1 | 0.3246 | 0.4471 | 0.3761 | 0.7335 | 0.2722 | 308 | 183 |
| Platt global F1 | 0.2985 | 0.4834 | 0.3691 | 0.7335 | 0.2722 | 376 | 171 |
| region F1 | 0.2659 | 0.4411 | 0.3318 | 0.7335 | 0.2722 | 403 | 185 |
| global high precision | 0.4439 | 0.2628 | 0.3302 | 0.7335 | 0.2722 | 109 | 244 |
| global high recall | 0.1803 | 0.6193 | 0.2793 | 0.7335 | 0.2722 | 932 | 126 |
| region high recall | 0.1717 | 0.6133 | 0.2683 | 0.7335 | 0.2722 | 979 | 128 |

Interpretation:

- The validation-selected global F1 threshold `0.82` performs almost identically to the previous reference threshold `0.80`.
- Global F1 threshold slightly reduces false positives:
  - reference FP: 336
  - global F1 FP: 308
- However, it slightly increases false negatives:
  - reference FN: 176
  - global F1 FN: 183
- F1 remains effectively stable:
  - reference F1: 0.3771
  - global F1 F1: 0.3761

High-precision policy:

- Threshold 0.95 strongly reduces false positives:
  - FP: 109
- But recall drops:
  - recall: 0.2628
  - FN: 244
- This policy may be useful only when false alarms are very costly.

High-recall policy:

- Threshold 0.43 increases recall:
  - recall: 0.6193
- But false positives become very high:
  - FP: 932
- This policy may be useful only for surveillance screening where missing outbreaks is much more costly than field verification.

Regional threshold findings:

- Region-specific F1 thresholds did not improve overall test F1.
- North required a much higher validation-selected threshold:
  - region F1 threshold: 0.92
  - interpretation: North tends to over-predict unless threshold is raised.
- South required a lower threshold:
  - region F1 threshold: 0.54
  - interpretation: South may need more sensitive thresholding.
- Northeast remained close to the global threshold:
  - region F1 threshold: 0.78
- West selected a very low threshold:
  - 0.05
  - interpretation should be cautious because positive samples are sparse.
- Central selected a low threshold from validation but had no positives in test, causing avoidable false positives.

Region-wise implication:

- Regional thresholding is epidemiologically appealing but unstable with current validation/test distribution.
- Some regional thresholds appear to overfit validation 2020.
- Regional threshold governance should require multi-year validation before being adopted.

Probability calibration:

- Platt scaling improved reliability of probability bins.
- Calibration made predicted probabilities less extreme and better aligned with observed prevalence.
- However, calibrated global F1 did not improve test F1 over the uncalibrated global F1 threshold.

Reliability interpretation:

- The uncalibrated DNN is overconfident at high score ranges.
- Example from test:
  - uncalibrated 0.9-1.0 bin mean score: 0.960
  - observed positive rate: 0.339
- Platt calibration reduces overconfidence:
  - calibrated high bins are closer to observed rates.
- This is useful for risk communication even if classification F1 does not improve.

Conclusion:

- Step 9.6 confirms that the current controlled DNN core-only baseline is already near its best global decision threshold.
- Global threshold governance is preferable to regional thresholding at this stage.
- Recommended operational policies:
  - balanced policy: global threshold around 0.80-0.82
  - high-precision policy: threshold around 0.95
  - high-recall surveillance policy: threshold around 0.43
- Regional thresholds should not be frozen yet because they are not stable enough from one validation year.
- Probability calibration is valuable for interpretation and communication, but not yet for improving F1.

Next direction:

- Export validation predictions by default for every future model.
- Test threshold policies across multiple validation years if possible.
- Study region-specific thresholds only after multi-year validation.
- Use calibrated probabilities for decision support dashboards, while keeping classification threshold policy explicit.

## 2026-05-23 Step 9.6B Decision Policy Error Analysis

Goal:

- Analyze operational behavior of calibrated and threshold-based decision policies from Step 9.6.
- Interpret model outputs as agricultural disease decision-support behavior.
- No new model training, no architecture change, and no test-based threshold selection.

Inputs:

- `experiments/outputs/calibrated_test_predictions.csv`
- `experiments/outputs/calibration_policy_comparison.csv`
- `experiments/outputs/calibration_region_performance.csv`
- `experiments/outputs/calibration_confusion_matrix.csv`
- `experiments/outputs/calibration_reliability_summary.csv`
- `experiments/outputs/region_temporal_sequence_dataset_2015_2021.csv`

Policies analyzed:

- balanced policy: `global_f1`, threshold 0.82
- high precision policy: `global_high_precision`, threshold 0.95
- high recall policy: `global_high_recall`, threshold 0.43
- calibrated policy: `platt_global_f1`, calibrated threshold 0.28

Outputs:

- `experiments/outputs/decision_policy_error_summary.csv`
- `experiments/outputs/decision_policy_region_summary.csv`
- `experiments/outputs/decision_policy_province_summary.csv`
- `experiments/outputs/decision_policy_week_summary.csv`
- `experiments/outputs/decision_policy_risk_context_summary.csv`
- `experiments/outputs/alert_tier_summary.csv`
- `experiments/outputs/alert_tier_region_summary.csv`
- `experiments/outputs/alert_tier_error_summary.csv`
- `experiments/outputs/decision_policy_behavior_summary.csv`

Policy behavior summary:

| policy | predicted positive | precision | recall | f1 | false positive | false negative |
|---|---:|---:|---:|---:|---:|---:|
| global F1 | 456 | 0.3246 | 0.4471 | 0.3761 | 308 | 183 |
| Platt global F1 | 536 | 0.2985 | 0.4834 | 0.3691 | 376 | 171 |
| global high precision | 196 | 0.4439 | 0.2628 | 0.3302 | 109 | 244 |
| global high recall | 1,137 | 0.1803 | 0.6193 | 0.2793 | 932 | 126 |

Interpretation:

- `global_high_recall` over-predicts most.
- `global_high_precision` under-predicts most.
- `global_f1` remains the most balanced operational decision policy.
- `platt_global_f1` improves probability interpretation and recall but increases false positives compared with `global_f1`.

Regional behavior:

- Highest false-positive region across most policies: Northeast.
- Highest false-negative region across most policies: North.
- Central has no positive rows in test 2021, so any predicted positive is operationally a false alarm.
- West remains difficult because positive rows are sparse and both balanced/calibrated policies miss all positives.

Global F1 regional summary:

| region | positives | precision | recall | f1 | false positive | false negative |
|---|---:|---:|---:|---:|---:|---:|
| Central | 0 | 0.0000 | 0.0000 | 0.0000 | 2 | 0 |
| East | 28 | 0.3462 | 0.3214 | 0.3333 | 17 | 19 |
| North | 120 | 0.2961 | 0.4417 | 0.3545 | 126 | 67 |
| Northeast | 112 | 0.3143 | 0.5893 | 0.4099 | 144 | 46 |
| South | 57 | 0.5128 | 0.3509 | 0.4167 | 19 | 37 |
| West | 14 | 0.0000 | 0.0000 | 0.0000 | 0 | 14 |

Policy-specific interpretation:

- High precision policy:
  - Best for reducing unnecessary field alerts.
  - False positives drop to 109.
  - But false negatives rise to 244.
  - Useful only if false alarms are costly and missed outbreaks are tolerable.
- High recall policy:
  - Best for surveillance coverage.
  - False negatives drop to 126.
  - But false positives rise to 932.
  - Useful only when screening/monitoring capacity is high.
- Balanced global F1:
  - Best default operational compromise.
  - Keeps false positives far below high-recall policy while retaining more recall than high-precision policy.
- Platt calibrated policy:
  - Better for risk communication than binary classification improvement.
  - Slightly higher recall than global F1 but more false positives.

Alert-tier design:

Calibrated probabilities were converted to operational alert tiers:

- low risk: 0.00-0.10
- watch: 0.10-0.25
- warning: 0.25-0.40
- high alert: 0.40-1.00

Alert-tier summary:

| tier | rows | positives | positive rate | false positive | false negative | mean calibrated score |
|---|---:|---:|---:|---:|---:|---:|
| low risk | 2,593 | 121 | 0.0467 | 0 | 121 | 0.0511 |
| watch | 667 | 45 | 0.0675 | 0 | 45 | 0.1613 |
| warning | 433 | 85 | 0.1963 | 278 | 5 | 0.3292 |
| high alert | 178 | 80 | 0.4494 | 98 | 0 | 0.4183 |

Interpretation:

- Alert tiers are more useful for communication than a single binary decision.
- `high_alert` has the highest observed positive rate, approximately 45%.
- `warning` captures many positives but still creates many false positives.
- `low_risk` and `watch` are not "no disease" guarantees; they still contain positives.
- Operationally, low/watch tiers should communicate lower priority, not absence of risk.

Classification vs risk communication:

- Threshold policies are suitable for operational action decisions.
- Alert tiers are better for dashboards, extension communication, and staged field monitoring.
- A single binary threshold hides important uncertainty.
- Calibrated tiers can separate:
  - routine monitoring
  - watch-level awareness
  - warning-level field checking
  - high-alert priority response

Decision governance conclusion:

- The current best default remains global balanced threshold around 0.80-0.82.
- High precision and high recall policies should be treated as operational modes, not replacements.
- Regional thresholds remain unstable, but regional error summaries are valuable for monitoring.
- Alert tiers provide a practical decision-support layer even when binary F1 does not improve.

Next direction:

- Define operational decision modes explicitly:
  - balanced default
  - high precision field-alert mode
  - high recall surveillance mode
  - calibrated alert-tier dashboard mode
- Add region-specific monitoring notes without freezing region-specific thresholds.
- Evaluate decision policies with stakeholders or domain cost assumptions before optimizing further.

## 2026-05-24 Updated Data Intake Audit

Goal:

- Inspect newly added data under `updated data/`.
- Determine whether the new data should be integrated before the next modeling phase.
- Preserve the existing model pipeline until data quality and research implications are understood.

Inputs audited:

- `updated data/weather_hourly`
- `updated data/pov_rice_monthly`
- `updated data/rice_blast_outbreak_weekly`
- `updated data/bus_value_dayly`
- `updated data/thailand_province_name.csv`

Scripts:

- `experiments/audit_updated_data.py`
- `experiments/audit_updated_data_content.py`

Outputs:

- `experiments/outputs/updated_data_file_inventory.csv`
- `experiments/outputs/updated_data_category_summary.csv`
- `experiments/outputs/updated_data_schema_samples.csv`
- `experiments/outputs/updated_outbreak_weekly_summary.csv`
- `experiments/outputs/updated_outbreak_weekly_by_province.csv`
- `experiments/outputs/updated_pov_monthly_summary.csv`
- `experiments/outputs/updated_pov_top_varieties.csv`
- `experiments/outputs/updated_bus_daily_summary.csv`
- `experiments/outputs/updated_bus_daily_detail.csv`
- `experiments/outputs/updated_province_mapping_summary.csv`

High-level inventory:

| category | coverage | key finding |
|---|---|---|
| weather hourly | 2015-2022 | 924 files per year; schema matches previous hourly weather structure |
| POV monthly | 2015-2022 | in-season data covers 77 provinces each year; off-season covers 70-73 provinces depending on year |
| rice blast outbreak weekly | 2016-2022 | 77 province files per year; provides 2022 outbreak labels |
| BUS daily | 2020-2023 | daily `maxbus`, `minbus`, `avgbus` from rice research/seed centers |
| province mapping | 77 rows | English-Thai province name mapping available |

Updated outbreak weekly summary:

| year | rows | provinces | positive rows | total outbreak area |
|---:|---:|---:|---:|---:|
| 2016 | 77 | 77 | 1 | 2,000 |
| 2017 | 924 | 77 | 32 | 46,741 |
| 2018 | 693 | 77 | 28 | 162,133 |
| 2019 | 3,850 | 77 | 119 | 3,880,290 |
| 2020 | 3,927 | 77 | 471 | 975,192 |
| 2021 | 3,850 | 77 | 308 | 32,409 |
| 2022 | 3,850 | 77 | 161 | 8,475 |

Updated POV monthly summary:

- In-season POV covers all 77 provinces for 2015-2022.
- Off-season POV coverage varies:
  - 73 provinces in 2015-2018
  - 70 provinces in 2019
  - 71 provinces in 2020 and 2022
  - 72 provinces in 2021
- 2022 off-season data currently covers January-June only.
- The POV schema includes key varieties already used in susceptibility v0:
  - `กข6`
  - `กข15`
  - `ขาวดอกมะลิ105`

BUS daily summary:

| year | center type | files | rows | locations | date coverage |
|---:|---|---:|---:|---:|---|
| 2020 | Rice Research Center | 18 | 1,775 | 18 | 2020-01-01 to 2020-12-31 |
| 2020 | Rice Seed Center | 6 | 486 | 6 | 2020-08-15 to 2020-12-31 |
| 2021 | Rice Research Center | 22 | 7,832 | 22 | 2021-01-01 to 2021-12-31 |
| 2021 | Rice Seed Center | 7 | 2,527 | 7 | 2021-01-01 to 2021-12-31 |
| 2022 | Rice Research Center | 24 | 8,633 | 24 | 2022-01-01 to 2022-12-31 |
| 2022 | Rice Seed Center | 8 | 2,680 | 8 | 2022-01-01 to 2022-12-31 |
| 2023 | Rice Research Center | 24 | 1,388 | 24 | 2023-01-01 to 2023-02-28 |
| 2023 | Rice Seed Center | 8 | 472 | 8 | 2023-01-01 to 2023-02-28 |

Research interpretation:

- The updated dataset is highly valuable because it extends the full weather/POV/outbreak structure to 2022.
- The new 2022 outbreak labels may allow a stronger held-out temporal generalization test after rebuilding sequence features.
- The weekly outbreak data appears more standardized than the earlier label construction, but 2016 remains extremely sparse and should not be treated as a normal training year without caution.
- BUS daily data is potentially important as an external mechanistic disease-pressure reference, but its spatial coverage is center-based rather than province-complete.
- BUS values should be introduced as an exploratory external reference feature or validation covariate, not as a direct replacement for outbreak labels.
- The province name mapping can improve Thai-English consistency across weather, POV, outbreak, and reporting outputs.

Immediate recommendation:

- Treat this as a new data governance step before retraining:
  - updated data intake
  - label comparison with existing disease labels
  - 2022 sequence dataset extension
  - BUS feature feasibility analysis
- Do not merge into the ML/DNN/LSTM pipeline until old-vs-new label consistency has been checked.

Proposed next step:

- Step 9.7: Updated Data Integration and Label Governance.
- Main question:
  - Does the updated weekly outbreak label source change the disease signal, validation results, or thesis interpretation compared with the current 2015-2021 sequence dataset?

## 2026-05-24 Updated Core Data Comparison and BUS Intake

Goal:

- Check whether updated `weather_hourly` and `pov_rice_monthly` differ from the original data.
- Prepare to replace the old blast disease labels with `rice_blast_outbreak_weekly`.
- Assess where BUS (Blast Unit of Severity) can be used in the research pipeline.

New scripts/utilities:

- `experiments/compare_updated_core_data.py`
- `experiments/compare_updated_blast_labels.py`
- `tools/updated_data_loaders.py`

Outputs:

- `experiments/outputs/updated_vs_old_weather_file_summary.csv`
- `experiments/outputs/updated_vs_old_weather_comparison_summary.csv`
- `experiments/outputs/updated_vs_old_weather_monthly_comparison.csv`
- `experiments/outputs/updated_vs_old_pov_file_summary.csv`
- `experiments/outputs/updated_vs_old_pov_comparison_summary.csv`
- `experiments/outputs/updated_vs_old_pov_variety_comparison.csv`
- `experiments/outputs/updated_vs_old_blast_label_summary.csv`
- `experiments/outputs/updated_vs_old_blast_label_comparison.csv`
- `experiments/outputs/bus_weekly_feature_summary.csv`
- `experiments/outputs/bus_weekly_features.csv`

Weather comparison:

- Original weather files:
  - 1,848 files/year
  - monthly weather is split into `-1` and `-2` files.
- Updated weather files:
  - 924 files/year
  - one monthly file per province.
- Representative value comparison was run across:
  - 6 provinces
  - 4 months/year
  - 2015-2022
  - 192 province-year-month keys.

Weather comparison result:

| metric | value |
|---|---:|
| matched monthly keys | 192 |
| old-only monthly keys | 0 |
| updated-only monthly keys | 0 |
| keys with row-count difference | 0 |
| keys with numeric difference | 0 |
| max temperature mean absolute difference | approximately 0 |
| max humidity mean absolute difference | approximately 0 |
| max precipitation mean absolute difference | approximately 0 |

Interpretation:

- Updated `weather_hourly` appears to be the same underlying weather data as the original source, but stored in a cleaner monthly file structure.
- The updated weather source is preferable for future rebuilding because it reduces file count and removes the `-1/-2` split.
- No evidence was found that weather values materially differ from the original data in the sampled comparison.

POV comparison:

- Original POV files are daily-expanded:
  - approximately 28,105-28,182 rows/year/season for 77 provinces.
  - date coverage appears daily across the whole year.
- Updated POV files are monthly:
  - in-season: 693 rows/year for 77 provinces.
  - off-season: 426-584 rows/year depending on year and province coverage.

POV comparison result:

- Raw area totals differ greatly because the old data appears daily-expanded while the updated data is monthly.
- Therefore, raw area totals are not directly comparable between old and updated POV.
- The updated monthly POV is likely the cleaner source for host composition.
- Susceptibility features should be rebuilt from updated monthly ratios rather than raw daily-expanded area totals.
- Before replacing the POV pipeline, compare variety ratios by province-month, not raw area sums.

Updated blast outbreak labels:

- The new `rice_blast_outbreak_weekly` source should replace the old `blast disease` labels because the old raw source has known errors.
- `tools/updated_data_loaders.py` now includes `load_updated_blast_outbreak_weekly()`.
- The loader converts source dates to the project convention of week-ending Sunday.
- It preserves `source_year` separately because week-ending Sunday can shift late-year reports into the next calendar year.

Old-vs-updated label comparison:

| year | old positives | updated positives | old positive / updated negative | old negative / updated positive | agreement rate |
|---:|---:|---:|---:|---:|---:|
| 2016 | 2 | 1 | 1 | 0 | 0.9998 |
| 2017 | 65 | 32 | 33 | 0 | 0.9919 |
| 2018 | 27 | 28 | 0 | 1 | 0.9998 |
| 2019 | 148 | 119 | 33 | 4 | 0.9909 |
| 2020 | 573 | 471 | 102 | 0 | 0.9750 |
| 2021 | 359 | 308 | 66 | 15 | 0.9802 |

Interpretation:

- The updated labels are not identical to the old labels.
- Most disagreements are old-positive / updated-negative.
- This confirms that replacing the old labels can materially change model training and validation.
- Results after Step 9.2-9.6 should be treated as based on the old label source and should not be considered final after the label correction.

BUS intake:

- BUS means Blast Unit of Severity.
- It is a biologically meaningful weather-risk index based on temperature, relative humidity, and dew/leaf wetness duration.
- A common critical threshold is BUS >= 2.25.
- `tools/updated_data_loaders.py` now includes:
  - `load_bus_daily()`
  - `bus_to_weekly_features()`
- Weekly BUS features created:
  - `avgbus_mean`
  - `avgbus_max`
  - `maxbus_max`
  - `minbus_min`
  - `bus_critical_days`
  - `bus_critical_any`
  - `bus_critical_ratio`

BUS weekly summary:

| year | center type | locations | critical weeks | mean critical ratio |
|---:|---|---:|---:|---:|
| 2020 | Rice Research Center | 18 | 31 | 0.1507 |
| 2020 | Rice Seed Center | 6 | 4 | 0.0304 |
| 2021 | Rice Research Center | 22 | 84 | 0.0466 |
| 2021 | Rice Seed Center | 7 | 10 | 0.0140 |
| 2022 | Rice Research Center | 24 | 51 | 0.0428 |
| 2022 | Rice Seed Center | 8 | 3 | 0.0051 |
| 2023 | Rice Research Center | 24 | 11 | 0.0970 |
| 2023 | Rice Seed Center | 8 | 0 | 0.0000 |

Recommended BUS use:

1. Mechanistic reference benchmark
   - Compare `risk_score`, `leaf_wet_hours`, and `host_weighted_risk` against BUS.
   - Test whether BUS >= 2.25 aligns with outbreak weeks.

2. External explanatory feature
   - Add weekly BUS features as a separate feature family.
   - Do not replace existing weather features immediately.

3. Spatially cautious covariate
   - BUS stations/centers are not province-complete.
   - Province-level use should require a nearest-center or regional aggregation rule.
   - This rule should be documented because it introduces spatial assumptions.

4. Decision-support interpretation
   - BUS critical weeks can support alert-tier explanation:
     - high model probability + BUS critical = stronger warning evidence.
     - high model probability without BUS critical = possible host/spatial-driven risk.

Important caution:

- BUS should not become the target label.
- BUS is a weather suitability index, not observed disease occurrence.
- It can improve mechanistic explanation and validation, but outbreak labels should remain the disease target.

Decision:

- Use updated weather for future rebuilds because it is cleaner and equivalent to the old weather data.
- Use updated monthly POV for future host feature rebuilds, but compare variety ratios before freezing.
- Replace old blast disease labels with updated weekly outbreak labels.
- Introduce BUS in the next phase as an external mechanistic risk feature/reference, not as a replacement for disease labels.

Proposed next step:

- Step 9.7: Rebuild sequence dataset using updated labels and updated source paths.
- Step 9.7B: BUS mechanistic benchmark and feature feasibility analysis.

## 2026-05-24 Step 9.7 Rebuild Updated Sequence Dataset with Corrected Labels

Goal:

- Rebuild the rice blast temporal epidemiology sequence dataset using updated data sources.
- Replace the old `blast disease` labels with corrected `rice_blast_outbreak_weekly`.
- Preserve previous Step 9.2-9.6 results as methodological experiments, not final performance claims.
- Prepare BUS as an external mechanistic risk feature/reference without using it as the target.

Updated official sources going forward:

- weather: `updated data/weather_hourly`
- POV: `updated data/pov_rice_monthly`
- disease label: `updated data/rice_blast_outbreak_weekly`
- BUS reference: `updated data/bus_value_dayly`

Implementation:

- Added/updated:
  - `tools/updated_data_loaders.py`
  - `experiments/rebuild_updated_sequence_dataset.py`
  - `tools/susceptibility_v0.py`
- `tools/susceptibility_v0.py` now includes Thai-name aliases for the same v0 weights:
  - offseason `พิษณุโลก2,60-2` = 0.70
  - inseason `กข15` = 0.65
  - inseason `ขาวดอกมะลิ105` = 0.65
  - `กข6` = 0.50
- This does not change the susceptibility logic; it fixes compatibility with correctly decoded updated POV names.

Outputs:

- `experiments/outputs/region_temporal_sequence_dataset_updated_labels_2015_2021.csv`
- `experiments/outputs/updated_sequence_dataset_summary.csv`
- `experiments/outputs/updated_label_distribution_summary.csv`
- `experiments/outputs/updated_feature_integrity_summary.csv`
- `experiments/outputs/updated_old_vs_new_label_comparison.csv`
- `experiments/outputs/updated_pov_variety_ratio_summary.csv`
- `experiments/outputs/updated_susceptibility_summary.csv`
- `experiments/outputs/updated_bus_feature_summary.csv`

Updated sequence dataset summary:

| year | rows | provinces | regions | label source available | label observed rows | blast positive | blast t+1 positive | blast t+2 positive | BUS feature rows |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2015 | 4,081 | 77 | 6 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2016 | 4,081 | 77 | 6 | 1 | 77 | 1 | 1 | 1 | 0 |
| 2017 | 4,077 | 77 | 6 | 1 | 924 | 32 | 32 | 32 | 0 |
| 2018 | 4,077 | 77 | 6 | 1 | 693 | 28 | 28 | 28 | 0 |
| 2019 | 4,081 | 77 | 6 | 1 | 3,850 | 119 | 116 | 115 | 0 |
| 2020 | 4,081 | 77 | 6 | 1 | 3,927 | 471 | 467 | 463 | 317 |
| 2021 | 4,025 | 77 | 6 | 1 | 3,794 | 308 | 308 | 294 | 1,454 |

Important label interpretation:

- Corrected outbreak labels are available for 2016-2022, not 2015.
- The exported 2015 rows are retained as feature-only rows for continuity, but `label_source_available = 0`.
- 2015 should not be used as supervised training data under the corrected-label regime.
- For years with corrected label files, missing province-weeks are treated as no reported outbreak, while `label_observed` records whether the source file explicitly provided that province-week row.
- This is important because early years are sparse:
  - 2016 has only 77 observed label rows.
  - 2017 has 924 observed label rows.
  - 2018 has 693 observed label rows.

Old vs updated label comparison:

| year | old positives | updated positives | old positive / updated negative | old negative / updated positive |
|---:|---:|---:|---:|---:|
| 2016 | 2 | 1 | 1 | 0 |
| 2017 | 65 | 32 | 33 | 0 |
| 2018 | 27 | 28 | 0 | 1 |
| 2019 | 148 | 119 | 33 | 4 |
| 2020 | 573 | 471 | 102 | 0 |
| 2021 | 359 | 308 | 66 | 15 |

2020 regional disagreement:

| region | old positives | updated positives | disagreements | old positive / updated negative | old negative / updated positive |
|---|---:|---:|---:|---:|---:|
| Central | 43 | 38 | 5 | 5 | 0 |
| East | 79 | 65 | 14 | 14 | 0 |
| North | 134 | 110 | 24 | 24 | 0 |
| Northeast | 251 | 213 | 38 | 38 | 0 |
| South | 56 | 38 | 18 | 18 | 0 |
| West | 10 | 7 | 3 | 3 | 0 |

Interpretation:

- Updated labels materially reduce positive outbreak weeks.
- The biggest correction occurs in 2020:
  - old positives: 573
  - updated positives: 471
  - removed positives: 102
- In 2020, every regional disagreement is old-positive / updated-negative.
- This means previous 2020 validation behavior may have been partly shaped by false or corrected positives in the old label source.
- Step 9.2-9.6 model performance should be retained as historical methodology, but all final model claims must be rerun against updated labels.

Updated POV and susceptibility:

- Updated POV is monthly and is expanded to weekly province-variety ratios.
- Susceptibility v0 is recomputed from updated monthly variety ratios.
- Unknown or unstable varieties still default to 0.50.
- Updated susceptibility remains conservative:
  - yearly mean susceptibility is approximately 0.521-0.526.
  - min is 0.50.
  - max is approximately 0.649.
- Missing POV weeks are handled through default host susceptibility when joined to weekly weather.

BUS feature integration:

- BUS is prepared as an external mechanistic risk index, not a disease label.
- Critical BUS threshold:
  - `BUS >= 2.25`
- Weekly BUS features included:
  - `avgbus_mean`
  - `avgbus_max`
  - `maxbus_max`
  - `bus_critical_days`
  - `bus_critical_any`
  - `bus_critical_ratio`
- BUS coverage in the updated 2015-2021 dataset:

| year | BUS feature rows | provinces with BUS | max avgbus | BUS critical weeks |
|---:|---:|---:|---:|---:|
| 2015 | 0 | 0 | NA | 0 |
| 2016 | 0 | 0 | NA | 0 |
| 2017 | 0 | 0 | NA | 0 |
| 2018 | 0 | 0 | NA | 0 |
| 2019 | 0 | 0 | NA | 0 |
| 2020 | 317 | 22 | 7.2 | 35 |
| 2021 | 1,454 | 25 | 8.0 | 94 |

BUS interpretation:

- BUS is spatially incomplete because it is center-based, not province-complete.
- BUS was assigned to the nearest province centroid for this rebuild.
- This is acceptable for feature feasibility/governance, but future BUS analysis should explicitly test nearest-center assumptions.
- BUS should be used first as:
  - mechanistic benchmark,
  - explanatory covariate,
  - risk communication support,
  - not as the target variable.

Feature integrity notes:

- Final updated sequence dataset has 28,503 rows.
- Weather feature missingness is very low, around 0.1% for key weather/risk columns.
- `mean_wind_gust` remains sparse, with approximately 70% missingness.
- BUS numeric features are missing for most rows because BUS exists only from 2020 and only for selected centers/provinces.
- Current/future labels are missing for 2015 because the corrected label source does not include 2015.

Decision:

- Updated weekly outbreak labels are now the official disease label source.
- The old `blast disease` label source should not be used for final model training or final claims.
- The updated sequence dataset becomes the correct base for future ML/DNN/LSTM reruns.
- Step 9.2-9.6 should be described as old-label methodological experiments.

Next direction:

- Step 9.7B: BUS mechanistic benchmark and feature feasibility analysis.
- Step 9.8: Rerun classical ML/DNN baselines using the updated-label sequence dataset.
- Revisit train/validation/test policy under corrected labels:
  - 2015 is feature-only under corrected labels.
  - 2016 has extremely sparse label observations.
  - 2017-2019 remain candidates for training.
  - 2020 validation and 2021 test should be rerun with corrected labels.

## 2026-05-24 Step 9.7B BUS Mechanistic Benchmark and Feature Feasibility Analysis

Goal:

- Evaluate BUS as an external mechanistic rice blast risk index under the corrected-label dataset.
- Test whether BUS provides useful information beyond the existing explainable epidemiological features.
- Keep this as feasibility/benchmark analysis, not final nationwide model performance.

Team note:

- Current research collaborators tracked in the working context:
  - user/research lead
  - Pete
  - James
  - Dream

Dataset:

- `experiments/outputs/region_temporal_sequence_dataset_updated_labels_2015_2021.csv`

Target:

- `blast_t_plus_1`

BUS features:

- `avgbus_mean`
- `avgbus_max`
- `maxbus_max`
- `bus_critical_days`
- `bus_critical_any`
- `bus_critical_ratio`

BUS critical threshold:

- BUS critical if BUS >= 2.25

Script:

- `experiments/analyze_bus_benchmark.py`

Outputs:

- `experiments/outputs/bus_coverage_audit.csv`
- `experiments/outputs/bus_rule_baseline_metrics.csv`
- `experiments/outputs/bus_feature_association_summary.csv`
- `experiments/outputs/bus_region_summary.csv`
- `experiments/outputs/bus_feature_feasibility_summary.csv`
- `experiments/outputs/bus_ablation_metrics.csv`
- `experiments/outputs/bus_ablation_feature_manifest.csv`
- `experiments/outputs/bus_ablation_predictions.csv`
- `experiments/outputs/bus_vs_core_comparison_summary.csv`

BUS coverage audit:

| year | rows | BUS rows | BUS missing rate | BUS critical weeks | target positive rows | BUS rows with target | BUS target positives |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2015 | 4,081 | 0 | 1.0000 | 0 | 0 | 0 | 0 |
| 2016 | 4,081 | 0 | 1.0000 | 0 | 1 | 0 | 0 |
| 2017 | 4,077 | 0 | 1.0000 | 0 | 32 | 0 | 0 |
| 2018 | 4,077 | 0 | 1.0000 | 0 | 28 | 0 | 0 |
| 2019 | 4,081 | 0 | 1.0000 | 0 | 116 | 0 | 0 |
| 2020 | 4,081 | 299 | 0.9267 | 35 | 467 | 299 | 100 |
| 2021 | 4,025 | 1,268 | 0.6850 | 94 | 308 | 1,263 | 128 |

Coverage interpretation:

- BUS appears only in 2020-2021 in the current rebuilt 2015-2021 sequence dataset.
- There are zero BUS-covered rows in the standard training period 2017-2019.
- Therefore, BUS cannot yet support a valid standard train 2017-2019 / validation 2020 / test 2021 model comparison.
- DNN was skipped because BUS has no standard training coverage and only one BUS-covered exploratory training year.
- Any BUS model result in this step is feasibility analysis only.

BUS-only rule benchmark:

Full updated dataset:

| rule | precision | recall | f1 | ROC-AUC | PR-AUC | false positive | false negative |
|---|---:|---:|---:|---:|---:|---:|---:|
| `bus_critical_any` | 0.2326 | 0.0315 | 0.0555 | 0.5136 | 0.0458 | 99 | 922 |
| `bus_critical_ratio > 0` | 0.2326 | 0.0315 | 0.0555 | 0.5136 | 0.0458 | 99 | 922 |
| `avgbus_mean >= 2.25` | 0.3000 | 0.0063 | 0.0123 | 0.5028 | 0.0414 | 14 | 946 |
| `avgbus_max >= 2.25` | 0.2326 | 0.0315 | 0.0555 | 0.5136 | 0.0458 | 99 | 922 |

BUS-covered subset:

| rule | precision | recall | f1 | ROC-AUC | PR-AUC | false positive | false negative |
|---|---:|---:|---:|---:|---:|---:|---:|
| `bus_critical_any` | 0.2326 | 0.1316 | 0.1681 | 0.5287 | 0.1574 | 99 | 198 |
| `bus_critical_ratio > 0` | 0.2326 | 0.1316 | 0.1681 | 0.5287 | 0.1574 | 99 | 198 |
| `avgbus_mean >= 2.25` | 0.3000 | 0.0263 | 0.0484 | 0.5079 | 0.1500 | 14 | 222 |
| `avgbus_max >= 2.25` | 0.2326 | 0.1316 | 0.1681 | 0.5287 | 0.1574 | 99 | 198 |

BUS-only interpretation:

- BUS critical threshold has weak outbreak-capture behavior under corrected labels.
- `BUS >= 2.25` is conservative and misses many future outbreak weeks.
- BUS critical weeks have some positive association, but BUS-only rules are not strong enough as a standalone forecasting decision policy.
- `avgbus_mean >= 2.25` has higher precision but extremely low recall.

Association analysis:

Top associations with `blast_t_plus_1` in BUS-covered rows:

| feature | rows | positive rows | effect diff | correlation |
|---|---:|---:|---:|---:|
| `neighbor_prevweek_blast` | 1,562 | 228 | 0.1077 | 0.2225 |
| `wind_aligned_neighbor_blast` | 1,562 | 228 | 0.0340 | 0.1411 |
| `avgbus_mean` | 762 | 120 | 0.2281 | 0.1295 |
| `avgbus_max` | 762 | 120 | 0.3844 | 0.0942 |
| `maxbus_max` | 762 | 120 | 0.4678 | 0.0848 |
| `bus_critical_any` | 1,562 | 228 | 0.0574 | 0.0736 |
| `bus_critical_ratio` | 1,562 | 228 | 0.0211 | 0.0714 |
| `bus_critical_days` | 1,562 | 228 | 0.1372 | 0.0675 |
| `leaf_wet_hours` | 1,562 | 228 | 3.5912 | 0.0419 |
| `host_weighted_risk` | 1,562 | 228 | 1.2590 | 0.0225 |

Interpretation:

- BUS continuous features have measurable but modest association with future outbreak labels.
- Neighbor and wind-aligned spatial features remain stronger than BUS features in this BUS-covered subset.
- BUS appears biologically meaningful, but not dominant.

Regional BUS behavior:

| region | BUS rows | positives | positive rate | BUS critical rows | BUS critical rate | positive rate in BUS critical weeks |
|---|---:|---:|---:|---:|---:|---:|
| Central | 351 | 5 | 0.0142 | 6 | 0.0171 | 0.0000 |
| East | 117 | 26 | 0.2222 | 12 | 0.1026 | 0.2500 |
| North | 429 | 65 | 0.1515 | 64 | 0.1492 | 0.2500 |
| Northeast | 444 | 115 | 0.2590 | 16 | 0.0360 | 0.6250 |
| South | 166 | 10 | 0.0602 | 22 | 0.1325 | 0.0000 |
| West | 55 | 7 | 0.1273 | 9 | 0.1636 | 0.1111 |

Regional interpretation:

- BUS-covered provinces are not evenly distributed across the country.
- Northeast has the highest positive rate in BUS critical weeks, but only 16 BUS critical rows.
- Central and South show BUS critical weeks with no future positives in this subset.
- BUS usefulness appears region-dependent and sample-size sensitive.

Exploratory model ablation:

Because BUS has no rows in 2017-2019, the standard train/validation/test protocol cannot be used.
The following ablation uses:

- exploratory train: BUS-covered 2020 rows
- exploratory test: BUS-covered 2021 rows
- interpretation: feasibility only, not final performance

Test 2021 BUS-covered subset:

| model | feature set | precision | recall | f1 | ROC-AUC | PR-AUC | false positive | false negative |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| XGBoost | BUS only | 0.1431 | 0.5703 | 0.2288 | 0.6422 | 0.1375 | 437 | 55 |
| XGBoost | core no BUS | 0.3684 | 0.1094 | 0.1687 | 0.7470 | 0.2511 | 24 | 114 |
| XGBoost | core plus BUS | 0.3243 | 0.0938 | 0.1455 | 0.7462 | 0.2397 | 25 | 116 |
| XGBoost | BUS plus host/spatial | 0.1702 | 0.3125 | 0.2204 | 0.6558 | 0.1722 | 195 | 88 |
| Logistic class-weighted | BUS only | 0.1647 | 0.6563 | 0.2633 | 0.6615 | 0.1435 | 426 | 44 |
| Logistic class-weighted | core no BUS | 0.2547 | 0.4219 | 0.3176 | 0.7248 | 0.2326 | 158 | 74 |
| Logistic class-weighted | core plus BUS | 0.2694 | 0.4063 | 0.3240 | 0.7170 | 0.2192 | 141 | 76 |
| Logistic class-weighted | BUS plus host/spatial | 0.2161 | 0.5234 | 0.3059 | 0.7340 | 0.2587 | 243 | 61 |

BUS vs core comparison:

| model | comparison | F1 delta | precision delta | recall delta | PR-AUC delta |
|---|---|---:|---:|---:|---:|
| XGBoost | core plus BUS - core no BUS | -0.0232 | -0.0441 | -0.0156 | -0.0114 |
| XGBoost | BUS plus host/spatial - BUS only | -0.0085 | 0.0271 | -0.2578 | 0.0347 |
| Logistic class-weighted | core plus BUS - core no BUS | 0.0063 | 0.0147 | -0.0156 | -0.0134 |
| Logistic class-weighted | BUS plus host/spatial - BUS only | 0.0426 | 0.0514 | -0.1328 | 0.1153 |

Interpretation of Pete's five questions:

1. BUS coverage enough for real model training?
   - No.
   - BUS exists only in 2020-2021, with zero BUS-covered rows in standard training years 2017-2019.

2. Does BUS critical >= 2.25 align with corrected outbreaks?
   - Weakly.
   - In BUS-covered rows, BUS critical has precision 0.2326, recall 0.1316, and F1 0.1681.

3. Is BUS-only better than our mechanistic features?
   - Not clearly.
   - BUS-only can increase recall but creates many false positives and lower PR-AUC than core features in XGBoost.
   - Core no BUS has stronger ROC-AUC/PR-AUC in the exploratory XGBoost comparison.

4. Does core plus BUS beat core no BUS?
   - Not consistently.
   - XGBoost worsens after adding BUS.
   - Logistic shows tiny F1 gain, but PR-AUC decreases.
   - This is not strong evidence that BUS adds robust predictive value yet.

5. If BUS helps little, do our features already capture weather-risk physiology?
   - Current evidence suggests yes, at least partially.
   - Core features built from humidity, leaf wetness proxy, temporal accumulation, host susceptibility, and spatial pressure already capture much of the available signal.
   - BUS remains valuable as an external mechanistic reference and communication aid, but the model should not depend on BUS.

Conclusion:

- BUS is scientifically useful but operationally limited by coverage.
- BUS should remain an optional external mechanistic benchmark/reference feature.
- BUS should not be used as a final nationwide model dependency unless historical coverage expands before 2020.
- Current algorithmic features appear able to perform without relying on BUS.
- Future work should test BUS more seriously only if BUS can be reconstructed historically from weather or expanded spatially/temporally.

Next direction:

- Step 9.8: rerun classical ML/DNN baselines with corrected labels and without depending on BUS.
- Optional later step:
  - Reconstruct BUS-like features from hourly weather for all years if exact BUS formula can be specified.
  - Then compare reconstructed BUS-like features against official BUS where available.

## 2026-05-24 Step 9.8 Corrected-Label Core ML/DNN Baselines

Goal:

- Rerun the main ML/DNN baselines using corrected `rice_blast_outbreak_weekly` labels.
- Use the updated sequence dataset from Step 9.7.
- Focus on `core_no_BUS` because Step 9.7B showed BUS is coverage-limited and should not be a required nationwide dependency.

Dataset:

- `experiments/outputs/region_temporal_sequence_dataset_updated_labels_2015_2021.csv`

Target:

- `blast_t_plus_1`

Split:

- train: 2017-2019
- validation: 2020
- test: 2021
- 2015 excluded from supervised training because corrected labels are not available.

Feature policy:

- Included:
  - mechanistic weather features
  - humidity / leaf wetness features
  - rolling temporal risk features
  - updated `susceptibility_score`
  - host-weighted features
  - spatial pressure features
  - regional temporal features
  - wind alignment features
  - province / region categorical metadata
  - week seasonality features
- Excluded:
  - all BUS features
  - `blast_t_plus_1`
  - `blast_t_plus_2`
  - `blast_any`
  - `blast_days`
  - `blast_area`
  - `datetime`
  - raw `year`
  - raw `week`
  - `label_source_available`
  - `label_observed`

Script:

- `experiments/train_updated_label_core_baselines.py`

Outputs:

- `experiments/outputs/updated_label_baseline_metrics.csv`
- `experiments/outputs/updated_label_model_comparison.csv`
- `experiments/outputs/updated_label_test_predictions.csv`
- `experiments/outputs/updated_label_confusion_matrix.csv`
- `experiments/outputs/updated_label_feature_importance.csv`
- `experiments/outputs/updated_label_region_performance.csv`
- `experiments/outputs/updated_label_false_positives.csv`
- `experiments/outputs/updated_label_false_negatives.csv`
- `experiments/outputs/updated_label_split_summary.csv`
- `experiments/outputs/updated_label_feature_manifest.csv`
- `experiments/outputs/updated_label_old_vs_new_metric_comparison.csv`
- `experiments/outputs/updated_label_dnn_training_history.csv`

Corrected-label split summary:

| split | years | rows | positives | positive rate | provinces | regions | label observed rate |
|---|---|---:|---:|---:|---:|---:|---:|
| train | 2017-2019 | 12,004 | 176 | 0.0147 | 77 | 6 | 0.4554 |
| validation | 2020 | 4,004 | 467 | 0.1166 | 77 | 6 | 0.9615 |
| test | 2021 | 3,948 | 308 | 0.0780 | 77 | 6 | 0.9415 |
| feature only | 2015 | 4,081 | NA | NA | 77 | 6 | 0.0000 |

Interpretation:

- Corrected-label training data is highly imbalanced.
- 2017-2019 have only 176 positive target rows.
- Validation 2020 remains a much higher outbreak year than the training period.
- This confirms that corrected-label modeling is still a distribution-shift problem.

Test 2021 corrected-label model comparison:

| model | threshold | precision | recall | f1 | ROC-AUC | PR-AUC | false positive | false negative |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DNN class-weighted | 0.70 | 0.2815 | 0.3409 | 0.3084 | 0.6730 | 0.2048 | 268 | 203 |
| Random Forest | 0.35 | 0.2543 | 0.2890 | 0.2705 | 0.6898 | 0.1871 | 261 | 219 |
| DNN no class weight | 0.05 | 0.2146 | 0.3539 | 0.2672 | 0.7067 | 0.2213 | 399 | 199 |
| XGBoost | 0.45 | 0.1783 | 0.3312 | 0.2318 | 0.6673 | 0.1764 | 470 | 206 |

Interpretation:

- DNN class-weighted remains the best F1 model under corrected labels.
- DNN no-class-weight has the highest ROC-AUC and PR-AUC, but its F1 is lower due to many false positives at the validation-selected threshold.
- Random Forest is more conservative than DNN and XGBoost.
- XGBoost performs weakest in this corrected-label rerun.

Old-label methodology reference vs corrected-label rerun:

| old reference | updated model | old F1 | corrected F1 | delta | old PR-AUC | corrected PR-AUC | old FP | corrected FP | old FN | corrected FN |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| controlled DNN class-weighted core_only | DNN class-weighted core_no_BUS | 0.3771 | 0.3084 | -0.0688 | 0.2722 | 0.2048 | 336 | 268 | 176 | 203 |
| controlled XGBoost core_only | XGBoost core_no_BUS | 0.2821 | 0.2318 | -0.0502 | 0.2423 | 0.1764 | 339 | 470 | 221 | 206 |
| classical RF core | Random Forest core_no_BUS | 0.2457 | 0.2705 | +0.0248 | 0.2034 | 0.1871 | 990 | 261 | 146 | 219 |
| classical XGBoost core | XGBoost core_no_BUS | 0.2285 | 0.2318 | +0.0033 | 0.2048 | 0.1764 | 421 | 470 | 234 | 206 |

Interpretation:

- Old-label results are retained only as methodological evidence.
- Corrected labels make the best DNN F1 lower.
- DNN false positives decrease:
  - old-label DNN FP: 336
  - corrected-label DNN FP: 268
- DNN false negatives increase:
  - old-label DNN FN: 176
  - corrected-label DNN FN: 203
- This suggests the corrected labels reduce some over-alert behavior but make outbreak capture harder.

Feature importance:

Random Forest top signals:

- `susceptibility_score`
- `regional_neighbor_pressure_3w`
- `regional_host_pressure`
- `regional_wind_alignment_frequency`
- `total_pov_area`
- `regional_neighbor_pressure_2w`
- `wind_direction_variability`
- `prevailing_wind_direction`
- `regional_leaf_wet_accumulation`
- `neighbor_prevweek_risk`

XGBoost top signals:

- `regional_neighbor_pressure_3w`
- `regional_wind_alignment_frequency`
- `region_Northeast`
- `regional_neighbor_pressure_2w`
- `region_South`
- `regional_host_pressure`
- `total_pov_area`
- `wind_aligned_neighbor_count`
- `susceptibility_score`
- `regional_leaf_wet_accumulation`

Interpretation:

- Feature importance still supports the thesis narrative:
  - host susceptibility matters,
  - regional pressure matters,
  - temporal/regional accumulation matters,
  - wind alignment contributes,
  - leaf wetness remains part of the useful mechanistic feature family.
- Corrected labels did not erase the epidemiological structure; they reduced apparent performance and sharpened the need for robust decision governance.

DNN class-weighted region performance on corrected-label test 2021:

| region | positives | precision | recall | f1 | ROC-AUC | PR-AUC | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Central | 1 | 0.0000 | 0.0000 | 0.0000 | 0.8529 | 0.0095 | 4 | 1 |
| East | 25 | 0.3243 | 0.4800 | 0.3871 | 0.7068 | 0.5171 | 25 | 13 |
| North | 113 | 0.2429 | 0.3009 | 0.2688 | 0.5760 | 0.1974 | 106 | 79 |
| Northeast | 108 | 0.2914 | 0.4074 | 0.3398 | 0.7106 | 0.2415 | 107 | 64 |
| South | 49 | 0.3659 | 0.3061 | 0.3333 | 0.6214 | 0.2332 | 26 | 34 |
| West | 12 | 0.0000 | 0.0000 | 0.0000 | 0.7740 | 0.3298 | 0 | 12 |

Regional interpretation:

- East has the best corrected-label DNN F1 among regions.
- Northeast remains important but F1 is lower than under old-label decision analysis.
- North remains difficult, with many false positives and false negatives.
- South performance drops compared with old-label interpretation.
- Central and West have very few positives; F1 is not meaningful as a stable regional measure there.

Pete/Peach watchlist:

1. Does DNN core_no_BUS still beat XGBoost/RF?
   - Yes for F1.
   - DNN class-weighted F1 = 0.3084.
   - RF F1 = 0.2705.
   - XGBoost F1 = 0.2318.

2. Did corrected labels reduce or increase F1/PR-AUC?
   - For the best DNN reference, both decrease.
   - F1: 0.3771 -> 0.3084.
   - PR-AUC: 0.2722 -> 0.2048.

3. Did 2021 false positives decrease?
   - For DNN class-weighted, yes.
   - FP: 336 -> 268.
   - But FN increases: 176 -> 203.

4. Does feature importance still support host + regional pressure + leaf wetness?
   - Yes.
   - Top features include susceptibility, regional neighbor pressure, regional host pressure, regional wind alignment, and regional leaf wetness accumulation.

5. Did Northeast / North / South behavior change?
   - Yes.
   - Northeast and South F1 are lower than old-label decision-policy interpretation.
   - North remains hard and is still a major source of errors.
   - Corrected labels make regional heterogeneity more evident rather than less.

Conclusion:

- Corrected-label Step 9.8 confirms that DNN class-weighted core_no_BUS remains the best current baseline by F1.
- However, corrected labels lower apparent performance and increase missed outbreaks.
- This is scientifically useful: the model is now evaluated against cleaner labels, so performance is more conservative and more credible.
- The core epidemiological feature structure remains supported even without BUS.
- Future results should use Step 9.8 corrected-label baselines as the new reference point, not the old Step 9.2-9.6 metrics.

Next direction:

- Step 9.9: corrected-label threshold/calibration governance for the DNN class-weighted core_no_BUS baseline.
- Do not return to old labels for final model claims.
- Keep BUS as optional external mechanistic reference until wider historical BUS coverage is available.

## 2026-05-24 Step 9.9 Extended Corrected-Label Forward-Year Split with 2022 Test

Goal:

- Extend the corrected-label sequence dataset through 2022.
- Rerun `core_no_BUS` baselines with a stronger chronological forecasting split:
  - train: 2017-2020
  - validation: 2021
  - test: 2022
- Test whether adding outbreak year 2020 to training improves forward-year generalization.

Motivation:

- Step 9.8 used train 2017-2019, validation 2020, test 2021.
- That training split had only 176 positive target rows.
- Updated labels include 2022, so 2020 can be moved into training while preserving a held-out future test year.
- This better reflects forecasting evaluation than the previous split.

Scripts:

- `experiments/rebuild_updated_sequence_dataset_2022.py`
- `experiments/train_updated_2022_forward_baselines.py`

Dataset:

- `experiments/outputs/region_temporal_sequence_dataset_updated_labels_2015_2022.csv`

Outputs:

- `experiments/outputs/updated_2022_sequence_dataset_summary.csv`
- `experiments/outputs/updated_2022_split_summary.csv`
- `experiments/outputs/updated_2022_baseline_metrics.csv`
- `experiments/outputs/updated_2022_model_comparison.csv`
- `experiments/outputs/updated_2022_test_predictions.csv`
- `experiments/outputs/updated_2022_confusion_matrix.csv`
- `experiments/outputs/updated_2022_feature_importance.csv`
- `experiments/outputs/updated_2022_region_performance.csv`
- `experiments/outputs/updated_2022_old_split_comparison.csv`
- `experiments/outputs/updated_2022_feature_manifest.csv`

Extended dataset summary:

| year | rows | provinces | label observed rows | blast positive | blast t+1 positive | blast t+2 positive | BUS feature rows |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2015 | 4,081 | 77 | 0 | 0 | 0 | 0 | 0 |
| 2016 | 4,081 | 77 | 77 | 1 | 1 | 1 | 0 |
| 2017 | 4,077 | 77 | 924 | 32 | 32 | 32 | 0 |
| 2018 | 4,077 | 77 | 693 | 28 | 28 | 28 | 0 |
| 2019 | 4,081 | 77 | 3,850 | 119 | 116 | 115 | 0 |
| 2020 | 4,081 | 77 | 3,927 | 471 | 467 | 463 | 317 |
| 2021 | 4,025 | 77 | 3,794 | 308 | 308 | 294 | 1,454 |
| 2022 | 4,081 | 77 | 3,850 | 161 | 161 | 160 | 1,610 |

Forward split audit:

| split | years | rows | positives | positive rate | provinces | regions | label observed rate |
|---|---|---:|---:|---:|---:|---:|---:|
| train | 2017-2020 | 16,008 | 643 | 0.0402 | 77 | 6 | 0.5820 |
| validation | 2021 | 3,948 | 308 | 0.0780 | 77 | 6 | 0.9415 |
| test | 2022 | 4,004 | 161 | 0.0402 | 77 | 6 | 0.9423 |
| feature only | 2015 | 4,081 | NA | NA | 77 | 6 | 0.0000 |
| sparse reported | 2016 | 4,004 | 1 | 0.0002 | 77 | 6 | 0.0000 |

Interpretation:

- Adding 2020 increases training positives from 176 to 643.
- Training positive rate rises from 1.47% to 4.02%.
- Test 2022 positive rate is also 4.02%, much closer to training than the old 2021 test distribution.
- Validation 2021 remains higher prevalence at 7.80%.
- This split is more epidemiologically balanced for forward-year forecasting.

Test 2022 model comparison:

| model | threshold | precision | recall | f1 | ROC-AUC | PR-AUC | false positive | false negative |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DNN no class weight | 0.20 | 0.3923 | 0.3168 | 0.3505 | 0.7818 | 0.2904 | 79 | 110 |
| Random Forest | 0.50 | 0.3662 | 0.3230 | 0.3432 | 0.7886 | 0.2407 | 90 | 109 |
| DNN class-weighted | 0.80 | 0.2906 | 0.3665 | 0.3242 | 0.7790 | 0.2450 | 144 | 102 |
| XGBoost | 0.65 | 0.2653 | 0.3230 | 0.2913 | 0.7755 | 0.2523 | 144 | 109 |

Interpretation:

- With the forward-year split, DNN no-class-weight becomes the best F1 model.
- Random Forest is very close and has the highest ROC-AUC.
- DNN class-weighted still gives the highest recall but lower precision.
- XGBoost improves compared with Step 9.8 but remains below DNN/RF in F1.

Comparison with previous corrected-label split:

| model | previous F1 | new F1 | delta | previous PR-AUC | new PR-AUC | previous FP | new FP | previous FN | new FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DNN class-weighted | 0.3084 | 0.3242 | +0.0158 | 0.2048 | 0.2450 | 268 | 144 | 203 | 102 |
| Random Forest | 0.2705 | 0.3432 | +0.0727 | 0.1871 | 0.2407 | 261 | 90 | 219 | 109 |
| DNN no class weight | 0.2672 | 0.3505 | +0.0834 | 0.2213 | 0.2904 | 399 | 79 | 199 | 110 |
| XGBoost | 0.2318 | 0.2913 | +0.0595 | 0.1764 | 0.2523 | 470 | 144 | 206 | 109 |

Important caveat:

- This comparison changes both the training period and the held-out test year.
- It is not a same-test ablation.
- The result should be interpreted as forward-year split improvement, not purely as the isolated effect of adding 2020.

Key finding:

- Every model improves in F1 under the 2022 forward-year split.
- False positives fall sharply for all models.
- False negatives also fall compared with Step 9.8, partly because test 2022 has fewer positives than test 2021.
- This supports the hypothesis that the model needs outbreak-year examples during training.

Feature importance:

Random Forest top signals:

- `regional_neighbor_pressure_3w`
- `regional_neighbor_pressure_2w`
- `regional_wind_alignment_frequency`
- `susceptibility_score`
- `regional_host_pressure`
- `neighbor_prevweek_blast`
- `week_sin`
- `total_pov_area`
- `temperature_mean`
- `pov_variety_count`
- `regional_leaf_wet_accumulation`

XGBoost top signals:

- `regional_neighbor_pressure_2w`
- `regional_neighbor_pressure_3w`
- `spatial_host_weather_risk`
- `rainfall_sum`
- `regional_wind_alignment_frequency`
- `total_pov_area`
- `susceptibility_score`
- `region_South`
- `region_Northeast`
- `regional_leaf_wet_accumulation`

Interpretation:

- The feature importance pattern remains epidemiologically coherent.
- Regional neighbor pressure becomes even more dominant after adding 2020 to training.
- Host susceptibility remains important.
- Regional wind alignment and regional leaf wet accumulation remain part of the signal.
- This reinforces the thesis argument that rice blast forecasting needs host + spatial + temporal + weather structure.

Regional performance:

DNN no-class-weight, test 2022:

| region | positives | precision | recall | f1 | ROC-AUC | PR-AUC | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Central | 10 | 0.0000 | 0.0000 | 0.0000 | 0.7230 | 0.0858 | 0 | 10 |
| East | 7 | 0.4000 | 0.2857 | 0.3333 | 0.7475 | 0.2848 | 3 | 5 |
| North | 18 | 0.0000 | 0.0000 | 0.0000 | 0.3464 | 0.0150 | 1 | 18 |
| Northeast | 120 | 0.4153 | 0.4083 | 0.4118 | 0.7373 | 0.3881 | 69 | 71 |
| South | 4 | 0.0000 | 0.0000 | 0.0000 | 0.8847 | 0.0492 | 6 | 4 |
| West | 2 | 0.0000 | 0.0000 | 0.0000 | 0.2549 | 0.0095 | 0 | 2 |

DNN class-weighted, test 2022:

| region | positives | precision | recall | f1 | ROC-AUC | PR-AUC | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Central | 10 | 0.1176 | 0.2000 | 0.1481 | 0.6475 | 0.0637 | 15 | 8 |
| East | 7 | 0.4000 | 0.2857 | 0.3333 | 0.8362 | 0.2306 | 3 | 5 |
| North | 18 | 0.0000 | 0.0000 | 0.0000 | 0.2843 | 0.0141 | 14 | 18 |
| Northeast | 120 | 0.3571 | 0.4583 | 0.4015 | 0.7578 | 0.3516 | 99 | 65 |
| South | 4 | 0.0000 | 0.0000 | 0.0000 | 0.9033 | 0.0436 | 13 | 4 |
| West | 2 | 0.0000 | 0.0000 | 0.0000 | 0.1675 | 0.0086 | 0 | 2 |

Regional interpretation:

- Test 2022 outbreak labels are heavily concentrated in the Northeast:
  - Northeast positives: 120 out of 161.
- The model's useful performance is mostly coming from Northeast and East.
- North, South, West, and Central have few positives and remain unstable at region-level F1.
- North is especially difficult in 2022; all main models miss North positives.
- This suggests 2022 is not just easier overall; it is regionally concentrated.

Decision:

- Step 9.9 becomes the new corrected-label forward-year baseline.
- The best F1 model in this split is:
  - DNN no-class-weight core_no_BUS
  - F1: 0.3505
  - ROC-AUC: 0.7818
  - PR-AUC: 0.2904
- Random Forest is a very strong interpretable competitor:
  - F1: 0.3432
  - ROC-AUC: 0.7886
  - PR-AUC: 0.2407
- DNN class-weighted should not be assumed best under the new split; it is better for recall-oriented policy but not best F1.

Research conclusion:

- Adding outbreak year 2020 to training improves apparent forward-year performance.
- The model appears to benefit from learning outbreak-regime patterns.
- The forward-year split is more credible than the previous split for forecasting methodology.
- However, 2022 has strong regional concentration, so improved metrics should be interpreted with regional context.

Next direction:

- Step 9.10: corrected-label forward-split threshold and calibration governance.
- Use validation 2021 only for threshold/calibration.
- Keep test 2022 held out.
- Compare DNN no-class-weight, DNN class-weighted, and Random Forest as candidate operational models.

## 2026-05-24 Step 9.10A Forward-Split Temporal Model Revisit

Goal:

- Re-evaluate compact temporal sequence models under the corrected-label 2022 forward-year split.
- Test whether improved training coverage from adding outbreak year 2020 helps temporal models.
- Compare temporal models against Step 9.9 tabular baselines.

Dataset:

- `experiments/outputs/region_temporal_sequence_dataset_updated_labels_2015_2022.csv`

Target:

- `blast_t_plus_1`

Split:

- train: 2017-2020
- validation: 2021
- test: 2022

Feature policy:

- `core_no_BUS` only.
- BUS features, current disease labels, future labels, raw year/week, `label_source_available`, and `label_observed` are excluded.
- Province and region are one-hot encoded.
- Preprocessing is fit on train 2017-2020 only.

Models:

- GRU
- TCN
- Hybrid DNN + GRU
- Hybrid DNN + TCN

Sequence lengths:

- 2 weeks
- 4 weeks

Script:

- `experiments/train_temporal_forward_models.py`

Outputs:

- `experiments/outputs/temporal_model_forward_metrics.csv`
- `experiments/outputs/temporal_model_forward_predictions.csv`
- `experiments/outputs/temporal_model_forward_region_performance.csv`
- `experiments/outputs/temporal_model_forward_training_history.csv`
- `experiments/outputs/temporal_model_forward_manifest.csv`

Sequence manifest:

| sequence length | split | rows | positive rows | feature dim |
|---:|---|---:|---:|---:|
| 2 | train | 15,700 | 638 | 118 |
| 2 | validation | 3,871 | 294 | 118 |
| 2 | test | 3,927 | 160 | 118 |
| 4 | train | 15,084 | 627 | 118 |
| 4 | validation | 3,717 | 268 | 118 |
| 4 | test | 3,773 | 159 | 118 |

Test 2022 temporal model results:

| model | sequence length | threshold | precision | recall | f1 | ROC-AUC | PR-AUC | false positive | false negative |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Hybrid DNN + TCN | 2 | 0.80 | 0.2771 | 0.4000 | 0.3274 | 0.7844 | 0.2157 | 167 | 96 |
| Hybrid DNN + GRU | 2 | 0.75 | 0.2623 | 0.4000 | 0.3168 | 0.7721 | 0.1983 | 180 | 96 |
| Hybrid DNN + GRU | 4 | 0.85 | 0.2660 | 0.3396 | 0.2983 | 0.7662 | 0.1769 | 149 | 105 |
| Hybrid DNN + TCN | 4 | 0.80 | 0.2284 | 0.4151 | 0.2946 | 0.7711 | 0.1989 | 223 | 93 |
| TCN | 4 | 0.85 | 0.2336 | 0.3585 | 0.2829 | 0.7777 | 0.1618 | 187 | 102 |
| TCN | 2 | 0.80 | 0.2088 | 0.3875 | 0.2713 | 0.7527 | 0.1972 | 235 | 98 |
| GRU | 2 | 0.80 | 0.2275 | 0.3313 | 0.2697 | 0.7545 | 0.2042 | 180 | 107 |
| GRU | 4 | 0.85 | 0.2486 | 0.2704 | 0.2590 | 0.7624 | 0.1977 | 130 | 116 |

Comparison with Step 9.9 tabular baselines:

| model | f1 | ROC-AUC | PR-AUC |
|---|---:|---:|---:|
| Step 9.9 DNN no class weight | 0.3505 | 0.7818 | 0.2904 |
| Step 9.9 Random Forest | 0.3432 | 0.7886 | 0.2407 |
| Step 9.9 DNN class-weighted | 0.3242 | 0.7790 | 0.2450 |
| Best temporal: Hybrid DNN + TCN 2w | 0.3274 | 0.7844 | 0.2157 |

Interpretation:

- Temporal models still do not beat the best Step 9.9 tabular baseline.
- The best temporal model, Hybrid DNN + TCN with 2-week memory, is close to DNN class-weighted F1 but below DNN no-class-weight and Random Forest.
- PR-AUC is weaker than the best tabular DNN and Random Forest.
- Short memory remains better than longer memory:
  - best 2-week temporal F1: 0.3274
  - best 4-week temporal F1: 0.2983
- This supports the earlier finding that national weekly rice blast forecasting benefits more from short-term epidemiological memory than longer sequence memory.

Regional performance for best temporal model:

Best temporal model:

- Hybrid DNN + TCN, 2-week sequence

| region | positives | precision | recall | f1 | ROC-AUC | PR-AUC | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Central | 10 | 0.1250 | 0.1000 | 0.1111 | 0.6161 | 0.0504 | 7 | 9 |
| East | 6 | 0.4000 | 0.3333 | 0.3636 | 0.8172 | 0.2268 | 3 | 4 |
| North | 18 | 0.0000 | 0.0000 | 0.0000 | 0.3149 | 0.0151 | 18 | 18 |
| Northeast | 120 | 0.3280 | 0.5083 | 0.3987 | 0.7480 | 0.3161 | 125 | 59 |
| South | 4 | 0.0000 | 0.0000 | 0.0000 | 0.9356 | 0.0567 | 14 | 4 |
| West | 2 | 0.0000 | 0.0000 | 0.0000 | 0.4035 | 0.0123 | 0 | 2 |

Regional interpretation:

- The temporal model mainly improves recall in the Northeast.
- North remains unsolved; all positives are missed by the best temporal model.
- East has acceptable regional behavior but only six positives in the sequence-filtered test set.
- South and West remain too sparse for stable F1 interpretation.

Research interpretation:

- Adding 2020 to training helps temporal models enough to make them competitive with DNN class-weighted, but not enough to beat the best tabular baselines.
- Hybrid temporal models outperform pure GRU/TCN models.
- The current best temporal architecture is hybrid, not sequence-only.
- However, tabular models using current-week and engineered rolling features still capture the signal more efficiently than compact temporal neural models.

Conclusion:

- Step 9.10A does not justify replacing the Step 9.9 tabular baseline with GRU/TCN.
- The strongest operational candidates remain:
  - DNN no-class-weight core_no_BUS
  - Random Forest core_no_BUS
  - DNN class-weighted core_no_BUS for recall-oriented policy
- Temporal models remain useful as research evidence:
  - short temporal memory matters,
  - hybrid current-week + sequence representation is better than sequence-only,
  - regional outbreak concentration dominates temporal model behavior.

Next direction:

- Step 9.10B: forward-split threshold/calibration governance for the top tabular candidates and best temporal candidate.
- Keep validation 2021 for threshold/calibration.
- Keep test 2022 held out.

## 2026-05-24 Step 9.10B Forward-Split Calibration and Decision Governance

Goal:

- Evaluate threshold, calibration, and operational decision behavior for the top corrected-label forward-split models.
- Use validation 2021 only for threshold selection and calibration.
- Preserve test 2022 as held-out evaluation.

Dataset:

- `experiments/outputs/region_temporal_sequence_dataset_updated_labels_2015_2022.csv`

Candidate models:

- DNN no-class-weight `core_no_BUS`
- Random Forest `core_no_BUS`
- DNN class-weighted `core_no_BUS`
- Hybrid DNN + TCN 2-week `core_no_BUS`

Scripts / updated prediction exports:

- `experiments/train_updated_2022_forward_baselines.py`
  - now exports `experiments/outputs/updated_2022_all_predictions.csv`
- `experiments/train_temporal_forward_models.py`
  - now exports `experiments/outputs/temporal_model_forward_all_predictions.csv`
- `experiments/forward_decision_governance.py`

Outputs:

- `experiments/outputs/forward_decision_policy_metrics.csv`
- `experiments/outputs/forward_model_thresholds.csv`
- `experiments/outputs/forward_calibrated_predictions.csv`
- `experiments/outputs/forward_decision_region_performance.csv`
- `experiments/outputs/forward_decision_confusion_matrix.csv`
- `experiments/outputs/forward_alert_tier_summary.csv`
- `experiments/outputs/forward_alert_tier_region_summary.csv`
- `experiments/outputs/forward_policy_model_comparison.csv`
- `experiments/outputs/forward_calibration_reliability_summary.csv`
- `experiments/outputs/forward_decision_failure_cases.csv`

Validation-selected global thresholds:

| model | policy | threshold | validation precision | validation recall | validation F1 |
|---|---:|---:|---:|---:|---:|
| DNN no class weight | global F1 | 0.21 | 0.3531 | 0.3669 | 0.3599 |
| DNN no class weight | balanced default | 0.22 | 0.3645 | 0.3539 | 0.3591 |
| DNN no class weight | high precision | 0.39 | 0.5000 | 0.1104 | 0.1809 |
| DNN no class weight | high recall | 0.01 | 0.1106 | 0.8571 | 0.1959 |
| Random Forest | global F1 | 0.52 | 0.2369 | 0.4838 | 0.3180 |
| Random Forest | balanced default | 0.59 | 0.2434 | 0.3312 | 0.2806 |
| DNN class weighted | global F1 | 0.84 | 0.3885 | 0.3734 | 0.3808 |
| DNN class weighted | balanced default | 0.83 | 0.3722 | 0.3831 | 0.3776 |
| Hybrid DNN + TCN 2w | global F1 | 0.83 | 0.3453 | 0.4252 | 0.3811 |
| Hybrid DNN + TCN 2w | balanced default | 0.85 | 0.3564 | 0.3673 | 0.3618 |

Test 2022 policy comparison:

| model | policy | threshold | precision | recall | F1 | ROC-AUC | PR-AUC | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DNN no class weight | Platt global F1 | 0.14 | 0.3667 | 0.3416 | 0.3537 | 0.7818 | 0.2904 | 95 | 106 |
| DNN no class weight | global F1 | 0.21 | 0.4118 | 0.3043 | 0.3500 | 0.7818 | 0.2904 | 70 | 112 |
| DNN no class weight | balanced default | 0.22 | 0.4128 | 0.2795 | 0.3333 | 0.7818 | 0.2904 | 64 | 116 |
| Random Forest | global F1 | 0.52 | 0.3920 | 0.3043 | 0.3427 | 0.7886 | 0.2407 | 76 | 112 |
| Random Forest | high precision | 0.57 | 0.4333 | 0.2422 | 0.3108 | 0.7886 | 0.2407 | 51 | 122 |
| DNN class weighted | balanced default | 0.83 | 0.3250 | 0.3230 | 0.3240 | 0.7790 | 0.2450 | 108 | 109 |
| Hybrid DNN + TCN 2w | global F1 | 0.83 | 0.2944 | 0.3625 | 0.3249 | 0.7844 | 0.2157 | 139 | 102 |

Interpretation:

- DNN no-class-weight remains the best default candidate by F1 and PR-AUC.
- Platt-calibrated DNN no-class-weight slightly improves test F1:
  - uncalibrated global F1: 0.3500
  - Platt global F1: 0.3537
- The improvement is small, so calibration should be treated mainly as probability governance rather than a model-performance breakthrough.
- Random Forest remains a strong interpretable operational competitor:
  - lower F1 than DNN no-class-weight,
  - highest ROC-AUC among candidates,
  - fewer false positives than temporal and class-weighted neural policies.
- DNN class-weighted is no longer the best F1 candidate under the forward split, but remains useful when recall is operationally prioritized.
- Hybrid DNN + TCN 2w increases recall relative to DNN no-class-weight global F1:
  - Hybrid recall: 0.3625
  - DNN no-class-weight recall: 0.3043
  - but with more false positives and lower PR-AUC.

Operational policy interpretation:

- Balanced default:
  - DNN no-class-weight remains preferred for default decision support.
  - Use threshold around 0.21-0.22 before calibration.
- High precision field-alert mode:
  - Random Forest threshold 0.57 gives precision 0.4333 and reduces false positives to 51.
  - This mode is useful when field verification capacity is limited.
- High recall surveillance mode:
  - High-recall thresholds capture more outbreaks but create many false positives.
  - This mode should be used only for broad monitoring, not direct field alerts.
- Temporal sensitivity mode:
  - Hybrid DNN + TCN 2w is useful when missing Northeast outbreaks is more costly than extra alerts.

Regional behavior under global F1 policies:

| model | region | positives | precision | recall | F1 | FP | FN |
|---|---|---:|---:|---:|---:|---:|---:|
| DNN no class weight | Northeast | 120 | 0.4312 | 0.3917 | 0.4105 | 62 | 73 |
| Random Forest | Northeast | 120 | 0.4340 | 0.3833 | 0.4071 | 60 | 74 |
| Hybrid DNN + TCN 2w | Northeast | 120 | 0.3394 | 0.4667 | 0.3930 | 109 | 64 |
| DNN class weighted | Northeast | 120 | 0.4052 | 0.3917 | 0.3983 | 69 | 73 |
| DNN no class weight | East | 7 | 0.5000 | 0.2857 | 0.3636 | 2 | 5 |
| Random Forest | East | 7 | 0.3750 | 0.4286 | 0.4000 | 5 | 4 |
| Hybrid DNN + TCN 2w | East | 6 | 0.5000 | 0.3333 | 0.4000 | 2 | 4 |
| DNN no class weight | North | 18 | 0.0000 | 0.0000 | 0.0000 | 1 | 18 |
| Random Forest | North | 18 | 0.0000 | 0.0000 | 0.0000 | 0 | 18 |
| Hybrid DNN + TCN 2w | North | 18 | 0.0000 | 0.0000 | 0.0000 | 15 | 18 |

Regional interpretation:

- Northeast remains the main source of usable model performance in 2022.
- Hybrid DNN + TCN 2w improves Northeast recall:
  - Hybrid Northeast recall: 0.4667
  - DNN no-class-weight Northeast recall: 0.3917
  - Random Forest Northeast recall: 0.3833
- The recall gain comes with substantially more Northeast false positives.
- North remains unresolved:
  - all global F1 candidate policies miss all North positives.
  - temporal modeling did not solve North generalization.
- East has promising behavior but too few positives for stable conclusions.
- Central, South, and West remain too sparse for reliable regional F1 interpretation.

Calibrated alert tiers:

Alert tiers were created from Platt-calibrated probabilities:

- low risk: 0.00-0.05
- watch: 0.05-0.15
- warning: 0.15-0.30
- high alert: 0.30-1.00

Alert-tier summary:

| model | tier | rows | positives | observed positive rate | mean calibrated score |
|---|---|---:|---:|---:|---:|
| DNN no class weight | low risk | 2,609 | 48 | 0.0184 | 0.0467 |
| DNN no class weight | watch | 1,263 | 62 | 0.0491 | 0.0649 |
| DNN no class weight | warning | 95 | 30 | 0.3158 | 0.2106 |
| DNN no class weight | high alert | 37 | 21 | 0.5676 | 0.3975 |
| Random Forest | low risk | 2,816 | 50 | 0.0178 | 0.0337 |
| Random Forest | watch | 1,084 | 70 | 0.0646 | 0.0754 |
| Random Forest | warning | 79 | 28 | 0.3544 | 0.2242 |
| Random Forest | high alert | 25 | 13 | 0.5200 | 0.3563 |
| Hybrid DNN + TCN 2w | high alert | 21 | 9 | 0.4286 | 0.3097 |
| DNN class weighted | high alert | 19 | 10 | 0.5263 | 0.3108 |

Alert-tier interpretation:

- Alert tiers provide useful risk communication even when binary F1 changes only slightly.
- DNN no-class-weight has the clearest high-alert separation:
  - high-alert observed positive rate: 56.8%
  - warning observed positive rate: 31.6%
  - watch observed positive rate: 4.9%
  - low-risk observed positive rate: 1.8%
- Low-risk and watch tiers are not disease-free guarantees.
- Operationally, tiers should communicate monitoring priority, not certainty.

Decision governance conclusion:

- The recommended default operational model is DNN no-class-weight `core_no_BUS`.
- The recommended default threshold is the validation-selected global threshold around 0.21, or Platt-calibrated threshold around 0.14 when calibrated probabilities are used.
- Random Forest should remain as an interpretable operational comparator and possible field-alert model.
- Hybrid DNN + TCN 2w should not replace the tabular baseline, but it is useful as a recall-sensitive temporal candidate, especially for Northeast monitoring.
- Region-specific thresholds should remain exploratory because regional behavior is still unstable and 2022 positives are highly concentrated in the Northeast.
- North requires targeted follow-up analysis; current models fail to capture North positives under global policies.

Next direction:

- Step 9.11: province similarity / analog analysis.
- Investigate whether difficult provinces, especially North and sparse regions, need similarity-based borrowing from epidemiologically similar provinces.
- Keep DNN no-class-weight, Random Forest, and Hybrid DNN + TCN 2w as candidate models for future governance comparisons.

## 2026-05-24 Step 9.11 Province Similarity / Analog Epidemiology Analysis

Goal:

- Analyze whether provinces with similar epidemiological, environmental, host, and outbreak profiles can support rice blast forecasting beyond geographic adjacency alone.
- Investigate difficult regions, especially North, before adding new model complexity.
- Treat this as analog discovery, not a new forecasting model.

Dataset:

- `experiments/outputs/region_temporal_sequence_dataset_updated_labels_2015_2022.csv`

Similarity construction policy:

- Similarity profiles were built from train years only:
  - 2017-2020
- Validation 2021 and test 2022 were used only for inspection/evaluation.
- 2022 outbreak labels were not used to construct province analog sets.

Script:

- `experiments/analyze_province_similarity.py`

Outputs:

- `experiments/outputs/province_similarity_matrix_combined.csv`
- `experiments/outputs/province_similarity_matrix_weather.csv`
- `experiments/outputs/province_similarity_matrix_host.csv`
- `experiments/outputs/province_similarity_matrix_pressure.csv`
- `experiments/outputs/province_similarity_matrix_outbreak_history.csv`
- `experiments/outputs/province_top_analog_neighbors.csv`
- `experiments/outputs/province_analog_vs_geographic_neighbors.csv`
- `experiments/outputs/province_similarity_cluster_summary.csv`
- `experiments/outputs/analog_feature_effects_validation_2021.csv`
- `experiments/outputs/analog_feature_effects_test_2022.csv`
- `experiments/outputs/north_failure_analog_analysis.csv`
- `experiments/outputs/analog_feature_manifest.csv`
- `experiments/outputs/province_similarity_profile_manifest.csv`

Profile groups:

- Weather / moisture:
  - temperature, humidity, rainfall, leaf wetness, regional leaf wet accumulation
- Host / POV:
  - susceptibility score, host-weighted risk, POV area, variety count
- Spatial / regional pressure:
  - neighbor blast/risk pressure, regional pressure, regional wind alignment
- Outbreak history:
  - train-year blast frequency, target frequency, monthly and seasonal outbreak pattern

Similarity method:

- Province profiles were standardized using train-year data only.
- Similarity combined:
  - cosine similarity
  - Euclidean distance converted to similarity
- Combined epidemiological similarity is the average of weather, host, pressure, and outbreak-history similarity.

Analog vs geographic comparison:

| metric | value |
|---|---:|
| provinces | 77 |
| mean top-5 analog/geographic overlap rate | 0.4182 |
| mean analog distance | 179.2 km |
| mean same-region analog rate | 0.8312 |
| mean cross-region analog rate | 0.1688 |

Interpretation:

- Analog neighbors are not identical to geographic neighbors.
- On average, only about 42% of top-5 analog provinces overlap with top-5 nearest geographic neighbors.
- Most analogs remain in the same region, but meaningful cross-region analogs exist.
- This supports the hypothesis that province similarity contains epidemiological structure beyond pure distance adjacency.

Validation 2021 analog feature effects:

| feature | nationwide disease mean | nationwide no-disease mean | effect diff | correlation |
|---|---:|---:|---:|---:|
| analog_prevweek_blast | 0.1525 | 0.0668 | 0.0857 | 0.1642 |
| analog_outbreak_frequency_train | 0.0512 | 0.0294 | 0.0218 | 0.1697 |
| analog_leaf_wet_pressure | 25.2242 | 25.8965 | -0.6723 | -0.0081 |
| analog_host_pressure | 23.4295 | 24.1040 | -0.6745 | -0.0108 |

Validation interpretation:

- In 2021, analog outbreak-history signals were more useful than analog weather/moisture pressure.
- `analog_prevweek_blast` and `analog_outbreak_frequency_train` showed positive nationwide association with `blast_t_plus_1`.
- Analog moisture and host pressure did not show stable nationwide positive association in 2021.

Test 2022 analog feature effects:

| feature | nationwide disease mean | nationwide no-disease mean | effect diff | correlation |
|---|---:|---:|---:|---:|
| analog_2w_pressure | 61.7120 | 53.2915 | 8.4204 | 0.0537 |
| analog_leaf_wet_pressure | 37.5069 | 29.4285 | 8.0784 | 0.0705 |
| analog_regional_leaf_wet_pressure | 93.0839 | 86.9002 | 6.1838 | 0.0214 |
| analog_host_pressure | 30.7761 | 26.6884 | 4.0877 | 0.0492 |
| analog_prevweek_risk | 29.4644 | 26.2626 | 3.2018 | 0.0398 |
| analog_prevweek_blast | 0.1871 | 0.0338 | 0.1533 | 0.2552 |
| analog_outbreak_frequency_train | 0.0755 | 0.0291 | 0.0463 | 0.2647 |

Test interpretation:

- In 2022, analog features showed clearer positive association with corrected outbreak labels.
- The strongest nationwide correlations were:
  - `analog_outbreak_frequency_train`: 0.2647
  - `analog_prevweek_blast`: 0.2552
- This suggests analog outbreak memory may be a useful epidemiological signal.
- Analog moisture/host pressure also had positive effect differences, but weaker correlations.

Regional findings:

- Northeast 2022 had strong analog signal:
  - `analog_leaf_wet_pressure` correlation: 0.1965
  - `analog_2w_pressure` correlation: 0.1757
  - `analog_host_pressure` correlation: 0.1648
  - `analog_prevweek_risk` correlation: 0.1583
- North 2022 remained weak:
  - `analog_prevweek_blast` effect diff was negative.
  - `analog_outbreak_frequency_train` effect diff was negative.
  - moisture analog features had small positive differences but very weak correlations.

North failure analysis:

- North false negatives from the DNN no-class-weight global F1 policy were inspected.
- Several missed North outbreak rows had:
  - `analog_prevweek_blast = 0`
  - very low model scores
  - modest or high analog moisture/risk pressure but little analog outbreak-history support
- Example pattern:
  - Lamphun missed weeks had top analogs mostly within North:
    - Mae Hong Son, Chiang Mai, Kamphaeng Phet, Lampang, Nan
  - analog previous-week blast was 0 across inspected failures.
- Interpretation:
  - North failures are not simply due to missing geographic adjacency.
  - Analog provinces often did not provide prior-week outbreak signals.
  - North may require different features, better label density, field reporting context, or sub-regional seasonality treatment.

Cluster findings:

- KMeans clustering was explored with k = 4, 6, and 8.
- The k = 6 solution produced interpretable groups:
  - high outbreak-frequency Northeast-like cluster,
  - low outbreak central/western cluster,
  - high leaf-wet South cluster,
  - mixed North/East/Northeast analog cluster,
  - moderate Northeast/North analog cluster,
  - small high outbreak-frequency mixed cluster.
- Clusters should not be treated as final model classes yet.
- They are useful for hypothesis generation and province analog grouping.

Scientific interpretation:

- Province similarity is epidemiologically meaningful and partially distinct from geographic adjacency.
- Analog outbreak history and analog previous-week blast contain measurable signal, especially in 2022.
- Analog moisture/host pressure appears region-dependent rather than uniformly useful nationwide.
- Similarity-based analog pressure may help future spatial modeling, but it does not immediately solve North.

Decision:

- Do not replace existing spatial features yet.
- Do not train a new model yet.
- Preserve analog features as candidate features for a controlled future experiment.
- Use analog clusters to guide province-level diagnostics and region-specific modeling hypotheses.

Next direction:

- Step 9.12: controlled analog-feature ablation.
- Compare:
  - core_no_BUS baseline,
  - core_no_BUS + analog outbreak-history features,
  - core_no_BUS + analog pressure/moisture features,
  - core_no_BUS + geographic neighbor pressure.
- Keep train 2017-2020, validation 2021, test 2022.
- Do not use 2022 labels to learn analog sets.

## 2026-05-24 Step 9.12 Controlled Analog-Feature Ablation

Goal:

- Test whether province analog epidemiology features improve corrected-label forward-year forecasting beyond the existing `core_no_BUS` baseline.
- Keep the experiment controlled:
  - no BUS features,
  - no old labels,
  - no new model architecture,
  - no aggressive tuning.

Dataset:

- `experiments/outputs/region_temporal_sequence_dataset_updated_labels_2015_2022.csv`

Split:

- train: 2017-2020
- validation: 2021
- test: 2022

Script:

- `experiments/train_analog_feature_ablation.py`

Outputs:

- `experiments/outputs/analog_ablation_metrics.csv`
- `experiments/outputs/analog_ablation_model_comparison.csv`
- `experiments/outputs/analog_ablation_region_performance.csv`
- `experiments/outputs/analog_ablation_feature_importance.csv`
- `experiments/outputs/analog_ablation_test_predictions.csv`
- `experiments/outputs/analog_ablation_failure_cases.csv`
- `experiments/outputs/analog_ablation_feature_manifest.csv`

Temporal-safety note:

- Analog sets were learned from train years 2017-2020 only.
- Analog weekly features were merged by `province`, `datetime`, `year`, and `week` to avoid ISO week cross-year duplication.
- 2022 labels were not used to construct analog sets.

Feature sets:

- `core_no_BUS`
- `core_plus_analog_history`
  - `analog_prevweek_blast`
  - `analog_outbreak_frequency_train`
- `core_plus_analog_pressure`
  - `analog_prevweek_risk`
  - `analog_2w_pressure`
  - `analog_leaf_wet_pressure`
  - `analog_regional_leaf_wet_pressure`
  - `analog_host_pressure`
- `core_plus_all_analog`
- `core_plus_geographic_pressure_only`
  - equivalent to `core_no_BUS` under the current feature policy because geographic/regional pressure features are already included in core.
- `core_plus_analog_and_geographic`
  - equivalent to `core_plus_all_analog` under the current feature policy.

Models:

- DNN no-class-weight
- Random Forest

Test 2022 model comparison:

| model | feature set | threshold | precision | recall | F1 | ROC-AUC | PR-AUC | FP | FN |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DNN no class weight | core plus analog history | 0.20 | 0.3421 | 0.4037 | 0.3704 | 0.8029 | 0.2818 | 125 | 96 |
| DNN no class weight | core no BUS | 0.20 | 0.3923 | 0.3168 | 0.3505 | 0.7818 | 0.2904 | 79 | 110 |
| Random Forest | core no BUS | 0.50 | 0.3662 | 0.3230 | 0.3432 | 0.7886 | 0.2407 | 90 | 109 |
| Random Forest | core plus analog pressure | 0.45 | 0.3069 | 0.3602 | 0.3314 | 0.7914 | 0.2471 | 131 | 103 |
| Random Forest | core plus all analog | 0.40 | 0.2533 | 0.4783 | 0.3312 | 0.8284 | 0.3014 | 227 | 84 |
| Random Forest | core plus analog history | 0.40 | 0.2317 | 0.4907 | 0.3147 | 0.8326 | 0.2953 | 262 | 82 |
| DNN no class weight | core plus analog pressure | 0.20 | 0.3333 | 0.3106 | 0.3215 | 0.7703 | 0.2733 | 100 | 111 |
| DNN no class weight | core plus all analog | 0.10 | 0.2042 | 0.4845 | 0.2873 | 0.7911 | 0.2623 | 304 | 83 |

Interpretation:

- The best F1 model is:
  - DNN no-class-weight + analog history
  - F1: 0.3704
- This improves over the Step 9.9 DNN no-class-weight core baseline:
  - F1: 0.3505 -> 0.3704
  - recall: 0.3168 -> 0.4037
  - false negatives: 110 -> 96
- The trade-off is more false positives:
  - FP: 79 -> 125
- PR-AUC does not improve for DNN analog history:
  - 0.2904 -> 0.2818
- Therefore, analog history improves classification threshold behavior, but not ranking quality.

Random Forest interpretation:

- Random Forest benefits strongly in ranking metrics from analog features:
  - core PR-AUC: 0.2407
  - all analog PR-AUC: 0.3014
  - analog history PR-AUC: 0.2953
  - all analog ROC-AUC: 0.8284
  - analog history ROC-AUC: 0.8326
- However, validation-selected thresholds produce many false positives and lower F1 than the DNN analog-history model.
- This suggests analog features carry strong information, but threshold governance remains important.

Regional performance: DNN no-class-weight

| feature set | region | positives | precision | recall | F1 | FP | FN |
|---|---|---:|---:|---:|---:|---:|---:|
| core no BUS | Northeast | 120 | 0.4153 | 0.4083 | 0.4118 | 69 | 71 |
| core plus analog history | Northeast | 120 | 0.3810 | 0.5333 | 0.4444 | 104 | 56 |
| core plus all analog | Northeast | 120 | 0.2992 | 0.6083 | 0.4011 | 171 | 47 |
| core no BUS | North | 18 | 0.0000 | 0.0000 | 0.0000 | 1 | 18 |
| core plus analog history | North | 18 | 0.0000 | 0.0000 | 0.0000 | 8 | 18 |
| core plus all analog | North | 18 | 0.0000 | 0.0000 | 0.0000 | 60 | 18 |
| core no BUS | East | 7 | 0.4000 | 0.2857 | 0.3333 | 3 | 5 |
| core plus analog history | East | 7 | 0.2000 | 0.1429 | 0.1667 | 4 | 6 |

Regional interpretation:

- Analog history improves Northeast recall and F1:
  - Northeast F1: 0.4118 -> 0.4444
  - Northeast recall: 0.4083 -> 0.5333
- Analog all features increase Northeast recall further:
  - recall: 0.6083
  - but false positives rise sharply.
- North remains unresolved:
  - all tested DNN analog feature sets still have recall 0 in North.
  - analog features increase false positives in North without capturing positives.
- East does not benefit from analog history in this split.

Regional performance: Random Forest

- RF with all analog features improves Northeast recall:
  - core recall: 0.4000
  - all analog recall: 0.6000
- RF all analog also improves Northeast F1:
  - core F1: 0.4051
  - all analog F1: 0.4390
- But North remains recall 0 across RF feature sets.

Feature importance:

Top Random Forest analog signals:

| feature set | analog feature | importance |
|---|---|---:|
| core plus analog history | analog_outbreak_frequency_train | 0.1207 |
| core plus all analog | analog_outbreak_frequency_train | 0.1163 |
| core plus analog history | analog_prevweek_blast | 0.0771 |
| core plus all analog | analog_prevweek_blast | 0.0733 |
| core plus analog pressure | analog_regional_leaf_wet_pressure | 0.0166 |
| core plus analog pressure | analog_leaf_wet_pressure | 0.0132 |
| core plus analog pressure | analog_host_pressure | 0.0126 |

Interpretation:

- Analog history features dominate analog pressure features.
- `analog_outbreak_frequency_train` is the strongest analog signal.
- `analog_prevweek_blast` is also important.
- Analog moisture/host pressure features carry weaker but nonzero signal.

Scientific conclusion:

- Province analog epidemiology adds measurable predictive value, especially through outbreak-history analogs.
- Analog history improves DNN F1 and recall under the corrected-label forward-year split.
- Analog features strongly improve Random Forest ranking metrics, but threshold behavior needs governance.
- Analog pressure/moisture features alone are not enough to improve the DNN baseline.
- Analog features help Northeast more than other regions.
- North remains unsolved, supporting the hypothesis that North failures require additional regional/field-reporting or sub-regional seasonality explanations rather than simple analog borrowing.

Decision:

- Do not replace the current default model yet.
- Promote `core_plus_analog_history` to a serious candidate feature set for future governance.
- Keep `core_no_BUS` as the stable operational baseline.
- Keep Random Forest + analog features as an interpretable ranking comparator.
- Do not use all analog features as default because they increase false positives substantially.

Next direction:

- Step 9.13: threshold/calibration governance for DNN `core_plus_analog_history` vs DNN `core_no_BUS`.
- Use validation 2021 only.
- Evaluate whether analog-history gains survive calibrated policy governance.
- Continue separate North-focused diagnostics.

## 2026-05-24 Step 9.13 Analog-History Decision Governance

Goal:

- Evaluate whether DNN no-class-weight + analog history remains useful after threshold and calibration governance.
- Compare against the stable DNN `core_no_BUS` baseline and Random Forest analog candidates.
- Use validation 2021 only for threshold selection and calibration.
- Preserve test 2022 as held-out evaluation.

Dataset:

- `experiments/outputs/region_temporal_sequence_dataset_updated_labels_2015_2022.csv`

Prediction source:

- `experiments/outputs/analog_ablation_all_predictions.csv`

Candidate model-feature sets:

- DNN no-class-weight + `core_no_BUS`
- DNN no-class-weight + `core_plus_analog_history`
- Random Forest + `core_no_BUS`
- Random Forest + `core_plus_analog_history`
- Random Forest + `core_plus_all_analog` as ranking comparator

Scripts:

- `experiments/train_analog_feature_ablation.py`
  - updated to export validation and test predictions in `analog_ablation_all_predictions.csv`
- `experiments/analog_history_decision_governance.py`

Outputs:

- `experiments/outputs/analog_decision_policy_metrics.csv`
- `experiments/outputs/analog_decision_model_comparison.csv`
- `experiments/outputs/analog_decision_region_performance.csv`
- `experiments/outputs/analog_decision_confusion_matrix.csv`
- `experiments/outputs/analog_decision_alert_tier_summary.csv`
- `experiments/outputs/analog_decision_alert_tier_region_summary.csv`
- `experiments/outputs/analog_decision_calibration_reliability.csv`
- `experiments/outputs/analog_decision_failure_cases.csv`
- `experiments/outputs/analog_decision_thresholds.csv`
- `experiments/outputs/analog_decision_calibrated_predictions.csv`

Test 2022 policy comparison:

| model | policy | threshold | precision | recall | F1 | ROC-AUC | PR-AUC | FP | FN |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| RF all analog | balanced default | 0.54 | 0.3987 | 0.3913 | 0.3950 | 0.8284 | 0.3014 | 95 | 98 |
| DNN analog history | balanced default | 0.26 | 0.4069 | 0.3665 | 0.3856 | 0.8029 | 0.2818 | 86 | 102 |
| DNN analog history | global F1 | 0.19 | 0.3367 | 0.4161 | 0.3722 | 0.8029 | 0.2818 | 132 | 94 |
| DNN analog history | Platt global F1 | 0.12 | 0.3350 | 0.4099 | 0.3687 | 0.8029 | 0.2818 | 131 | 95 |
| RF analog history | balanced default | 0.58 | 0.4113 | 0.3168 | 0.3579 | 0.8326 | 0.2953 | 73 | 110 |
| DNN core | Platt global F1 | 0.14 | 0.3667 | 0.3416 | 0.3537 | 0.7818 | 0.2904 | 95 | 106 |
| DNN core | global F1 | 0.21 | 0.4118 | 0.3043 | 0.3500 | 0.7818 | 0.2904 | 70 | 112 |
| RF core | global F1 | 0.52 | 0.3920 | 0.3043 | 0.3427 | 0.7886 | 0.2407 | 76 | 112 |

Interpretation:

- After governance, analog history still improves DNN decision behavior over DNN core.
- DNN analog history balanced default improves over DNN core global F1:
  - F1: 0.3500 -> 0.3856
  - recall: 0.3043 -> 0.3665
  - FN: 112 -> 102
  - FP: 70 -> 86
- DNN analog history global F1 improves recall further:
  - recall: 0.4161
  - FN: 94
  - but FP rises to 132.
- Platt calibration does not materially improve DNN analog history F1:
  - uncalibrated global F1: 0.3722
  - Platt global F1: 0.3687
- Therefore, analog-history gain is mainly a threshold-policy effect, not a calibration gain.

Random Forest interpretation:

- RF all analog balanced default is the best overall F1 policy in this governance pass:
  - F1: 0.3950
  - ROC-AUC: 0.8284
  - PR-AUC: 0.3014
- RF analog history and RF all analog have strong ranking metrics.
- However, RF global F1 analog policies tend to create many false positives.
- RF analog is promising as an interpretable ranking/decision-support comparator, but should not replace DNN core without more policy analysis.

Regional behavior: balanced default

| model | region | positives | precision | recall | F1 | FP | FN |
|---|---|---:|---:|---:|---:|---:|---:|
| DNN core | Northeast | 120 | 0.4300 | 0.3583 | 0.3909 | 57 | 77 |
| DNN analog history | Northeast | 120 | 0.4143 | 0.4833 | 0.4462 | 82 | 62 |
| RF all analog | Northeast | 120 | 0.4126 | 0.4917 | 0.4487 | 84 | 61 |
| RF analog history | Northeast | 120 | 0.4261 | 0.4083 | 0.4170 | 66 | 71 |
| DNN core | North | 18 | 0.0000 | 0.0000 | 0.0000 | 0 | 18 |
| DNN analog history | North | 18 | 0.0000 | 0.0000 | 0.0000 | 1 | 18 |
| RF all analog | North | 18 | 0.0000 | 0.0000 | 0.0000 | 0 | 18 |
| DNN core | East | 7 | 0.5000 | 0.2857 | 0.3636 | 2 | 5 |
| DNN analog history | East | 7 | 0.5000 | 0.1429 | 0.2222 | 1 | 6 |
| RF all analog | East | 7 | 0.3750 | 0.4286 | 0.4000 | 5 | 4 |

Regional interpretation:

- Analog history clearly improves Northeast recall/F1 under balanced policy.
- DNN analog history Northeast:
  - recall: 0.3583 -> 0.4833 compared with DNN core balanced default
  - F1: 0.3909 -> 0.4462
- RF all analog performs similarly well in Northeast:
  - recall: 0.4917
  - F1: 0.4487
- North remains unsolved:
  - every governed candidate still has North recall 0.
  - analog history does not solve North at practical thresholds.
- East is sparse and unstable:
  - DNN analog history hurts East recall compared with DNN core.
  - RF all analog improves East recall but with more false positives.

High-precision and high-recall modes:

- DNN analog history high-precision threshold 0.47:
  - precision: 0.5714
  - recall: 0.0994
  - FP: 12
  - FN: 145
- DNN analog history high-recall threshold 0.01:
  - recall: 0.8571
  - FP: 1,636
  - operationally too many false positives for field alerts.
- RF analog history high-recall captures more outbreaks but creates even more false positives:
  - recall: 0.9503
  - FP: 2,281

Alert-tier summary:

| model | tier | rows | positives | observed positive rate | mean calibrated score |
|---|---|---:|---:|---:|---:|
| DNN core | low risk | 2,609 | 48 | 0.0184 | 0.0467 |
| DNN core | watch | 1,263 | 62 | 0.0491 | 0.0649 |
| DNN core | warning | 95 | 30 | 0.3158 | 0.2106 |
| DNN core | high alert | 37 | 21 | 0.5676 | 0.3975 |
| DNN analog history | low risk | 1,735 | 16 | 0.0092 | 0.0492 |
| DNN analog history | watch | 2,114 | 83 | 0.0393 | 0.0599 |
| DNN analog history | warning | 96 | 32 | 0.3333 | 0.2152 |
| DNN analog history | high alert | 59 | 30 | 0.5085 | 0.3873 |
| RF all analog | low risk | 2,745 | 38 | 0.0138 | 0.0329 |
| RF all analog | watch | 1,065 | 52 | 0.0488 | 0.0740 |
| RF all analog | warning | 147 | 43 | 0.2925 | 0.1979 |
| RF all analog | high alert | 47 | 28 | 0.5957 | 0.3927 |
| RF analog history | high alert | 50 | 31 | 0.6200 | 0.3879 |

Alert-tier interpretation:

- Analog history improves prioritization in alert tiers:
  - DNN analog history low-risk tier has fewer positives than DNN core:
    - 16 vs 48
  - DNN analog history high-alert tier captures more positives:
    - 30 vs 21
- RF analog history has the highest high-alert observed positive rate:
  - 62.0%
- RF all analog also has strong high-alert separation:
  - 59.6%
- These are useful for dashboard/risk communication, even if binary default policy remains conservative.

Decision governance conclusion:

- Analog history remains useful after threshold governance.
- DNN `core_plus_analog_history` should not automatically replace DNN `core_no_BUS` as the single default yet because:
  - PR-AUC is lower than DNN core,
  - false positives increase,
  - East and North do not clearly benefit.
- Recommended operational interpretation:
  - stable default: DNN `core_no_BUS`
  - Northeast monitoring / recall-sensitive mode: DNN `core_plus_analog_history`
  - interpretable ranking comparator: RF `core_plus_all_analog` or RF `core_plus_analog_history`
  - dashboard alert-tier candidate: RF analog history / RF all analog
- North requires a separate diagnostic path; analog history does not solve it.

Scientific conclusion:

- Province analog history provides real epidemiological signal.
- The signal is strongest for Northeast outbreak detection and alert prioritization.
- Analog history is better treated as a governance feature or regional monitoring layer than as a universal nationwide replacement.
- Calibration improves interpretability of tiers, but does not turn analog history into a clear final default.

Next direction:

- Step 9.14: North-focused diagnostic analysis.
- Investigate terrain/elevation, label sparsity, sub-regional seasonality, and province-specific outbreak reporting patterns.
- Keep DNN core and DNN analog history as parallel candidates.

## 2026-05-24 Weather Source Terrain / Elevation Metadata Audit

Goal:

- Check whether the updated `weather_hourly` source contains terrain or elevation-related fields.
- Determine whether pressure fields can be used as a proxy for elevation.
- Prepare a clean input format for future terrain features.
- No model training and no merge into the main dataset in this audit.

Script:

- `experiments/audit_weather_terrain_metadata.py`

Weather source:

- `updated data/weather_hourly`

Files scanned:

- 7,392 CSV files
- years 2015-2022
- 77 provinces
- 924 weather files per year

Outputs:

- `experiments/outputs/weather_hourly_schema_file_scan.csv`
- `experiments/outputs/weather_hourly_unique_columns.csv`
- `experiments/outputs/weather_hourly_pressure_column_summary.csv`
- `experiments/outputs/weather_hourly_metadata_sample_values.csv`
- `experiments/outputs/weather_source_metadata_file_inventory.csv`
- `experiments/outputs/province_terrain_table_template.csv`

Unique weather columns:

| column | file count | years |
|---|---:|---|
| address | 7,392 | 2015-2022 |
| datetime | 7,392 | 2015-2022 |
| mint | 7,392 | 2015-2022 |
| maxt | 7,392 | 2015-2022 |
| temp | 7,392 | 2015-2022 |
| dew | 7,392 | 2015-2022 |
| humidity | 7,392 | 2015-2022 |
| heatindex | 7,392 | 2015-2022 |
| wspd | 7,392 | 2015-2022 |
| wgust | 7,392 | 2015-2022 |
| wdir | 7,392 | 2015-2022 |
| windchill | 7,392 | 2015-2022 |
| precip | 7,392 | 2015-2022 |
| precipcover | 7,392 | 2015-2022 |
| snowdepth | 7,392 | 2015-2022 |
| visibility | 7,392 | 2015-2022 |
| cloudcover | 7,392 | 2015-2022 |
| sealevelpressure | 7,392 | 2015-2022 |
| weathertype | 7,392 | 2015-2022 |
| latitude | 7,392 | 2015-2022 |
| longitude | 7,392 | 2015-2022 |
| resolvedAddress | 7,392 | 2015-2022 |
| name | 7,392 | 2015-2022 |
| info | 7,392 | 2015-2022 |
| conditions | 7,392 | 2015-2022 |

Terrain / elevation columns:

- No direct terrain or elevation fields were found.
- No columns matched:
  - `elevation`
  - `altitude`
  - `station elevation`
  - `height above sea level`
  - `terrain`
  - `slope`
  - `DEM`

Weather metadata columns:

- `address`
- `latitude`
- `longitude`
- `resolvedAddress`
- `name`
- `info`

Metadata interpretation:

- `address` is province name.
- `latitude` and `longitude` are province-level coordinates or query coordinates.
- `name` and `resolvedAddress` usually repeat the coordinate pair.
- `info` is empty in sampled weather rows.
- No separate weather-station metadata table was found inside `updated data/weather_hourly`.
- `updated data/thailand_province_name.csv` provides province naming metadata only, not elevation.
- BUS files contain rice research center names, but they are separate BUS source files, not weather-hourly station metadata.

Pressure fields:

- Only one pressure column exists:
  - `sealevelpressure`
- No `surface_pressure`, `station_pressure`, or `barometric station pressure` field was found.

Sea-level pressure coverage:

| year | files | provinces | mean coverage rate | mean pressure |
|---:|---:|---:|---:|---:|
| 2015 | 924 | 77 | 0.3303 | 1010.27 |
| 2016 | 924 | 77 | 0.3242 | 1009.53 |
| 2017 | 924 | 77 | 0.3303 | 1009.54 |
| 2018 | 924 | 77 | 0.3301 | 1009.45 |
| 2019 | 924 | 77 | 0.3356 | 1009.61 |
| 2020 | 924 | 77 | 0.3334 | 1009.37 |
| 2021 | 924 | 77 | 0.6787 | 1009.51 |
| 2022 | 924 | 77 | 0.7627 | 1009.12 |

Pressure interpretation:

- `sealevelpressure` is pressure adjusted to sea level.
- Because it is normalized to sea level, it should not be used as a direct proxy for elevation.
- If station pressure or surface pressure existed, lower station pressure could partially reflect higher elevation after weather-state correction.
- But the current weather source does not contain station/surface pressure.
- Therefore, pressure in this source is useful as a weather-state feature, not a terrain/elevation proxy.

Conclusion:

- Updated `weather_hourly` does not contain a direct terrain/elevation feature.
- It contains coordinates, but not elevation.
- It contains sea-level pressure, but this is not suitable as an elevation proxy.
- Terrain must be introduced from an external province-level or raster-derived terrain table.

Recommended future input file:

`province_terrain_table.csv`

Required columns:

| column | meaning |
|---|---|
| province | English province name matching project convention |
| elevation_mean | mean elevation in meters |
| elevation_min | minimum elevation in meters |
| elevation_max | maximum elevation in meters |
| elevation_range | elevation_max - elevation_min |
| elevation_std | within-province elevation standard deviation |
| terrain_roughness | terrain ruggedness or roughness index |
| source | data source, e.g. SRTM, ASTER, DEM, government GIS |
| notes | processing notes |

Interpretation for research:

- Terrain/elevation is still a plausible explanation for North behavior.
- Current weather data cannot test that hypothesis directly.
- A province terrain table should be added as an external explanatory layer before modeling terrain effects.
- Terrain should be treated as static province metadata, not a temporal weather variable.

Next direction:

- Acquire or prepare province-level terrain/elevation table.
- Audit terrain coverage and province-name matching.
- Only after audit, run controlled terrain-feature association and ablation.

## 2026-05-24 Step 9.14 North-Focused Diagnostic Analysis

Goal:

- Diagnose why North-region rice blast positives remain missed under the corrected-label forward-year split.
- Focus on failure interpretation, not new model training.
- Use corrected labels only, no BUS features, no old labels, and no fabricated terrain values.

Dataset:

- `experiments/outputs/region_temporal_sequence_dataset_updated_labels_2015_2022.csv`

Relevant model/error sources:

- `experiments/outputs/updated_2022_test_predictions.csv`
- `experiments/outputs/temporal_model_forward_predictions.csv`
- `experiments/outputs/analog_ablation_test_predictions.csv`
- `experiments/outputs/analog_decision_region_performance.csv`
- `experiments/outputs/analog_decision_policy_metrics.csv`
- `experiments/outputs/province_top_analog_neighbors.csv`
- `experiments/outputs/north_failure_analog_analysis.csv`

Script:

- `experiments/analyze_north_failures.py`

Outputs:

- `experiments/outputs/north_positive_case_table.csv`
- `experiments/outputs/north_positive_vs_negative_feature_summary.csv`
- `experiments/outputs/north_vs_northeast_positive_comparison.csv`
- `experiments/outputs/north_seasonality_diagnostic.csv`
- `experiments/outputs/north_province_failure_summary.csv`
- `experiments/outputs/north_analog_failure_diagnostic.csv`
- `experiments/outputs/north_label_observation_summary.csv`
- `experiments/outputs/north_failure_type_summary.csv`
- `experiments/outputs/north_diagnostic_recommendations.csv`

North test 2022 positive cases:

- Total North positive target cases: 18
- Positive provinces:
  - Lamphun: 8
  - Nan: 7
  - Phichit: 2
  - Nakhon Sawan: 1
- Every North positive case was missed by all available candidate models:
  - DNN `core_no_BUS`
  - DNN `core_plus_analog_history`
  - RF `core_plus_all_analog`
  - RF `core_plus_analog_history`
  - Hybrid DNN + TCN 2-week

North province failure summary:

| province | test positives | train positives | test positive rate | train positive rate | missed by all models | top analog provinces |
|---|---:|---:|---:|---:|---:|---|
| Lamphun | 8 | 1 | 0.1509 | 0.0047 | 8 | Mae Hong Son, Chiang Mai, Kamphaeng Phet, Lampang, Nan |
| Nan | 7 | 6 | 0.1321 | 0.0283 | 7 | Lamphun, Mae Hong Son, Chiang Mai, Lampang, Nong Khai |
| Phichit | 2 | 3 | 0.0377 | 0.0142 | 2 | Phitsanulok, Phetchabun, Sukhothai, Nakhon Sawan, Uthai Thani |
| Nakhon Sawan | 1 | 1 | 0.0189 | 0.0047 | 1 | Phetchabun, Kamphaeng Phet, Phichit, Phitsanulok, Uthai Thani |

Interpretation:

- Lamphun is the clearest regime-shift case:
  - train positives: 1
  - test 2022 positives: 8
- Nan also increases strongly in 2022 relative to train history.
- The missed North cases are concentrated in a small number of provinces rather than spread evenly across the region.

North vs Northeast positive comparison:

| feature | North positive mean | Northeast positive mean | North minus Northeast |
|---|---:|---:|---:|
| rainfall_sum | 29.61 | 36.78 | -7.17 |
| leaf_wet_hours | 27.78 | 36.76 | -8.98 |
| rolling_3w_leaf_wet_hours | 88.28 | 110.93 | -22.66 |
| risk_score | 25.28 | 29.44 | -4.15 |
| susceptibility_score | 0.5034 | 0.5575 | -0.0542 |
| host_weighted_risk | 25.36 | 31.84 | -6.47 |
| host_weighted_rolling_3w | 77.39 | 96.19 | -18.80 |
| neighbor_prevweek_blast | 0.0000 | 0.1083 | -0.1083 |
| regional_neighbor_pressure_2w | 0.0216 | 0.1199 | -0.0983 |
| regional_wind_alignment_frequency | 0.0026 | 0.0270 | -0.0244 |
| analog_prevweek_blast | 0.0000 | 0.2510 | -0.2510 |

Interpretation:

- North positives have weaker weather/moisture intensity than Northeast positives.
- North positives also have lower host susceptibility and lower host-weighted risk.
- The largest practical gap is outbreak-propagation signal:
  - `neighbor_prevweek_blast` is zero for North positives.
  - `analog_prevweek_blast` is zero for North positives.
  - regional neighbor pressure is much lower than in Northeast positives.
- This explains why analog history improves Northeast but does not transfer to North.

North positive vs North negative interpretation:

- Some moisture/risk pressure exists in North positives:
  - `rolling_3w_leaf_wet_hours` is higher in positives than negatives.
  - `neighbor_prevweek_risk` is higher in positives than negatives.
  - analog leaf-wet pressure is also higher.
- However, these signals are not strong enough to push model scores above governed thresholds.
- The strongest analog-history signals are absent because prior-week analog/proximal outbreak labels are mostly zero.

Seasonality:

Test 2022 North positives:

| period | positive rows | share of North positives |
|---|---:|---:|
| weeks 1-13 | 2 | 0.1111 |
| weeks 14-26 | 2 | 0.1111 |
| weeks 27-39 | 6 | 0.3333 |
| weeks 40-53 | 8 | 0.4444 |

Train 2017-2020 North positives:

| period | positive rows | share of North train positives |
|---|---:|---:|
| weeks 1-13 | 38 | 0.2222 |
| weeks 14-26 | 11 | 0.0643 |
| weeks 27-39 | 52 | 0.3041 |
| weeks 40-53 | 70 | 0.4094 |

Interpretation:

- North 2022 seasonality is not completely outside historical North seasonality.
- Late-year positives are expected from train history.
- The issue is more province-specific and signal-intensity specific than purely seasonal.

Label/reporting context:

| scope | rows | label observed rate | positives | positive rate |
|---|---:|---:|---:|---:|
| train 2017-2020 North | 3,604 | 0.5755 | 171 | 0.0474 |
| train 2017-2020 Northeast | 4,232 | 0.5766 | 269 | 0.0636 |
| validation 2021 North | 893 | 0.9429 | 113 | 0.1265 |
| test 2022 North | 901 | 0.9434 | 18 | 0.0200 |
| test 2022 Northeast | 1,060 | 0.9434 | 120 | 0.1132 |

Interpretation:

- North 2022 has good label observation coverage.
- North 2022 has much lower prevalence than validation 2021 North and test 2022 Northeast.
- The North failure is not simply missing labels in 2022.
- The model is trying to detect sparse, low-prevalence positives with weaker propagation signals.

Failure type summary:

| failure type | cases | provinces |
|---|---:|---:|
| no neighbor/analog outbreak signal | 18 | 4 |
| possible terrain/microclimate missing feature | 18 | 4 |
| low host susceptibility/risk signal | 4 | 2 |
| low weather-risk signal | 3 | 2 |
| unobserved label context | 1 | 1 |

Terrain hypothesis:

- The current weather source has no direct elevation or terrain feature.
- `sealevelpressure` should not be used as an elevation proxy.
- North failures remain compatible with a missing terrain/microclimate explanation, but this cannot be tested from current weather data alone.
- Terrain must be introduced from an external province-level or raster-derived terrain table.

Diagnostic conclusion:

- North failure is not solved by:
  - analog history,
  - temporal neural models,
  - calibration,
  - threshold governance.
- North 2022 positives are concentrated in a few provinces, especially Lamphun and Nan.
- These positives have weaker host/moisture/risk/spatial-propagation signatures than Northeast positives.
- The main missing operational signal is prior outbreak pressure:
  - no geographic neighbor previous-week blast signal,
  - no analog previous-week blast signal.
- Therefore, North likely requires a separate diagnostic path rather than simply adding analog features to the national model.

Recommendations:

- Add an external terrain/elevation table before testing terrain effects.
- Do not treat analog history as a North solution.
- Investigate North sub-regional seasonality and reporting density.
- Keep Northeast analog-history monitoring separate from North diagnostics.
- Prioritize terrain/microclimate features for the next North-specific analysis.

Next direction:

- Prepare `province_terrain_table.csv` from an external DEM or province-level GIS source.
- Audit province-name matching and terrain coverage.
- Then run a controlled terrain-feature association analysis before any model retraining.

## 2026-05-24 Step 9.15 Feature Agent Specification and Feature Lifecycle Governance

Goal:

- Formalize a Feature Agent system for managing feature discovery, validation, ablation, governance, and missing-data escalation.
- Keep the rice blast AI research platform reproducible, explainable, and thesis-oriented before adding more feature complexity.
- Define how future candidate features move from biological hypothesis to governed use.

Context:

- The project now contains many feature families:
  - mechanistic weather,
  - humidity and leaf wetness,
  - temporal accumulation,
  - host susceptibility,
  - spatial pressure,
  - wind alignment,
  - spore-window features,
  - BUS external reference,
  - province analog history,
  - analog pressure and moisture,
  - future terrain/elevation candidates.
- Recent findings show that feature governance is necessary:
  - `core_no_BUS` remains the stable nationwide feature baseline.
  - analog history improves Northeast recall/F1 but increases false positives.
  - BUS is useful as an external reference but should not be a required nationwide dependency.
  - all-analog feature expansion can improve ranking but is not safe as the default.
  - North remains unresolved and may require terrain or microclimate data.
  - updated `weather_hourly` has no direct terrain/elevation fields.

Documents created:

- `FEATURE_AGENT_SPEC.md`
- `DATA_SCOUT_AGENT_SPEC.md`

Registry outputs:

- `experiments/outputs/feature_registry_template.csv`
- `experiments/outputs/feature_registry_current.csv`

Feature Agent roles:

| agent | responsibility |
|---|---|
| Feature Scientist Agent | propose biologically meaningful features, define hypotheses, mechanisms, data needs, and leakage risks |
| Feature Validation Agent | run feature-effect, stability, regional association, missingness, coverage, and redundancy checks |
| Feature Ablation Agent | test feature sets in controlled experiments against baseline models and evaluate FP/FN tradeoffs |
| Feature Governance Agent | assign feature status and decide whether a feature is core, regional, dashboard, reference, rejected, or future-data-needed |
| Data Scout Agent | activate when useful features cannot be built from existing data and evaluate external data sources before integration |

Feature lifecycle statuses:

- `proposed`
- `data_available`
- `data_missing`
- `audited`
- `validated`
- `ablated`
- `governed`
- `accepted_core`
- `accepted_regional`
- `accepted_dashboard`
- `accepted_reference`
- `rejected`
- `future_data_needed`

Required feature metadata:

- `feature_name`
- `feature_family`
- `hypothesis`
- `biological_rationale`
- `data_source`
- `temporal_scope`
- `spatial_scope`
- `leakage_risk`
- `missingness`
- `validation_result`
- `ablation_result`
- `regional_behavior`
- `governance_status`
- `notes`

Initial governance decisions:

| feature family | preliminary status | interpretation |
|---|---|---|
| core weather / moisture | `accepted_core` | stable mechanistic baseline |
| leaf wetness | `accepted_core` | biologically important infection proxy |
| temporal rolling risk | `accepted_core` | short-term memory is useful |
| host susceptibility | `accepted_core` | supported by feature importance and biological rationale |
| spatial / regional pressure | `accepted_core` | strong corrected-label signal |
| wind alignment | `accepted_core` with regional interpretation | useful but heterogeneous |
| spore-window features | `accepted_core` or `candidate_only` | biologically informed but still monitored |
| BUS | `accepted_reference` | external mechanistic benchmark, not national dependency |
| analog history | `accepted_regional` | useful for Northeast monitoring, not universal default |
| analog pressure / moisture | `candidate_only` | weaker than analog history |
| all-analog feature expansion | `candidate_only` / not default | can raise false positives |
| terrain/elevation | `future_data_needed` | official missing-data candidate for North diagnostics |
| sea-level pressure as elevation proxy | `rejected` | scientifically inappropriate because pressure is sea-level adjusted |

Data Scout Agent:

- Defined as the escalation mechanism for features that are scientifically plausible but absent from current data.
- Must evaluate source quality, license, cost, resolution, coverage, and reproducibility.
- Must propose data source options before download or integration.
- Must not download or integrate external datasets without approval.

First official Data Scout case:

- Missing data: province-level terrain/elevation.
- Reason: North failures remain unresolved, and terrain/microclimate may explain low-signal positives.
- Candidate sources:
  - SRTM DEM
  - Copernicus DEM
  - ASTER GDEM
  - Thai government GIS / DEM sources
  - commercial DEM if public sources are insufficient
- Expected integration file:
  - `province_terrain_table.csv`

Feature registry:

- `feature_registry_template.csv` defines the required registry columns.
- `feature_registry_current.csv` records current governance status for:
  - weather/moisture features,
  - leaf wetness,
  - temporal rolling features,
  - host susceptibility,
  - regional/spatial pressure,
  - wind alignment,
  - spore-window features,
  - BUS reference features,
  - analog history,
  - analog pressure,
  - terrain/elevation candidates,
  - rejected sea-level-pressure terrain proxy.

Conclusion:

- Step 9.15 converts feature development from ad hoc experimentation into a governed scientific lifecycle.
- Future features should not enter the model only because they are available.
- Every feature must pass hypothesis definition, data audit, validation, ablation, and governance decision.
- Terrain/elevation is now the first official missing-data scouting case.

Next direction:

- Use the Data Scout Agent workflow to evaluate terrain/elevation sources.
- Prepare a province-level terrain table only after source approval.
- Audit terrain coverage before any terrain-feature modeling.
