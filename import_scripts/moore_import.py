# -*- coding: utf-8 -*-
"""
Moore import.

Loads the already-wide young and aged CSVs from moore/rat_data, remaps trial
suffixes using trial_type_key_y_moore.csv / trial_type_key_a_moore.csv, adds
IDCARD metadata, and writes moore/moore.csv.
"""

import re
from pathlib import Path

import pandas as pd

try:
    from import_tools import load_df
except ModuleNotFoundError:
    from import_scripts.import_tools import load_df

PROJECT_ROOT = Path(__file__).resolve().parents[1]
current_directory = PROJECT_ROOT / "moore"
rat_data_dir = current_directory / "rat_data"
keys_dir = current_directory / "keys"

YOUNG_FILE = rat_data_dir / "moore_young_data.csv"
AGED_FILE = rat_data_dir / "moore_aged_data.csv"
YOUNG_KEY_FILE = keys_dir / "trial_type_key_y_moore.csv"
AGED_KEY_FILE = keys_dir / "trial_type_key_a_moore.csv"

TYPE_LETTER = {
    "spatial": "s",
    "probe": "p",
    "visible": "c",
    "cue": "c",
}

TRIAL_COL_RE = re.compile(r"^(?P<stem>.+)_(?P<ttype>[spc])_(?P<num>\d+)$")
STEM_RENAME = {
    "cum_dist": "dist_cum",
    "dist": "dist_total",
    "datetime": "datetime_trial",
    "time_of_day": "time",
}

METADATA_CONSTANTS = {
    "pi_name": "Moore",
    "species": "mouse",
    "subsequent_measures": "yes",
    "lights_on": "7:00",
    "lights_off": "19:00",
    "index_calc_type": "N/A",
    "tracking_system": "Watermaze",
    "rat_source": "custom",
    "housing": "Paired",
    "pool_diam": "120",
    "acclimation": "5 days handling",
    "tracking_marker": "no",
    "light_level": "high",
}


def _load_trial_type_key(path):
    key = pd.read_csv(path)
    key.columns = [str(c).strip().lower().replace(" ", "_") for c in key.columns]
    return key


def _old_trial_id(row):
    """Source CSVs label spatial/visible by trial_num and probes by protocol_day."""
    ttype = TYPE_LETTER[str(row["trial_type"]).strip().lower()]
    if ttype == "p":
        return ttype, int(row["protocol_day"])
    return ttype, int(row["trial_num"])


def _rename_trial_stems(df):
    rename = {}
    for col in df.columns:
        match = TRIAL_COL_RE.match(str(col))
        if not match:
            continue
        stem = STEM_RENAME.get(match.group("stem"), match.group("stem"))
        rename[col] = f"{stem}_{match.group('ttype')}_{match.group('num')}"
    return df.rename(columns=rename)


def _remap_suffixes_with_key(df, trial_type_key):
    """Rename {stem}_{s|p|c}_{source_num} using new_suffix from the trial-type key."""
    mapping = {}
    for _, row in trial_type_key.iterrows():
        mapping[_old_trial_id(row)] = str(row["new_suffix"]).lstrip("_")

    rename = {}
    unmatched = []
    for col in df.columns:
        match = TRIAL_COL_RE.match(str(col))
        if not match:
            continue
        key = (match.group("ttype"), int(match.group("num")))
        if key not in mapping:
            unmatched.append(col)
            continue
        rename[col] = f"{match.group('stem')}_{mapping[key]}"
    if unmatched:
        print(f"Unmapped trial columns (not in trial-type key): {unmatched}")
    return df.rename(columns=rename)


def _add_trial_num_columns(df, trial_type_key):
    existing_suffixes = set()
    for col in df.columns:
        match = TRIAL_COL_RE.match(str(col))
        if match:
            existing_suffixes.add(f"{match.group('ttype')}_{match.group('num')}")

    for _, row in trial_type_key.iterrows():
        suffix = str(row["new_suffix"]).lstrip("_")
        if suffix in existing_suffixes:
            df[f"trial_num_{suffix}"] = int(row["trial_num"])
    return df


