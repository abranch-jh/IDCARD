# -*- coding: utf-8 -*-
"""
Created on Tue Feb 10 19:07:50 2026

@author: abranch6
"""
#rapp_file = r"Z:\audrey\watermazeDatabase\gui_code\water_maze\preprocessing\rapp\combined_data_rapp.csv"
#barnes_file = r"Z:\audrey\watermazeDatabase\gui_code\water_maze\preprocessing\barnes\combined_data_barnes.csv"
#mcquail_file = r"Z:\audrey\watermazeDatabase\gui_code\water_maze\preprocessing\mquail\mcquail_data.csv"
#gallagher_file = r"Z:\audrey\watermazeDatabase\gui_code\water_maze\preprocessing\gallagher\gallagher_data_passedCue.csv"

import numpy as np
import pandas as pd
import os
from pathlib import Path
import json
import glob
import re
import matplotlib.pyplot as plt
from scipy.stats import sem, t

#Z:\audrey\watermazeDatabase\gui_code\final\combined

#top_folder = r"Z:\audrey\watermazeDatabase\gui_code\water_maze\preprocessing"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
top_folder = PROJECT_ROOT
file_list = glob.glob(str(top_folder / "*" / "*.csv"))
print(file_list)
key_file = PROJECT_ROOT / "combined" / "shared_keys" / "shared_keys.json"
#print(file_list)

meters_per_sec_labs = ['Barnes', 'Rapp', 'Burke']
cm_per_sec_labs = ['Gallagher', 'McQuail']
distance_columns = ['dist', 'speed']

with open(str(key_file), 'r') as f:
    key_data = json.load(f)

def apply_column_renames(df: pd.DataFrame, key_data, dataset_name: str) -> pd.DataFrame:
    """
    For a given dataset:
      - Metadata: exact column rename (key -> value)
      - Trials: prefix replacement in column names (key prefix -> value prefix)
    """
    if dataset_name not in key_data:
        return df

    mapping = key_data[dataset_name]

    # 1) Metadata: simple rename
    meta_map = mapping.get("Metadata", {})
    if isinstance(meta_map, dict):
        df = df.rename(columns=meta_map)

    # 2) Trials: prefix-based rename
    trials_map = mapping.get("Trials", {})
    new_columns = {}
    for col in df.columns:
        new_col = col
        for old_prefix, new_prefix in trials_map.items():
            if old_prefix in new_col:              # or new_col.startswith(old_prefix)
                new_col = new_col.replace(old_prefix, new_prefix)
        new_columns[col] = new_col

    df = df.rename(columns=new_columns)
    return df

def get_column_keys(key_data, dataset_name):
    """Collect all source column names (keys) from Metadata and Trials for a dataset."""
    if dataset_name not in key_data:
        return set()
    mapping = key_data[dataset_name]
    keys = set()
    for section in ("Metadata", "Trials"):
        if section in mapping and isinstance(mapping[section], dict):
            keys.update(mapping[section].keys())
    return keys


def select_columns_by_keys(df, column_keys, match="contains"):
    """
    Keep only columns whose names are in column_keys or contain one of them.
    match: "exact" = column name must be in column_keys;
           "contains" = keep column if any key is a substring of the column name (e.g. trial_num_ matches trial_num_1).
    """
    column_keys = set(column_keys)
    if match == "exact":
        keep = [c for c in df.columns if c in column_keys]
    else:
        keep = [c for c in df.columns if any(k in c for k in column_keys)]
    return df[[c for c in keep if c in df.columns]].copy()


def convert_cm_per_sec_to_m_per_sec(df: pd.DataFrame, column_substrings: list) -> pd.DataFrame:
    """
    Convert columns whose names contain any of column_substrings from cm/s to m/s (divide by 100).
    Only modifies numeric columns.
    """
    cols_to_convert = [
        c for c in df.columns
        if any(sub in c for sub in column_substrings) and pd.api.types.is_numeric_dtype(df[c])
    ]
    if cols_to_convert:
        df = df.copy()
        df[cols_to_convert] = df[cols_to_convert] / 100.0
    return df


