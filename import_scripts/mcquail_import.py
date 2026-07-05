# -*- coding: utf-8 -*-
"""
Created on Sun Feb  8 14:13:09 2026

@author: abranch6
"""

import os
import re
from pathlib import Path
import pandas as pd
from functools import reduce
from import_tools import *

PROJECT_ROOT = Path(__file__).resolve().parents[1]
current_directory = PROJECT_ROOT / "mcquail"
file = current_directory / "rat_data" / "mcquail_data_plus.csv"
trial_type_key, rename_dict_full = get_data(str(current_directory), 'mcquail')
df_raw = pd.read_csv(str(file), low_memory=False)
df = df_raw

## ----- clean up formatting ---- #
# Extract numeric trial index; keep as numeric with NaNs instead of failing on missing values
trial_num_str = df_raw['trial'].astype(str).str.extract(r'(\d+)')[0]
df['trial'] = pd.to_numeric(trial_num_str, errors='coerce')

df['block'] = df_raw['block'].astype(str).str.extract(r'(\d+)')[0]

# Extract day number; keep as numeric with NaNs
day_num_str = df_raw['day_num'].astype(str).str.extract(r'(\d+)')[0]
day_num_str = day_num_str.astype(str).str.lstrip('0')
df['day'] = pd.to_numeric(day_num_str, errors='coerce')

df['trial_num_cum'] = (df['trial'] + (df['day'] * 3)) - 3
df['date'] = pd.to_datetime(df['date'], origin='1899-12-30', unit='D')
df['date'] = df['date'].dt.strftime('%m/%d/%Y')
df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y', errors='coerce').dt.date
df['time'] = df_raw['time'].astype(str).str.strip()
df = df[~df['trial_type'].str.contains('Rev', na=False)] # dropping reversal trials


COMMENT_PATTERN = "|".join(["already"])
df_filtered = df[~df["Comments"].str.contains(COMMENT_PATTERN, case=False, na=False)].copy()
df_filtered["trial_type"] = df_filtered["trial_type"].replace({"Train": "Spatial", "Probe": "Probe", "Cue": "Visible"})
df_filtered["date"] = df.loc[df_filtered.index, "date"]
df_filtered = rename_trial_num_cols(df_filtered, trial_type_key)
df_filtered = df_filtered[~df_filtered["Comments"].str.contains(COMMENT_PATTERN, case=False, na=False)]
df_filtered = df_filtered[~df_filtered["trial_type"].str.contains("Rev", na=False)]
df_filtered['trial_num_cum'] = df_filtered['trial_num_cum'].replace({  # renumbering trial number for cue training trials where there was reversal trials so they match other cue trials
    31: 25,
    32: 26,
    33: 27,
    34: 28,
    35: 29,
    36: 30
})

trial_counts = df_filtered.groupby('animal').size()
subjects_with_30_trials = trial_counts[trial_counts == 30].index
df_filtered = df_filtered[df_filtered['animal'].isin(subjects_with_30_trials)]
num_animals = len(df_filtered['animal'].unique())
df_filtered['protocol_time'] = generate_protocol_time(num_animals)



TRIAL_NAME_COL = "trial_num_cum"  

