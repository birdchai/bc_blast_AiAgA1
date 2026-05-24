# Province Boundary Data Scout Recommendation

## Purpose

This recommendation supports Step 9.16B: Province Boundary and Name Matching Audit.

No DEM processing, Google Earth Engine processing, terrain feature creation, or model training was performed.

## Local Boundary Decision

- Local boundary status: no usable local boundary found
- Project provinces: 77
- Matched provinces: 0

## Interpretation

The local project folders were scanned for boundary-ready GIS files:

- `.shp`
- `.shx`
- `.dbf`
- `.prj`
- `.geojson`
- `.json`
- `.gpkg`
- `.kml`
- `.kmz`
- boundary-like `.csv` files with geometry/WKT/polygon indicators

No usable Thailand province polygon boundary was found locally.

The available `thailand_province_name.csv` file is useful as project province-name metadata, but it is not a polygon boundary source.

## Step 9.17 Readiness

Step 9.17 should not start DEM extraction until a province boundary file is approved and audited.

A usable boundary source must satisfy:

- polygon or multipolygon geometry,
- province-level Thailand coverage,
- 77 province features or equivalent,
- English or mappable province names,
- known or recoverable CRS,
- documented license/source,
- 77/77 project province-name match or near-complete match with documented manual mapping.

## Recommended Boundary Source Order

1. geoBoundaries
   - Recommended first source if local boundary remains missing.
   - Rationale: reproducible research-oriented administrative boundary access.

2. GADM
   - Strong fallback.
   - Rationale: widely used administrative boundaries.
   - Caveat: license and redistribution terms must be checked before thesis/project packaging.

3. HDX / Humanitarian Data Exchange
   - Candidate source.
   - Rationale: may provide administrative boundaries with humanitarian provenance.
   - Caveat: source freshness and provenance must be checked.

4. Thai government GIS / NSO / DOPA / RID / GISTDA
   - Official-source candidate.
   - Rationale: potentially authoritative Thailand boundary data.
   - Caveat: access, license, and reproducibility may require manual review.

5. Natural Earth
   - Not preferred.
   - Rationale: likely too coarse for province-level terrain extraction.

## Required Approved Boundary Schema

Minimum required fields:

- province name in English, or a stable province code plus mapping table,
- polygon or multipolygon geometry,
- CRS metadata,
- source name,
- source version or download date,
- license/terms note.

Preferred fields:

- province English name,
- province Thai name,
- province code,
- region if available,
- geometry validity flag after audit.

## Manual Name-Mapping Needs

After acquiring a boundary source:

- normalize province names conservatively,
- run exact normalized matching first,
- flag uncertain matches for manual review,
- do not silently force ambiguous matches,
- save manual mapping decisions in a tracked mapping table.

## Recommendation

Acquire or approve a province-level Thailand boundary dataset before Step 9.17.

The next technical action should be:

1. obtain a boundary candidate,
2. rerun the boundary/name audit,
3. verify 77/77 province matching,
4. only then proceed to SRTM/GEE terrain extraction.
