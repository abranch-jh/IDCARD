import chardet
import pandas as pd
import os
import json
import re
import glob

def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        raw_data = file.read()  # Read the first 10,000 bytes (you can adjust this size)
        result = chardet.detect(raw_data)
    return result['encoding']

def convert_to_military_time(time_str, time_of_day):
    try:
        # Ensure the time_str is a string and not a float (e.g., NaN)
        if isinstance(time_str, str):
            # Check if the time is already in 24-hour format (e.g., '13:23')
            hour_part = int(time_str.split(":")[0])
            
            if 0 <= hour_part <= 23:
                # If the hour is in 24-hour format, return the time as is
                return pd.to_datetime(time_str, format='%H:%M').strftime('%H:%M')
            else:
                # Otherwise, assume it's in 12-hour format and append AM/PM
                return pd.to_datetime(time_str + ' ' + time_of_day, format='%I:%M %p').strftime('%H:%M')
        else:
            # If time_str is not a string, return None
            return None
    except ValueError:
        # Handle cases where the time is invalid
        return None

def generate_protocol_time(repeat_count):
    all_sequences = []  # This will hold all the repeated sequences
    
    # First pattern: Two increments of 60, followed by an increment of 86400
    def generate_one_cycle(start):
        cycle = []
        cycle.append(start + 60)
        cycle.append(cycle[-1] + 60)
        cycle.append(cycle[-1] + 86400)
        return cycle
    
    # Generate the full sequence based on repeat_count
    for _ in range(repeat_count):
        sequence = [0]  # Start each cycle from 0
        for _ in range(8):  # Repeat the first pattern 8 times
            sequence.extend(generate_one_cycle(sequence[-1]))
        
        # Second pattern: Increment by 60 (6 times)
        for _ in range(5):
            sequence.append(sequence[-1] + 60)
        
        all_sequences.extend(sequence)  # Add the full sequence (starting from 0)

    return all_sequences


def compute_cumulative_time(df, prefix, dropStart=False):
    """
    Computes the cumulative time in seconds from the beginning of each trial for each subject.
    
    Parameters:
    - df (pd.DataFrame): The input DataFrame containing datetime columns.
    - prefix (str): The prefix used for trial datetime columns, e.g. "datetime_trial_".
    - dropStart: default is False, if true the start_time column will be dropped
    
    Returns:
    - pd.DataFrame: Updated DataFrame with cumulative time columns added.
    """
    # Step 1: Identify trial columns dynamically
    trial_cols = [col for col in df.columns if col.startswith(prefix)]
    
    if not trial_cols:
        raise ValueError(f"No columns found with prefix '{prefix}'")

    # Step 2: Convert columns to datetime format (if needed)
    # print(df[trial_cols])
    df[trial_cols] = df[trial_cols].apply(pd.to_datetime)
    # print(df[trial_cols])

    # Step 3: Compute cumulative time in seconds for each trial
    for i, col in enumerate(trial_cols):
        trial_num = col.split('_')[-2] + col.split('_')[-1]  # Extract the trial number
        
        # Find the earliest timestamp for that row
        min_time = df[trial_cols].min(axis=1)
        
        # Compute the cumulative time
        if i == 0:  # For the first trial, set cumulative time to 0
            df[f"cumulative_time_{trial_num}"] = 0.0
        else:
            # Compute cumulative time for subsequent trials
            # df[f"cumulative_time_{trial_num}"] = (df[col] - min_time).dt.total_seconds()
            df[f"cumulative_time_{trial_num}"] = ((df[col] - min_time).dt.total_seconds()).astype(int)

    if dropStart:
        df.drop(columns=["start_time"], inplace=True)

    return df

def format_time_anymaze(time_str):
    if pd.isna(time_str) or time_str == '':
        return ''
    time_str = time_str.rstrip(':')  # Remove trailing colon
    parts = time_str.split(':')
    if len(parts) == 2:
        hour, minute = parts
        second = '00'  # Default seconds to '00'
    elif len(parts) == 3:
        hour, minute, second = parts
    else:
        return time_str  # Return as is if format is unexpected

    # Ensure two-digit hour and minute
    hour = hour.zfill(2)
    minute = minute.zfill(2)
    
    
    # Return formatted time
    return f"{hour}:{minute}"

def standardize_dates(column):
    # Ensure the input is a Series
    column = pd.Series(column)

    # First attempt with specific format
    dates = pd.to_datetime(column, format='%m/%d/%Y', errors='coerce')

    # Second attempt for remaining NaT values with general parsing
    remaining_dates = pd.to_datetime(column, errors='coerce')

    # Combine the two results, using general parsing for NaT in the first attempt
    dates = dates.fillna(remaining_dates)

    # Convert to date format
    return dates.dt.date

