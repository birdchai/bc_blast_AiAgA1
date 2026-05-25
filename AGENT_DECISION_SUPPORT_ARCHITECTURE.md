# Agent-Orchestrated Decision Support Architecture

## Purpose

This document defines the high-level AI Agent decision-support architecture for the rice blast forecasting platform. It integrates feature governance, model governance, decision governance, regional routing, missing-data escalation, explanation, and research reporting.

This is an architecture and governance design. It does not train models, tune thresholds, download data, process terrain, or modify the prediction pipeline.

## System Objective

The platform is designed to support:

- rice blast early warning,
- explainable decision support,
- region-aware model routing,
- biology-informed feature governance,
- evidence-based model governance,
- validation-only threshold and calibration governance,
- missing-data escalation,
- thesis, publication, and dashboard readiness.

The system should behave as an agent-governed plant disease decision-support platform, not a single forecasting script.

## Local AI Deployment Constraint

The initial agent system is intended to run on a local research laptop:

- MSI GS65 Stealth Thin 8RE
- GTX 1060 6GB
- RAM 24GB

Design guidance:

- Use one local quantized LLM as the shared reasoning core.
- Avoid multiple concurrent large LLM agents.
- Prefer sequential agent orchestration.
- Use Python scripts for computation-heavy tasks.
- Use Markdown and CSV registries as persistent agent memory.
- Keep agent outputs compact, auditable, and reproducible.
- Avoid unnecessary architecture search.
- Design for local reproducibility, not cloud-scale compute.

Operational implication:

- Agent roles are logical responsibilities, not necessarily separate always-on LLM processes.
- Heavy computation should remain in deterministic Python scripts.
- The LLM should coordinate, interpret, document, and govern decisions rather than run large-scale parallel model exploration.

## Current Governed Evidence

| model / evidence | governed role |
|---|---|
| DNN no-class-weight + `core_no_BUS` | stable nationwide default baseline |
| Random Forest + `core_no_BUS` | interpretable comparator / ranking reference |
| DNN class-weighted + `core_no_BUS` | recall-sensitive surveillance candidate |
| Hybrid DNN + TCN 2-week | temporal support model |
| DNN no-class-weight + analog history | Northeast monitoring / regional recall candidate |
| Random Forest + all analog | interpretable ranking / dashboard prioritization comparator |
| BUS-only rule baseline | external mechanistic reference |
| North region | unresolved diagnostic backlog |
| terrain/elevation | future-data-needed path |

## Major Agents

### A. Research Coordinator Agent

Responsibilities:

- Orchestrate the research workflow.
- Decide which agent acts next.
- Track research phase, evidence base, and backlog.
- Prevent the project from jumping from diagnostics to modeling without governance.
- Maintain consistency between thesis narrative, technical outputs, and current model roles.

Outputs:

- research phase decision,
- next-agent routing,
- backlog priority,
- research memory update request.

### B. Data Audit Agent

Responsibilities:

- Audit labels, coverage, missingness, and leakage risk.
- Audit updated data sources.
- Validate train/validation/test split readiness.
- Detect old-label vs corrected-label conflicts.
- Check whether a dataset is appropriate for supervised training, validation, or feature-only use.

Current scope:

- corrected `rice_blast_outbreak_weekly`,
- updated `weather_hourly`,
- updated `pov_rice_monthly`,
- BUS coverage,
- terrain source readiness,
- province boundary availability.

### C. Feature Agent

Responsibilities:

- Use biology-informed feature governance.
- Manage feature registry.
- Determine whether features are:
  - `accepted_core`,
  - `accepted_regional`,
  - `accepted_reference`,
  - `accepted_dashboard`,
  - `candidate_only`,
  - `rejected`,
  - `future_data_needed`.
- Ensure every feature has a rice blast biological or epidemiological interpretation.

Examples:

- leaf wetness represents infection moisture window,
- susceptibility represents host vulnerability,
- neighbor blast represents inoculum pressure,
- wind alignment represents directional dispersal hypothesis,
- analog history represents latent outbreak-regime memory,
- terrain/elevation represents microclimate and airflow hypothesis.

### D. Data Scout Agent

Responsibilities:

- Activate when missing evidence is detected.
- Evaluate external data sources before acquisition.
- Assess source quality, license, coverage, cost, resolution, and reproducibility.
- Produce recommendations before download or integration.

Current cases:

- terrain/elevation source scouting,
- province boundary source acquisition.

Rule:

- No external data should be downloaded or integrated without human approval.

### E. Model Agent

Responsibilities:

- Select model families appropriate to governed feature sets.
- Maintain the model registry.
- Prevent blind AutoML or leaderboard chasing.
- Enforce approved split policy.
- Ensure model complexity follows scientific need.
- Assign model lifecycle roles with evidence and caveats.

Current roles:

- stable default,
- interpretable comparator,
- recall-sensitive candidate,
- temporal support model,
- regional monitoring candidate,
- external reference.

### F. Decision Governance Agent

Responsibilities:

- Select thresholds using validation data only.
- Manage decision modes:
  - balanced default,
  - high precision,
  - high recall,
  - calibrated alert-tier dashboard,
  - ranking / prioritization,
  - diagnostic backlog.
- Separate binary operational decisions from risk communication.
- Evaluate calibration and alert tiers.
- Record threshold and policy decisions.

Rule:

- Test year is not used for threshold selection, calibration fitting, or model selection.

### G. Regional Routing Agent

Responsibilities:

- Route province-week predictions through the appropriate model/policy role.
- Apply region-specific caveats.
- Support Northeast enhanced monitoring.
- Mark North predictions as low confidence when appropriate.
- Preserve sparse-region caveats for Central, West, South, and low-positive contexts.

