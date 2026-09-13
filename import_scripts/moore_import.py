# -*- coding: utf-8 -*-
"""
Moore import.

Reads young and aged trial data from the Moore Excel workbook (sheets whose
names contain 'young' or 'aged'), maps trials with age-specific trial-type
keys, and writes moore_young.csv and moore_aged.csv.

Animal IDs have trailing '*' stripped before grouping subjects.
"""

import re
from datetime import datetime, time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MOORE_DIR = PROJECT_ROOT / "moore"
EXCEL_FILE = MOORE_DIR / "rat_data" / "raw_data_Acarbose 5xFAD WMW.xlsx"

COHORT_CONFIG = {
    "young": {
        "key_file": MOORE_DIR / "keys" / "trial_type_key_y_moore.csv",
        "output_file": MOORE_DIR / "moore_young.csv",
        "sheets": {
            "spatial": "training young",
            "visible": "visible young",
            "probe": "probe young",
        },
        "metadata": {
            "protocol_id": "Moore_WM_young",
            "age_mo": 7,
        },
    },
    "aged": {
        "key_file": MOORE_DIR / "keys" / "trial_type_key_a_moore.csv",
        "output_file": MOORE_DIR / "moore_aged.csv",
        "sheets": {
            "spatial": "training aged",
            "visible": "visible aged",
            "probe": "probe aged",
        },
        "metadata": {
            "protocol_id": "Moore_WM_aged",
            "age_mo": 24,
        },
    },
}

TRAINING_COLUMNS = {
    "Animal": "animal_raw",
    "Cage": "cage",
    "Hole Punch": "hole_punch",
    "Genotype": "genotype",
    "Diet": "treatment",
    "Sex": "sex",
    "Cohort": "cohort",
    "Date": "date",
    "Time": "clock_time",
    "Day": "day",
    "Trial": "trial",
    "Trial duration": "duration",
    "Distance travelled (cm)": "dist_total",
    "Average speed": "mean_speed",
    "Cumulative Proximity": "dist_cum",
}

PROBE_COLUMNS = {
    "subject_id": "animal_raw",
    "cage": "cage",
    "hole_punch": "hole_punch",
    "age": "age_mo",
    "genotype": "genotype",
    "treatment": "treatment",
    "sex": "sex",
    "cohort": "cohort",
    "date": "date",
    "time_of_day": "clock_time",
    "day": "day",
    "trial": "trial",
    "dist_cm": "dist_total",
    "avg_speed": "mean_speed",
    "cum_dist": "dist_cum",
}

VISIBLE_COLUMNS = {
    **TRAINING_COLUMNS,
    "age": "age_mo",
}

WIDE_METRICS = ["dist_total", "mean_speed", "dist_cum", "duration", "date", "clock_time", "trial_num"]
META_COLUMNS = ["genotype", "treatment", "sex", "cohort", "cage", "hole_punch", "age_mo"]
SUFFIX_RE = re.compile(r"^[spc]_\d+$")
TRIAL_COL_RE = re.compile(r"^(?P<stem>.+)_(?P<ttype>[spc])_(?P<num>\d+)$")

SHARED_METADATA = {
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


def load_trial_type_key(path):
    key = pd.read_csv(path)
    key.columns = [str(c).strip().lower().replace(" ", "_") for c in key.columns]
    key["trial_type"] = key["trial_type"].astype(str).str.strip().str.lower()
    key["new_suffix"] = key["new_suffix"].astype(str).str.lstrip("_")
    return key


def normalize_subject_id(value):
    subject = str(value).replace("*", "").strip()
    if not subject or subject.lower() == "nan":
        return pd.NA
    if not subject.endswith(".SM"):
        subject = f"{subject}.SM"
    return subject


def normalize_sex(value):
    if pd.isna(value):
        return pd.NA
    sex = str(value).strip()
    if not sex or sex.lower() == "nan":
        return pd.NA
    lower = sex.lower()
    if lower in {"male", "m"}:
        return "M"
    if lower in {"female", "f"}:
        return "F"
    return sex


def normalize_date(value):
    if pd.isna(value):
        return pd.NA
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return pd.NA
    return parsed.strftime("%m/%d/%Y")


def normalize_clock_time(value):
    if pd.isna(value):
        return pd.NA
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, (pd.Timestamp, datetime)):
        return pd.Timestamp(value).strftime("%H:%M")

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return pd.NA

    parsed = pd.to_datetime(text, format="%I:%M %p", errors="coerce")
    if pd.isna(parsed):
        parsed = pd.to_datetime(text, format="%H:%M:%S", errors="coerce")
    if pd.isna(parsed):
        parsed = pd.to_datetime(text, format="%H:%M", errors="coerce")
    if pd.isna(parsed):
        return pd.NA
    return parsed.strftime("%H:%M")