def remove_trailing_colon(value):
    if isinstance(value, str) and value.endswith(':'):
        return value.rstrip(':')
    else:
        if isinstance(value, str) and value.endswith(';'):
            return value.rstrip(';')
    return value

# def edit_column_names(col, file_type, trial_type_counter, rename_dict_full):
#     for key in list(rename_dict_full[file_type].keys()):
#         if key in col:
#             base_name = rename_dict_full[file_type][key]
#             if "_" in base_name:
#                 base_name = f"{base_name}{trial_type_counter}"   # Reformat to the desired pattern
#                 print(base_name)
#             break
#     return base_name

def edit_column_names(col, file_type, trial_type_counter, rename_dict_full):
    base_name = col  # Initialize base_name with the original column name
    for key in list(rename_dict_full[file_type].keys()):
        if key in col:
            base_name = rename_dict_full[file_type][key]
            if "_" in base_name:
                base_name = f"{base_name}{trial_type_counter}"  # Reformat to the desired pattern
                # print(base_name)  # Debug print (you can remove it later)
            break  # Exit loop after the first match
    return base_name

def rename_trial_num_cols(df, trial_type_key):
    trial_num_cols = [col for col in df.columns if "trial_" in col]
    for trial_num, suffix in zip(trial_type_key['trial_num'], trial_type_key['old_suffix']):
        trial_num_column = [col for col in trial_num_cols if col.endswith(suffix)]
        df[trial_num_column] = trial_num
    return df

def get_data(file_path, PI):
    trial_type_key = pd.read_csv(os.path.join(file_path, fr"keys\trial_type_key_{PI}.csv")) #TODO make this an input statement or simple gui
    
    encoding = detect_encoding(os.path.join(file_path, fr"keys\{PI}.json"))

    try: 
        with open(os.path.join(file_path, fr"keys\{PI}.json"), 'r', encoding=encoding) as f, open(os.path.join(file_path, fr"keys\{PI}_utf8.json"), 'w', encoding='utf-8') as e:
            text = f.read() # for small files, for big use chunks
            e.write(text)
        os.remove(os.path.join(file_path, fr"keys\{PI}.json")) # remove old encoding file
        os.rename(os.path.join(file_path, fr"keys\{PI}_utf8.json"), os.path.join(file_path, fr"keys\{PI}.json")) # rename new encoding
    except UnicodeDecodeError:
        print('Decode Error')
    except UnicodeEncodeError:
        print('Encode Error')
    with open(os.path.join(file_path, fr"keys\{PI}.json"), "r") as json_file:
        data = json.load(json_file)

    rename_dict_full = {'Spatial': data["Spatial"], "Probe": data["Probe"], "Visible": data["Visible"]}

    return trial_type_key, rename_dict_full

def get_files_barnes(file_path):
    spatial_file_lists = [file for file in glob.glob(os.path.join(file_path, '*Spatial*'))] + [file for file in glob.glob(os.path.join(file_path, '*AQ*'))]

    probe_file_lists = [file for file in glob.glob(os.path.join(file_path, '*Probe*'))]

    cue_file_lists = [file for file in glob.glob(os.path.join(file_path, '*Visible*'))] + [file for file in glob.glob(os.path.join(file_path, '*Cue*'))]

    info_file_lists = [file for file in glob.glob(os.path.join(file_path, '*Info*'))]

    file_lists = [(spatial_file_lists, "Spatial"), (probe_file_lists, "Probe"), (cue_file_lists, "Visible"), (info_file_lists, "Info")]
    # print(spatial_file_lists, probe_file_lists)
    return file_lists

def get_files_rapp(file_path):
    spatial_file_lists = [file for file in glob.glob(os.path.join(file_path, '*Spatial*'))] + [file for file in glob.glob(os.path.join(file_path, '*AQ*'))]

    probe_file_lists = [file for file in glob.glob(os.path.join(file_path, '*Probe*'))]

    cue_file_lists = [file for file in glob.glob(os.path.join(file_path, '*Visible*'))] + [file for file in glob.glob(os.path.join(file_path, '*Cue*'))]


    file_lists = [(spatial_file_lists, "Spatial"), (probe_file_lists, "Probe"), (cue_file_lists, "Visible")]
    # print(spatial_file_lists, probe_file_lists)
    return file_lists

