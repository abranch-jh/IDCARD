# Burke Lab

Shared column naming, key-file formats, combining, and the GUI are in the [project README](../README.md). This file covers Burke import sources and keys.

## Overview

Videos for individual trials were analyzed with Actimetrics Watermaze software, and selected data variables were exported as .stc text files and converted to .csv with Excel. Raw exports are organized by cohort and protocol day, with trial type (Spatial, Probe, Visible) dependent on the protocol sequence outlined in `burke/keys/trial_type_key_burke.csv`. One CSV per cohort and protocol day can be found in `rat_data/csv/`. 

`import_scripts/burke_import.py` merges days, assigns types from the trial-type key, and writes `burke.csv`. Animal IDs get a `.SB` suffix.

![Burke Protocol Diagram](keys/burke_protocol.png)

## Folder layout

```
burke/
├── burke.csv
├── keys/
│   ├── burke.json
│   ├── trial_type_key_burke.csv
│   └── CW Darth Maul Rat Diet Genotype.csv
└── rat_data/
    ├── csv/          # Raw Actimetrics exports (e.g. 1.1018D1.csv)
    └── stc/          # Original .stc source files
```

## Import

```powershell
python -m import_scripts.burke_import
```

Or from the `import_scripts` folder:

```powershell
cd import_scripts
python burke_import.py
```

1. Read `rat_data/csv/` grouped by cohort prefix; `protocol_day` from file order within the cohort.
2. Match trials using `DESCRIPT` (e.g. `swim01`) and `keys/trial_type_key_burke.csv`.
3. Split by trial; combine `RUNDATEx` + `RUNTIMEx` → `datetime_trial`; rename via `keys/burke.json`.
4. Append `new_suffix` from the trial-type key.
5. Merge genotype/treatment from `CW Darth Maul Rat Diet Genotype.csv`.
6. Compute `cumulative_time_*`; append `.SB`; write `burke.csv`.

`burke.json` maps `PATHISmt` → `ttr_dist` (total path length in meters) and `GALCUMms` → `cum_dist` (Gallagher cumulative search error). At combine time, `cum_dist` is renamed to `dist_cum` via `shared_keys.json`; `ttr_dist` is kept as-is.

## Trial column mapping

| Standardized variable | Raw data source | Internal name (post-import) |
|-----------------------|-----------------|-----------------------------|
| `dist_total` | `PATHISmt` | `ttr_dist_<type>_<n>` |
| `dist_mean` | `PROXIMmt` | `ttr_platform_mean_dist_<type>_<n>` |
| `dist_cum` | `GALCUMms` | `cum_dist_<type>_<n>` (Gallagher cumulative search error) |
| `mean_speed` | `SPEEDmts` | `mean_speed_<type>_<n>` |
| `duration` | `LATENTsc` | `duration_<type>_<n>` |
| `datetime_trial` | `RUNDATEx`, `RUNTIMEx` | `datetime_trial_<type>_<n>` |
| `trial_num` | `DESCRIPT` → trial key | `trial_num_<type>_<n>` |
| `date` / `time` | `RUNDATEx` / `RUNTIMEx` | trailing `:` stripped from time |
| `test` | `TRIALISx` | `test_<type>_<n>` |

## Metadata

| Column | Source / derivation |
|--------|---------------------|
| `animal` | `SUBJECTx`; `.SB` appended |
| `genotype`, `treatment` | `CW Darth Maul Rat Diet Genotype.csv` merged on `animal` |
| `sex` | `'M'` |
| `lights_on` / `lights_off` | `'7:00'` / `'19:00'` |
| `index_calc_type` | `'Gall_SearchError'` |
| `tracking_system` | `'Watermaze'` |
| `pool_diam` | `184` (centimeters) |
| `rat_source` | `'NIA'` |
| `protocol_id` / `pi_name` | `'Burke_WM_1'` / `'Burke'` |

`watermaze_date` and `calculated_index` are not populated in the import.

## Raw source columns

The same headings appear in every day CSV; trial type comes from `DESCRIPT`, not from different files.

`TRIALISx`, `TXPNAMEx`, `RUNDATEx`, `RUNTIMEx`, `STARTPTx`, `SUBJECTx`, `DESCRIPT`, `MAXTIMsc`, `LATENTsc`, `PATHISmt`, `SPEEDmts`, `xTIMEFLT`, `HEADGdeg`, `THGTIMEx`, `THGPATHx`, `SLICEISx`, `SLCxONsc`, `SLCxGOsc`, `QUAD{n}xsc`, `QUAD{n}xmt`, `PROXIMmt`, `PROXmt0{n}`, `GALCUMms`, `CUMUms0{n}` (n = 1–4).

## Keys

- **`keys/burke.json`** — Actimetrics names → internal base names.
- **`keys/trial_type_key_burke.csv`** — `trial_name` (e.g. `swim01`), protocol day, type → suffix.
- **`keys/CW Darth Maul Rat Diet Genotype.csv`** — genotype and treatment by animal.
- **`shared_keys.json` (Burke)** — e.g. `cum_dist` → `dist_cum`, `ttr_platform_mean_dist` → `dist_mean`.