def clean_sheet(df):
    id_col = "subject_id" if "subject_id" in df.columns else "Animal"
    cleaned = df[df[id_col].notna()].copy()
    cleaned = cleaned[~cleaned[id_col].astype(str).str.contains("Smoothing", na=False)]
    return cleaned, id_col


def _first_valid(series):
    valid = series.dropna()
    valid = valid[~valid.astype(str).str.strip().str.lower().eq("nan")]
    if valid.empty:
        return pd.NA
    return valid.iloc[0]


def accumulate_subject_metadata(df, metadata_store):
    for col in META_COLUMNS:
        if col not in df.columns:
            continue
        for subject_id, group in df.groupby("subject_id", sort=False):
            if subject_id not in metadata_store:
                metadata_store[subject_id] = {}
            if col in metadata_store[subject_id]:
                continue
            value = _first_valid(group[col])
            if pd.notna(value):
                metadata_store[subject_id][col] = value


def read_sheet(path, sheet_name, trial_type, metadata_store=None):
    df = pd.read_excel(path, sheet_name=sheet_name)
    df, _ = clean_sheet(df)

    if trial_type == "spatial":
        rename_map = {k: v for k, v in TRAINING_COLUMNS.items() if k in df.columns}
    elif trial_type == "probe":
        df.columns = [str(c).strip() for c in df.columns]
        rename_map = {k: v for k, v in PROBE_COLUMNS.items() if k in df.columns}
    else:
        rename_map = {k: v for k, v in VISIBLE_COLUMNS.items() if k in df.columns}

    df = df.rename(columns=rename_map)
    df["subject_id"] = df["animal_raw"].map(normalize_subject_id)
    df = df.dropna(subset=["subject_id"])

    if "sex" in df.columns:
        df["sex"] = df["sex"].map(normalize_sex)
    if "age_mo" in df.columns:
        df["age_mo"] = pd.to_numeric(df["age_mo"], errors="coerce")

    if metadata_store is not None:
        accumulate_subject_metadata(df, metadata_store)

    df = df.dropna(subset=["day", "trial"])
    df["day"] = pd.to_numeric(df["day"], errors="coerce")
    df["trial"] = pd.to_numeric(df["trial"], errors="coerce")
    df = df.dropna(subset=["day", "trial"])
    df["day"] = df["day"].astype(int)
    df["trial"] = df["trial"].astype(int)

    if "date" in df.columns:
        df["date"] = df["date"].map(normalize_date)
    if "clock_time" in df.columns:
        df["clock_time"] = df["clock_time"].map(normalize_clock_time)

    return df


def assign_suffix(day, trial, trial_type, trial_type_key, cohort):
    if trial_type == "spatial":
        matches = trial_type_key[
            (trial_type_key["trial_type"] == "spatial") & (trial_type_key["protocol_day"] == day)
        ].sort_values("trial_num")
        if len(matches) < trial:
            raise ValueError(f"No spatial suffix for cohort={cohort}, day={day}, trial={trial}")
        return matches.iloc[trial - 1]["new_suffix"]

    if trial_type == "probe":
        probes = trial_type_key[trial_type_key["trial_type"] == "probe"].sort_values("protocol_day")
        if len(probes) < day:
            raise ValueError(f"No probe suffix for cohort={cohort}, day={day}")
        return probes.iloc[day - 1]["new_suffix"]

    visible = trial_type_key[trial_type_key["trial_type"] == "visible"].sort_values("trial_num")
    index = (trial - 1) if cohort == "young" else (day - 1)
    if len(visible) <= index:
        raise ValueError(f"No visible suffix for cohort={cohort}, day={day}, trial={trial}")
    return visible.iloc[index]["new_suffix"]


def suffix_to_trial_num(suffix, trial_type_key):
    match = trial_type_key[trial_type_key["new_suffix"] == suffix]
    if match.empty:
        return pd.NA
    return int(match.iloc[0]["trial_num"])


def sheet_to_long(path, sheet_name, trial_type, trial_type_key, cohort, metadata_store=None):
    df = read_sheet(path, sheet_name, trial_type, metadata_store)
    if df.empty:
        return pd.DataFrame()

    rows = []
    for _, row in df.iterrows():
        suffix = assign_suffix(row["day"], row["trial"], trial_type, trial_type_key, cohort)
        record = {
            "subject_id": row["subject_id"],
            "suffix": suffix,
            "dist_total": row.get("dist_total"),
            "mean_speed": row.get("mean_speed"),
            "dist_cum": row.get("dist_cum"),
            "duration": row.get("duration"),
            "date": row.get("date"),
            "clock_time": row.get("clock_time"),
            "trial_num": suffix_to_trial_num(suffix, trial_type_key),
        }
        for col in META_COLUMNS:
            if col in row.index:
                record[col] = row[col]
        rows.append(record)

    return pd.DataFrame(rows)


