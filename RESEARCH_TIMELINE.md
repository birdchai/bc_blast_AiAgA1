# Research Timeline: Thailand Rice Blast Epidemiology System

This document records the scientific progression of the rice blast epidemiology
research project. It is intended for thesis, proposal, publication, and
methodology writing. The focus is on evolving hypotheses, explainable modeling
decisions, empirical findings, limitations, and next research directions.

---

## Step 1: Project Foundation and Multi-Agent Architecture

### Objective

Establish a local AI-assisted research system for rice blast epidemiology,
including agent orchestration, reasoning refinement, and modular research
workflows.

### Hypothesis

A multi-agent workflow can support scientific reasoning more effectively than a
single chatbot-style interaction, especially when the task requires planning,
critique, and iterative refinement.

### Methods

- Set up a local Python research environment.
- Integrated AutoGen-style agent components.
- Connected local LLM execution through Ollama using `qwen2.5:7b`.
- Created early research agents:
  - planner agent
  - critic agent
  - orchestrator agent
- Tested reasoning workflows:
  - planner response
  - critic feedback
  - planner refinement
- Organized the project into modular directories:
  - `agents/`
  - `tools/`
  - `experiments/`
  - `workflows/`

### Implemented Features

- Planner-critic refinement loop
- Initial orchestrator structure
- Tool integration pattern for scientific functions
- Local report generation workflow
- English-first reasoning workflow

### Datasets Used

- No full epidemiological dataset was required at this stage.
- Small tool-level examples were used to test agent behavior.

### Validation Strategy

- Verified that local agents could execute.
- Tested planner-critic-planner refinement.
- Compared runtime behavior with and without translation.
- Checked whether tool outputs could be injected into the reasoning workflow.

### Findings

- The multi-agent loop worked as a research reasoning structure.
- Critic feedback improved the clarity of planner reasoning.
- Translation inside the main loop created unnecessary latency.
- Local LLM execution was feasible but required performance-aware workflow
  design.

### Interpretation

The project should use AI agents as a reasoning and orchestration layer, not as
the primary computation layer. Scientific computation should remain in explicit
tools, while agents interpret, critique, and plan around tool outputs.

### Limitations

- Local LLM latency limits complex multi-agent loops.
- Translation should not be part of the main research reasoning path.
- Agent reasoning must be grounded in explicit data outputs to avoid unsupported
  claims.

### Next Direction

Build robust data pipelines before expanding the agent workflow further.

---

## Step 2: Weather Data Pipeline

### Objective

Create a reliable hourly-to-weekly weather data pipeline for all Thai provinces
across multiple years.

### Hypothesis

Weather data contain the primary environmental signal for rice blast infection,
but the signal can only be evaluated after consistent cleaning, datetime
parsing, and temporal aggregation.

### Methods

- Loaded large numbers of hourly weather CSV files.
- Standardized key weather columns:
  - `temperature`
  - `humidity`
  - `rainfall`
  - wind-related variables where available
- Parsed raw datetime strings into a consistent datetime format.
- Cleaned missing or invalid records.
- Aggregated hourly records into province-week summaries.
- Verified year and province coverage.

### Implemented Features

- Province-level hourly weather table
- Province-week weather table
- Weekly summaries:
  - mean temperature
  - mean humidity
  - rainfall sum
  - observed hour counts

### Datasets Used

- Hourly weather data, 2015-2022
- 77 provinces

### Validation Strategy

- Checked total files loaded.
- Checked row counts and weekly aggregation shape.
- Verified datetime year distribution.
- Verified province coverage.

### Findings

- Weather coverage was sufficient for nationwide analysis.
- Rainfall values of zero were interpreted as no rain rather than missing rain.
- The hourly weather dataset contains rich temporal information for mechanistic
  infection modeling.

### Interpretation

The weather data are suitable for mechanistic epidemiology, especially for
hourly infection-hour logic and weekly risk aggregation.

### Limitations

- Some weather variables are missing in some hours.
- Rainfall alone is unlikely to represent leaf wetness adequately.
- Raw weather columns must be preserved carefully because later hypotheses may
  require variables not used in the first baseline.

### Next Direction

Integrate rice variety data to represent host composition.

---

## Step 3: Plant Variety Data Integration

### Objective

Transform rice planting variety data into a usable host-composition layer for
epidemiological modeling.