def _watermaze_date(df):
    date_cols = [c for c in df.columns if TRIAL_COL_RE.match(str(c)) and str(c).startswith("date_")]
    if not date_cols:
        return pd.Series(pd.NA, index=df.index)
    parsed = df[date_cols].apply(pd.to_datetime, errors="coerce")
    return parsed.min(axis=1).dt.strftime("%m/%d/%Y")


def _format_time_columns(df):
    time_cols = [c for c in df.columns if TRIAL_COL_RE.match(str(c)) and str(c).startswith("time_")]
    for col in time_cols:
        parsed = pd.to_datetime(df[col], format="%I:%M %p", errors="coerce")
        still_na = parsed.isna() & df[col].notna()
        if still_na.any():
            parsed.loc[still_na] = pd.to_datetime(df.loc[still_na, col], format="%H:%M", errors="coerce")
        df[col] = parsed.dt.strftime("%H:%M")
    return df


def compute_cumulative_time_skip_nans(df, prefix="datetime_trial_"):
    trial_cols = [c for c in df.columns if str(c).startswith(prefix)]
    if not trial_cols:
        return df
    df = df.copy()
    df[trial_cols] = df[trial_cols].apply(pd.to_datetime, errors="coerce")
    min_time = df[trial_cols].min(axis=1)
    for col in trial_cols:
        match = TRIAL_COL_RE.match(str(col))
        suffix = f"{match.group('ttype')}_{match.group('num')}" if match else str(col).rsplit("_", 2)[-1]
        df[f"cumulative_time_{suffix}"] = (df[col] - min_time).dt.total_seconds()
    return df


def format_moore_wide(df, trial_type_key, protocol_id):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    if "subject_id" in df.columns:
        df["subject_id"] = df["subject_id"].astype(str).str.replace("*", "", regex=False).str.strip()
        df["subject_id"] = df["subject_id"].where(
            df["subject_id"].str.endswith(".SM"),
            df["subject_id"] + ".SM",
        )
        df["animal"] = df["subject_id"]
    if "age" in df.columns:
        df["age_mo"] = pd.to_numeric(df["age"], errors="coerce")
        df = df.drop(columns=["age"])
    if "sex" in df.columns:
        sex = df["sex"].astype(str).str.strip()
        lower = sex.str.lower()
        df["sex"] = sex.where(~lower.isin(["male", "female"]), lower.map({"male": "M", "female": "F"}))

    df = _rename_trial_stems(df)
    df = _remap_suffixes_with_key(df, trial_type_key)
    df = _format_time_columns(df)
    df["watermaze_date"] = _watermaze_date(df)
    df["protocol_id"] = protocol_id
    for col, value in METADATA_CONSTANTS.items():
        df[col] = value
    df = _add_trial_num_columns(df, trial_type_key)
    return df


young_key = _load_trial_type_key(YOUNG_KEY_FILE)
aged_key = _load_trial_type_key(AGED_KEY_FILE)

df_young = format_moore_wide(load_df(str(YOUNG_FILE)), young_key, "Moore_WM_young")
df_aged = format_moore_wide(load_df(str(AGED_FILE)), aged_key, "Moore_WM_aged")
print(f"Loaded young {df_young.shape} from {YOUNG_FILE}")
print(f"Loaded aged {df_aged.shape} from {AGED_FILE}")

wide_final = pd.concat([df_young, df_aged], ignore_index=True, sort=False)
wide_final = compute_cumulative_time_skip_nans(wide_final, prefix="datetime_trial_")

outpath = current_directory / "moore.csv"
wide_final.to_csv(outpath, index=False)
print(f"Wrote {len(wide_final)} animals to {outpath}")
