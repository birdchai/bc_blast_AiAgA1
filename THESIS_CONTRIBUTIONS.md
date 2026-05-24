# Thesis Contributions

## Central Thesis

Rice blast forecasting should be framed as a spatiotemporal plant epidemiology problem rather than a weather-only prediction task.

The evidence developed so far suggests that rice blast occurrence is shaped by an interacting structure of:

- host susceptibility
- short-term temporal epidemiological memory
- regional heterogeneity
- spatial neighboring pressure
- directional wind-mediated spread
- mechanistic environmental suitability

The project therefore contributes not only a forecasting model, but an explainable computational epidemiology framework for national-scale rice blast risk analysis.

## Contribution 1: Beyond Weather-Only Modeling

### Claim

Rice blast forecasting requires integrated epidemiological structure beyond weather-only modeling.

### Evidence

- Weather-only mechanistic baselines produced measurable but weak national forecasting performance.
- Weather-only risk scores had useful recall in some settings but suffered from high false positives.
- Adding host susceptibility, spatial context, wind alignment, regional structure, and controlled machine learning improved predictive performance.
- The best current baseline is not a pure weather model, but a controlled DNN using compact core epidemiological features.

### Interpretation

Weather is necessary but insufficient. Rice blast risk cannot be explained by temperature, humidity, rainfall, and leaf wetness alone at national weekly scale.

The disease process requires a host-pathogen-environment framing where weather creates infection suitability, but host availability, regional disease ecology, and spatial pressure shape whether disease occurs.

### Limitation

The weather-only baseline remains important as an explainable mechanistic reference. It should not be discarded; it should serve as the environmental component of a broader epidemiological system.

### Next Direction

Use weather-only risk as a mechanistic layer inside calibrated and region-aware models rather than as a standalone national predictor.

## Contribution 2: Host, Spatial, and Directional Epidemiological Signal

### Claim

Host susceptibility, spatial neighbor pressure, and directional wind-mediated connectivity contain measurable and regionally heterogeneous signal.

### Evidence

- Multi-year feature-effect analysis showed that rice variety composition can be associated with blast occurrence.
- Conservative susceptibility v0 improved the epidemiological interpretation of weather risk.
- Spatial neighbor pressure contained signal, especially in region-aware analysis.
- Wind speed alone was insufficient, but directional alignment from infected neighboring provinces showed exploratory signal.
- Regional analysis showed that the Northeast has especially strong host, spatial, and wind-aligned signal.

### Interpretation

Rice blast is not simply a local weather response. It behaves as a spatial epidemiological process, where infection pressure may depend on neighboring disease occurrence, host distribution, and airflow direction.

The regional heterogeneity suggests that a single national disease mechanism is too coarse. Different regions may require different weighting, calibration, or model interpretation.

### Limitation

Directional wind analysis is still exploratory. Weather station wind direction may not fully represent canopy-level airflow, and weekly aggregation may dilute short dispersal events.

### Next Direction

Develop region-aware spatial and wind-mediated features carefully, with conservative assumptions and explicit validation before using them to modify risk scores.

## Contribution 3: Short-Term Temporal Memory

### Claim

Short-term epidemiological memory, approximately 2 weeks, is more useful than long sequence memory under national weekly aggregation.

### Evidence

- Temporal accumulation features improved interpretation over single-week weather risk.
- LSTM sequence governance compared 2, 4, 8, and 12 week sequences.
- The 2-week sequence length performed best among tested LSTM governance configurations.
- Longer windows generally reduced performance, likely by adding noise and reducing usable training samples.

### Interpretation

At weekly national scale, rice blast signal appears to be short-memory rather than long-memory. Recent infection suitability and recent regional/spatial pressure are more informative than long historical sequences in the current data representation.

This does not mean long-term seasonal structure is irrelevant. It means that the current weekly forecasting target benefits most from recent epidemiological conditions.

### Limitation

The current LSTM setup is a baseline and not a final temporal architecture. Longer memory may become useful with different sequence design, region-specific models, daily data, or better representation of phenology and cropping calendars.

### Next Direction

