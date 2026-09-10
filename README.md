
# IDCARD User Guide

## Table of Contents

   - [Overview](#overview)
   - [Installation](#installation)
   - [Project Structure](#project-structure)
   - [Data Pipeline Overview](#data-pipeline-overview)
   - [Column Naming Convention](#column-naming-convention)
   - [Key/Configuration Files](#keyconfiguration-files)
   - [Running the Import Scripts](#running-the-import-scripts)
   - [Launching the GUI](#launching-the-gui)
   - [GUI Walkthrough](#gui-walkthrough)
      - [Open Dialog](#open-dialog)
      - [Filter Panel](#filter-panel)
      - [Data Table](#data-table)
      - [Plotting](#plotting)
      - [Saving Data](#saving-data)
   - [Troubleshooting](#troubleshooting)

---

## Overview

IDCARD (**I**ndividual **D**ifferences in **C**ognitive **A**ging of **R**odent **D**atasets) is a
Python toolkit for preprocessing, integrating, and visualizing rodent Morris Water Maze
datasets collected across multiple laboratories across varying ages and strains. Each lab may use different acquisition
systems, naming conventions, file formats, and protocol structure. IDCARD harmonizes those differences at the level of individual trials
integrated into a single wide-format table and provides an interactive GUI for filtering animals and
trials, inspecting the data, generating plots, and exporting subsets. This collaborative effort is an outcome of the
Collaboratory on Research Definitions for Reserve and Resilience in Cognitive Aging and Dementia 4th Workshop (https://reserveandresilience.com/)
funded by the National Institute on Aging.

How each lab’s raw files are imported, and how that lab’s key files work, is documented in that lab folder’s `README.md`. This file covers installation, the shared column scheme, shared key formats, combining, and the GUI.


### Included Lab Datasets

| PI / Source | Lab (folder name) | Tracking System | Species | Lab README |
|--------------------|-------------|-----------------|---------|------------|
| Barnes           | `barnes`      | ANYMaze         | rat | [barnes/README.md](barnes/README.md) |
| Burke            | `burke`        | Actimetrics Watermaze | rat | [burke/README.md](burke/README.md) |
| Disterhoft       | `disterhoft`  | Actimetrics Watermaze | rat | Pending |
| Foster           | `foster`       | Ethovision      | rat | [foster/README.md](foster/README.md) |
| Gallagher        | `gallagher`   | HVS             | rat | [gallagher/README.md](gallagher/README.md) |
| McQuail          | `mcquail`    | Ethovision      | rat | [mcquail/README.md](mcquail/README.md) |
| Moore            | `moore`       | Actimetrics Watermaze | mouse | [moore/README.md](moore/README.md) |
| Rapp             | `rapp`       | ANYMaze         | rat | [rapp/README.md](rapp/README.md) |

---

## Installation

### Prerequisites

- **Python 3.9 or newer** (the project is developed on Python 3.13)
- **pip**

### Step 1 &mdash; Clone or Copy the Project

If you received the project as a folder (for example, via a
repository clone), simply make sure the entire `IDCARD` directory is accessible on your
machine. Throughout this guide, the project root is referred to as:

```
<your_path>\IDCARD
```

Replace `<your_path>` with the actual location on your system (e.g.
`C:\Users\jsmith\projects\IDCARD`).

### Step 2 &mdash; Create a Virtual Environment (recommended)

Open a terminal and navigate to the project root:

```powershell
cd "<your_path>\IDCARD"
python -m venv .venv
```

Activate the environment:

```powershell
# PowerShell
.\.venv\Scripts\Activate.ps1

# Command Prompt
.\.venv\Scripts\activate.bat
```

### Step 3 &mdash; Install Dependencies

IDCARD depends on the following Python packages:

| Package      | Purpose                                |
|--------------|----------------------------------------|
| `PySide6`    | Qt-based GUI framework                 |
| `pandas`     | Data manipulation and CSV I/O          |
| `numpy`      | Numerical operations                   |
| `matplotlib` | Plotting                               |
| `scipy`      | Statistics (SEM, confidence intervals) |
| `chardet`    | Automatic character-encoding detection |

Install them all at once:

```powershell
pip install PySide6 pandas numpy matplotlib scipy chardet
```

### Step 4 &mdash; Install IDCARD Itself (optional, editable mode)

If you want Python to recognize `import idcard` / `from gui import ...` from any
directory, you can install the package in editable mode:

```powershell
pip install -e .
```

This reads the `pyproject.toml` at the project root and makes the package importable
without changing `PYTHONPATH`.

### Step 5 &mdash; Verify the Installation

```powershell
python -c "from gui.watermaze_gui import FilterApp; print('IDCARD is ready.')"
```

If this prints `IDCARD is ready.` with no errors, everything is set up correctly.

---

## Project Structure

```
IDCARD/
├── pyproject.toml              # Package metadata and build config
├── README.md                   # Shared project documentation (this file)
├── __init__.py
│
├── gui/                        # Interactive GUI application
│   ├── watermaze_gui.py
│   └── import_tools.py
│
├── import_scripts/             # Per-lab raw-data import pipelines
│   ├── import_tools.py
│   ├── barnes_import.py
│   ├── burke_import.py
│   ├── foster_import.py
│   ├── gallagher_import.py
│   ├── mcquail_import.py
│   ├── moore_import.py
│   └── rapp_import.py
│
├── combined/                   # Cross-lab combining and normalization
│   ├── combine_data.py
│   └── shared_keys/
│       ├── shared_keys.json
│       └── trial_type_key_template.csv
│
├── barnes/                     # Each lab folder: README, <lab>.csv, keys/, rat_data/
├── burke/
├── foster/
├── disterhoft/
├── gallagher/
├── mcquail/
├── moore/
└── rapp/
```

Each lab folder contains its own `README.md` (import steps, raw columns, key files, and dataset description for that dataset).

---

## Data Pipeline Overview

The data flows through three stages:

### Stage 1: Raw Import (per lab)

Each lab has an import script under `import_scripts/` (e.g. `barnes_import.py`). Scripts differ by acquisition system and file layout, but they all produce a wide-format `<lab>/<lab>.csv` (one row per animal, trial measures as columns). See the lab README for source files, trial classification, and lab-specific metadata.

Typical steps (not every lab uses all of these):

1. Read raw files from `<lab>/rat_data/`.
2. Rename columns using the lab JSON key (`<lab>/keys/<lab>.json`) when one exists.
3. Assign standardized trial suffixes (`_s_1`, `_p_1`, `_c_1`, …) from the trial-type key CSV.
4. Merge trials into one wide row per animal.
5. Derive shared fields such as `cumulative_time_*` when trial datetimes exist.
6. Write `<lab>/<lab>.csv`.

### Stage 2: Cross-Lab Combining

`combined/combine_data.py` loads every `<lab>.csv` from the lab folders and:

1. Selects only the columns listed in `combined/shared_keys/shared_keys.json`.
2. Renames lab-specific column names to a common schema (e.g. `ttr_dist` becomes
   `dist_total`).
3. Converts units where needed: Gallagher, McQuail, and Moore distance and speed
   recorded in cm / cm/s are divided by 100 to meters and m/s.
4. Normalizes categorical values (e.g. "Male"/"Female" to "M"/"F").
5. Fills `species` if missing (`mouse` for Moore, `rat` otherwise).
6. Produces a dictionary of aligned DataFrames, one per lab.

### Stage 3: GUI Exploration

The GUI (`gui/watermaze_gui.py`) concatenates all lab DataFrames and presents a
filter-and-plot interface.

---

## Column Naming Convention

Trial-level data columns follow this pattern:

```
<variable>_<trial_type>_<trial_number>
```

- **variable**: `dist_total`, `dist_cum`, `dist_mean`, `mean_speed`, `duration`,
  `cumulative_time`, `datetime_trial`, `trial_num`, `protocol_time`, etc.
- **trial_type**: `s` (Spatial), `p` (Probe), `c` (Visible/Cue)
- **trial_number**: Sequential integer within that type (e.g. 1, 2, …)

Example: `dist_cum_s_12` = cumulative distance, spatial trial 12.

After import, some labs still use internal prefixes (`ttr_*`, `cipl_*`). `shared_keys.json` maps those prefixes to the standardized names above at combine time.

| Standardized variable | Typical meaning |
|-----------------------|-----------------|
| `dist_total` | Path length |
| `dist_cum` | Cumulative distance or cumulative search error |
| `dist_mean` | Mean distance from the platform / mean search error |
| `mean_speed` | Mean swim speed |
| `duration` | Escape latency |
| `datetime_trial` | Trial date and time |
| `cumulative_time` | Seconds from the earliest `datetime_trial_*` in the row (when datetimes exist) |
| `protocol_time` | Seconds from protocol start using a fixed inter-trial interval (when used) |
| `trial_num` | Sequential trial index in the protocol |

Which raw columns map to these names, and which of these variables a lab actually has, are documented in that lab’s README.

Animal IDs usually receive a lab suffix at import (e.g. `.CB`, `.SB`, `.PR`, `.JM`, `.SM`, `.MG`) so IDs stay unique after combining.

---

## Key/Configuration Files

### Lab-Specific JSON Keys (`<lab>/keys/<lab>.json`)

When present, this file maps raw acquisition-system column names (or unique substrings) to internal base names. Sections are typically `Spatial`, `Probe`, `Visible`, and sometimes `Info`:

```json
{
  "Spatial": { "raw_col_name": "standardized_name_", ... },
  "Probe":   { "raw_col_name": "standardized_name_", ... },
  "Visible": { "raw_col_name": "standardized_name_", ... }
}
```

The trailing underscore on standardized names indicates trial-level columns; a numeric
trial suffix (e.g. `_s_1`) is appended during import.

### Trial-Type Key CSV (`<lab>/keys/trial_type_key_<lab>.csv`)

Maps each sequential trial number to a trial type and protocol day. Typical columns:

| Column       | Meaning                                    |
|--------------|--------------------------------------------|
| trial_num    | Sequential trial number (1, 2, 3, ...)     |
| trial_type   | `spatial`, `probe`, or `visible`           |
| protocol_day | Which day of the protocol this trial falls on|
| new_suffix   | The standardized suffix (e.g. `_s_1`, `_p_1`, `_c_1`)|

Some labs add extra columns (`trial_name`, `protocol_time`, separate young/aged keys). See the lab README.

### Shared Keys (`combined/shared_keys/shared_keys.json`)

Defines the cross-lab column mapping. Each lab has a `Metadata` section (direct renames)
and a `Trials` section (prefix-based renames). For example, Barnes `cipl_dist` maps to
`dist_total`, while Rapp `ttr_dist` also maps to `dist_total`.

---

## Running the Import Scripts

You normally only need to run the import scripts once (or when raw data changes).
Lab-specific notes (which files are read, what is overwritten) are in each lab README.

```powershell
cd "<your_path>\IDCARD"
python -m import_scripts.barnes_import
python -m import_scripts.rapp_import
python -m import_scripts.burke_import
python -m import_scripts.foster_import
python -m import_scripts.mcquail_import
python -m import_scripts.gallagher_import
python -m import_scripts.moore_import
```

Each script prints progress messages and writes its output CSV under the lab folder.

---

## Launching the GUI

There are two ways to launch the GUI.

### Option A &mdash; Combined Mode (recommended)

This loads all labs, applies the shared key mappings, concatenates the data, and opens
the filter window in one step:

```powershell
cd "<your_path>\IDCARD"
python -m gui.watermaze_gui
```

### Option B &mdash; Open Dialog Mode

You can also launch the GUI and manually select which data file to load:

```python
import sys
from PySide6.QtWidgets import QApplication
from gui.watermaze_gui import open as OpenDialog

app = QApplication(sys.argv)
dialog = OpenDialog()
dialog.show()
sys.exit(app.exec())
```

This opens a dialog where you pick:

1. **Data file (.csv)** &mdash; A single preprocessed CSV (e.g. `barnes/barnes.csv`) or
   any combined file.
2. **Key file (.csv)** &mdash; An optional trial-type key for reference.
3. **Save folder** &mdash; Default location for exported CSVs.

Click **Open** to proceed to the main filter window.

---

## GUI Walkthrough

The main window is split into two areas:

- **Left panel** &mdash; Collapsible filter sections and action buttons
- **Right panel** &mdash; Scrollable data table

### Open Dialog

When using Option B above, the open dialog prompts for three paths:

| Field             | What to select                                       |
|-------------------|------------------------------------------------------|
| Data file (.csv)  | A preprocessed lab CSV or a combined cross-lab CSV   |
| Key file (.csv)   | A trial-type key CSV (optional)                      |
| Save folder       | Destination folder for any data you export later     |

### Filter Panel

The left panel contains four collapsible sections. Click the **arrow** (▶ / ▼) next to
each section title to expand or collapse it.

#### 1. Rat Metadata

Filters based on animal-level characteristics:

| Filter   | Type        | Description                                       |
|----------|-------------|---------------------------------------------------|
| species  | Checkboxes  | Include mouse and/or rat.                         |
| age      | Min / Max   | Filter by age in months. Type a number in each box.|
| sex      | Checkboxes  | Check/uncheck M (Male) or F (Female).             |
| strain   | Checkboxes  | Select one or more strains.                       |
| genotype | Checkboxes  | Select one or more genotypes.                     |

#### 2. Protocol Metadata

Filters based on experimental protocol details:

| Filter         | Type        | Description                                     |
|----------------|-------------|-------------------------------------------------|
| pi             | Checkboxes  | Select which PI's data to include.              |
| source         | Checkboxes  | Filter by animal source (e.g. NIA).             |
| housing        | Checkboxes  | Filter by housing type.                         |
| pool_diam      | Min / Max   | Pool diameter in centimeters.                   |
| Start Date     | Date pickers| Min and max water maze start dates.              |
| lights_on      | Time pickers| Earliest and latest lights-on time.             |
| lights_off     | Time pickers| Earliest and latest lights-off time.            |

#### 3. Trial Metadata

Filters that control which trial columns appear and which animals qualify:

| Filter            | Type        | Description                                |
|-------------------|-------------|--------------------------------------------|
| Trial Type (s/p/c)| Checkboxes | Include Spatial, Probe, and/or Visible trials.|
| ttr_mean_speed_   | Min / Max   | Filter by mean swim speed.                 |
| ttr_dist_         | Min / Max   | Filter by total distance per trial.        |
| ttr_cum_dist_     | Min / Max   | Filter by cumulative distance.             |
| ttr_duration_     | Min / Max   | Filter by trial duration.                  |
| S Trial Number    | Min / Max   | Include spatial trials from N to M.        |
| P Trial Number    | Min / Max   | Include probe trials from N to M.          |
| C Trial Number    | Min / Max   | Include visible/cue trials from N to M.    |

#### 4. Plot

Controls for generating cumulative-variable-vs-time plots (see [Plotting](#plotting)
below).

### Applying Filters

After adjusting any filters, click the **Filter** button. The status bar at the bottom
of the filter panel updates to show:

- **Animals:** (number of rows remaining after filtering)
- **Columns:** (number of columns remaining)

The data table on the right refreshes to show only the matching subset.

### Reset Filters

Click **Reset Filters** at the top of the filter panel to restore all controls to their
original (unfiltered) defaults and redisplay the full dataset.

### Data Table

The right side of the window shows the currently filtered data in a scrollable table.
Columns correspond to metadata fields and trial-level measures. Rows represent individual
animals.

- Scroll horizontally to see additional trial columns.
- Scroll vertically to browse animals.
- The table updates automatically each time you click **Filter**.

### Plotting

Expand the **Plot** section in the filter panel to access plotting controls.

#### Plot Controls

| Control         | Options / Description                                    |
|-----------------|----------------------------------------------------------|
| Time column     | Dropdown: `protocol_time`, `datetime_trial`, `cumulative_time`, `trial_num` &mdash; selects the x-axis.|
| Trial variable  | Dropdown: automatically populated with numeric trial-variable stems found in the data (e.g. `dist_cum`, `mean_speed`, `duration`).|
| Shaded area     | Dropdown: `95% confidence interval`, `Standard error of the mean`, `Standard deviation` &mdash; controls the uncertainty band.|
| Trial types     | Checkboxes: **S (spatial)**, **P (probe)**, **C (visible)** &mdash; select which trial types to plot.|

#### How the Plot Works

1. Click **Plot trials vs time** to generate the figure.
2. The plot shows **cumulative mean** of the selected variable over time for each
   selected trial type.
3. If an `age` or `age_mo` column exists, lines are further split by age group (in
   months), with colors drawn from a viridis colormap.
4. A shaded band around each line represents the selected uncertainty statistic.
5. The legend (right side of the figure) labels each curve by trial type and, if
   applicable, age group.
6. The plot appears in a separate matplotlib window. You can pan, zoom, and save the
   figure from there using the matplotlib toolbar.

#### Plot Tips

- Filter your data first (e.g. select only one PI or age range) to make plots easier to
  interpret.
- Try different time-axis choices: `cumulative_time` gives seconds from the first trial;
  `trial_num` simply numbers the trials sequentially.
- The variable dropdown only shows stems with numeric data for the currently filtered
  dataset.

### Saving Data

Click **Save to .csv** to export the currently filtered and displayed data.

1. A save dialog appears with a folder selector.
2. If you specified a save folder at launch, it appears pre-filled.
3. Click **Browse...** to choose a different folder, or accept the default.
4. Click **Save**. The file is written as `saved_data.csv` in the chosen folder.

---

## Troubleshooting

### "No module named 'PySide6'"

Install PySide6:

```powershell
pip install PySide6
```

### "ModuleNotFoundError: No module named 'combined'" (or similar relative import error)

You are likely running a script directly instead of as a module. Use the `-m` flag:

```powershell
python -m gui.watermaze_gui
```

Or install the package in editable mode (`pip install -e .`) so that relative imports
resolve correctly.

### GUI window is blank or extremely wide

This can occur if the dataset has hundreds of columns. The table is wrapped in a scroll
area, so use the horizontal scrollbar to browse columns. You can also uncheck trial
types (S / P / C) to reduce the visible column count.

### "Skipping file due to permissions" messages in the console

The GUI logs these when it cannot read a CSV file (e.g. the file is open in Excel or
on a locked network share). Close any programs that may have the file open and try
again.
