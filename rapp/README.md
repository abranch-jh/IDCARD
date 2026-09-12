# Rapp Lab

Shared column naming, key-file formats, combining, and the GUI are in the [project README](../README.md). This file covers Rapp import sources and keys.

## Overview

The rats selected for inclusion in the Rapp lab data set were collected as monthly cohorts used for studies of cognitive aging in outbred Long Evans rats. Data were collected with ANYMaze, and selected data was exported into Excel. Raw exports are organized by cohort, protocol day, and trial type (Spatial/AQ, Probe, Visible/Cue). ANYMaze provides an option to compute search error based on cumulative integrated path length (CIPL) or by custom functions. Use of different search error calculations result in small differences in some per trial measurements. To take advantage of this feature in ANYMaze, data were exported using both CIPL based calculations (raw data columns contain '_cipl' prefix) as well as in the style used by Gallagher, Rapp, Burke, and McQuail labs (based on Gallagher et. al., 1993; time needed to travel straight line path is removed, these raw data columns contain '_ttr' prefix). 

ANYMaze Morris Water Maze data by cohort and trial type (Spatial/AQ, Probe, Visible/Cue). `import_scripts.rapp_import.py` merges per-day CSVs into one wide row per animal. Animal IDs get a `.PR` suffix.

![Rapp Protocol Diagram](keys/rapp_protocol.png)

## Folder layout

```
rapp/
├── combined_data_rapp.csv
├── keys/
│   ├── rapp.json
│   └── trial_type_key_rapp.csv
└── rat_data/
    └── raw/
        └── outfiles/
```

## Import

```powershell
python -m import_scripts.rapp_import
```

1. Read `rat_data/raw/`; group by experiment prefix; classify Spatial, Probe, Visible, or Info from the filename.
2. Iterate trial files by `Stage:` and `Trial:`; combine `Date:` + `Time:` → `datetime_trial`; rename via `keys/rapp.json`.
3. Append suffixes from `keys/trial_type_key_rapp.csv`.
4. Merge per animal; compute `cumulative_time_*`; append `.PR`.

## Trial column mapping

After import, names use `ttr_*` / `cipl_*` prefixes. Spatial and Probe files use `AQ TRR to End of Test` / `Probe TRR to 30s` prefixes; Visible (Cue) uses unprefixed measure names.

| Standardized variable | Raw data source | Internal name (post-import) |
|-----------------------|-----------------|-----------------------------|
| `dist_total` | `Base; Distance (m):` or Visible `Distance (m):` | `ttr_dist_*` / `cipl_dist_*` |
| `dist_cum` | `Base; Platform : cumulative distance (` or Visible equivalent | `ttr_cum_dist_*` / `cipl_cum_dist_*` |
| `dist_mean` | `Base; Platform : mean distance from (m):` | `ttr_platform_mean_dist_*` |
| `mean_speed` | `Base; Mean speed (m/s):` | `ttr_mean_speed_*` |
| `duration` | `Base; Duration (s):` | `ttr_duration_*` |
| `cipl` | `Platform : CIPL (` | `cipl_cipl_*` |
| `datetime_trial` | `Date:`, `Time:` | `datetime_trial_*` |
| `trial_num` | `Trial:` | `trial_<type>_<n>` |
| `stage` | `Stage:` | `stage_<type>_<n>` |
| `date` / `time` | `Date:` / `Time:` | `date_*` / `time_*` |

## Metadata

Most fields are import constants (no Info files in the current pipeline).

| Column | Source / derivation |
|--------|---------------------|
| `animal` | `Animal:`; `.PR` appended |
| `strain` / `genotype` / `sex` | `'Long Evans'` / `'WT'` / `'M'` |
| `subsequent_measures` | `'no'` |
| `lights_on` / `lights_off` | `'6:30'` / `'18:30'` |
| `index_calc_type` | `'Gall_SearchError'` |
| `tracking_system` | `'AnyMaze'` |
| `rat_source` | `'Charles River'` |
| `housing` | `'Single'` |
| `pool_diam` | `184` (centimeters) |
| `protocol_id` / `pi_name` | `'Rapp_WM_1'` / `'Rapp'` |
| `light_level` / `acclimation` | `'high'` / `'5 days handling'` |
| `probe_weight_block2` / `3` / `4` | `'1.26'` / `'1.43'` / `'1.43'` |
| `tracking_marker` | `'no'` |
| `video_id` | `Recorded video file:` (via shared_keys from `source_id`) |

`cohort`, `experiment`, and `watermaze_date` are not populated in the import.

## Raw source columns

### Shared trial IDs

`Test`, `Animal`, `Stage`, `Trial`, `Date`, `Time`, `Time of day`, `User` (who ran the trial), `Recorded video file`

### Trial measures

Same ANYMaze measures as Barnes (duration, distance, mean speed, path efficiency, platform mean/cumulative distance, CIPL, probe quadrant times and % goal). Column form:

- **Spatial** (`*.AQ.csv`): `{Prefix}; {Measure}` — `AQ TRR to End of Test` or `Base`
- **Probe** (`*.Probe.csv`): `{Prefix}; {Measure}` — `Probe TRR to 30s` or `Base`
- **Visible** (`*.Cue.csv`): `{Measure}` only (no TTR/`Base` prefix)

## Keys

- **`keys/rapp.json`** — ANYMaze substrings → internal base names.
- **`keys/trial_type_key_rapp.csv`** — sequential trial → type, protocol day, suffix.
- **`shared_keys.json` (Rapp)** — e.g. `ttr_dist` → `dist_total`.
