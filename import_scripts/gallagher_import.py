# -*- coding: utf-8 -*-
"""
Gallagher import.

Loads HVS BL1/IN1/TR1 exports into a long-format table, assigns trial types
from keys/trial_type_key_gallagher.csv, pivots to wide format with
{base}_{s|p|c}_{n} columns, and writes gallagher/gallagher.csv.
"""

import re
from functools import reduce
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from import_tools import get_data, load_df
except ModuleNotFoundError:
    from import_scripts.import_tools import get_data, load_df

PROJECT_ROOT = Path(__file__).resolve().parents[1]
current_directory = PROJECT_ROOT / "gallagher"
rat_data_dir = current_directory / "rat_data"

trial_type_key, rename_dict_full = get_data(str(current_directory), current_directory.name)

TRIAL_COLUMNS = ["NUMBER", "GROUP", "TRIAL", "DAY", "BLOCK", "COND", "RUNDATE",
                 "LAT", "SPEED", "PATH", "CUMDS", "TAVDS"]
INDEX_COLUMNS = ["NUMBER", "GROUP", "YEAR", "AGE", "IDX30_3"]
BLOCK_COLUMNS = ["NUMBER", "GROUP", "BLOCK", "COND", "BSPEEDTT", "TAVDS30",
                 "TTPATH", "TTLAT", "TMQUADB", "TMQUADD", "ANCROSB", "ANCROSD"]
COND_TO_TYPE = {"TT": "Spatial", "FS": "Probe", "CUE": "Visible"}
TRIAL_NAME_COL = "trial_num_cum"
merge_key = "animal"


def _files_ending_with(folder, suffix):
    folder = Path(folder)
    suffix = suffix.lower()
    return [str(p) for p in folder.iterdir() if p.is_file() and p.name.lower().endswith(suffix)]


def _normalize_columns(df):
    df = df.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df


def _norm_id(series):
    s = series.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    return s


def _select_existing(df, columns):
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise KeyError(f"Missing columns {missing}")
    return df.loc[:, columns].copy()


def _protocol_day(day_series):
    s = day_series.astype(str).str.strip().str.upper()
    s = s.replace({"CT": "9"})
    s = s.str.replace(r"\.0$", "", regex=True)
    s = s.str.lstrip("0").replace({"": "0"})
    return pd.to_numeric(s, errors="coerce")


def _cohort_ids_from_index_file(index_file):
    prefix = Path(index_file).name.split("_")[0]
    year = prefix[:2]
    month = prefix[2:][-2:]
    return year, month


def _repair_rundate_years(trial_df):
    trial_df = trial_df.copy()
    for idx, row in trial_df.iterrows():
        parts = str(row["RUNDATE"]).split("/")
        if len(parts) != 3:
            continue
        try:
            year_part = int(parts[-1])
        except ValueError:
            continue
        group = str(row["GROUP"])
        if year_part < 10 and parts[-1] != group:
            trial_df.at[idx, "RUNDATE"] = str(row["RUNDATE"]).replace(parts[-1], group)
    return trial_df


def _assign_protocol_dates(trial_df, year_yy):
    """Overwrite days 1–8 from the earliest rundate + day offset (same as original script)."""
    trial_df = trial_df.copy()
    start = str(trial_df["RUNDATE"].min())
    try:
        start_mon, start_day, _ = start.split("/")
        start_day = int(start_day)
    except (ValueError, AttributeError):
        trial_df["rundate"] = trial_df["RUNDATE"].astype(str)
        return trial_df

    day = _protocol_day(trial_df["DAY"])
    new_day = start_day + (day.fillna(1) - 1)
    assigned = start_mon + "/" + new_day.astype("Int64").astype(str) + "/" + year_yy
    trial_df["rundate"] = trial_df["RUNDATE"].astype(str)
    overwrite = day.between(1, 8)
    trial_df.loc[overwrite, "rundate"] = assigned[overwrite]
    return trial_df


