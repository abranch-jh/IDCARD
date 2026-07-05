# -*- coding: utf-8 -*-
"""
Created on Fri Sep 20 10:09:43 2024

@author: abranch
"""


import os
import glob
import chardet
import pandas as pd
import numpy as np
import re
from functools import reduce
import sys
from pathlib import Path
# import Path
from import_tools import *


PROJECT_ROOT = Path(__file__).resolve().parents[1]
current_directory = PROJECT_ROOT / "burke"
genotype_diet_file = current_directory / "keys" / "CW Darth Maul Rat Diet Genotype.csv"
trial_type_key, rename_dict_full = get_data(str(current_directory), current_directory.name)

full_re = re.compile(r"^(?P<cohort>\d+\.) (?P<md>\d{2,4}) D (?P<day>\d+)\.csv$".replace(" ", ""))

file_paths = glob.glob(str(current_directory / "rat_data" / "csv" / "*.csv"))

groups = {}
for file_path in file_paths:
    filename = os.path.basename(file_path)
    m = full_re.match(filename)
    if not m:
        print(f"Skipping file with unexpected name: {filename}")
        continue
    cohort = m.group("cohort").split('.')[0]               # e.g. "1." or "10."
    protocol_day = int(m.group("day"))       # number after 'D'
    groups.setdefault(cohort, []).append((file_path, protocol_day))

# read files and concatenate per cohort

ANIMAL_COL_RAW = "Subject"  # subject column name in Burke CSVs before adding ':'
cohort_dfs = {}
for cohort, file_info in groups.items():
    dfs = []
    for idx, (path, _) in enumerate(sorted(file_info, key=lambda x: x[1])):
        df = pd.read_csv(path)
        df.columns = [str(c).strip().rstrip(":") + ":" for c in df.columns]
        df["protocol_day"] = idx + 1  # position 0 -> day 1, position 1 -> day 2, ...
        for cand in [ANIMAL_COL_RAW + ":", ANIMAL_COL_RAW, "animal:"]:
            if cand in df.columns:
                df = df.rename(columns={cand: "animal"})
                break
        dfs.append(df)
    if dfs:
        cohort_dfs[cohort] = pd.concat(dfs, ignore_index=True)
    else:
        cohort_dfs[cohort] = pd.DataFrame()

# Build data_dict by trial type from cohort_dfs and trial_type_key
# trial_type_key columns: trial_num, trial_name, trial_type, protocol_day, new_suffix
# DataFrame column for trial label (must match trial_name in key): DESCRIPT:
TRIAL_NAME_COL = "DESCRIPT:"   # column in read DataFrames that holds trial_name (e.g. swim01, swim02)

def _change_time_cols(df, date_key, time_key):
    df[date_key] = pd.to_datetime(df[date_key], format='%m/%d/%Y', errors='coerce').dt.date
    time_columns = [col for col in df.columns if time_key in col]
    for col in time_columns:
        df[col] = df[col].apply(remove_trailing_colon)
    return df

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
        full_df["_protocol_day"] = pd.to_numeric(full_df[day_col], errors="coerce").astype("Int64")
        data_dict[cohort] = {"Spatial": [], "Probe": [], "Visible": [], "Info": []}
        for tt in ["Spatial", "Probe", "Visible"]:
            key_tt = key[key[trial_type_col].astype(str).str.strip().str.capitalize() == tt]
            if key_tt.empty:
                continue
            key_tt = key_tt.copy()
            key_tt["_protocol_day"] = pd.to_numeric(key_tt[protocol_day_col], errors="coerce").astype("Int64")
            for protocol_day in sorted(key_tt["_protocol_day"].dropna().unique()):
                key_day = key_tt[key_tt["_protocol_day"] == protocol_day]
                if has_trial_name:
                    trial_vals_in_key = key_day[trial_name_col].astype(str).str.strip().str.lower().tolist()
                    df_vals = full_df[trial_name_col_in_df].astype(str).str.strip().str.lower()
                    day_df = full_df[
                        (full_df["_protocol_day"] == protocol_day) & df_vals.isin(trial_vals_in_key)
                    ].copy()
                    if not day_df.empty:
                        name_to_num = dict(zip(
                            key_day[trial_name_col].astype(str).str.strip().str.lower(),
                            key_day[trial_num_col].dropna().astype(int),
                        ))
                        day_df["Trial:"] = day_df[trial_name_col_in_df].astype(str).str.strip().str.lower().map(name_to_num)
                        data_dict[cohort][tt].append(day_df)
                else:
                    trial_nums_in_key = pd.to_numeric(key_day[trial_num_col], errors="coerce").dropna().astype(int).tolist()
                    df_vals = pd.to_numeric(full_df[trial_name_col_in_df], errors="coerce")
                    day_df = full_df[
                        (full_df["_protocol_day"] == protocol_day) & df_vals.isin(trial_nums_in_key)
                    ].copy()
                    if not day_df.empty:
                        day_df["Trial:"] = pd.to_numeric(day_df[trial_name_col_in_df], errors="coerce").astype("Int64")
                        data_dict[cohort][tt].append(day_df)
    return data_dict