def aggregate_subject_metadata(long_df, metadata_store=None):
    meta_fields = [c for c in META_COLUMNS if c in long_df.columns]
    records = []
    for subject_id, group in long_df.groupby("subject_id", sort=False):
        record = {"subject_id": subject_id}
        stored = metadata_store.get(subject_id, {}) if metadata_store else {}
        for col in meta_fields:
            value = _first_valid(group[col])
            if pd.isna(value) and col in stored:
                value = stored[col]
            record[col] = value
        records.append(record)
    return pd.DataFrame(records)


def long_to_wide(long_df, metadata_store=None):
    if long_df.empty:
        return pd.DataFrame(columns=["subject_id"])

    meta = aggregate_subject_metadata(long_df, metadata_store)

    wide = meta.set_index("subject_id")
    for metric in WIDE_METRICS:
        if metric not in long_df.columns:
            continue
        pivot = long_df.pivot_table(index="subject_id", columns="suffix", values=metric, aggfunc="first")
        prefix = "time" if metric == "clock_time" else metric
        pivot.columns = [f"{prefix}_{col}" for col in pivot.columns]
        wide = wide.join(pivot)

    wide = wide.reset_index()
    wide["animal"] = wide["subject_id"]
    return wide


def format_dates_and_times(df):
    for col in [c for c in df.columns if c.startswith("date_")]:
        df[col] = df[col].map(normalize_date)

    for col in [c for c in df.columns if c.startswith("time_")]:
        df[col] = df[col].map(normalize_clock_time)
    return df


def add_datetime_trial_columns(df):
    suffixes = set()
    for col in df.columns:
        if not str(col).startswith("date_"):
            continue
        suffix = str(col)[len("date_") :]
        if SUFFIX_RE.match(suffix):
            suffixes.add(suffix)

    for suffix in sorted(suffixes, key=lambda s: (s[0], int(s.split("_")[1]))):
        date_col = f"date_{suffix}"
        time_col = f"time_{suffix}"
        if date_col not in df.columns or time_col not in df.columns:
            continue

        combined = df[date_col].astype(str).str.strip() + " " + df[time_col].astype(str).str.strip()
        parsed = pd.to_datetime(combined, format="%m/%d/%Y %H:%M", errors="coerce")
        still_na = parsed.isna() & df[date_col].notna() & df[time_col].notna()
        if still_na.any():
            parsed.loc[still_na] = pd.to_datetime(combined.loc[still_na], errors="coerce")
        df[f"datetime_trial_{suffix}"] = parsed
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


def watermaze_date(df):
    date_cols = [c for c in df.columns if c.startswith("date_")]
    if not date_cols:
        return pd.Series(pd.NA, index=df.index)
    parsed = df[date_cols].apply(pd.to_datetime, errors="coerce")
    return parsed.min(axis=1).dt.strftime("%m/%d/%Y")


def build_cohort_wide(path, cohort, trial_type_key):
    config = COHORT_CONFIG[cohort]
    metadata_store = {}
    long_parts = [
        sheet_to_long(path, sheet_name, trial_type, trial_type_key, cohort, metadata_store)
        for trial_type, sheet_name in config["sheets"].items()
    ]
    long_df = pd.concat(long_parts, ignore_index=True)
    wide = long_to_wide(long_df, metadata_store)

    default_age = config["metadata"]["age_mo"]
    if "age_mo" not in wide.columns:
        wide["age_mo"] = default_age
    else:
        wide["age_mo"] = pd.to_numeric(wide["age_mo"], errors="coerce").fillna(default_age)

    wide = format_dates_and_times(wide)
    wide = add_datetime_trial_columns(wide)
    wide["watermaze_date"] = watermaze_date(wide)

    for col, value in SHARED_METADATA.items():
        wide[col] = value
    for col, value in config["metadata"].items():
        if col != "age_mo":
            wide[col] = value

    return wide


def trial_counts(df):
    counts = {}
    for letter, label in (("s", "spatial"), ("p", "probe"), ("c", "visible")):
        cols = [c for c in df.columns if c.startswith(f"mean_speed_{letter}_") and df[c].notna().any()]
        counts[label] = len(cols)
    return counts


def run_import():
    if not EXCEL_FILE.is_file():
        raise FileNotFoundError(f"Moore Excel source not found: {EXCEL_FILE}")

    results = {}
    print(f"Loaded Moore data from {EXCEL_FILE}")

    for cohort in ("young", "aged"):
        config = COHORT_CONFIG[cohort]
        trial_type_key = load_trial_type_key(config["key_file"])
        wide = build_cohort_wide(EXCEL_FILE, cohort, trial_type_key)
        wide = compute_cumulative_time_skip_nans(wide, prefix="datetime_trial_")
        wide.to_csv(config["output_file"], index=False)

        counts = trial_counts(wide)
        print(
            f"  {cohort}: spatial={counts['spatial']}, probe={counts['probe']}, "
            f"visible={counts['visible']}, animals={len(wide)}"
        )
        print(f"  Wrote {config['output_file']}")
        results[cohort] = wide

    return results


if __name__ == "__main__":
    run_import()
