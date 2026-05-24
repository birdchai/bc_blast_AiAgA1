# Data Scout Terrain / Elevation Recommendation

## Purpose

This document evaluates candidate terrain/elevation data sources for creating a province-level terrain table for Thailand. The immediate research purpose is to support North-focused rice blast diagnostics after Step 9.14 showed that North positives remain missed by all major candidate models.

This is a Data Scout recommendation only. No terrain raster has been downloaded, no terrain features have been merged into the sequence dataset, and no model has been trained.

## Research Need

The current corrected-label project has strong evidence that North-region failures are not solved by:

- core weather and host features,
- regional pressure features,
- province analog history,
- temporal neural models,
- threshold or calibration governance.

The updated `weather_hourly` source does not contain direct elevation or terrain fields. It contains `sealevelpressure`, but that variable is adjusted to sea level and should not be used as an elevation proxy.

Terrain/elevation should therefore be treated as static province metadata, not hourly weather.

## Candidate Sources

### 1. SRTM 30m / NASA-USGS SRTMGL1

Summary:

- Provider: NASA / USGS / JPL-Caltech.
- Resolution: approximately 30m / 1 arc-second.
- Coverage: near-global and suitable for Thailand.
- Access: Google Earth Engine `USGS/SRTMGL1_003`, USGS EarthExplorer, or NASA Earthdata.
- Data type: DEM raster.

Strengths:

- Widely used and well cited.
- Simple to access through Google Earth Engine.
- Sufficient for province-level mean, range, roughness, and slope summaries.
- Strong reproducibility for thesis and publication workflows.

Limitations:

- The source is based on a 2000-era radar mission.
- It is not a field-scale microtopography dataset.
- It may include vegetation or surface effects in some areas.
- It should be used for province-level terrain context, not fine local field elevation.

### 2. Copernicus DEM GLO-30 / GLO-90

Summary:

- Provider: Copernicus Programme / ESA.
- Resolution: GLO-30 at 30m where public; GLO-90 at 90m.
- Coverage: global; Thailand is within expected public coverage.
- Access: Google Earth Engine, Copernicus Data Space, or Sentinel Hub.
- Data type: Digital Surface Model.

Strengths:

- Newer and high-quality global elevation product.
- GLO-30 is a strong 30m alternative to SRTM.
- GLO-90 is easier and lighter if 30m processing is unnecessary.

Limitations:

- It is a DSM, representing surface features including vegetation, buildings, and infrastructure.
- This must be explicit in thesis interpretation.
- Licensing and citation terms must be documented carefully.

### 3. ASTER GDEM v3

Summary:

- Provider: NASA / METI.
- Resolution: 30m.
- Coverage: land from 83N to 83S; includes Thailand.
- Access: NASA Earthdata / LP DAAC / ASTER distribution.

Strengths:

- Global 30m source.
- Useful as a secondary comparison dataset.
- Can help check whether SRTM/Copernicus terrain summaries are robust.

Limitations:

- Known stereo-optical artifacts.
- May have cloud, noise, and above-ground feature effects.
- Requires more quality-control attention.
- Not recommended as the first-pass default.

### 4. Thai Government GIS / DEM Sources

Summary:

- Possible providers include Thai government GIS, geological, irrigation, mapping, or space agencies.
- Resolution and availability may be better than global DEMs if a national DEM exists.

Strengths:

- Potentially more locally authoritative.
- May provide official Thai terrain data or high-resolution products.

Limitations:

- Nationwide coverage is not yet confirmed.
- Licensing and reproducibility may be unclear.
- Access may require manual request or Thai-language portal review.
- Some visible public datasets are local rather than nationwide.

This is worth scouting further, but not suitable as the first operational source until availability is confirmed.

### 5. Commercial DEM / GIS Sources

Summary:

- Commercial providers may offer high-resolution DEM/DSM products.

Strengths:

- Potentially higher spatial resolution.
- Useful if sub-provincial terrain becomes essential.

Limitations:

- Paid or restricted.
- Reproducibility may be weaker.
- Publication and redistribution rights may be constrained.
- Not needed for province-level first-pass diagnostics.

## Recommended First Dataset

Recommended first source:

- SRTM 30m / NASA-USGS SRTMGL1 through Google Earth Engine.

Rationale:

- It is free and widely used.
- It is simple to reproduce.
- It is available in Google Earth Engine as a single global DEM image.
- It is sufficient for province-level terrain summaries.
- It minimizes local raster storage and processing burden.
- It supports the immediate research goal: testing whether static terrain context helps explain North failures.

## Recommended Fallback Dataset

Recommended fallback:

- Copernicus DEM GLO-30.

Rationale:

- It is also 30m.
- It is newer and high quality.
- It can be used to validate whether SRTM-derived province terrain rankings are robust.

Secondary fallback:

- Copernicus GLO-90 if GLO-30 processing is unnecessarily heavy.

ASTER GDEM v3 should be treated as a secondary comparison source, not the default.

## Paid Data Decision

A paid dataset is not needed now.

Reason:

- The immediate target is a province-level terrain table.
- Free/open 30m DEM sources are sufficient for first-pass diagnostic analysis.
- Commercial data would add license and reproducibility complications before the research has shown that terrain improves the explanation.

## Google Earth Engine Decision

Google Earth Engine is recommended for the first pass.

Reasons:

- It avoids downloading large raster files locally.
- It supports reproducible zonal statistics by province.
- It can compute slope directly from DEM rasters.
- It can export a compact province-level CSV table.

Requirement:

- Earth Engine account access is needed.
- Province boundary polygons must be available or uploaded.

## Local Raster Download Decision

Local raster download is not recommended for the first pass.

Reasons:

- It adds storage and processing overhead.
- It is unnecessary for a province-level table.
- Google Earth Engine can produce the required summary table directly.

Local raster processing can be considered later if:

- Earth Engine access is blocked,
- boundary upload is difficult,
- reproducibility requires a fully local workflow,
- sub-provincial or field-scale terrain analysis becomes necessary.

## Expected Processing Workflow

First-pass workflow:

1. Obtain province boundary polygons for Thailand.
2. Load SRTM 30m in Google Earth Engine.
3. Clip or reduce DEM by province polygons.
4. Compute province-level elevation statistics:
   - `elevation_mean`
   - `elevation_min`
   - `elevation_max`
   - `elevation_range`
   - `elevation_std`
5. Compute slope from DEM.
6. Compute province-level slope statistics:
   - `slope_mean`
   - `slope_std`
7. Compute terrain roughness:
   - for example, local elevation standard deviation or ruggedness index summarized by province.
8. Compute area ratios:
   - `mountainous_area_ratio`
   - `lowland_area_ratio`
   - thresholds should be defined before analysis and documented.
9. Export `province_terrain_table.csv`.
10. Audit province-name matching against project province names.
11. Audit missingness and plausible value ranges.
12. Run terrain association analysis before any model retraining.

## Expected Output Table

Expected file:

- `province_terrain_table.csv`

Required fields:

- `province`
- `elevation_mean`
- `elevation_min`
- `elevation_max`
- `elevation_range`
- `elevation_std`
- `terrain_roughness`
- `slope_mean`
- `slope_std`
- `mountainous_area_ratio`
- `lowland_area_ratio`
- `source`
- `source_resolution`
- `processing_method`
- `notes`

## Risks And Caveats

- Terrain is static province metadata, not hourly weather.
- Province-level terrain may still hide sub-provincial heterogeneity.
- DEM products may represent surface height, not bare-earth terrain.
- Terrain effects should be interpreted as association, not causation.
- North-region failure may also involve reporting patterns, crop calendars, local varieties, or field-level microclimate.
- Terrain features must be validated before use in models.

## Decision

| question | decision |
|---|---|
| recommended first dataset | SRTM 30m / NASA-USGS SRTMGL1 |
| recommended fallback dataset | Copernicus DEM GLO-30 |
| paid dataset needed now | No |
| Google Earth Engine recommended | Yes |
| local raster download recommended now | No |
| can proceed with province-level table first | Yes |

## References

- USGS global elevation data FAQ: https://www.usgs.gov/faqs/where-can-i-get-global-elevation-data
- USGS SRTM archive: https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm
- Google Earth Engine SRTMGL1 dataset: https://developers.google.com/earth-engine/datasets/catalog/USGS_SRTMGL1_003
- Google Earth Engine Copernicus GLO-30 dataset: https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_DEM_GLO30
- Copernicus DEM data documentation: https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM.html
- NASA ASTER GDEM v3 announcement: https://www.earthdata.nasa.gov/fr/news/new-version-aster-gdem
- ASTER GDEM official page: https://asterweb.jpl.nasa.gov/gdem.asp