### Hypothesis

Rice blast risk depends not only on weather but also on the susceptibility of
the planted rice varieties in each province and season.

### Methods

- Loaded in-season and off-season POV datasets.
- Handled Thai text encoding using `cp874`.
- Converted wide variety columns into long format.
- Computed variety area ratios per province-date.
- Preserved season labels for later susceptibility analysis.

### Implemented Features

- `season`
- `variety`
- `area`
- `ratio`
- long-format POV table
- weekly variety-ratio table

### Datasets Used

- In-season rice POV data, 2015-2021
- Off-season rice POV data, 2015-2021

### Validation Strategy

- Read representative province-year files.
- Verified Thai variety column decoding.
- Checked long-format transformation.
- Checked that positive area values were retained and ratios could be computed.

### Findings

- Rice variety composition varies by province and season.
- Variety structure contains meaningful epidemiological signal.
- Host composition became a necessary candidate layer for later modeling.

### Interpretation

POV data provide a biologically meaningful host layer. They should be integrated
after a weather baseline is established, not used as an opaque predictor.

### Limitations

- Variety susceptibility was not known directly and had to be inferred from
  stability analysis.
- Variety effects may be region-specific.
- Area ratios represent planted distribution, not necessarily crop growth stage
  or phenological susceptibility.

### Next Direction

Construct weekly disease labels for validation.

---

## Step 4: Blast Disease Label Construction

### Objective

Create weekly province-level disease labels suitable for validating risk
features and mechanistic hypotheses.

### Hypothesis

Daily or expanded blast occurrence data can be transformed into weekly labels
that align with weather and POV features.

### Methods

- Loaded blast disease CSV files by province and year.
- Parsed dates into a common datetime format.
- Converted positive blast values into binary occurrence.
- Aggregated daily values into weekly province-level labels.

### Implemented Features

- `blast_any`
- `blast_days`
- `observed_days`

### Datasets Used

- Blast disease data, 2015-2021

### Validation Strategy

- Inspected representative files.
- Verified date parsing.
- Checked weekly disease counts by year.
- Checked join compatibility with weekly weather data.

### Findings

- Disease labels are highly imbalanced.
- 2015 contains no positive disease weeks.
- 2016 contains very few positive disease weeks.
- Stronger disease signals appear from 2017 onward.

### Interpretation

The validation dataset is usable, but early years must be treated as weak-label
or low-information years. Evaluation must report disease-week coverage, not only
aggregate metrics.

### Limitations

- Positive values may represent magnitude or affected area, but were initially
  converted to binary occurrence.
- Sparse labels make precision and F1 unstable in low-disease years.
- Disease reporting quality may vary by province and year.

### Next Direction

Develop interpretable infection logic from hourly weather.

---

## Step 5: Mechanistic Infection Logic Preparation

### Objective

Prepare biologically interpretable infection logic from hourly weather before
building formal validation models.

### Hypothesis

Rice blast infection risk should emerge from accumulated favorable hourly
conditions, especially high humidity and suitable temperature.

### Methods

- Defined favorable and optimal temperature ranges.
- Defined humidity thresholds.
- Created hourly infection indicators.
- Developed early leaf wetness proxy logic.
- Prepared rolling temporal accumulation concepts.

### Implemented Features

- infection hours
- favorable humidity conditions
- favorable temperature conditions
- leaf wetness proxy
- rolling accumulation framework

### Datasets Used

- Hourly weather data
- Weekly blast labels for early exploratory validation

### Validation Strategy

- Checked whether infection-hour features could be aggregated weekly.
- Compared early weather-derived features with weekly blast occurrence.
- Examined false positives and weak signal behavior.

### Findings

- Weather-only features contain some signal.
- Humidity-related features are more consistently informative than rainfall.
- False positives remain high under weather-only logic.
- Temporal accumulation appears biologically important.

### Interpretation

Mechanistic infection logic is a necessary baseline, but it cannot explain
national disease occurrence alone. Host, spatial, and regional components are
needed.

### Limitations

- Infection thresholds were conservative and exploratory.
- Leaf wetness was estimated indirectly from humidity and temperature.
- No host susceptibility or inoculum pressure was included yet.

### Next Direction

Formalize the weather-only mechanistic baseline and validate it nationally.

---

## Step 6: Weather Baseline