def build_data_dict_by_trial_type(cohort_dfs, trial_type_key, trial_name_col_in_df="trial_num_cum", protocol_day_col_in_df="protocol_day"):
    """
    Organize cohort DataFrames into data_dict[cohort][trial_type] = list of day DataFrames.
    trial_type_key must have: trial_type, protocol_day, and either trial_name or trial_num (+ optional new_suffix).
    If key has trial_name: match by protocol_day and trial_name. If only trial_num: match by protocol_day and trial_num.
    """
    key = trial_type_key.copy()
    key.columns = [str(c).strip().lower().replace(" ", "_") for c in key.columns]
    trial_num_col = "trial_num"
    trial_type_col = "trial_type"
    trial_name_col = "trial_name"
    protocol_day_col = "protocol_day"
    if trial_type_col not in key.columns or protocol_day_col not in key.columns:
        raise ValueError(f"trial_type_key must have '{trial_type_col}' and '{protocol_day_col}' (got {list(key.columns)})")
    has_trial_name = trial_name_col in key.columns
    if not has_trial_name and trial_num_col not in key.columns:
        raise ValueError(f"trial_type_key must have '{trial_name_col}' or '{trial_num_col}' (got {list(key.columns)})")
    data_dict = {}
    for cohort, full_df in cohort_dfs.items():
        if full_df.empty or trial_name_col_in_df not in full_df.columns:
            data_dict[cohort] = {"Spatial": [], "Probe": [], "Visible": [], "Info": []}
            continue
        full_df = full_df.copy()
        day_col = protocol_day_col_in_df if protocol_day_col_in_df in full_df.columns else "protocol_day"
        if day_col not in full_df.columns:
            data_dict[cohort] = {"Spatial": [], "Probe": [], "Visible": [], "Info": []}
            continue
        full_df["protocol_day"] = pd.to_numeric(full_df[day_col], errors="coerce").astype("Int64")
        data_dict[cohort] = {"Spatial": [], "Probe": [], "Visible": [], "Info": []}
        for tt in ["Spatial", "Probe", "Visible"]:
            key_tt = key[key[trial_type_col].astype(str).str.strip().str.capitalize() == tt]
            if key_tt.empty:
                continue
            key_tt = key_tt.copy()
            key_tt["protocol_day"] = pd.to_numeric(key_tt[protocol_day_col], errors="coerce").astype("Int64")
            for protocol_day in sorted(key_tt["protocol_day"].dropna().unique()):
                key_day = key_tt[key_tt["protocol_day"] == protocol_day]
                if has_trial_name:
                    trial_vals_in_key = key_day[trial_name_col].astype(str).str.strip().str.lower().tolist()
                    df_vals = full_df[trial_name_col_in_df].astype(str).str.strip().str.lower()
                    day_df = full_df[
                        (full_df["protocol_day"] == protocol_day) & df_vals.isin(trial_vals_in_key)
                    ].copy()
                    if not day_df.empty:
                        name_to_num = dict(zip(
                            key_day[trial_name_col].astype(str).str.strip().str.lower(),
                            key_day[trial_num_col].dropna().astype(int),
                        ))
                        day_df["trial_num"] = day_df[trial_name_col_in_df].astype(str).str.strip().str.lower().map(name_to_num)
                        data_dict[cohort][tt].append(day_df)
                else:
                    trial_nums_in_key = pd.to_numeric(key_day[trial_num_col], errors="coerce").dropna().astype(int).tolist()
                    df_vals = pd.to_numeric(full_df[trial_name_col_in_df], errors="coerce")
                    day_df = full_df[
                        (full_df["protocol_day"] == protocol_day) & df_vals.isin(trial_nums_in_key)
                    ].copy()
                    if not day_df.empty:
                        day_df["trial_num"] = pd.to_numeric(day_df[trial_name_col_in_df], errors="coerce").astype("Int64")
                        data_dict[cohort][tt].append(day_df)
    return data_dict

# Mquail: single cohort; ensure protocol_day exists (from day) and wrap in dict
if "protocol_day" not in df_filtered.columns and "day" in df_filtered.columns:
    df_filtered = df_filtered.copy()
    df_filtered["protocol_day"] = df_filtered["day"]
    
cohort_dfs = {"mquail": df_filtered}

data_dict = build_data_dict_by_trial_type(cohort_dfs, trial_type_key, trial_name_col_in_df=TRIAL_NAME_COL, protocol_day_col_in_df="protocol_day")


def _allowed_original_columns(file_type, rename_dict_full, merge_key="animal", sample_columns=None):
    """Set of original column names to keep: merge_key, columns matching a rename_dict key, or a rename_dict value."""
    if file_type not in rename_dict_full or sample_columns is None:
        return {merge_key}
    allowed = {merge_key}
    keys = list(rename_dict_full[file_type].keys())
    values = set(str(v).strip().rstrip("_") for v in rename_dict_full[file_type].values())
    for col in sample_columns:
        if col == merge_key:
            continue
        if any(str(k) in str(col) for k in keys):
            allowed.add(col)
        elif col in values or any(col == v or col.startswith(v + "_") for v in values):
            allowed.add(col)
    return allowed


def _trim_data_dict_columns(data_dict, rename_dict_full, merge_key="animal"):
    """Keep only merge_key, trial_num, protocol_day, and columns allowed by rename_dict_full."""
    for cohort in data_dict:
        for file_type in ["Spatial", "Probe", "Visible"]:
            if file_type not in data_dict[cohort] or file_type not in rename_dict_full:
                continue
            day_dfs = data_dict[cohort][file_type]
            if not day_dfs:
                continue
            all_cols = set()
            for d in day_dfs:
                all_cols.update(d.columns)
            allowed = _allowed_original_columns(file_type, rename_dict_full, merge_key, all_cols) | {"trial_num", "protocol_day"}
            data_dict[cohort][file_type] = [d[[c for c in d.columns if c in allowed]].copy() for d in day_dfs]


