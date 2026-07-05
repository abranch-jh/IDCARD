\# ID-CARD



\*\*ID-CARD\*\* is a Python package for standardized preprocessing, integration, and visualization of rodent water maze datasets across multiple labs/cohorts. It converts heterogeneous source files into a consistent wide-format schema, computes derived trial metrics, and provides a GUI for filtering and plotting trial-level outcomes.



\## What ID-CARD does



\- Imports and harmonizes data from multiple pipelines/cohorts (e.g., Barnes, Burke, McQuail, Rapp, Foster).

\- Applies shared key-based renaming/mapping so trial and metadata fields are consistent across datasets.

\- Builds trial-type aware wide tables (`s`:spatial/learning trials, `p`: probe trials, `c`: cued/visible platform trials) with standardized column naming.

\- Preserves and merges subject-level metadata (e.g., age, sex, genotype, source, calculated index fields).

\- Computes derived features such as cumulative timing and cumulative behavioral metrics.

\- Provides a GUI to:

&#x20; - filter subjects/trials/metadata,

&#x20; - plot trial variables vs. selected time axes,

&#x20; - split curves by trial type and age groups,

&#x20; - display uncertainty bands (95% CI, SEM, or SD).



\## Package structure



\- \*\*`import\_scripts/`\*\* – cohort-specific import/transformation pipelines.

\- \*\*`combined/`\*\* – cross-cohort combining and shared normalization utilities.

\- \*\*`gui/`\*\* – interactive filtering and plotting application.

\- \*\*`\*/keys/`\*\* and \*\*`combined/shared\_keys/`\*\* – mapping/config files for schema harmonization.



\## Intended use



\*\*ID-CARD\*\* is designed for reproducible water maze data preparation and exploratory analysis, especially when combining datasets produced with different acquisition systems and naming conventions. It is suitable both for one-off preprocessing and for standardized repeated runs in analysis workflows.