def get_files_by_experiment_barnes(directory):
    # Define patterns for identifying different types of CSV files
    csv_patterns = {
        "Info": "*_Info.csv",  # Updated to match Info files correctly
        "Spatial": "*_Spatial*.csv",  # Match Spatial files
        "Probe": "*_Probe*.csv",  # Match Probe files
        "Visible": "*_Visible[0-9]*.csv",  # Match Visible files
    }

    # Dictionary to hold the files categorized by experiment and type
    file_dict = {}

    # Iterate through each pattern to gather files
    for key, pattern in csv_patterns.items():
        # Use glob to find files matching the pattern
        full_pattern = os.path.join(directory, pattern)
        # print(f"Using pattern: {full_pattern}")  # Debugging output

        files = glob.glob(full_pattern)
        # print(f"Found files for {key}: {files}")  # Debugging output

        # Group files by their experiment prefix
        for filepath in files:
            filename = os.path.basename(filepath)
            # Extract the experiment prefix (e.g., '01_01.18.2016_')
            prefix = "_".join(filename.split("_")[:2])  # This combines the first two parts of the filename to form the prefix.
            # Normalize the key for "visible" files by removing trailing digits
            if key == "Visible":
                if re.search(r'_Visible\d*\.csv$', filename):
                    file_dict.setdefault(prefix, {}).setdefault("Visible", []).append(filepath)
            else:
                file_dict.setdefault(prefix, {}).setdefault(key, []).append(filepath)

    return file_dict


def get_files_by_experiment_rapp(directory):

    file_dict = {}

    # Iterate through each file in the directory
    for filepath in glob.glob(os.path.join(directory, '*.csv')):
        filename = os.path.basename(filepath)
        
        # Extract the experiment prefix from the filename
        prefix = filename.split('.')[0]  # This gets the prefix from the filename
        
        # Determine the file type based on presence of specific strings
        file_type = None
        if 'AQ' in filename:
            file_type = 'Spatial'
        elif 'Probe' in filename:
            file_type = 'Probe'
        elif 'Cue' in filename:
            file_type = 'Visible'

        # If file_type is determined, add it to the dictionary
        if file_type:
            file_dict.setdefault(prefix, {}).setdefault(file_type, []).append(filepath)

    return file_dict


def change_time_cols(df):
    df['Date:'] = pd.to_datetime(df['Date:'], format='%m/%d/%Y', errors='coerce').dt.date
    time_columns = [col for col in df.columns if 'Time' in col]
    for col in time_columns:
        df[col] = df[col].apply(remove_trailing_colon)
    df['Time:'] = df.apply(lambda row: convert_to_military_time(row['Time:'], row['Time of day:']), axis=1)
    return df

def create_combined_df(files):
    combined_dfs = []
    for file in files:
        # Detect encoding of the file
        encoding = detect_encoding(file)
        
        # Read the CSV file with the detected encoding
        df = pd.read_csv(file, header=0, encoding=encoding)
        df.columns = [f"{col}:" for col in df.columns]
        
        # Append the DataFrame to the list
        combined_dfs.append(df)
        
    return combined_dfs


# def compute_cumulative_time(df, date_cols, time_cols, dropStart=False):
#     """
#     Computes the cumulative time in seconds from the first trial for each subject
#     using separate date and time columns.
    
#     Parameters:
#     - df (pd.DataFrame): The input DataFrame containing date and time columns.
#     - date_cols (list): List of columns containing date information.
#     - time_cols (list): List of columns containing time information.
#     - dropStart (bool): Default is False, if True, the start_time column will be dropped.
    
#     Returns:
#     - pd.DataFrame: Updated DataFrame with cumulative time columns added.
#     """
#     # Step 1: Combine date and time columns into a single datetime column for each trial
#     trial_cols = []
    
#     if len(date_cols) != len(time_cols):
#         raise ValueError("Date and time column lists must be of the same length")
    
#     for date_col, time_col in zip(date_cols, time_cols):
#         # Combine the date and time columns into a single datetime column
#         trial_col = pd.to_datetime(df[date_col] + ' ' + df[time_col])
#         trial_cols.append(trial_col)
    
#     # Add the trial columns to the dataframe
#     df["trial_datetime"] = pd.concat(trial_cols, axis=1).min(axis=1)

#     # Step 2: Find the first trial start time
#     df["start_time"] = df["trial_datetime"]

#     # Step 3: Compute cumulative time in seconds for each trial
#     for i, trial_col in enumerate(trial_cols):
#         trial_num = i + 1  # Trial numbers starting from 1
#         df[f"cumulative_time_{trial_num}"] = (trial_col - df["start_time"]).dt.total_seconds()

#     if dropStart:
#         df.drop(columns=["start_time"], inplace=True)

#     return df