# Model Agent Specification

## Purpose

The Model Agent system formalizes how forecasting models are selected, trained, evaluated, governed, and registered in the rice blast AI research platform.

The purpose is not to automate blind model search. The purpose is to keep model development aligned with:

- governed feature sets,
- rice blast biology and plant epidemiology,
- temporal integrity,
- validation-only model and threshold selection,
- region-wise behavior,
- operational decision roles,
- interpretability,
- and overfitting risk.

The Model Agent system works alongside the Feature Agent, Data Scout Agent, and Decision Governance workflow. Feature governance determines which predictors are scientifically eligible. Model governance determines which model families are appropriate for those features and what operational role, if any, each model should hold.

## Current Research Context

The corrected-label forward-year split is the current reference evaluation setting:

- train: 2017-2020
- validation: 2021
- test: 2022
- target: `blast_t_plus_1`
- core feature policy: `core_no_BUS`

Current evidence:

- DNN no-class-weight + `core_no_BUS` is the stable nationwide default baseline.
- DNN + analog history improves Northeast recall/F1 but increases false positives.
- Random Forest + all analog has strong ranking metrics and interpretability.
- Hybrid DNN + TCN 2-week provides temporal support but does not replace the tabular baseline.
- DNN class-weighted can support recall-sensitive surveillance.
- BUS remains an external mechanistic reference, not a required model dependency.
- North remains a low-confidence diagnostic backlog and is not solved by current models.

## Model Agent Roles

### A. Model Scientist Agent

Responsibilities:

- Choose candidate model families based on feature type and hypothesis.
- Decide whether tabular, temporal, hybrid, or interpretable models are appropriate.
- Justify model choices scientifically.
- Avoid unnecessary model complexity.
- Ensure the model family is consistent with feature structure:
  - tabular current-week and rolling features,
  - temporal sequence features,
  - analog similarity features,
  - external mechanistic reference features,
  - sparse regional diagnostic problems.

Decision principle:

- Model complexity must follow scientific need, not curiosity or leaderboard chasing.

### B. Model Training Agent

Responsibilities:

- Train approved candidate models only.
- Use the approved train/validation/test split.
- Apply preprocessing using train-only fit.
- Preserve temporal integrity.
- Preserve province integrity for sequence construction.
- Export validation and test predictions.
- Save model training metadata.
- Record random seeds and class-weight policy when applicable.

Training rules:

- Do not fit preprocessing on validation or test data.
- Do not use test year for threshold selection.
- Do not mix weeks across provinces in temporal sequence models.
- Do not use future labels or current disease leakage columns as predictors.

### C. Model Evaluation Agent

Responsibilities:

- Evaluate:
  - precision,
  - recall,
  - F1,
  - ROC-AUC,
  - PR-AUC,
  - false positives,
  - false negatives,
  - confusion matrix.
- Analyze false-positive and false-negative patterns.
- Analyze region-wise behavior.
- Compare ranking performance against binary threshold behavior.
- Inspect calibration and alert-tier behavior when applicable.
- Identify whether a model is over-predicting, under-predicting, region-biased, or year-sensitive.

Evaluation principle:

- A model can have strong ranking metrics but still be unsuitable as a binary operational default.

### D. Model Governance Agent

Responsibilities:

- Assign model lifecycle status.
- Decide whether a model is:
  - stable default,
  - regional model,
  - recall-sensitive model,
  - high-precision model,
  - ranking comparator,
  - temporal support model,
  - external reference,
  - candidate only,
  - rejected,
  - future retest.
- Document rationale and caveats.
- Ensure region-specific gains are not misrepresented as nationwide gains.

Governance principle:

- A model may be useful even if it is not the default.

### E. Model Registry Agent

Responsibilities:

- Maintain model registry outputs.
- Record:
  - model family,
  - feature set,
  - split,
  - metrics,
  - thresholds,
  - calibration policy,
  - region behavior,
  - accepted role,
  - caveats,
  - last tested step.
- Keep model roles synchronized with Feature Agent and Decision Governance outputs.
- Update registry whenever a model is retested under a new label source, split, feature set, or threshold policy.

## Model Lifecycle Statuses

| status | meaning |
|---|---|
| proposed | Model idea is defined but not trained. |
| trained | Model has been trained using an approved split. |
| validated | Validation-year results have been produced. |
| evaluated | Held-out test-year evaluation has been produced. |
| calibrated | Calibration or threshold policy has been evaluated using validation data. |
| governed | Governance decision has been recorded. |
| accepted_default | Stable default operational baseline. |
| accepted_regional | Accepted for region-specific monitoring or use. |
| accepted_ranking | Accepted as ranking, prioritization, or dashboard comparator. |
| accepted_temporal_support | Accepted as temporal evidence/support model, not default. |
| accepted_recall_sensitive | Accepted for surveillance or recall-sensitive policy. |
| accepted_reference | Accepted as external reference or mechanistic benchmark. |
| candidate_only | Retained for comparison but not recommended operationally. |
| rejected | Not useful, unsafe, leaky, or unjustified under current evidence. |
| future_retest | Worth retesting after data, labels, features, or split changes. |

## Required Model Metadata

Every model registry row must include:

| field | description |
|---|---|
| model_name | Human-readable model identifier. |
| model_family | DNN, Random Forest, XGBoost, GRU, TCN, hybrid, rule baseline, etc. |
| feature_set | Governed feature set used by the model. |
| target | Target label. |
| split | Train/validation/test split description. |
| train_years | Training years. |
| validation_year | Validation year. |
| test_year | Test year. |
| preprocessing | Imputation, scaling, encoding, or sequence construction policy. |
| class_weight_policy | None, class-weighted, or other imbalance policy. |
| threshold_policy | Validation-selected threshold or policy. |
| calibration_policy | None, Platt, isotonic, alert-tier, or other calibration policy. |
| precision | Test precision under governed threshold/policy. |
| recall | Test recall under governed threshold/policy. |
| f1 | Test F1 under governed threshold/policy. |
| roc_auc | Test ROC-AUC. |
| pr_auc | Test PR-AUC. |
| false_positives | Test false positives. |
| false_negatives | Test false negatives. |
| region_strengths | Regions where model is useful. |
| region_failures | Regions where model fails or is unstable. |
| biological_plausibility_check | Whether predictions/features align with disease context. |
| interpretability_level | High, medium, low. |
| operational_role | Default, regional, ranking, surveillance, temporal support, reference, candidate, rejected. |
| governance_status | Current model lifecycle status. |
| caveats | Known limitations. |
| last_tested_step | Most recent research step that tested the model. |

## Candidate Model Policy

Model family should be selected based on feature type:

| feature type | candidate model families | governance caution |
|---|---|---|
| tabular core features | DNN, Random Forest, XGBoost | prefer stable simple models before complex architectures |
| analog history features | DNN, Random Forest | monitor false positives and regional overfitting |
| high-dimensional analog/statistical features | Random Forest, XGBoost, controlled DNN | avoid all-feature expansion without feature governance |
| temporal sequence features | TCN, GRU, Hybrid DNN+TCN | preserve province-wise sequence integrity |
| mechanistic reference features | rule baseline, simple logistic, reference-only benchmark | do not treat reference features as target labels |
| sparse regional problem | simple interpretable diagnostics first | avoid complex deep models unless positive sample size is sufficient |

## Anti-Overfitting Rules

- Do not select models based on test-year metrics alone.
- Use validation year for model selection, thresholds, calibration, and policy.
- Test year is held out for final evaluation only.
- Avoid trying many architectures without a hypothesis.
- More complex models must show meaningful operational improvement, not tiny metric gains.
- Region-specific gains must be documented separately from nationwide gains.
- If a complex model does not beat a simpler baseline, it should remain `candidate_only`, `accepted_temporal_support`, or `future_retest`, not default.
- A model that improves recall but creates many false positives should be considered regional, surveillance, or dashboard support rather than stable default.

## Biology and Epidemiology Plausibility Checks

Model predictions should be inspected against rice blast disease context:

- leaf wetness / humidity suitability,
- temperature suitability,
- host susceptibility,
- inoculum / neighbor pressure,
- spatial or regional outbreak pressure,
- temporal accumulation,
- wind/spatial context,
- analog outbreak history,
- region-specific caveats,
- reporting and observation limitations.

Review rules:

- If a model predicts high risk without plausible disease context, flag the model for review.
- If a model misses a region systematically, create a diagnostic backlog rather than forcing thresholds.
- If a model learns a feature that is biologically weak but statistically strong, return the feature to Feature Governance for review.
- If a model depends on coverage-limited reference features, govern it as reference or candidate, not nationwide default.

## Model-Role Decision Rules

| evidence pattern | governance decision |
|---|---|
| Best or strong F1 with acceptable FP/FN balance and stable interpretation | `accepted_default` |
| Best F1 but too many false positives | regional, recall-sensitive, or candidate; not default |
| High ROC-AUC/PR-AUC and interpretability | `accepted_ranking` or dashboard support |
| Improves one region only | `accepted_regional` |
| Supports temporal interpretation but does not beat tabular baseline | `accepted_temporal_support` |
| Biologically plausible but coverage-limited | `accepted_reference` |
| Complex and does not beat simpler baseline | `candidate_only`, `future_retest`, or `rejected` |
| Systematically fails a region | diagnostic backlog rather than threshold forcing |

## Current Model Governance Summary

| model | feature set | current role |
|---|---|---|
| DNN no-class-weight | `core_no_BUS` | stable nationwide default baseline |
| Random Forest | `core_no_BUS` | interpretable comparator / ranking reference |
| DNN class-weighted | `core_no_BUS` | recall-sensitive surveillance candidate |
| Hybrid DNN + TCN 2-week | `core_no_BUS` temporal sequences | temporal support model, especially Northeast-sensitive evidence |
| DNN no-class-weight | `core_plus_analog_history` | Northeast monitoring / regional recall candidate |
| Random Forest | all analog | interpretable ranking / dashboard prioritization comparator |
| XGBoost | `core_no_BUS` | classical ML comparator / candidate only |
| BUS-only rule baseline | BUS reference features | external mechanistic reference, not model dependency |

## Model Agent Interaction With Other Agents

### Feature Agent

- Governs feature eligibility.
- Defines biological rationale and leakage risk.
- Determines whether a feature set is core, regional, reference, dashboard, candidate, rejected, or future-data-needed.

### Model Agent

- Chooses models appropriate for governed feature sets.
- Trains and evaluates models under approved splits.
- Assigns model roles based on evidence, not leaderboard position alone.

### Decision Governance Agent

- Selects thresholds using validation data only.
- Evaluates calibration and alert tiers.
- Defines operational modes such as balanced, high precision, high recall, and dashboard risk tiers.

### Data Scout Agent

- Activates when model failures indicate missing explanatory data.
- Example: North-region failures triggered terrain/elevation scouting.

### Report Writer Agent

- Summarizes findings for thesis, proposal, publication, and project memory.
- Ensures old-label and corrected-label evidence are clearly distinguished.

## Operating Principle

The Model Agent system prevents model development from becoming AutoML-like leaderboard chasing. Models are selected because they fit a governed feature set and a scientific question. A model is accepted only when its evidence, operational role, biological plausibility, temporal integrity, and regional behavior are documented.