data_dict = build_data_dict_by_trial_type(cohort_dfs, trial_type_key, trial_name_col_in_df=TRIAL_NAME_COL)


def _rename_col_with_suffix(col, file_type, new_suffix_str, rename_dict_full, merge_key="animal"):
    """
    Per-trial column rename: (1) map using rename_dict_full[file_type] (key in col -> base name),
    (2) append new_suffix from trial_type_key so names are unique. Subject column stays 'animal'.
    """
    if file_type not in rename_dict_full:
        return col
    base_name = None
    for key in list(rename_dict_full[file_type].keys()):
        if key in col:
            base_name = rename_dict_full[file_type][key]
            break
    if base_name is None:
        return col + new_suffix_str
    if base_name == merge_key:
        return merge_key
    if base_name.endswith("_"):
        base_name = base_name.rstrip("_") + new_suffix_str
    else:
        base_name = base_name + new_suffix_str
    return base_name


def apply_rename_to_data_dict(data_dict, rename_dict_full, trial_type_key):
    """
    Rename columns using rename_dict_full and new_suffix from trial_type_key so each column
    has a unique name (e.g. latency_s_1, latency_s_2). Only trial types in rename_dict_full
    are processed. Each day_df is split by Trial:, renamed per trial with that trial's
    new_suffix, and replaced with the list of those trial DataFrames.
    """
    key = trial_type_key.copy()
    key.columns = [str(c).strip().lower().replace(" ", "_") for c in key.columns]
    trial_type_col = "trial_type"
    protocol_day_col = "protocol_day"
    trial_num_col = "trial_num"
    new_suffix_col = "new_suffix"
    if new_suffix_col not in key.columns:
        raise ValueError(f"trial_type_key must have column '{new_suffix_col}' for unique column names.")
    for cohort in data_dict:
        for tt in ["Spatial", "Probe", "Visible"]:
            if tt not in rename_dict_full:
                continue
            key_tt = key[key[trial_type_col].astype(str).str.strip().str.capitalize() == tt]
            if key_tt.empty:
                continue
            key_tt = key_tt.sort_values([protocol_day_col, trial_num_col])
            new_suffixes = key_tt[new_suffix_col].astype(str).tolist()
            trial_dfs = []
            trial_idx = 0
            for day_df in data_dict[cohort][tt]:
                day_df = day_df.copy()
                if "RUNDATEx:" in day_df.columns and "RUNTIMEx:" in day_df.columns:
                    day_df = _change_time_cols(day_df, "RUNDATEx:", "RUNTIMEx:")
                for trial_number in sorted(day_df["Trial:"].dropna().unique()):
                    if trial_idx >= len(new_suffixes):
                        break
                    trial_rows = day_df[day_df["Trial:"] == trial_number].copy()
                    if trial_rows.empty:
                        trial_idx += 1
                        continue
                    date_col = next((col for col in trial_rows.columns if col.startswith("RUNDATEx")), None)
                    time_col = next((col for col in trial_rows.columns if col.startswith("RUNTIMEx:")), None)
                    if date_col is not None and time_col is not None:
                        trial_rows[date_col] = pd.to_datetime(trial_rows[date_col], errors="coerce")
                        trial_rows[date_col] = trial_rows[date_col].dt.strftime("%m/%d/%Y")
                        trial_rows[time_col] = trial_rows[time_col].apply(format_time_anymaze)
                        trial_rows["datetime_trial"] = pd.to_datetime(
                            trial_rows[date_col].astype(str) + " " + trial_rows[time_col].astype(str),
                            errors="coerce",
                        )
                    new_suffix_str = new_suffixes[trial_idx]
                    trial_rows.columns = [
                        _rename_col_with_suffix(c, tt, new_suffix_str, rename_dict_full)
                        for c in trial_rows.columns
                    ]
                    trial_idx += 1
                    trial_dfs.append(trial_rows)
            data_dict[cohort][tt] = trial_dfs
    return data_dict


