# Thailand Rice Blast Epidemiology System

## Project Objective

Build a nationwide rice blast disease prediction system for Thailand using:

* mechanistic epidemiology
* weather-driven infection modeling
* rice variety susceptibility
* multi-agent AI workflow

Goal:
Create an explainable disease prediction framework before moving to ML.

---

# Current Datasets

## 1. Hourly Weather Data (2015–2022)

77 provinces in Thailand.

Variables:

* temperature
* humidity
* rainfall

Resolution:

* hourly

Current usage:

* infection feature generation
* weekly aggregation
* lag analysis

## 2. Blast Disease Data

Resolution:

* weekly (expanded into daily)

Current usage:

* weekly validation labels

Current features:

* blast_any
* blast_days

## 3. Rice Variety Data (POV)

Separated into:

* In-season
* Off-season

Contains:

* rice variety areas by province/date

Already transformed into long format:

* variety
* area
* ratio

---

# Current Architecture

Project structure:

agents/
tools/
workflows/
experiments/
data/

Main mechanistic model:
tools/blast_model_v1.py

---

# Current Mechanistic Pipeline

hourly weather
→ favorable infection hours
→ weekly aggregation
→ lag analysis
→ nationwide validation

Current weather features:

* temp_favorable
* temp_optimal
* humidity_favorable
* humidity_optimal
* favorable_hour
* optimal_hour

Current weekly features:

* infection_ratio
* optimal_ratio
* humidity_ratio
* rainfall_ratio
* risk_score
* risk_level

---

# Current Validation System

Validation implemented:

* precision
* recall
* f1
* correlation
* false positive
* false negative

Supports:

* threshold sweep
* lag sweep

Files:

* experiments/test_blast_model_v1.py
* experiments/test_blast_model_v1_batch.py

---

# Current Findings

## Province-Year Sample (Buri Ram 2017)

Best result:

* lag 0
* threshold 45

Metrics:

* precision = 0.10
* recall = 1.00
* f1 = 0.1818

Interpretation:
Weather signal exists but false positives remain high.

## Nationwide Batch Validation (2017)

Results:

* weather-only model does not generalize well nationally
* lag effect exists
* best lag approximately 2 weeks

Interpretation:
Weather-only mechanistic model is insufficient alone.

---

# Important Research Insights

The current findings strongly suggest:

Disease risk depends on:

* weather favorability
* host susceptibility
* temporal accumulation
* inoculum pressure

Not weather alone.

---

# Important Design Philosophy

* Explainable models preferred
* Mechanistic reasoning before ML
* Avoid black-box prediction first
* Modular architecture required
* Research-oriented workflow

---

# Already Completed

✔ infection hours
✔ weekly aggregation
✔ lag sweep
✔ threshold sweep
✔ nationwide validation
✔ POV transformation
✔ susceptibility groundwork

---

# NEXT IMPLEMENTATION TARGET

Implement temporal accumulation features.

Priority tasks:

1. Rolling cumulative risk
   Examples:

* rolling_2w_risk
* rolling_3w_risk
* rolling infection hours

2. Leaf wetness estimation
   Simple version:

* RH >= 90
* suitable temperature

Generate:

* leaf_wet_hours
* leaf_wet_ratio

3. Integrate rice variety susceptibility

Goal:
Reduce false positives from weather-only model.

---

# IMPORTANT

Do NOT redesign the entire architecture.

Extend the current mechanistic pipeline incrementally.

Maintain explainability and modularity.
