# Data Scout Agent Specification

## Purpose

The Data Scout Agent is activated when a scientifically useful feature cannot be constructed from current project data. Its role is to identify, evaluate, and recommend external data sources before any download, purchase, or integration occurs.

The Data Scout Agent does not train models and does not modify the prediction pipeline. It prepares evidence for a data-acquisition decision.

## Trigger Conditions

Activate the Data Scout Agent when at least one condition is true:

- A validated research hypothesis requires a feature not present in current data.
- A model failure pattern suggests a missing environmental, host, spatial, or reporting variable.
- Existing proxy variables are scientifically inappropriate.
- Coverage limitations prevent a feature from becoming a national dependency.
- A future thesis or publication claim requires an independently reproducible external source.

Current official trigger:

- North-region failures remain unresolved, and terrain/microclimate is a plausible missing explanatory layer.
- Updated `weather_hourly` has no direct elevation or terrain fields.
- `sealevelpressure` is sea-level adjusted and should not be used as an elevation proxy.

## Search Workflow

1. Define missing feature need.
2. Define minimum spatial and temporal resolution.
3. Identify candidate data sources.
4. Check source quality and provenance.
5. Check license, cost, and usage restrictions.
6. Check geographic coverage for Thailand and all 77 provinces.
7. Check whether data can be processed reproducibly.
8. Propose an input-file schema.
9. Request approval before download, purchase, or integration.
10. After approval, create an audit script and coverage report before modeling.

## Dataset Evaluation Rubric

| criterion | evaluation question |
|---|---|
| scientific relevance | Does the source directly support the missing feature hypothesis? |
| spatial resolution | Is the resolution sufficient for province-level summaries? |
| temporal resolution | Is the dataset static or temporal, and does that match the feature need? |
| coverage | Does it cover all provinces and all required years if temporal? |
| provenance | Is the source authoritative and traceable? |
| license | Can it be used for research, thesis, and publication? |
| cost | Is it free, paid, or restricted? |
| reproducibility | Can another researcher reproduce the extraction? |
| processing burden | Is GIS/raster processing required? |
| integration risk | Are province names, boundaries, projection, or units likely to cause errors? |

## Source Recommendation Template

Each candidate source should be documented as:

| field | description |
|---|---|
| source_name | Dataset or provider name. |
| provider | Organization or platform. |
| url_or_access_path | Official access point, if available. |
| data_type | Raster, vector, table, API, station metadata, or report. |
| resolution | Spatial/temporal resolution. |
| coverage | Geographic and year coverage. |
| license | License and usage limitations. |
| cost | Free, paid, or restricted. |
| expected_features | Features that can be derived. |
| processing_steps | Required transformation before use. |
| risks | Known limitations or integration risks. |
| recommendation | Use, inspect further, avoid, or reserve as fallback. |

## Approval Checkpoint

The Data Scout Agent must request explicit approval before:

- downloading external datasets,
- purchasing or accessing paid datasets,
- adding large external files to local storage,
- integrating external features into the main dataset,
- changing model or feature pipeline behavior.

Before approval, the agent may create:

- source comparison tables,
- proposed schemas,
- metadata templates,
- non-executed processing plans.

## Expected Output Files

For each scouting case:

- `data_scout_<topic>_source_candidates.csv`
- `data_scout_<topic>_recommendation.md`
- `<topic>_input_template.csv`
- `<topic>_audit_plan.md`

For terrain/elevation:

- `province_terrain_table.csv`
- `province_terrain_source_candidates.csv`
- `province_terrain_audit_summary.csv`

## First Data Scout Case: Province Terrain / Elevation

### Reason

North-region rice blast positives in 2022 remain missed by all major model candidates. The failures are concentrated in Lamphun, Nan, Phichit, and Nakhon Sawan. Current weather, host, spatial, analog, temporal, and calibration features do not solve this pattern.

Terrain and microclimate are plausible missing explanatory layers because topography can affect:

- humidity persistence,
- dew formation,
- local airflow,
- temperature gradients,
- rice field microclimates,
- reporting and production geography.

### Missing Data

Required province-level terrain fields:

- `province`
- `elevation_mean`
- `elevation_min`
- `elevation_max`
- `elevation_range`
- `elevation_std`
- `terrain_roughness`
- `source`
- `notes`

### Candidate External Data Sources

Initial candidates:

- SRTM DEM
- Copernicus DEM
- ASTER GDEM
- Thai government GIS / DEM sources
- Commercial DEM products if free/public sources are insufficient

### Expected Output

Primary expected integration file:

- `province_terrain_table.csv`

This should be audited before modeling:

- province-name matching,
- missingness,
- unit consistency,
- elevation summary plausibility,
- source reproducibility,
- static-feature leakage safety.

## Governance Rule

Data Scout output is advisory until approved. A scouted data source does not become part of the model pipeline until it passes:

- source approval,
- schema audit,
- coverage audit,
- leakage review,
- feature validation,
- controlled ablation,
- governance decision.
