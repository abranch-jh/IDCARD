# -*- coding: utf-8 -*-
"""
Created on Sun Sep 15 10:56:31 2024

@author: abranch6
"""


import os
from pathlib import Path
import pandas as pd
import numpy as np
from functools import reduce
from import_tools import *
import glob

PROJECT_ROOT = Path(__file__).resolve().parents[1]
current_directory = PROJECT_ROOT / "rapp"  

trial_type_key, rename_dict_full = get_data(str(current_directory), current_directory.name)

file_lists = get_files_rapp(str(current_directory / "rat_data" / "raw"))

data_dict = get_files_by_experiment_rapp(str(current_directory / "rat_data" / "raw"))

cohort_sets = []
experiment_name = []

for experiment_prefix, file_lists in data_dict.items():
    experiment_name.append(experiment_prefix)
    wide_df_parts = []
    for file_type, files in file_lists.items():
        if len(files) > 0:
            combined_dfs = create_combined_df(files)
        
            trial_type_counter = 1
            trial_rows_dfs = []
            for day_df in combined_dfs:
    
                day_df = change_time_cols(day_df)
                
                for aq_day in np.unique(day_df["Stage:"].to_numpy()):
                    for trial_number in range(day_df['Trial:'].min(), day_df["Trial:"].max()+1):
                        trial_rows = day_df[(day_df["Trial:"] == trial_number) & (day_df["Stage:"] == aq_day)].copy() 
                        # trial_rows = day_df[day_df["Trial:"] == trial_number].copy()  
                        if trial_rows.shape[0] == 0:
                            continue
                        date_col = next((col for col in trial_rows.columns if col.startswith('Date:')), None)
                        time_col = next((col for col in trial_rows.columns if col.startswith('Time:')), None)
    
                        if date_col is not None and time_col is not None:
                           
                            # Convert the date column to datetime
                            trial_rows[date_col] = pd.to_datetime(trial_rows[date_col])
                            trial_rows[date_col] = trial_rows[date_col].dt.strftime('%m/%d/%Y')
                            
                            trial_rows[time_col] = trial_rows[time_col].apply(format_time_anymaze)

                            trial_rows['datetime_trial'] = pd.to_datetime(trial_rows[date_col].astype(str) + ' ' + trial_rows[time_col])
                            # print(trial_rows['datetime_trial'])
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
    # cohort.columns = [col.lower() for col in cohort.columns]
    
    # cohort = rename_trial_num_cols(cohort, trial_type_key)
 
    cohort['pi_name'] = 'Rapp' 
    cohort['protocol_id'] = 'Rapp_WM_1'
    cohort['strain'] = 'Long Evans'
    cohort['genotype'] = 'WT'
    cohort['sex'] = 'M'
    cohort['subsequent_measures'] = 'no'
    cohort['lights_on'] = '6:30'
    cohort['lights_off'] = '18:30'
    cohort['index_calc_type'] = 'Gall_SearchError'
    cohort['tracking_system'] = 'AnyMaze'
    cohort['rat_source'] = 'Charles River'
    cohort['housing'] = 'Single'
    cohort['pool_diam'] = '184'
    cohort['light_level'] = 'high'
    cohort['acclimation'] = '5 days handling'
    cohort['probe_weight_block2'] = '1.26'
    cohort['probe_weight_block3'] = '1.43'
    cohort['probe_weight_block4'] = '1.43'
    cohort['tracking_marker'] = 'no'
    cohort['animal'] = cohort['animal'].astype(str) + '.PR'


    cohort = compute_cumulative_time(cohort, prefix="datetime_trial_", dropStart=False)
    
    # Remove rows where all values are missing (NA)
    cohort.dropna(how='all', inplace=True)
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
    df.to_csv(outpath / filename, index=False)  # Save without the index
    
    print(f"Saved DataFrame {i} as {filename}")

files = glob.glob(str(outpath / "*.csv"))

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

# Now concatenate all loaded DataFrames
try:
    combined_df = pd.concat(dataframes, ignore_index=True)
    print("Successfully concatenated all DataFrames.")
    print("Combined DataFrame shape:", combined_df.shape)

    # Save the combined DataFrame to a new CSV file
    combined_df.to_csv(current_directory / "combined_data_rapp.csv", index=False)
    print("Saved combined DataFrame as 'combined_data_rapp.csv'.")
except Exception as e:
    print(f"Error while concatenating DataFrames: {str(e)}")