Use 2-week memory as the initial default for temporal modeling, then test previous-only windows, calibrated temporal summaries, and region-specific temporal behavior.

## Contribution 4: Governed Feature Selection

### Claim

Controlled biologically governed feature selection outperforms uncontrolled statistical feature expansion.

### Evidence

- Advanced statistical temporal features were created safely using historical-only rolling statistics, slopes, EWMA, and province-relative anomalies.
- The full statistical feature dataset contained useful signal, especially for tree-based models.
- However, adding all statistical features did not improve the best overall forecasting performance.
- Controlled feature selection showed that the compact `core_only` feature set outperformed statistical feature expansions.
- The best current model is controlled DNN class-weighted with `core_only` features:
  - test F1: 0.3771
  - ROC-AUC: 0.7335
  - PR-AUC: 0.2722

### Interpretation

More features do not automatically produce better epidemiological forecasting. Feature expansion can dilute signal, increase noise, and make model behavior less stable.

The strongest current representation is a compact, biologically interpretable set of mechanistic, host, spatial, wind, and regional features.

### Limitation

Some statistical feature families are informative, especially rolling statistics and province-relative susceptibility features. They should not be rejected entirely; they require controlled subset testing.

### Next Direction

Freeze the compact core feature set as the current reference and test statistical feature families only through explicit, interpretable subsets.

## Contribution 5: Explainable DNN Generalization Versus Naive Hybrid LSTM

### Claim

Simple explainable DNN architectures currently generalize better than naive hybrid LSTM systems under outbreak-year distribution shift.

### Evidence

- Classical ML models improved over mechanistic threshold baselines.
- A simple DNN with class weighting improved over Random Forest, XGBoost, and mechanistic baselines.
- Controlled DNN with `core_only` features became the strongest current model.
- LSTM and hybrid mechanistic-LSTM baselines were feasible but did not outperform the controlled DNN.
- Hybrid LSTM error analysis showed stronger validation-to-test degradation than the DNN.
- The hybrid model over-predicted in several regions and appeared sensitive to outbreak-year patterns from 2020.

### Interpretation

The current forecasting problem benefits from a compact nonlinear tabular representation more than from naive temporal sequence fusion.

This does not mean LSTM is inappropriate. It means that temporal deep learning must be introduced with stronger governance: calibrated thresholds, regional diagnostics, explicit sequence design, and careful handling of distribution shift.

### Limitation

The hybrid LSTM tested so far is a baseline, not a final hybrid architecture. It used a simple fusion design and limited temporal memory.

### Next Direction

Before further hybrid complexity, prioritize:

- probability calibration
- region-wise threshold analysis
- regional error governance
- validation prediction export
- sequence design refinement
- controlled comparison against the compact DNN reference

## Current Best Reference Baseline

The current best empirical baseline is:

- model: controlled DNN with class weighting
- feature set: `core_only`
- target: `blast_t_plus_1`
- split:
  - train: 2017-2019
  - validation: 2020
  - test: 2021
- test performance:
  - precision: 0.3157
  - recall: 0.4683
  - F1: 0.3771
  - ROC-AUC: 0.7335
  - PR-AUC: 0.2722

This should be treated as the current reference baseline before adding more complex hybrid architectures.

## Scientific Position

This project does not primarily show whether LSTM is good or bad.

It shows that rice blast forecasting is best approached as a spatiotemporal plant epidemiology problem with several interacting components:

- environmental infection suitability
- host susceptibility
- short-term temporal memory
- regional heterogeneity
- neighboring disease pressure
- directional spread potential

The current evidence supports a hybrid epidemiological AI framework, but also shows that model complexity must be governed by biological interpretability, leakage-safe validation, regional diagnostics, and controlled feature selection.

## Thesis-Level Summary

The core contribution of this research is the development of an explainable national-scale computational plant epidemiology framework for rice blast forecasting.

The framework integrates mechanistic weather risk, host susceptibility, spatial disease pressure, wind-directional context, regional heterogeneity, temporal memory, and AI-based learning.

The strongest current insight is that biologically governed feature design and controlled validation are more important than immediately adopting more complex temporal neural architectures.