### Objective

Create a mechanistic weather-only baseline for rice blast infection risk.

### Hypothesis

Rice blast risk should increase under favorable temperature and high humidity.
Rainfall may contribute, but humidity is expected to be more directly relevant
to infection conditions.

### Methods

- Defined hourly infection conditions from weather variables.
- Aggregated hourly infection indicators into weekly risk features.
- Created a simple risk score using interpretable weights.
- Compared weekly risk against weekly blast occurrence.

### Implemented Features

- `temp_favorable`
- `temp_optimal`
- `humidity_favorable`
- `humidity_optimal`
- `favorable_hour`
- `optimal_hour`
- `infection_ratio`
- `optimal_ratio`
- `humidity_ratio`
- `rainfall_ratio`
- `risk_score`
- `risk_level`

### Datasets Used

- Hourly weather
- Weekly blast labels

### Validation Strategy

- Threshold sweep
- Lag sweep
- Nationwide validation by year
- Metrics:
  - precision
  - recall
  - F1
  - false positives
  - false negatives
  - correlation

### Findings

- Province-year samples showed some weather signal.
- Nationwide validation showed weak generalization.
- Weather-only models produced many false positives.

### Interpretation

Weather favorability is necessary but not sufficient. Rice blast occurrence
cannot be explained by weather alone at the national scale.

### Limitations

- No host susceptibility.
- No inoculum pressure.
- No spatial disease pressure.
- No regional differentiation.

### Next Direction

Add temporal accumulation and leaf wetness proxy features.

---

## Step 6.1: Temporal Accumulation and Leaf Wetness

### Objective

Test whether accumulated favorable conditions improve epidemiological signal.

### Hypothesis

Rice blast infection risk may depend not only on current-week weather but also
on accumulated infection pressure over recent weeks.

### Methods

- Added weekly leaf wetness proxy based on humidity and suitable temperature.
- Added rolling 2-week and 3-week cumulative weather risk.
- Added rolling infection-hour and leaf-wet-hour summaries.

### Implemented Features

- `leaf_wet_hours`
- `leaf_wet_ratio`
- `rolling_2w_risk`
- `rolling_3w_risk`
- `rolling_2w_infection_hours`
- `rolling_3w_infection_hours`
- `rolling_2w_leaf_wet_hours`
- `rolling_3w_leaf_wet_hours`

### Datasets Used

- Hourly weather
- Weekly blast labels

### Validation Strategy

- Compared weekly risk and rolling risk scores.
- Ran nationwide validation for 2017.
- Examined precision, recall, F1, and false positives.

### Findings

- Rolling accumulation sometimes reduced false positives at higher thresholds.
- Recall dropped sharply when thresholds were raised.
- Rolling scores did not consistently outperform the original weather baseline.

### Interpretation

Temporal accumulation captures biologically plausible exposure, but weather-only
temporal accumulation remains insufficient at national scale.

### Limitations

- No host or inoculum signal.
- Rolling windows were simple and not optimized.
- Accumulation may differ by region or crop calendar.

### Next Direction

Incorporate host susceptibility from rice variety distribution.

---

## Step 7: Host Susceptibility

### Objective

Test whether rice variety distribution explains additional disease occurrence
beyond weather conditions.

### Hypothesis

Provinces with higher proportions of susceptible rice varieties should have
higher blast occurrence under similar weather conditions.

### Methods

- Performed multi-year feature-effect stability analysis for rice varieties.
- Assigned conservative susceptibility weights based on stability.
- Computed province-week susceptibility scores from variety area ratios.
- Created host-weighted risk scores.

### Implemented Features

- `susceptibility_score`
- `host_modifier`
- `host_weighted_risk`
- `host_weighted_rolling_2w`
- `host_weighted_rolling_3w`

### Datasets Used

- Rice POV data
- Weekly weather risk
- Weekly blast labels

### Validation Strategy

- Multi-year feature-effect stability, 2015-2021
- Host-weighted validation, 2015-2021
- Comparison against weather-only scores

### Findings

Stable positive variety candidates included:

- offseason `พิษณุโลก2,60-2`
- inseason `กข15`
- inseason `ขาวดอกมะลิ105`

`กข6` was not stable nationally and was therefore kept at the default weight.

Host-weighted validation:

- Improved F1 in 4 of 5 meaningful years when excluding 2015 and 2016.
- Improvements were modest.
- 2021 did not improve.

### Interpretation

Host susceptibility is a useful explanatory layer, but national variety weights
are not sufficient for all years or regions.

### Limitations

- Weights are conservative and experimental.
- Variety effects are associations, not causal estimates.
- Regional variety behavior may differ.

### Next Direction

Test whether spatial disease pressure improves prediction.

---

## Step 8: Spatial Epidemiology

### Objective

Evaluate whether neighboring province disease pressure improves validation.

### Hypothesis

Rice blast occurrence may be influenced by nearby disease pressure due to
regional inoculum availability and spatially correlated environments.

### Methods

- Computed province centroids from latitude and longitude.
- Computed province-to-province haversine distances.
- Defined top 5 nearest neighboring provinces.
- Created previous-week neighbor pressure features.
- Combined host-weighted weather risk with neighbor risk conservatively.

### Implemented Features

- `neighbor_prevweek_risk`
- `neighbor_prevweek_blast`
- `spatial_host_weather_risk`

Combined score:

```text
spatial_host_weather_risk =
    0.7 * host_weighted_risk
  + 0.3 * neighbor_prevweek_risk
```

### Datasets Used

- Province coordinates from POV data
- Weekly weather risk
- Weekly host susceptibility
- Weekly blast labels

### Validation Strategy

- Nationwide validation, 2017-2021
- Compared:
  - weather-only
  - host-weighted
  - spatial-host-weather

### Findings

- Spatial-host-weather improved over weather-only in 4 of 5 years.
- It improved over host-weighted in only 2 of 5 years.
- Neighbor blast pressure appeared informative, but simple distance-only
  aggregation did not consistently beat host-weighted rolling features.

### Interpretation

Spatial pressure contains useful signal, but distance-only adjacency is too
coarse to fully represent inoculum movement.

### Limitations

- Neighbor definition uses distance only.
- No wind direction or transport mechanism included.
- No region-specific spatial weighting.

### Next Direction

Explore wind as a potential mechanism for spatial disease connectivity.

---

## Step 8.5: Wind Exploration

### Objective

Assess whether wind-related weather variables contain useful epidemiological
signal before building a wind-mediated spatial model.

### Hypothesis

Wind speed and direction may help explain spatial rice blast spread because
spores can disperse through air movement.

### Methods

- Extended weather extraction to include wind variables.
- Created weekly wind features.
- Ran feature-effect and stability analysis, 2015-2021.
- Compared wind features with humidity, leaf wetness, weather risk, host risk,
  and spatial pressure features.

### Implemented Features

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

### Datasets Used

- Hourly weather with wind columns
- Weekly blast labels
- Existing host and spatial feature tables

### Validation Strategy

- Association analysis only
- Multi-year stability
- No risk-score modification

### Findings

- Simple wind speed did not show strong positive association with blast.
- Wind speed and direction variability were often lower in disease weeks.
- Humid-wind and leaf-wet-wind features were mixed across years.

### Interpretation

Simple wind-speed epidemiology is insufficient. Wind may matter only when
combined with infected neighboring sources and directional connectivity.

### Limitations

- Wind was summarized at province-week level.
- Wind direction was not yet connected to infected source provinces.
- No directional transport model was used.

### Next Direction

Test directional wind alignment from infected neighbors.

---

## Step 8.7: Directional Wind Alignment

### Objective

Test whether wind direction aligned with infected neighboring provinces contains
epidemiological signal.

### Hypothesis

Blast pressure from a neighboring province should be more relevant when the
prevailing wind direction is aligned from the infected neighbor toward the target
province.

### Methods

- Computed bearing from each neighbor province to target province.
- Compared bearing with weekly prevailing wind direction.
- Defined wind alignment using a conservative angular tolerance.
- Combined alignment with previous-week neighbor blast occurrence.

### Implemented Features

- `bearing_neighbor_to_province`
- `wind_alignment_angle`
- `wind_aligned_neighbor_blast`
- `wind_aligned_neighbor_count`

### Datasets Used

- Province centroids
- Weekly wind direction
- Weekly blast labels
- Top 5 nearest neighbors

### Validation Strategy

- Association analysis only
- Multi-year stability
- No risk-score modification

### Findings