Routing principle:

- Region-specific behavior should be documented and governed, not hidden inside a single national score.

### H. Explanation Agent

Responsibilities:

- Summarize key contributing signals.
- Report:
  - weather and leaf wetness,
  - host susceptibility,
  - spatial / regional pressure,
  - analog history,
  - BUS/reference context when available,
  - decision policy,
  - caveats.
- Flag predictions with weak biological plausibility.
- Explain model agreement or disagreement.

Expected use:

- dashboard text,
- decision-support reports,
- research case reviews,
- extension communication.

### I. Report Writer Agent

Responsibilities:

- Write `RESEARCH_NOTES.md`.
- Maintain consolidation documents.
- Generate thesis-ready summaries.
- Produce dashboard interpretation notes.
- Preserve distinction between old-label methodology and corrected-label evidence.
- Document agent decisions and governance status.

## Current Model Registry Summary

| model | role | use |
|---|---|---|
| DNN no-class-weight `core_no_BUS` | stable default | primary nationwide model |
| RF `core_no_BUS` | interpretable comparator | ranking and feature-importance reference |
| DNN class-weighted `core_no_BUS` | recall-sensitive candidate | surveillance mode |
| Hybrid DNN + TCN 2-week | temporal support | temporal evidence, Northeast sensitivity |
| DNN analog history | regional monitoring | Northeast recall-sensitive second opinion |
| RF all analog | ranking/dashboard comparator | prioritization and alert-tier support |
| BUS-only rule | external reference | mechanistic benchmark, not dependency |

## Regional Routing Logic

### Nationwide Default

- Primary model: DNN no-class-weight `core_no_BUS`.
- Use balanced default policy unless an operational mode is specified.
- RF `core_no_BUS` may be used as an interpretable comparator.

### Northeast

- Use DNN `core_no_BUS` as the base model.
- Use DNN analog history as a regional recall-sensitive second opinion.
- Use RF all analog as a ranking/dashboard comparator.
- Flag disagreement between core and analog models for review.

Interpretation:

- Analog history is epidemiological similarity, not direct dispersal.
- Northeast gains should not be generalized nationally without evidence.

### North

- Use DNN `core_no_BUS` only with low-confidence caveat.
- Do not force threshold lowering to fix North failures.
- Route unresolved North cases to diagnostic backlog.
- Trigger terrain/elevation and boundary Data Scout paths when approved.

Interpretation:

- Current models systematically miss North positives.
- North requires diagnostic work before region-specific model acceptance.

### East, South, Central, West

- Use DNN `core_no_BUS` as default.
- Apply sparse-positive caveats where appropriate.
- Use RF comparator for ranking support if needed.
- Avoid over-interpreting regional F1 when positives are very sparse.

### Dashboard Mode

- Use calibrated alert tiers.
- Include model agreement/disagreement.
- Include region caveats.
- Include key biological signals and missing-data caveats.

## Decision Modes

| decision mode | purpose | primary use |
|---|---|---|
| balanced default | balance precision and recall | routine operational decision support |
| high precision field alert | reduce false positives | costly field verification contexts |
| high recall surveillance | reduce missed outbreaks | broad monitoring / early screening |
| calibrated alert tier dashboard | communicate graded risk | dashboard and extension communication |
| ranking / prioritization mode | order provinces/weeks by risk | resource prioritization |
| diagnostic backlog mode | flag unresolved model failures | research follow-up and missing-data escalation |

## Low-Confidence Rules

Flag a prediction or region as low confidence when one or more conditions hold:

- region is systematically missed by governed models,
- positives are sparse,
- biological signal is weak,
- critical external feature is missing,
- model disagreement is high,
- model predicts high risk without plausible disease context,
- label observation or data coverage is low,
- province or region has known unresolved diagnostic backlog.

Current low-confidence route:

- North-region outbreak prediction under corrected-label 2022 forward test.

## Human-Review Checkpoints

Human review is required before:

- external data acquisition,
- accepting a new core feature,
- replacing the default model,
- enabling a region-specific model route,
- publishing final performance claims,
- treating a missing-data hypothesis as confirmed,
- using a model operationally outside its governed role.

## Alert Output Schema

The decision-support layer should emit alert records with:

- province,
- region,
- year,
- week,
- primary model and score,
- alert tier,
- selected policy,
- secondary model and score,
- model agreement,
- key weather, host, spatial, analog, and BUS/reference signals,
- region caveat,
- confidence flag,
- recommended action category,
- explanation notes.

Schema file:

- `experiments/outputs/alert_output_schema.csv`

## Research Backlog

Current backlog:

- North terrain/elevation diagnostic,
- province boundary acquisition,
- terrain table preparation,
- North sub-regional seasonality,
- reporting density / label observation analysis,
- future terrain-feature association,
- future terrain-feature ablation,
- future region-specific governance,
- possible sub-provincial data integration.

## System Workflow

1. Data Audit Agent checks data source, labels, coverage, leakage, and split readiness.
2. Feature Agent governs features through biology-informed registry.
3. Data Scout Agent activates if required evidence is missing.
4. Model Agent chooses and governs model families for approved feature sets.
5. Decision Governance Agent selects thresholds/calibration using validation data only.
6. Regional Routing Agent applies model roles and caveats by region.
7. Explanation Agent generates signal-level interpretation and confidence flags.
8. Report Writer Agent updates research notes, consolidation docs, and thesis-ready summaries.

## Operating Principle

The system should make conservative, explainable, evidence-based decisions. It should not hide uncertainty. If the platform lacks the data needed to explain a failure, it should escalate to Data Scout or diagnostic backlog rather than forcing model thresholds or adding complexity without evidence.