# Example: map folder name (from path) to key_data key (e.g. "barnes" -> "Barnes")
def dataset_name_from_path(filepath, key_data):
    folder = os.path.basename(os.path.dirname(filepath))
    for key in key_data:
        if folder.lower() == key.lower():
            return key
    return None

dataframes = {}
for filepath in file_list:
    name = os.path.basename(filepath)
    df = pd.read_csv(filepath)
    dataset = dataset_name_from_path(filepath, key_data)
    if dataset is not None:
        keys = get_column_keys(key_data, dataset)
        df = select_columns_by_keys(df, keys, match="contains")
        df = apply_column_renames(df, key_data, dataset)
        if dataset in cm_per_sec_labs:
            df = convert_cm_per_sec_to_m_per_sec(df, distance_columns)

    # --- normalize sex column here ---
    if 'sex' in df.columns:
        col = df['sex'].astype(str).str.strip()
        lower = col.str.lower()
        df['sex'] = np.where(
            lower == 'male', 'M',
            np.where(lower == 'female', 'F', col)
        )

    dataframes[name] = df


def plot_var_vs_time(
    df: pd.DataFrame,
    variable_prefix: str,
    time_prefix: str,
    id_col: str = "animal",
    subjects_to_plot: list | None = None,
):
    """
    Reshape wide trial columns to long and plot cumulative value vs time.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame containing the data.
    variable_prefix : str
        Prefix for columns representing the variable to plot (e.g. 'dist_mean_s_').
    time_prefix : str
        Prefix for columns representing the time axis (e.g. 'cumulative_time_s_').
    id_col : str, default 'animal'
        Column used as subject identifier. Must exist in df.
    subjects_to_plot : list or None
        Optional list of subject IDs to plot. If None, all subjects are used.
    """
    if id_col not in df.columns:
        raise ValueError(f"id_col '{id_col}' not found in DataFrame columns")

    var_cols = [c for c in df.columns if variable_prefix in c]
    time_cols = [c for c in df.columns if time_prefix in c]
    if not var_cols or not time_cols:
        raise ValueError("No matching variable or time columns found for given prefixes.")

    variable_long = pd.melt(
        df,
        id_vars=[id_col],
        value_vars=var_cols,
        var_name="trial",
        value_name="value",
    )
    trial_meta = variable_long["trial"].astype(str).str.extract(r"_([spc])_(\d+)$", flags=re.IGNORECASE)
    variable_long["trial_type"] = trial_meta[0].str.lower()
    variable_long["trial_number"] = pd.to_numeric(trial_meta[1], errors="coerce").astype("Int64")

    time_long = pd.melt(
        df,
        id_vars=[id_col],
        value_vars=time_cols,
        var_name="trial",
        value_name="time",
    )
    trial_meta_t = time_long["trial"].astype(str).str.extract(r"_([spc])_(\d+)$", flags=re.IGNORECASE)
    time_long["trial_type"] = trial_meta_t[0].str.lower()
    time_long["trial_number"] = pd.to_numeric(trial_meta_t[1], errors="coerce").astype("Int64")

    merged_df = pd.merge(variable_long, time_long, on=[id_col, "trial_type", "trial_number"])
    if merged_df.empty:
        raise ValueError("No rows after merging value and time columns; check prefixes.")

    merged_df["value"] = pd.to_numeric(merged_df["value"], errors="coerce")
    merged_df["time"] = pd.to_numeric(merged_df["time"], errors="coerce")
    merged_df = merged_df.dropna(subset=["value", "time"])
    if merged_df.empty:
        raise ValueError("All values/time became NaN after conversion; nothing to plot.")

    if subjects_to_plot is not None:
        merged_df = merged_df[merged_df[id_col].isin(subjects_to_plot)]
    if merged_df.empty:
        raise ValueError("No data left after filtering by subjects_to_plot.")

    merged_df = merged_df.dropna(subset=["trial_type", "trial_number"])
    if merged_df.empty:
        raise ValueError("No typed trial columns matched pattern '_s_#', '_p_#', or '_c_#'.")

    plt.figure(figsize=(10, 6))
    type_labels = {"s": "Spatial", "p": "Probe", "c": "Visible"}
    type_styles = {
        "s": {"color": "tab:blue", "marker": "o"},
        "p": {"color": "tab:orange", "marker": "s"},
        "c": {"color": "tab:green", "marker": "^"},
    }
    for trial_type, type_df in merged_df.groupby("trial_type"):
        # Average across subjects at each timepoint for this trial type, then cumsum.
        agg = (
            type_df.groupby("time", as_index=False)["value"]
            .mean()
            .sort_values("time")
        )
        if agg.empty:
            continue
        cum_vals = np.cumsum(agg["value"].to_numpy())
        style = type_styles.get(trial_type, {"color": None, "marker": "o"})
        plt.plot(
            agg["time"],
            cum_vals,
            marker=style["marker"],
            color=style["color"],
            alpha=0.9,
            label=type_labels.get(trial_type, trial_type),
        )

    plt.xlabel(f"{time_prefix} (time units)")
    plt.ylabel(f"Cumulative {variable_prefix}")
    plt.title(f"{variable_prefix} vs {time_prefix} by trial type")
    plt.grid(alpha=0.3)
    plt.legend(title="Trial type")
    plt.tight_layout()
    plt.show()


