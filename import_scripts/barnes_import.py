# -*- coding: utf-8 -*-
"""
Created on Sun Sep  8 13:47:00 2024

@author: abranch6
"""

import os
from pathlib import Path
import pandas as pd
from functools import reduce
import sys
from ..gui.import_tools import *

PROJECT_ROOT = Path(__file__).resolve().parents[1]
current_directory = PROJECT_ROOT / "barnes"

trial_type_key, rename_dict_full = get_data(str(current_directory), current_directory.name)

file_lists = get_files_barnes(str(current_directory / "rat_data" / "raw"))

data_dict = get_files_by_experiment_barnes(str(current_directory / "rat_data" / "raw"))


# List to hold combined DataFrames for different experiments

cohort_sets = []
experiment_name = []

for experiment_prefix, file_lists in data_dict.items():
    experiment_name.append(experiment_prefix)
    wide_df_parts = []
    for file_type, files in file_lists.items():
        if len(files) > 0:
            combined_dfs = create_combined_df(files)

            if file_type == 'Info':
                for df in combined_dfs:
                    df['dob'] = pd.to_datetime(df['Date_Birth:'], format='%m/%d/%Y', errors='coerce').dt.date
                    df['watermaze_date'] = pd.to_datetime(df['Date_Start_SpatialWatermaze:'], format='%m/%d/%Y', errors='coerce').dt.date
                    df = df.rename({'Barnes_ID:': "animal"}, copy=True, axis=1)
                    df = df.drop(["Date_Birth:", "Date_Start_SpatialWatermaze:"], axis=1)
                    wide_df_parts.append(df)
                continue

            trial_type_counter = 1
            trial_rows_dfs = []
            for day_df in combined_dfs:
                day_df = change_time_cols(day_df)
                for trial_number in range(day_df['Trial:'].min(), day_df["Trial:"].max() + 1):
                    trial_rows = day_df[day_df["Trial:"] == trial_number].copy()  

                    date_col = next((col for col in trial_rows.columns if col.startswith('Date:')), None)
                    time_col = next((col for col in trial_rows.columns if col.startswith('Time:')), None)

                    if date_col is not None and time_col is not None:  # Combine date and time into a datetime column if both columns exist
                        # Combine and create the datetime column
                        # trial_rows.loc[:, 'datetime_trial'] = pd.to_datetime(
                        #     trial_rows[date_col].astype(str) + ' ' + trial_rows[time_col].astype(str),
                        #     errors='coerce'
                        # )
                    
                            # Convert the date column to datetime
                            trial_rows[date_col] = pd.to_datetime(trial_rows[date_col])
                            trial_rows[date_col] = trial_rows[date_col].dt.strftime('%m/%d/%Y')
                            
                            trial_rows[time_col] = trial_rows[time_col].apply(format_time_anymaze)

                            trial_rows['datetime_trial'] = pd.to_datetime(trial_rows[date_col].astype(str) + ' ' + trial_rows[time_col])
                            # trial_rows['datetime_trial'] = trial_rows['datetime_trial'].dt.strftime('%Y-%m-%d %H:%M:%S')
                    # print(file_type,trial_type_counter)
                    trial_rows.columns = [edit_column_names(col, file_type, trial_type_counter, rename_dict_full) for col in trial_rows.columns]
                    trial_type_counter += 1
                    trial_rows_dfs.append(trial_rows)

            # Merge all the DataFrames into a single DataFrame
            trial_type_df = reduce(lambda left, right: pd.merge(left, right, on='animal', how='outer'), trial_rows_dfs)

            wide_df_parts.append(trial_type_df)
    cohort_sets.append(wide_df_parts)

all_cohorts = []
for cohort in cohort_sets:
    cohort = reduce(lambda left, right: pd.merge(left, right, on='animal', how='outer'), cohort)
    # print(cohort.shape)
    
    cohort['pi_name'] = 'Barnes'
    cohort['protocol_id'] = 'Barnes_WM_1'
    cohort['lights_on'] = '7:00'
    cohort['lights_off'] = '19:00'
    cohort['index_calc_type'] = 'CIPL'
    cohort['tracking_system'] = 'ANYMaze'
    cohort['pool_diam'] = '184'
    cohort['rat_source'] = 'NIA'
    cohort.dropna(how='all', inplace=True)
    cohort = compute_cumulative_time(cohort, prefix="datetime_trial_", dropStart=False)
    cohort['animal'] = cohort['animal'].astype(str) + '.CB'
    all_cohorts.append(cohort)

outpath = current_directory / "rat_data" / "raw" / "outfiles"

# Ensure both lists have the same length to avoid IndexError
if len(experiment_name) != len(all_cohorts):
    raise ValueError("The length of experiment_name must match the number of cohort DataFrames.")

# Saving each DataFrame with a corresponding name
for i, df in enumerate(all_cohorts):
    # Get the name for the current DataFrame
    cohort_name = experiment_name[i]
    
    # Define the filename, e.g., "experiment_2023_01_01.csv"
    filename = f"{cohort_name}.csv"
    
    # Save the DataFrame to a CSV file
    df.to_csv(outpath + '\\' + filename, index=False)  # Save without the index
    
    print(f"Saved DataFrame {i} as {filename}")

files = glob.glob(outpath + '\\*.csv')

# Initialize an empty list to hold the DataFrames
dataframes = []

# Load each CSV file into a DataFrame and append it to the list
for file in files:
    try:
        df = pd.read_csv(file)
        dataframes.append(df)
        print(f"Loaded {file} with shape {df.shape}")
    except Exception as e:
        print(f"Error loading {file}: {str(e)}")

# Concatenate all loaded DataFrames
try:
    combined_df = pd.concat(dataframes, ignore_index=True)
    print("Successfully concatenated all DataFrames.")
    print("Combined DataFrame shape:", combined_df.shape)

    # Save the combined DataFrame to a new CSV file
    combined_df.to_csv(current_directory + '\\combined_data_barnes.csv', index=False)
    print("Saved combined DataFrame as 'barnes.csv'.")
except Exception as e:
    print(f"Error while concatenating DataFrames: {str(e)}")