data_dict = apply_rename_to_data_dict(data_dict, rename_dict_full, trial_type_key)


def _allowed_columns_for_trial_type(file_type, rename_dict_full, merge_key="animal"):
    """Set of base names that are valid for this trial type (from rename_dict_full)."""
    if file_type not in rename_dict_full:
        return set()
    allowed = set()
    for v in rename_dict_full[file_type].values():
        v = str(v).strip()
        if v.endswith("_"):
            allowed.add(v.rstrip("_"))
        else:
            allowed.add(v)
    allowed.add(merge_key)
    return allowed


def _keep_renamed_columns_only(df, allowed_bases, merge_key="animal"):
    """Keep only columns that were renamed from rename_dict_full (match allowed base names)."""
    keep = []
    for col in df.columns:
        if col == merge_key:
            keep.append(col)
            continue
        for base in allowed_bases:
            if col == base or col.startswith(base + "_"):
                keep.append(col)
                break
    return df[[c for c in df.columns if c in keep]].copy()


def build_wide_dataframe(data_dict, rename_dict_full, merge_key="animal"):
    """
    Build one wide DataFrame per cohort from data_dict (after apply_rename_to_data_dict).
    - One row per subject (merge_key).
    - Columns = all trial columns with unique names (only columns that were renamed via rename_dict_full).
    - Trial types Spatial, Probe, Visible are merged on merge_key.
    """
    result = {}
    for cohort, type_lists in data_dict.items():
        wide_parts = []
        for file_type in ["Spatial", "Probe", "Visible"]:
            if file_type not in type_lists or file_type not in rename_dict_full:
                continue
            trial_dfs = type_lists[file_type]
            if not trial_dfs:
                continue
            allowed_bases = _allowed_columns_for_trial_type(file_type, rename_dict_full, merge_key)
            trimmed = [
                _keep_renamed_columns_only(t.copy(), allowed_bases, merge_key)
                for t in trial_dfs
            ]
            trimmed = [t for t in trimmed if merge_key in t.columns and not t.empty]
            if not trimmed:
                continue
            type_wide = reduce(
                lambda left, right: pd.merge(left, right, on=merge_key, how="outer"),
                trimmed,
            )
            wide_parts.append(type_wide)
        if not wide_parts:
            result[cohort] = pd.DataFrame()
            continue
        result[cohort] = reduce(
            lambda left, right: pd.merge(left, right, on=merge_key, how="outer"),
            wide_parts,
        )
    return result


wide_by_cohort = build_wide_dataframe(data_dict, rename_dict_full)

# Add genotype and treatment from genotype_diet_file (columns: animal, genotype, treatment)
if genotype_diet_file and os.path.isfile(genotype_diet_file):
    genotype_df = pd.read_csv(str(genotype_diet_file))
    merge_cols = [c for c in ["animal", "genotype", "treatment"] if c in genotype_df.columns]
    if len(merge_cols) > 1:  # need at least animal + one of genotype/treatment
        genotype_df = genotype_df[merge_cols].drop_duplicates(subset=["animal"])
        for cohort in wide_by_cohort:
            df = wide_by_cohort[cohort]
            if isinstance(df, pd.DataFrame) and not df.empty and "animal" in df.columns:
                wide_by_cohort[cohort] = df.merge(genotype_df, on="animal", how="left")

    
wide_by_cohort['pi_name'] = 'Burke'
wide_by_cohort['protocol_id'] = 'Burke_WM_1'
wide_by_cohort['lights_on'] = '7:00'
wide_by_cohort['lights_off'] = '19:00'
wide_by_cohort['index_calc_type'] = 'Gall_SearchError'
wide_by_cohort['tracking_system'] = 'Watermaze'
wide_by_cohort['pool_diam'] = '184'
wide_by_cohort['rat_source'] = 'NIA'
wide_by_cohort['sex'] = 'M'
# wide_by_cohort.dropna(how='all', inplace=True)
wide_by_cohort = compute_cumulative_time(wide_by_cohort['1'], prefix="datetime_trial_", dropStart=False)
wide_by_cohort['animal'] = wide_by_cohort['animal'].astype(str) + '.SB'


outpath = current_directory
wide_by_cohort.to_csv(outpath / "burke.csv", index=False)