def compute_error(age_group_data: pd.DataFrame, stat: str):
    """Computes SEM, standard deviation, or 95% confidence interval across rows."""
    if stat == "sem":
        return sem(age_group_data, axis=0, nan_policy="omit")
    elif stat == "std":
        return age_group_data.std(axis=0, ddof=1)
    elif stat == "95ci":
        sample_size = age_group_data.count(axis=0)  # Non-NaN count for each column
        t_value = t.ppf(0.975, df=sample_size - 1)  # 95% CI t-critical value
        return sem(age_group_data, axis=0, nan_policy="omit") * t_value
    else:
        raise ValueError("Invalid stat option. Choose 'sem', 'std', or '95ci'.")


def plot_cumulative_distance(df_aq: pd.DataFrame,
                             df_probe: pd.Series | pd.DataFrame,
                             ages: pd.Series,
                             title: str,
                             stat: str = "sem"):
    """
    Plot mean cumulative distance across trials by age group, with error bars, plus probe points.

    Parameters
    ----------
    df_aq : DataFrame
        Cumulative trial data, shape (n_subjects, n_trials).
    df_probe : Series or 1-column DataFrame
        Final probe cumulative distance per subject.
    ages : Series
        Age (or age group) per subject, aligned with df_aq rows.
    title : str
        Plot title.
    stat : {'sem', 'std', '95ci'}, default 'sem'
        Error metric to show as shaded band.
    """
    # Ensure alignment
    if len(df_aq) != len(ages):
        raise ValueError("Length of df_aq and ages must match.")

    if isinstance(df_probe, pd.DataFrame):
        if df_probe.shape[1] != 1:
            raise ValueError("df_probe should be a Series or 1-column DataFrame.")
        df_probe = df_probe.iloc[:, 0]

    unique_ages = np.sort(ages.dropna().unique())
    colors = plt.cm.viridis(np.linspace(0, 1, len(unique_ages)))
    age_color_map = dict(zip(unique_ages, colors))

    plt.figure(figsize=(10, 6))

    # Build x-axis labels from column names, e.g. dist_mean_s_3 -> s_3
    x_labels = []
    for i, col in enumerate(df_aq.columns, start=1):
        m = re.search(r"_(s_\d+)$", str(col))
        x_labels.append(m.group(1) if m else f"s_{i}")
    x_pos = np.arange(len(x_labels))
    probe_x = len(x_labels)

    for age in unique_ages:
        mask = ages == age
        age_group_data = df_aq.loc[mask]

        mean_values = age_group_data.mean(axis=0)
        error_values = compute_error(age_group_data, stat)

        plt.plot(x_pos, mean_values, color=age_color_map[age], label=f"{age} mo", lw=2)
        plt.fill_between(
            x_pos,
            mean_values - error_values,
            mean_values + error_values,
            color=age_color_map[age],
            alpha=0.2,
        )

        # Probe trial scatter points
        probe_vals = df_probe.loc[mask].values.ravel()
        plt.scatter(
            [probe_x] * len(probe_vals),
            probe_vals,
            color=age_color_map[age],
            edgecolor="black",
            alpha=0.7,
            s=30,
        )

    x_labels_with_probe = list(x_labels) + ["probe"]
    plt.xticks(np.arange(len(x_labels_with_probe)), x_labels_with_probe, rotation=45)

    plt.legend(title="Age Group", bbox_to_anchor=(1, 1), fontsize=8)
    plt.xlabel("Cumulative Distance Keys")
    plt.ylabel("Cumulative Distance")
    plt.title(title)
    plt.tight_layout()
    plt.show()