def _merge_on_key(df_list, merge_key, how="outer"):
    """Merge a list of DataFrames on merge_key."""
    if not df_list:
        return pd.DataFrame()
    return reduce(lambda left, right: pd.merge(left, right, on=merge_key, how=how), df_list)


merge_key = "animal"
_trim_data_dict_columns(data_dict, rename_dict_full, merge_key)

def _strip_trial_suffix(s):
    """Remove trailing _s_123, _p_1, _c_2 etc. so we don't double-add suffix."""
    if not s:
        return s
    s = str(s).strip().replace(" ", "_")
    return re.sub(r"_(s|p|c)_\d+$", "", s)


# Exact column names that contain 'trial': use as-is for base so naming is always {base}_{s|p|c}_{trial_number}
TRIAL_COLUMN_NAMES = frozenset({"trial", "trial_num", "trial_num_cum", "trial_type"})


def _base_name_for_column(col, file_type, rename_dict_full):
    """Base for final name {base}_{type_prefix}_{trial_number}. Exact match for trial columns."""
    raw = str(col).strip().replace(" ", "_")
    if raw in TRIAL_COLUMN_NAMES:
        return raw
    if file_type not in rename_dict_full:
        return _strip_trial_suffix(raw)
    keys_sorted = sorted(rename_dict_full[file_type].keys(), key=lambda k: -len(str(k)))
    for key in keys_sorted:
        if key in col:
            base = rename_dict_full[file_type][key]
            base = str(base).strip().rstrip("_").replace(" ", "_")
            if len(base) > 2 and base[-2] == "_" and base[-1] in ("s", "p", "c"):
                base = base[:-2]
            return base
    return _strip_trial_suffix(raw)


# Build wide DataFrame from data_dict (one row per animal, columns = trial variables with unique names)
experiment_name = []
wide_by_cohort = {}

for experiment_prefix, file_lists in data_dict.items():
    experiment_name.append(experiment_prefix)
    wide_df_parts = []
    for file_type, files in file_lists.items():
        if len(files) == 0:
            continue

        # files = list of day DataFrames (no create_combined_df needed)
        combined_dfs = files
        trial_type_counter = 1
        trial_rows_dfs = []
        # Column to slice by trial (set by build_data_dict_by_trial_type: "trial_num" for mquail)
        sample_cols = combined_dfs[0].columns if combined_dfs else []
        trial_col = next((c for c in ["trial_num", "_trial_num", "Trial:"] if c in sample_cols), None)
        if trial_col is None:
            continue
        type_prefix = {"Spatial": "s", "Probe": "p", "Visible": "c"}.get(file_type, "t")
        for day_df in combined_dfs:
            day_df = day_df.copy()
            if trial_col not in day_df.columns:
                continue
            for trial_number in sorted(day_df[trial_col].dropna().unique()):
                trial_rows = day_df[day_df[trial_col] == trial_number].copy()
                if trial_rows.empty:
                    continue
                date_col = next((c for c in trial_rows.columns if c.startswith("date") or c == "date"), None)
                time_col = next((c for c in trial_rows.columns if c.startswith("time") or c == "time"), None)
                if date_col is not None and time_col is not None:
                    trial_rows[date_col] = pd.to_datetime(trial_rows[date_col], errors="coerce")
                    trial_rows[date_col] = trial_rows[date_col].dt.strftime("%m/%d/%Y")
                    if time_col in trial_rows.columns:
                        trial_rows[time_col] = trial_rows[time_col].astype(str).str.strip()
                        try:
                            trial_rows[time_col] = trial_rows[time_col].apply(format_time_anymaze)
                        except Exception:
                            pass
                    trial_rows["datetime_trial"] = pd.to_datetime(
                        trial_rows[date_col].astype(str) + " " + trial_rows[time_col].astype(str),
                        errors="coerce",
                    )
                # Every column (except merge_key) must be: {base}_{type_prefix}_{trial_number}
                new_names = []
                used = set()
                for col in trial_rows.columns:
                    if col == merge_key:
                        new_names.append(col)
                        used.add(col)
                        continue
                    base = _base_name_for_column(col, file_type, rename_dict_full)
                    name = f"{base}_{type_prefix}_{trial_type_counter}"
                    disambiguate = 0
                    while name in used:
                        base = _strip_trial_suffix(str(col))
                        if disambiguate > 0:
                            base = f"{base}_{disambiguate}"
                        name = f"{base}_{type_prefix}_{trial_type_counter}"
                        disambiguate += 1
                    used.add(name)
                    new_names.append(name)
                trial_rows.columns = new_names
                trial_type_counter += 1
                trial_rows_dfs.append(trial_rows)

        if not trial_rows_dfs:
            continue
        if not all(merge_key in d.columns for d in trial_rows_dfs):
            continue
        wide_df_parts.append(_merge_on_key(trial_rows_dfs, merge_key))

    if wide_df_parts:
        wide_by_cohort[experiment_prefix] = _merge_on_key(wide_df_parts, merge_key)
    else:
        wide_by_cohort[experiment_prefix] = pd.DataFrame()


