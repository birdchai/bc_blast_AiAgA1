# Future Work: Thailand Rice Blast Epidemiology Platform

This document separates future research directions from current findings. It is
intended to guide thesis planning, proposal writing, and the transition from
mechanistic exploration to hybrid forecasting.

---

## Research Identity

The project has evolved beyond a single forecasting script or notebook. It is
now closer to a computational plant epidemiology platform for rice blast disease
in Thailand.

Core platform components:

- explainable weather-driven infection modeling
- rice variety host susceptibility analysis
- spatial disease pressure analysis
- wind-mediated connectivity exploration
- regional heterogeneity analysis
- sequence-ready epidemiological datasets
- multi-agent research workflow support

---

## Immediate Future Work Before ML

### 1. Transparent Temporal Baselines

Before training LSTM or other sequence models, build non-ML temporal baselines:

- previous-week blast baseline
- regional neighbor pressure baseline
- host-weighted temporal risk baseline
- rule-based `t+1` and `t+2` alert baseline

Purpose:

- establish interpretable benchmarks
- avoid overstating ML gains
- identify regions where simple temporal rules already work

### 2. Region-Specific Mechanistic Review

Review each region separately:

- Northeast
- North
- East
- South
- Central
- West

Questions:

- Which features are stable by region?
- Which regions are host-driven?
- Which regions are spatial-pressure-driven?
- Which regions show wind-alignment signal?
- Which regions have too little disease data for strong conclusions?

### 3. Data Quality and Label Review

Investigate disease label structure:

- binary occurrence versus outbreak magnitude
- province-year reporting differences
- years with weak labels, especially 2015 and 2016
- whether `blast_days` or raw positive values can support severity analysis

---

## Hybrid ML and LSTM Direction

### Goal

Use ML only after explainable epidemiological structure is established.

### Candidate Inputs

Sequence-ready features:

- `risk_score`
- `rolling_2w_risk`
- `rolling_3w_risk`
- `susceptibility_score`
- `host_weighted_risk`
- `neighbor_prevweek_blast`
- `neighbor_prevweek_risk`
- `wind_aligned_neighbor_blast`
- `regional_neighbor_pressure_2w`
- `regional_neighbor_pressure_3w`
- `regional_wind_alignment_frequency`
- `regional_leaf_wet_accumulation`

Targets:

- `blast_t_plus_1`
- `blast_t_plus_2`

### Candidate Models

- logistic regression baseline
- decision tree or shallow random forest for interpretability
- gradient boosting only after transparent baselines
- LSTM / GRU for temporal sequences
- temporal convolutional model
- hybrid mechanistic + LSTM model

### Important Constraint

ML models should not replace mechanistic reasoning. They should test whether
sequence learning can improve forecasts after mechanistic features are already
defined.

---

## Causal Inference Direction

Potential research questions:

- Does host susceptibility modify weather-risk effects?
- Does neighboring blast pressure precede local blast occurrence?
- Are wind-aligned infected neighbors more predictive than non-aligned infected
  neighbors?
- Are regional differences stable enough to support region-specific policies?

Possible methods:

- lagged association analysis
- matched province-week comparisons
- fixed-effect models by province and year
- region-stratified analysis
- sensitivity analysis for reporting bias

Important caution:

Current results are associations, not causal proof.

---

## Graph Epidemiology Direction

The spatial system can be reframed as a graph:

- nodes = provinces
- edges = distance, wind alignment, neighbor infection, regional adjacency
- node features = weather, host susceptibility, blast history
- edge features = distance, bearing, wind alignment, previous-week source blast

Future graph features:

- distance-weighted neighbor pressure
- wind-aligned edge pressure
- region-constrained graph pressure
- dynamic weekly graph edges based on wind direction

Potential models:

- graph feature engineering without ML
- graph-based alert rules
- graph neural networks only after interpretable graph baselines

---

## Regional Adaptive Forecasting

Regional findings suggest that a single national model is too coarse.

Potential approach:

- national baseline model
- region-specific modifiers
- Northeast spatial/wind emphasis
- East host-susceptibility emphasis
- North mixed temporal-spatial emphasis
- cautious treatment for South and West due to differing behavior or sparse
  labels

Research question:

Can a region-aware forecasting framework improve robustness without sacrificing
explainability?

---

## Agent Workflow Optimization

The multi-agent system can support research operations:

- planner agent for experiment design
- critic agent for methodological review
- orchestrator agent for workflow sequencing
- tool layer for deterministic computation
- report agent for thesis-oriented summaries

Future improvements:

- automatic experiment registry
- structured report generation
- automatic comparison of output CSV summaries
- region-specific research brief generation
- guardrails to separate evidence from speculation

Important principle:

Agents should interpret and coordinate; deterministic tools should compute.

---

## Publication and Thesis Directions

Potential thesis chapters:

1. Introduction and rice blast epidemiology context
2. Data sources and preprocessing
3. Mechanistic weather infection modeling
4. Host susceptibility from rice variety distributions
5. Spatial and wind-mediated disease pressure
6. Regional heterogeneity of rice blast epidemiology
7. Temporal sequence preparation and forecasting framework
8. Multi-agent AI research system

Potential publication themes:

- Explainable national rice blast risk modeling using weather and host data
- Regional heterogeneity in rice blast epidemiology across Thailand
- Wind-mediated spatial connectivity for plant disease pressure
- Multi-agent AI workflow for computational plant epidemiology

---

## Current Recommendation

Before Step 9, freeze the current research structure:

- keep mechanistic features explainable
- preserve all outputs and timeline documents
- avoid changing susceptibility weights prematurely
- avoid black-box ML until transparent temporal baselines are built
- use Step 9 to bridge mechanistic epidemiology and sequence forecasting