def _assign_trial_numbers(trial_df):
    trial_df = trial_df.copy()
    cond = trial_df["COND"].astype(str).str.strip().str.upper()
    block = pd.to_numeric(trial_df["BLOCK"], errors="coerce").replace({7: 5})
    trial = pd.to_numeric(trial_df["TRIAL"], errors="coerce")

    spatial_n = trial + (block - 1) * 5
    probe_n = trial + block - 6
    cue_n = trial

    trial_df["trial_type"] = cond.map(COND_TO_TYPE)
    trial_df["block"] = block.astype("Int64")
    trial_df["protocol_day"] = _protocol_day(trial_df["DAY"])
    trial_df.loc[cond == "CUE", "protocol_day"] = 9
    trial_df["trial_num_cum"] = np.select(
        [cond == "TT", cond == "FS", cond == "CUE"],
        [spatial_n + (spatial_n - 1) // 5, probe_n * 6, 24 + cue_n],
        default=np.nan,
    )
    return trial_df


def _find_complete_cohort_folders(base_path):
    folders = [p for p in Path(base_path).glob("*/*/*data") if p.is_dir()]
    complete = []
    for folder in folders:
        if "skipped" in folder.as_posix().lower():
            continue
        missing = [s for s in ("BL1.csv", "IN1.csv", "TR1.csv") if not _files_ending_with(folder, s)]
        if missing:
            print(f"Folder missing files: {folder}")
            print(f"Missing: {', '.join('*' + m for m in missing)}")
        else:
            complete.append(folder)
    return complete


def _build_subject_table(index_df, year, month, cohort_name, watermaze_date):
    index_df = index_df.copy()
    index_df["NUMBER"] = _norm_id(index_df["NUMBER"])
    index_df["IDX30_3"] = pd.to_numeric(index_df["IDX30_3"], errors="coerce")
    index_df = index_df[index_df["IDX30_3"].fillna(0) != 0]
    age = index_df["AGE"].astype(str).str.strip().str.upper()
    subjects = pd.DataFrame({
        "animal": year + month + "-" + index_df["NUMBER"] + ".MG",
        "subject_id": year + month + "-" + index_df["NUMBER"] + ".MG",
        "hvs_number": index_df["NUMBER"],
        "age": np.where(age == "O", 24, 6),
        "sex": "female" if "f" in cohort_name else "male",
        "strain": "Long Evans",
        "genotype": "WT",
        "watermaze_date": watermaze_date,
        "calculated_index": index_df["IDX30_3"],
        "source_id": "CharlesRiver",
    })
    return subjects


def _reshape_block_averages(block_df, subjects):
    block_df = block_df.copy()
    block_df["NUMBER"] = _norm_id(block_df["NUMBER"])
    block_df["BLOCK"] = pd.to_numeric(block_df["BLOCK"], errors="coerce").replace({7: 5})
    block_df = block_df[block_df["BLOCK"].fillna(0) != 0]
    block_df = block_df.merge(subjects[["hvs_number", "animal"]], left_on="NUMBER", right_on="hvs_number", how="inner")

    rows = []
    for _, row in block_df.iterrows():
        cond = str(row["COND"]).strip().upper()
        if cond == "TT":
            prefix = f"t_b{int(row['BLOCK'])}"
        elif cond == "CUE":
            prefix = f"c_b{int(row['BLOCK'])}"
        else:
            continue
        rows.append({
            "animal": row["animal"],
            f"avg_duration_{prefix}": row["TTLAT"],
            f"avg_speed_{prefix}": row["BSPEEDTT"],
            f"avg_path_length_{prefix}": row["TTPATH"],
            f"avg_cum_dist_{prefix}": row["TAVDS30"],
            f"avg_time_target_{prefix}": row["TMQUADB"],
            f"avg_time_opposite_{prefix}": row["TMQUADD"],
            f"annulus_crossing_target_{prefix}": row["ANCROSB"],
            f"annulus_crossing_opp_{prefix}": row["ANCROSD"],
        })
    if not rows:
        return pd.DataFrame(columns=["animal"])
    wide = pd.DataFrame(rows)
    return wide.groupby("animal", as_index=False).first()


def load_gallagher_long(base_path):
    """Read each HVS cohort into its own long-format table.

    Cohorts are kept separate so later animal-key merges cannot explode when
    male/female groups from the same month share MG.YYMM-NUMBER IDs.
    """
    cohort_dfs = {}
    block_by_cohort = {}
    for folder in _find_complete_cohort_folders(base_path):
        try:
            block_file = _files_ending_with(folder, "BL1.csv")[0]
            index_file = _files_ending_with(folder, "IN1.csv")[0]
            trial_file = _files_ending_with(folder, "TR1.csv")[0]
            trial_df = _select_existing(_normalize_columns(load_df(trial_file)), TRIAL_COLUMNS)
            index_df = _select_existing(_normalize_columns(load_df(index_file)), INDEX_COLUMNS)
            block_df = _select_existing(_normalize_columns(load_df(block_file)), BLOCK_COLUMNS)
        except (IndexError, KeyError, ValueError) as exc:
            print(f"Skipping {folder}: {exc}")
            continue

        year, month = _cohort_ids_from_index_file(index_file)
        trial_df["NUMBER"] = _norm_id(trial_df["NUMBER"])
        trial_df["BLOCK"] = pd.to_numeric(trial_df["BLOCK"], errors="coerce")
        trial_df = trial_df[trial_df["BLOCK"].fillna(0) != 0]
        if trial_df.empty:
            continue

        trial_df = _repair_rundate_years(trial_df)
        trial_df = _assign_protocol_dates(trial_df, year)
        trial_df = _assign_trial_numbers(trial_df)
        trial_df = trial_df[trial_df["trial_type"].notna() & trial_df["trial_num_cum"].notna()]

        watermaze_date = trial_df["rundate"].min()
        cohort_folder = Path(block_file).parent.parent.name
        subjects = _build_subject_table(index_df, year, month, cohort_folder, watermaze_date)
        if subjects.empty:
            continue

        trial_df = trial_df.merge(subjects, left_on="NUMBER", right_on="hvs_number", how="inner")
        trial_df["ttr_duration"] = pd.to_numeric(trial_df["LAT"], errors="coerce")
        trial_df["ttr_mean_speed"] = pd.to_numeric(trial_df["SPEED"], errors="coerce")
        trial_df["ttr_dist"] = pd.to_numeric(trial_df["PATH"], errors="coerce")
        trial_df["ttr_cum_dist"] = pd.to_numeric(trial_df["CUMDS"], errors="coerce")
        trial_df["ttr_cum_dist_mean"] = pd.to_numeric(trial_df["TAVDS"], errors="coerce")
        trial_df = trial_df.drop_duplicates(subset=["animal", "trial_num_cum"], keep="first")

        cohort_key = f"{Path(folder).parent.parent.name}_{cohort_folder}"
        cohort_dfs[cohort_key] = trial_df
        block_by_cohort[cohort_key] = _reshape_block_averages(block_df, subjects)
        #print(f"Loaded {folder} ({len(subjects)} animals)")

    if not cohort_dfs:
        raise RuntimeError(f"No complete Gallagher cohorts found under {base_path}")
    return cohort_dfs, block_by_cohort


def build_data_dict_by_trial_type(cohort_dfs, trial_type_key, trial_name_col_in_df="trial_num_cum", protocol_day_col_in_df="protocol_day"):
    """Organize cohort DataFrames into data_dict[cohort][trial_type] = list of day DataFrames."""
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


def _allowed_original_columns(file_type, rename_dict_full, merge_key="animal", sample_columns=None):
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
    """Merge trial slices on animal. One row per animal in each slice, or the join explodes."""
    cleaned = []
    for d in df_list:
        if d is None or d.empty or merge_key not in d.columns:
            continue
        cleaned.append(d.drop_duplicates(subset=[merge_key], keep="first"))
    if not cleaned:
        return pd.DataFrame()
    return reduce(lambda left, right: pd.merge(left, right, on=merge_key, how=how), cleaned)


def _strip_trial_suffix(s):
    if not s:
        return s
    s = str(s).strip().replace(" ", "_")
    return re.sub(r"_(s|p|c)_\d+$", "", s)


TRIAL_COLUMN_NAMES = frozenset({"trial", "trial_num", "trial_num_cum", "trial_type"})


def _base_name_for_column(col, file_type, rename_dict_full):
    raw = str(col).strip().replace(" ", "_")
    if raw in TRIAL_COLUMN_NAMES:
        return raw
    if file_type not in rename_dict_full:
        return _strip_trial_suffix(raw)
    keys_sorted = sorted(rename_dict_full[file_type].keys(), key=lambda k: -len(str(k)))
    for key in keys_sorted:
        if key in col:
            base = str(rename_dict_full[file_type][key]).strip().rstrip("_").replace(" ", "_")
            if len(base) > 2 and base[-2] == "_" and base[-1] in ("s", "p", "c"):
                base = base[:-2]
            return base
    return _strip_trial_suffix(raw)


def build_wide_by_cohort(data_dict, rename_dict_full, merge_key="animal"):
    wide_by_cohort = {}
    for experiment_prefix, file_lists in data_dict.items():
        wide_df_parts = []
        for file_type, files in file_lists.items():
            if len(files) == 0:
                continue
            trial_type_counter = 1
            trial_rows_dfs = []
            sample_cols = files[0].columns if files else []
            trial_col = next((c for c in ["trial_num", "_trial_num", "Trial:"] if c in sample_cols), None)
            if trial_col is None:
                continue
            type_prefix = {"Spatial": "s", "Probe": "p", "Visible": "c"}.get(file_type, "t")
            for day_df in files:
                day_df = day_df.copy()
                if trial_col not in day_df.columns:
                    continue
                for trial_number in sorted(day_df[trial_col].dropna().unique()):
                    trial_rows = day_df[day_df[trial_col] == trial_number].copy()
                    if trial_rows.empty:
                        continue
                    trial_rows = trial_rows.drop_duplicates(subset=[merge_key], keep="first")
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
            if trial_rows_dfs and all(merge_key in d.columns for d in trial_rows_dfs):
                wide_df_parts.append(_merge_on_key(trial_rows_dfs, merge_key))
        wide_by_cohort[experiment_prefix] = _merge_on_key(wide_df_parts, merge_key) if wide_df_parts else pd.DataFrame()
    return wide_by_cohort


def _add_info_columns_to_wide(wide_by_cohort, cohort_dfs, rename_dict_full, merge_key="animal"):
    if "Info" not in rename_dict_full:
        return wide_by_cohort
    info_map = rename_dict_full["Info"]
    for cohort, wide_df in list(wide_by_cohort.items()):
        if not isinstance(wide_df, pd.DataFrame) or wide_df.empty or cohort not in cohort_dfs:
            continue
        source = cohort_dfs[cohort]
        if merge_key not in source.columns:
            continue
        one_per_animal = source.drop_duplicates(subset=merge_key, keep="first").copy()
        keep_cols = [merge_key]
        rename_map = {}
        for col in one_per_animal.columns:
            if col == merge_key:
                continue
            if col in info_map:
                keep_cols.append(col)
                rename_map[col] = info_map[col]
                continue
            for key in info_map:
                if str(key) in str(col):
                    keep_cols.append(col)
                    rename_map[col] = info_map[key]
                    break
        if len(keep_cols) <= 1:
            continue
        info_df = one_per_animal[keep_cols].rename(columns=rename_map)
        overlap = [c for c in info_df.columns if c in wide_df.columns and c != merge_key]
        if overlap:
            info_df = info_df.drop(columns=overlap)
        if info_df.shape[1] > 1:
            wide_by_cohort[cohort] = wide_df.merge(info_df, on=merge_key, how="left")
    return wide_by_cohort


def _add_protocol_time_columns(df, trial_type_key):
    key = trial_type_key.copy()
    key.columns = [str(c).strip().lower().replace(" ", "_") for c in key.columns]
    if "new_suffix2" not in key.columns or "protocol_time" not in key.columns:
        return df
    df = df.copy()
    for _, row in key.iterrows():
        df[f"protocol_time{row['new_suffix2']}"] = row["protocol_time"]
    return df


cohort_dfs, block_by_cohort = load_gallagher_long(rat_data_dir)
data_dict = build_data_dict_by_trial_type(
    cohort_dfs, trial_type_key, trial_name_col_in_df=TRIAL_NAME_COL, protocol_day_col_in_df="protocol_day"
)
_trim_data_dict_columns(data_dict, rename_dict_full, merge_key)
wide_by_cohort = build_wide_by_cohort(data_dict, rename_dict_full, merge_key)
wide_by_cohort = _add_info_columns_to_wide(wide_by_cohort, cohort_dfs, rename_dict_full, merge_key=merge_key)

for cohort, wide_df in list(wide_by_cohort.items()):
    block_df = block_by_cohort.get(cohort)
    if isinstance(wide_df, pd.DataFrame) and not wide_df.empty and isinstance(block_df, pd.DataFrame) and not block_df.empty:
        block_df = block_df.drop_duplicates(subset=[merge_key], keep="first")
        wide_by_cohort[cohort] = wide_df.merge(block_df, on=merge_key, how="left")

wide_frames = [df for df in wide_by_cohort.values() if isinstance(df, pd.DataFrame) and not df.empty]
if not wide_frames:
    raise RuntimeError("Wide-format conversion produced no cohort tables")
wide_final = pd.concat(wide_frames, ignore_index=True, sort=False)

wide_final["pi_name"] = "Gallagher"
wide_final["species"] = "rat"
wide_final["watermaze_protocol_id"] = "Gallagher_WM_1"
wide_final["protocol_id"] = "Gallagher_WM_1"
wide_final["subsequent_measures"] = "No"
wide_final["index_calc_type"] = "Gall_SearchError"
wide_final["tracking_system"] = "HVS"
wide_final["light_on"] = "7:00"
wide_final["light_off"] = "19:00"
wide_final["lights_on"] = "7:00"
wide_final["lights_off"] = "19:00"
wide_final["housing"] = "Single"
wide_final["pool_diam"] = "184"
wide_final["probe_weight_p_2"] = 1.26
wide_final["probe_weight_p_3"] = 1.43
wide_final["probe_weight_p_4"] = 1.43
if "subject_id" not in wide_final.columns:
    wide_final["subject_id"] = wide_final["animal"]

wide_final = _add_protocol_time_columns(wide_final, trial_type_key)

cue_cols = [f"ttr_duration_c_{i}" for i in range(1, 7)]
if all(c in wide_final.columns for c in cue_cols):
    wide_final["avg_visible_latency"] = wide_final[cue_cols].mean(axis=1)

outpath = current_directory / "gallagher.csv"
wide_final.to_csv(outpath, index=False)
#print(f"Wrote {len(wide_final)} animals to {outpath}")
