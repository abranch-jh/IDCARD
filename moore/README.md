# Moore Lab

Shared column naming, key-file formats, combining, and the GUI are in the [project README](../README.md). This file covers Moore import sources and keys.

## Overview

Actimetrics Watermaze data from **mice**. Young and aged cohorts are already wide (one row per animal) in separate CSVs and use different protocols. `import_scripts/moore_import.py` remaps suffixes from age-specific trial-type keys, adds metadata, concatenates, and writes `moore.csv`. Animal IDs get a `.SM` suffix.

Distance and speed are stored in cm / cm/s and divided by 100 at combine time. The Excel workbook `rat_data/raw_data_Young Acarbose 5xFAD WMW.xlsx` is not used. `protocol_time_*` is not computed as date and time was documented for each individual trial.

## Folder layout

```
moore/
├── moore.csv
├── keys/
│   ├── moore.json
│   ├── trial_type_key_y_moore.csv
│   └── trial_type_key_a_moore.csv
└── rat_data/
    ├── moore_young_data.csv
    ├── moore_aged_data.csv
    └── raw_data_Young Acarbose 5xFAD WMW.xlsx  # Ignored
```

## Import

```powershell
python -m import_scripts.moore_import
```

Running the import command overwrites `moore/moore.csv`.

1. Load young and aged wide CSVs.
2. Strip `*` from `subject_id`, append `.SM`, copy to `animal`; `age` → `age_mo`; map sex to M/F.
3. Rename stems: `dist` → `dist_total`, `cum_dist` → `dist_cum`, `datetime` → `datetime_trial`, `time_of_day` → `time`.
4. Remap suffixes with the age-specific key (spatial/visible source numbers = key `trial_num`; probe source numbers = `protocol_day`).
5. Format times to `HH:MM`; `watermaze_date` = earliest trial date (`%m/%d/%Y`).
6. Add metadata constants; write `trial_num_*` from the key.
7. Concatenate; compute `cumulative_time_*` (skip missing trials).

Young (7 mo): 24 spatial + 4 probe. Aged (24 mo): 36 spatial + 4 visible. Visible rows in the young key and probe rows in the aged key are not in those source CSVs, so they stay missing after concat.

Source suffixes are not sequential within type (young probes `p_4`, `p_7`, `p_10`, `p_13` → `p_1`–`p_4`; aged visible `c_43`–`c_46` → `c_1`–`c_4`).

## Trial column mapping

| Standardized variable | Raw stem | Internal name (post-import) |
|-----------------------|----------|-----------------------------|
| `dist_total` | `dist_<type>_<n>` | `dist_total_<type>_<n>` |
| `dist_cum` | `cum_dist_<type>_<n>` | `dist_cum_<type>_<n>` |
| `mean_speed` | `mean_speed_<type>_<n>` | `mean_speed_<type>_<n>` |
| `duration` | `duration_<type>_<n>` | `duration_<type>_<n>` |
| `datetime_trial` | `datetime_<type>_<n>` | `datetime_trial_<type>_<n>` |
| `trial_num` | trial-type key | `trial_num_<type>_<n>` |
| `date` / `time` | `date_*` / `time_of_day_*` | time parsed to `HH:MM` |

## Metadata

| Column | Source / derivation |
|--------|---------------------|
| `subject_id` / `animal` | `subject_id`; strip `*`; append `.SM` |
| `age_mo` | `age` (`7` young, `24` aged) |
| `sex` | `male`/`female` → `M`/`F` |
| `genotype`, `treatment`, `cohort`, `cage`, `hole_punch` | Source |
| `species` | `'mouse'` |
| `watermaze_date` | Earliest trial date |
| `protocol_id` | `'Moore_WM_young'` or `'Moore_WM_aged'` |
| `pi_name` | `'Moore'` |
| `subsequent_measures` | `'yes'` |
| `lights_on` / `lights_off` | `'7:00'` / `'19:00'` |
| `index_calc_type` | `'N/A'` |
| `tracking_system` | `'Watermaze'` |
| `rat_source` | `'custom'` |
| `housing` | `'Paired'` |
| `pool_diam` | `120` (centimeters) |
| `acclimation` | `'5 days handling'` |
| `tracking_marker` / `light_level` | `'no'` / `'high'` |

`strain` is listed in `shared_keys.json` but is not in the source CSVs.

## Raw source columns

Wide files share stems; suffixes differ by age.

**Subject:** `subject_id`, `cage`, `hole_punch`, `age`, `genotype`, `treatment`, `sex`, `cohort`

**Trials:** `mean_speed`, `cum_dist`, `dist`, `duration`, `date`, `datetime`, `time_of_day`

Young: spatial `s_*` and probe `p_*` (probe `n` = protocol day). Aged: spatial `s_*` and visible `c_*` (visible `n` = key `trial_num` 43–46).

## Keys

- **`keys/moore.json`** — stem mapping by trial type; import also uses `STEM_RENAME` in `moore_import.py`.
- **`keys/trial_type_key_y_moore.csv`** — young: `_s_1` … `_s_24`, `_p_1` … `_p_4` (visible rows unused).
- **`keys/trial_type_key_a_moore.csv`** — aged: `_s_1` … `_s_36`, `_c_1` … `_c_4` (probe rows unused).
- **`shared_keys.json` (Moore)** — identity maps for prefixes; cm / cm/s conversion.