def prepare_cumulative_distance_inputs(
    df: pd.DataFrame,
    cum_prefix: str = "dist_cum",   # or "dist_cum_" depending on your schema
    age_col: str = "age_mo",
):
    """
    From a wide trial DataFrame, construct df_aq, df_probe, ages for plot_cumulative_distance.

    Parameters
    ----------
    df : DataFrame
        One dataset (e.g. Gallagher) with wide trial columns.
    cum_prefix : str
        Prefix for cumulative distance columns (e.g. "ttr_cum_dist_").
    age_col : str
        Column name holding age for each subject.

    Returns
    -------
    df_aq : DataFrame
        Per-subject cumulative spatial distance per trial (n_subjects x n_trials).
    df_probe : Series
        Per-subject final probe cumulative distance.
    ages : Series
        Per-subject age values aligned with df_aq / df_probe rows.
    """
    if age_col not in df.columns:
        raise ValueError(f"Age column '{age_col}' not found")

    # 1) Find spatial and probe cumulative-distance columns
    spatial_cols = [c for c in df.columns if cum_prefix in c and "_s_" in c]
    probe_cols   = [c for c in df.columns if cum_prefix in c and "_p_" in c]

    if not spatial_cols or not probe_cols:
        raise ValueError("No spatial or probe cumulative-distance columns found")

    # 2) Sort spatial / probe columns by trial number (…_s_1, …_s_2, …)
    def trial_key(col: str) -> int:
        m = re.search(r"_(s|p)_(\d+)$", col)
        return int(m.group(2)) if m else 0

    spatial_cols = sorted(spatial_cols, key=trial_key)
    probe_cols   = sorted(probe_cols,   key=trial_key)

    # 3) Build spatial cumulative per trial (df_aq)
    #    First take raw cumulative-distance per trial, then cumsum across trials for each subject
    spatial_raw = df[spatial_cols]                    # shape: n_subjects x n_trials
    df_aq = spatial_raw.cumsum(axis=1)                # cumulative across trials

    # 4) Probe cumulative distance: use the last probe trial column
    df_probe = df[probe_cols[-1]]                     # Series, length n_subjects

    # 5) Ages aligned with rows
    ages = df[age_col]

    return df_aq, df_probe, ages


# df_gall = dataframes['gallagher.csv']

# df_aq, df_probe, ages = prepare_cumulative_distance_inputs(
#     df_gall,
#     cum_prefix="dist_cum",   # or your actual prefix
#     age_col="age_mo",
# )

# plot_cumulative_distance(df_aq, df_probe, ages,
#                          "Mean Cumulative Distance by Age Group (SEM)",
#                          stat="sem")



# def split_trials_by_suffix(df):
#     spatial = {}  # 's' trials
#     probe = {}    # 'p' trials
#     visible = {}  # 'c' trials

#     for col in df.columns:
#         # Only look at trial columns (those that came from the Trials mapping)
#         # If you have a list of base Trial keys, you can check that here too.
#         if '_s_' in col:
#             spatial[col] = df[col]
#         elif '_p_' in col:
#             probe[col] = df[col]
#         elif '_c_' in col:
#             visible[col] = df[col]

#     return {
#         'Spatial': spatial,
#         'Probe': probe,
#         'Visible': visible,
#     }

# # Apply to all your DataFrames
# trials_subdicts = {}  # one entry per file
# for name, df in dataframes.items():
#     trials_subdicts[name] = split_trials_by_suffix(df)