- `wind_aligned_neighbor_blast` was positive in 4 of 6 observed years.
- Strongest positive signals appeared in 2018, 2020, and 2021.
- 2017 was slightly negative.
- 2016 had too few disease weeks to trust.

### Interpretation

Directional wind-mediated neighbor infection has meaningful exploratory signal,
but it is not stable enough yet to modify the risk score nationally.

### Limitations

- Uses weekly prevailing wind direction.
- Uses a fixed alignment tolerance.
- Does not model wind persistence, source intensity, or distance decay.

### Next Direction

Analyze whether spatial, host, and wind effects differ by region.

---

## Step 8.8: Regional Epidemiology

### Objective

Test whether rice blast epidemiological behavior differs by region.

### Hypothesis

A single national mechanistic score may be too coarse because weather regimes,
rice varieties, host susceptibility, and spatial disease processes differ across
regions.

### Methods

- Defined broad Thai regions:
  - North
  - Northeast
  - Central
  - East
  - West
  - South
- Ran feature-effect analysis by region and year.
- Ran validation by region and score family.
- Compared host, spatial, wind, and weather features across regions.

### Implemented Features

- `region`
- Region-level feature-effect summaries
- Region-level validation summaries

### Datasets Used

- Weekly weather risk
- Weekly host susceptibility
- Weekly spatial pressure
- Weekly wind alignment
- Weekly blast labels

### Validation Strategy

- Region-year validation
- Comparison of:
  - weather-only
  - host-weighted
  - spatial-host-weather

### Findings

Disease burden was concentrated in:

- Northeast
- North
- South
- East

Host effects were strongest in:

- Northeast
- East

Spatial pressure was strongest in:

- Northeast

Directional wind alignment was most promising in:

- Northeast

### Interpretation

Rice blast epidemiology is regionally heterogeneous. Northeast is the strongest
candidate for spatial and wind-mediated modeling. East appears more strongly
host-susceptibility driven.

### Limitations

- Regional grouping is broad.
- West has too few disease weeks for reliable inference.
- Some regions show sparse disease occurrence in early years.

### Next Direction

Prepare region-aware temporal datasets for future sequence forecasting.

---

## Step 8.9: Region-Aware Temporal Sequence Preparation

### Objective

Prepare explainable temporal epidemiological features and sequence-ready datasets
for future hybrid mechanistic and LSTM forecasting.

### Hypothesis

Future blast occurrence may be better represented by region-aware temporal
pressure features than by isolated province-week risk scores.

### Methods

- Combined weather, host, spatial, wind, and regional features.
- Created region-aware temporal pressure features.
- Added future target labels.
- Exported sequence-ready province-week dataset.
- Performed exploratory correlation and temporal consistency analysis.

### Implemented Features

- `regional_neighbor_pressure_2w`
- `regional_neighbor_pressure_3w`
- `regional_leaf_wet_accumulation`
- `regional_host_pressure`
- `regional_wind_alignment_frequency`
- `blast_t_plus_1`
- `blast_t_plus_2`

### Datasets Used

- Weekly weather risk
- Weekly host susceptibility
- Weekly spatial pressure
- Weekly wind alignment
- Weekly blast labels
- Regional mapping

### Validation Strategy

- Exploratory feature-effect analysis against:
  - `blast_t_plus_1`
  - `blast_t_plus_2`
- Temporal consistency by region
- Feature coverage checks

### Findings

The sequence-ready dataset contains:

- 28,503 rows
- 38 columns
- 77 provinces
- 6 regions
- 1,153 positive `blast_t_plus_1` labels
- 1,130 positive `blast_t_plus_2` labels

Strong future-signal patterns:

- Northeast:
  - regional wind alignment frequency
  - regional neighbor pressure
  - susceptibility score
- East:
  - susceptibility score
  - host-weighted rolling risk
- North:
  - regional neighbor pressure
  - regional wind alignment
- South:
  - regional pressure signal, but fewer observed disease years

### Interpretation

The project now has an explainable sequence-ready epidemiological dataset
suitable for future hybrid mechanistic and LSTM experiments.

### Limitations

- No ML has been introduced yet.
- Sequence features are not optimized.
- Future labels remain imbalanced.
- Regional pressure features are still broad and may require more refined
  agro-climatic zoning.

### Next Direction

Before training sequence models, build transparent non-ML temporal baselines and
document expected behavior by region.