# IDCARD User Guide

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Project Structure](#project-structure)
4. [Data Pipeline Overview](#data-pipeline-overview)
5. [Running the Import Scripts](#running-the-import-scripts)
6. [Launching the GUI](#launching-the-gui)
7. [GUI Walkthrough](#gui-walkthrough)
   - [Open Dialog](#open-dialog)
   - [Filter Panel](#filter-panel)
   - [Data Table](#data-table)
   - [Plotting](#plotting)
   - [Saving Data](#saving-data)
8. [Key/Configuration Files](#keyconfiguration-files)
9. [Adding a New Lab or Cohort](#adding-a-new-lab-or-cohort)
10. [Troubleshooting](#troubleshooting)

---

## Overview

IDCARD (**I**ndividual **D**ifferences in **C**ognitive **A**ging of **R**odent **D**atasets) is a
Python toolkit for preprocessing, integrating, and visualizing rodent Morris Water Maze
datasets collected across multiple laboratories across varying ages and strains. Each lab may use different acquisition
systems, naming conventions, file formats, and protocol structure. IDCARD harmonizes those differences at the level of individual trials
integrated into a single wide-format table and provides an interactive GUI for filtering animals and
trials, inspecting the data, generating plots, and exporting subsets.

### Included Lab Datasets

| Lab (folder name) | PI / Source | Tracking System |
|--------------------|-------------|-----------------|
| `barnes`           | Barnes      | ANYMaze         |
| `burke`            | Burke       | Actimetrics Watermaze         |
| `disterhoft`	     | Disterhoft  | Actimetrics' Watermaze        |
| `foster`           | Foster      | Ethovision      |
| `gallagher`        | Gallagher   | HVS, ANYMaze    |
| `mcquail`          | McQuail     | Ethovision      |
| `moore`            | Moore       | varies          |
| `rapp`             | Rapp        | ANYMaze         |

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
├── README.md                   # High-level project description
├── __init__.py                 # Top-level package init
│
├── gui/                        # Interactive GUI application
│   ├── __init__.py
│   ├── watermaze_gui.py        # Main GUI (FilterApp, open/save dialogs)
│   └── import_tools.py         # Shared utility functions used by GUI
│
├── import_scripts/             # Per-lab raw-data import pipelines
│   ├── __init__.py
│   ├── import_tools.py         # Shared utility functions for imports
│   ├── barnes_import.py        # Barnes lab import script
│   ├── burke_import.py         # Burke lab import script
│   ├── foster_import.py        # Foster lab import script
│   ├── mcquail_import.py       # McQuail lab import script
│   └── rapp_import.py          # Rapp lab import script
│
├── combined/                   # Cross-lab combining and normalization
│   ├── __init__.py
│   ├── combine_data.py         # Loads per-lab CSVs, applies shared keys
│   └── shared_keys/
│       ├── shared_keys.json    # Column mapping: lab-specific → standardized
│       └── trial_type_key_template.csv
│
├── barnes/                     # Barnes lab data and config
│   ├── barnes.csv              # Combined (preprocessed) output
│   ├── keys/
│   │   ├── barnes.json         # Column-rename mapping (Spatial/Probe/Visible)
│   │   └── trial_type_key_barnes.csv  # Trial numbering scheme
│   └── rat_data/
│       ├── raw/                # Original per-animal per-day CSVs
│       └── database_format/    # Merged wide-format output
│
├── burke/                      # (Same structure as barnes)
├── foster/
├── disterhoft/                      
├── gallagher/
├── mcquail/
├── moore/
└── rapp/
```

---

## Data Pipeline Overview

The data flows through three stages:

### Stage 1: Raw Import (per lab)

Each lab has an import script under `import_scripts/` (e.g. `barnes_import.py`). These
scripts:

1. Read raw CSV files from `<lab>/rat_data/raw/`.
2. Group files by experiment (animal + date prefix).
3. Classify each file as **Spatial**, **Probe**, **Visible**, or **Info** based on its
   filename.
4. Rename columns using the lab-specific JSON key file (`<lab>/keys/<lab>.json`).
5. Assign standardized trial suffixes (`_s_1`, `_p_1`, `_c_1`, etc.) according to the
   trial-type key CSV (`<lab>/keys/trial_type_key_<lab>.csv`).
6. Merge all trials for each animal into a single wide-format row.
7. Write the result to `<lab>/rat_data/raw/outfiles/` and a combined
   `<lab>/<lab>.csv`.

### Stage 2: Cross-Lab Combining

`combined/combine_data.py` loads every `<lab>.csv` from the lab folders and:

1. Selects only the columns listed in `combined/shared_keys/shared_keys.json`.
2. Renames lab-specific column names to a common schema (e.g. `ttr_dist` becomes
   `dist_total`).
3. Converts units where needed (cm/s to m/s for Gallagher and McQuail data).
4. Normalizes categorical values (e.g. "Male"/"Female" to "M"/"F").
5. Produces a dictionary of aligned DataFrames, one per lab.

### Stage 3: GUI Exploration

The GUI (`gui/watermaze_gui.py`) concatenates all lab DataFrames and presents a
filter-and-plot interface.

### Column Naming Convention

Trial-level data columns follow this pattern:

```
<variable>_<trial_type>_<trial_number>
```

- **variable**: `dist_total`, `dist_cum`, `dist_mean`, `mean_speed`, `duration`,
  `cumulative_time`, `datetime_trial`, `trial_num`, etc.
- **trial_type**: `s` (Spatial), `p` (Probe), `c` (Visible/Cue)
- **trial_number**: Sequential integer (e.g. 1, 2, ... 24)

Example: `dist_cum_s_12` = cumulative distance, spatial trial 12.

---

## Running the Import Scripts

You normally only need to run the import scripts once (or when raw data changes).

```powershell
cd "<your_path>\IDCARD"
python -m import_scripts.barnes_import
python -m import_scripts.rapp_import
python -m import_scripts.burke_import
python -m import_scripts.foster_import
python -m import_scripts.mcquail_import
```

Each script will print progress messages and write its output CSV to the lab folder.

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
| age      | Min / Max   | Filter by age in months. Type a number in each box.|
| sex      | Checkboxes  | Check/uncheck M (Male) or F (Female).             |
| strain   | Checkboxes  | Select one or more rat strains.                   |
| genotype | Checkboxes  | Select one or more genotypes.                     |

#### 2. Protocol Metadata

Filters based on experimental protocol details:

| Filter         | Type        | Description                                     |
|----------------|-------------|-------------------------------------------------|
| pi             | Checkboxes  | Select which PI's data to include.              |
| source         | Checkboxes  | Filter by animal source (e.g. NIA).             |
| housing        | Checkboxes  | Filter by housing type.                         |
| pool_diam      | Min / Max   | Pool diameter in meters.                        |
| Start Date     | Date pickers| Min and max watermaze start dates.              |
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

## Key/Configuration Files

### Lab-Specific JSON Keys (`<lab>/keys/<lab>.json`)

Each lab has a JSON file that maps raw column names from the acquisition system to
standardized internal names. The JSON has sections for each trial type:

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

Maps each sequential trial number to a trial type and protocol day:

| Column       | Meaning                                    |
|--------------|--------------------------------------------|
| trial_num    | Sequential trial number (1, 2, 3, ...)     |
| trial_type   | `spatial`, `probe`, or `visible`           |
| protocol_day | Which day of the protocol this trial falls on|
| new_suffix   | The standardized suffix (e.g. `_s_1`, `_p_1`, `_c_1`)|

### Shared Keys (`combined/shared_keys/shared_keys.json`)

Defines the cross-lab column mapping. Each lab has a `Metadata` section (direct renames)
and a `Trials` section (prefix-based renames). For example, Barnes `cipl_dist` maps to
`dist_total`, while Rapp `ttr_dist` also maps to `dist_total`.

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

