# Hypothesis Evolution: Thailand Rice Blast Epidemiology System

This document records how the project's scientific hypotheses evolved in
response to evidence. It is intended to support thesis, proposal, and
publication writing by showing that the research direction changed through
empirical findings rather than arbitrary model choices.

---

## Overview

The project began as a weather-driven rice blast prediction system. Through
successive experiments, the evidence showed that weather is necessary but not
sufficient. The research gradually evolved toward a broader computational plant
epidemiology platform combining:

- mechanistic weather infection logic
- temporal accumulation
- host susceptibility
- spatial inoculum pressure
- wind-mediated connectivity
- regional epidemiological heterogeneity
- sequence-ready temporal forecasting data

---

## Hypothesis Evolution Table

| Stage | Initial Hypothesis | Evidence / Result | Refined Hypothesis |
|---|---|---|---|
| Weather-only baseline | Weather conditions explain rice blast occurrence. | Weather features showed signal, but national validation was weak and false positives were high. | Weather is necessary but insufficient; additional biological and spatial context is required. |
| Humidity vs rainfall | Rainfall may be a major driver of blast risk. | Humidity and leaf-wetness proxies were more stable than rainfall. | Humidity-driven leaf wetness is more mechanistically useful than rainfall alone. |
| Temporal accumulation | Current-week weather may be enough for prediction. | Rolling 2-week and 3-week features sometimes improved signal but did not solve false positives. | Infection risk should include accumulated favorable conditions, but accumulation alone is insufficient. |
| Host susceptibility | Rice variety composition modifies disease risk. | Stable positive variety effects appeared for some varieties, but others were unstable. | Host susceptibility is useful, but must be conservative and may be region-specific. |
| `กข6` susceptibility | `กข6` may be globally susceptible. | Multi-year stability showed `กข6` was positive in some years and negative in others. | `กข6` should remain default/unknown until region- or context-specific analysis supports otherwise. |
| National susceptibility weights | One national host-weight table can improve prediction everywhere. | Host-weighted scores improved several years but not all; 2021 was a warning case. | Host effects exist, but national weights are incomplete and likely region-dependent. |
| Distance-only spatial pressure | Nearby provinces explain spatial disease pressure. | Spatial-host-weather improved over weather-only in many years but did not consistently beat host-weighted rolling features. | Neighbor pressure matters, but distance-only adjacency is too coarse. |
| Simple wind speed | Stronger wind should spread blast more. | Simple wind-speed features were weak and often negative. | Wind speed alone is insufficient; direction and infected source context matter. |
| Directional wind alignment | Wind aligned from infected neighbors may contain signal. | `wind_aligned_neighbor_blast` showed positive signal in several years, especially 2018, 2020, and 2021. | Wind-mediated spatial connectivity is promising, but should be modeled directionally and conservatively. |
| One national model | A single national mechanistic model can fit all regions. | Regional analysis showed different dominant signals across Northeast, East, North, South, Central, and West. | Rice blast epidemiology is regionally heterogeneous; regional modifiers are needed. |
| Static province-week risk | A single weekly risk score is enough. | Future-label analysis showed regional temporal pressure features are informative for `t+1` and `t+2`. | Forecasting should use temporal epidemiological sequences, not only static weekly scores. |

---

## Key Scientific Turning Points

### 1. Weather Is Necessary but Not Sufficient

The first major turning point was the weak national performance of the
weather-only baseline. This showed that favorable weather conditions alone
produce too many false positives. The disease process requires additional
epidemiological context.

### 2. Humidity and Leaf Wetness Are More Stable Than Rainfall

Humidity-based features and leaf-wetness proxies were more stable than rainfall.
This supported a mechanistic focus on infection-conducive hours rather than
simple rainfall totals.

### 3. Host Susceptibility Must Be Conservative

Rice variety composition contains signal, but variety effects are not uniformly
stable. This led to conservative susceptibility v0 weights and avoidance of
aggressive assumptions.

### 4. Neighbor Disease Pressure Matters

Previous-week neighbor blast occurrence emerged as one of the strongest stable
spatial signals, especially in the Northeast. This supports inoculum pressure as
a core epidemiological component.

### 5. Wind Matters Only When Directional and Source-Aware

Simple wind speed did not explain disease occurrence well. Directional alignment
from infected neighboring provinces showed stronger evidence. This shifted the
wind hypothesis from "wind speed spreads disease" to "directional connectivity
from infected sources may matter."

### 6. Regional Heterogeneity Is Central

Regional analysis showed that the Northeast, East, North, South, Central, and
West do not behave identically. This is a major methodological insight: the
project should not rely only on a single national score.

### 7. The Project Is Moving Toward Temporal Epidemiology

The creation of `blast_t_plus_1` and `blast_t_plus_2` labels reframed the work
from current-week risk scoring toward temporal forecasting. This prepares the
project for hybrid mechanistic and sequence-learning methods.

---

## Current Refined Research Hypothesis

Rice blast occurrence in Thailand is best represented as a regionally
heterogeneous epidemiological process driven by:

- local weather favorability
- accumulated humidity and leaf-wetness exposure
- host susceptibility from rice variety composition
- neighboring disease pressure
- directional wind-mediated connectivity
- region-specific temporal dynamics

Weather is a necessary environmental condition, but disease occurrence requires
host and inoculum context.

---

## Implication for Step 9

Before entering the ML era, the research structure should be treated as frozen
at the mechanistic-exploratory stage. Step 9 should not replace the mechanistic
system with a black-box model. Instead, it should build on the existing
explainable features as structured inputs for transparent baselines and later
hybrid sequence models.

