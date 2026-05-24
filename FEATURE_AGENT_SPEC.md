# Feature Agent Specification

## Purpose

The Feature Agent system formalizes how epidemiological features are proposed, validated, ablated, governed, and escalated when required data are missing. It is designed for the rice blast AI research platform as a reproducible scientific workflow, not as an automatic feature-generation shortcut.

The system protects the project from uncontrolled feature expansion by requiring every feature to have:

- a biological or epidemiological hypothesis,
- a defined data source,
- leakage and missingness checks,
- validation evidence,
- controlled ablation evidence,
- region-aware interpretation,
- an explicit governance decision.

## Research Context

The project currently contains several feature families:

- mechanistic weather features,
- humidity and leaf wetness features,
- temporal accumulation features,
- host susceptibility features,
- spatial pressure features,
- wind alignment features,
- spore-window wind and leaf-wetness features,
- BUS external reference features,
- province analog history features,
- analog pressure and moisture features,
- future terrain/elevation candidate features.

Recent corrected-label findings imply that feature governance is now more important than simply adding more predictors:

- `core_no_BUS` remains the stable nationwide feature baseline.
- Analog history improves recall and F1, especially in the Northeast, but increases false positives.
- BUS is useful as an external mechanistic reference but should not be a required national dependency because coverage is limited.
- All-analog feature sets can improve ranking but may increase false positives.
- North remains unresolved and may require missing terrain or microclimate data.
- Updated `weather_hourly` does not contain direct terrain or elevation fields.

## Agent Roles

### A. Feature Scientist Agent

Responsibilities:

- Propose biologically meaningful features.
- Define the feature hypothesis.
- Classify the feature family.
- Explain the expected epidemiological mechanism.
- Identify required input data.
- Identify temporal and spatial scope.
- Identify possible leakage risks.
- State whether the feature is mechanistic, observational, external reference, analog-derived, or static metadata.

Expected output:

- Feature proposal record.
- Required data list.
- Leakage-risk note.
- Initial feature status: `proposed`.

Example:

```text
Feature: elevation_mean
Family: terrain_static
Hypothesis: Higher elevation and terrain roughness may alter humidity persistence, dew formation, microclimate, and reporting patterns in North provinces.
Data needed: Province-level elevation summary from DEM/GIS.
Leakage risk: Low if static and computed independently from outbreak labels.
Status: future_data_needed.
```

### B. Feature Validation Agent

Responsibilities:

- Run feature-effect analysis.
- Run year-by-year stability analysis.
- Run regional association analysis.
- Inspect missingness and coverage.
- Test correlation with target labels.
- Compare against existing core features.
- Identify whether the feature duplicates existing signals.

Expected validation outputs:

- Feature-effect table.
- Stability summary.
- Regional association table.
- Missingness and coverage report.
- Correlation and redundancy summary.

Validation principles:

- Treat associations as non-causal unless supported by external design.
- Validate by year and by region.
- Check whether an effect is stable or concentrated in one outbreak year.
- Do not promote a feature based on national correlation alone.

### C. Feature Ablation Agent

Responsibilities:

- Add feature sets in controlled experiments.
- Compare against the current baseline.
- Evaluate precision, recall, F1, ROC-AUC, PR-AUC.
- Analyze false-positive and false-negative tradeoffs.
- Analyze region-wise benefit.
- Avoid aggressive tuning.
- Preserve the chronological split policy.

Controlled ablation requirements:

- Define baseline feature set.
- Define candidate feature set.
- Use the same target and split.
- Select thresholds using validation data only.
- Evaluate held-out test data only once per policy.
- Record whether the feature improves ranking, classification, recall, precision, or alert-tier behavior.

### D. Feature Governance Agent

Responsibilities:

- Assign feature lifecycle status.
- Decide whether a feature becomes:
  - core feature,
  - candidate feature,
  - regional feature,
  - dashboard or communication feature,
  - external reference,
  - rejected / not useful yet,
  - missing-data candidate.
- Record decision rationale.
- Prevent candidate features from becoming default without evidence.

Governance principles:

- A feature can be useful without becoming a default core feature.
- A feature can be regionally useful but nationally risky.
- A feature can improve ranking but not binary decisions.
- A feature can support dashboards without improving F1.
- Missing-data candidates must be escalated to the Data Scout Agent before integration.

### E. Data Scout Agent

Responsibilities:

- Activate when a useful feature cannot be created from existing data.
- Search for free or paid external datasets.
- Evaluate source quality, license, resolution, coverage, cost, and reproducibility.
- Propose data-source options before integration.
- Do not download, purchase, or integrate data without user approval.