def _add_info_columns_to_wide(wide_by_cohort, cohort_dfs, rename_dict_full, merge_key="animal"):
    """
    Add columns from rename_dict_full['Info'] to each wide DataFrame in wide_by_cohort.
    Info keys = column names (or substrings) in cohort_dfs to pull; values = name to use in wide df.
    Match rows on merge_key; take first row per animal from cohort_dfs.
    Returns wide_by_cohort (modified in place and returned for wide_final = ...).
    """
    if "Info" not in rename_dict_full:
        return wide_by_cohort
    info_map = rename_dict_full["Info"]
    for cohort, wide_df in list(wide_by_cohort.items()):
        if not isinstance(wide_df, pd.DataFrame) or wide_df.empty or cohort not in cohort_dfs:
            continue
        source = cohort_dfs[cohort]
        source_cols_lower = {str(c).lower(): c for c in source.columns}
        merge_col = merge_key if merge_key in source.columns else source_cols_lower.get(merge_key.lower())
        if merge_col is None:
            continue
        one_per_animal = source.drop_duplicates(subset=merge_col, keep="first").copy()
        keep_cols = [merge_col]
        rename_map = {}
        for col in one_per_animal.columns:
            if col == merge_col:
                continue
            col_str = str(col)
            if col in info_map:
                keep_cols.append(col)
                rename_map[col] = info_map[col]
                continue
            for key in info_map.keys():
                if str(key) in col_str:
                    keep_cols.append(col)
                    rename_map[col] = info_map[key]
                    break
        if len(keep_cols) <= 1:
            continue
        info_df = one_per_animal[keep_cols].rename(columns=rename_map)
        if merge_col != merge_key:
            info_df = info_df.rename(columns={merge_col: merge_key})
        overlap = [c for c in info_df.columns if c in wide_df.columns and c != merge_key]
        if overlap:
            info_df = info_df.drop(columns=overlap)
        if info_df.shape[1] <= 1:
            continue
        wide_by_cohort[cohort] = wide_df.merge(info_df, on=merge_key, how="left")
    return wide_by_cohort


def compute_cumulative_time_skip_nans(df, prefix, dropStart=False):
    """
    Computes cumulative time in seconds from the earliest trial datetime per row.
    Rows with NaN in a datetime_trial_ column get NaN in the corresponding
    cumulative_time column; the rest of the row is still computed.
    """
    trial_cols = [c for c in df.columns if c.startswith(prefix)]
    if not trial_cols:
        raise ValueError(f"No columns found with prefix '{prefix}'")
    df = df.copy()
    df[trial_cols] = df[trial_cols].apply(pd.to_datetime, errors="coerce")
    min_time = df[trial_cols].min(axis=1)
    for i, col in enumerate(trial_cols):
        trial_num = col.split("_")[-2] + col.split("_")[-1]
        if i == 0:
            sec = pd.Series(0.0, index=df.index).where(df[col].notna(), pd.NA)
        else:
            sec = (df[col] - min_time).dt.total_seconds()
        df[f"cumulative_time_{trial_num}"] = sec
    if dropStart and "start_time" in df.columns:
        df = df.drop(columns=["start_time"])
    return df


wide_final = _add_info_columns_to_wide(wide_by_cohort, cohort_dfs, rename_dict_full, merge_key=merge_key)
wide_final = pd.concat(wide_final.values(), ignore_index=True)
wide_final = compute_cumulative_time_skip_nans(wide_final, prefix="datetime_trial_", dropStart=False)
wide_final['animal'] = wide_final['animal'].astype(str) + '.JM'
wide_final['pi_name'] = 'McQuail'
wide_final['protocol_id'] = 'McQuail_WM_1'
wide_final['lights_on'] = '7:00'
wide_final['lights_off'] = '19:00'
wide_final['index_calc_type'] = "Gallagher/SearchError"
wide_final['tracking_system'] = "Ethovision"
wide_final['housing'] = "Paired/Single"
wide_final['pool_diam'] = "183"
if "calculated_index" not in wide_final.columns:
    wide_final["calculated_index"] = pd.NA

outpath = current_directory
wide_final.to_csv(outpath / "mcquail.csv", index=False)