Expected output:

- Data source recommendation table.
- License and cost note.
- Coverage and resolution assessment.
- Proposed input-file schema.
- Approval checkpoint.

## Feature Lifecycle Statuses

| status | meaning |
|---|---|
| proposed | Feature idea has been defined but not audited. |
| data_available | Required data exists locally or is already accessible. |
| data_missing | Required data is not present in the project. |
| audited | Schema, missingness, and coverage have been checked. |
| validated | Feature-effect, stability, and association checks have been completed. |
| ablated | Controlled model ablation has been completed. |
| governed | Governance decision has been recorded. |
| accepted_core | Feature is part of the stable core feature set. |
| accepted_regional | Feature is accepted for region-specific monitoring or interpretation. |
| accepted_dashboard | Feature is useful for dashboard, alert tier, or risk communication. |
| accepted_reference | Feature is useful as an external benchmark/reference but not as a dependency. |
| rejected | Feature is not useful or is scientifically inappropriate under current evidence. |
| future_data_needed | Feature may be useful but requires new external data. |

## Required Feature Metadata

Every feature or feature group must maintain the following metadata:

| field | description |
|---|---|
| feature_name | Exact feature or feature-group name. |
| feature_family | Biological or computational family. |
| hypothesis | Expected relationship with rice blast risk. |
| biological_rationale | Mechanistic or epidemiological explanation. |
| data_source | Source table, script, or external data source. |
| temporal_scope | Hourly, daily, weekly, monthly, static, historical, or future target. |
| spatial_scope | Province, region, neighbor, analog, national, station, or raster. |
| leakage_risk | Low, medium, high, with explanation. |
| missingness | Coverage or missing-data behavior. |
| validation_result | Feature-effect and stability result. |
| ablation_result | Controlled model impact. |
| regional_behavior | Region-specific benefit or instability. |
| governance_status | Current lifecycle status. |
| notes | Caveats, next action, or scientific interpretation. |

## Current Feature Governance Summary

| feature family | current governance decision |
|---|---|
| Core weather and moisture | `accepted_core` |
| Leaf wetness | `accepted_core` |
| Temporal rolling risk | `accepted_core` |
| Host susceptibility | `accepted_core` |
| Spatial / regional pressure | `accepted_core` |
| Wind alignment | `accepted_core` with regional interpretation |
| Spore-window features | `accepted_core` or candidate depending on coverage |
| BUS features | `accepted_reference` |
| Analog history | `accepted_regional` / candidate governance feature |
| Analog pressure / moisture | `candidate_only` |
| All-analog feature expansion | `candidate_only` / not default |
| Terrain / elevation | `future_data_needed` |
| Sea-level pressure as elevation proxy | `rejected` |

## Decision Rules

### Promote To Core

A feature can become `accepted_core` when it:

- has a clear biological rationale,
- has stable coverage,
- does not create leakage,
- improves or preserves performance without unacceptable operational cost,
- remains useful across years and regions,
- does not depend on a limited external data source.

### Promote To Regional

A feature can become `accepted_regional` when it:

- clearly improves a specific region,
- is unstable or harmful nationally,
- has a defensible epidemiological explanation,
- can be governed by region-specific policy.

### Promote To Dashboard

A feature can become `accepted_dashboard` when it:

- improves interpretability or alert tiers,
- supports risk communication,
- does not necessarily improve F1,
- is reliable enough for explanatory display.

### Promote To Reference

A feature can become `accepted_reference` when it:

- is scientifically meaningful,
- is useful for benchmarking,
- has limited coverage or dependency risk,
- should not be required for national model operation.

### Reject

A feature should be `rejected` when it:

- creates leakage,
- lacks scientific meaning,
- is a misleading proxy,
- has poor coverage and no reliable use case,
- repeatedly fails validation and ablation.

### Escalate To Data Scout

A feature should become `future_data_needed` when:

- the hypothesis is scientifically plausible,
- current data cannot construct the feature,
- missing data may explain current model failures,
- external data can likely be obtained reproducibly.

Current first official Data Scout case:

- province-level terrain and elevation metadata for North-focused rice blast diagnostics.

## Registry Files

Current registry artifacts:

- `experiments/outputs/feature_registry_template.csv`
- `experiments/outputs/feature_registry_current.csv`

The template defines required columns. The current registry records preliminary governance status for active feature families.

## Operating Principle

The Feature Agent system should keep the rice blast platform scientifically interpretable. Feature additions are not accepted because they are available; they are accepted only when their biological rationale, temporal safety, validation evidence, ablation result, and governance decision are documented.
