import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTimeEdit, QDateEdit, QTableView, QCheckBox, QSpacerItem, QSizePolicy, QFileDialog, QMainWindow, QScrollArea, QFrame, QComboBox)
from PySide6.QtGui import QFont
from PySide6.QtCore import (QAbstractTableModel, QDate, QTime, Qt)
import pandas as pd
import numpy as np
import os
import itertools
import re
from ..combined import combine_data
import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from scipy import stats
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

class save(QMainWindow):
    def __init__(self, df:pd.DataFrame, default_folder: str | None = None):
        super().__init__()

        self.df = df
        self.default_folder = default_folder
        self.setWindowTitle("Main App Launcher")
        self.setGeometry(300, 200, 300, 200)
        
        self.central_widget = QWidget()
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)

        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Choose Save folder...")
        if self.default_folder is not None:
            self.folder_input.setText(self.default_folder)
        self.layout.addWidget(self.folder_input)

        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.select_folder)
        self.layout.addWidget(self.browse_button)

        # If we already have a default folder, show the save button immediately
        if self.default_folder is not None:
            self.save_button = QPushButton("Save")
            self.save_button.clicked.connect(self.save)
            self.layout.addWidget(self.save_button)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Folder")
        if folder:
            self.folder_input.setText(folder)
            # Only create the button if it doesn't exist yet
            if not hasattr(self, "save_button"):
                self.save_button = QPushButton("Save")
                self.save_button.clicked.connect(self.save)
                self.layout.addWidget(self.save_button)

    def save(self):
        self.df.to_csv(os.path.join(self.folder_input.text(), "saved_data.csv"))
        self.close()

class open(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Main App Launcher")
        self.setGeometry(300, 200, 400, 250)
        
        self.central_widget = QWidget()
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)

        # 1) Data file (CSV)
        self.data_file_input = QLineEdit()
        self.data_file_input.setPlaceholderText("Choose data file (.csv)...")
        self.layout.addWidget(self.data_file_input)

        self.data_browse_button = QPushButton("Browse Data File...")
        self.data_browse_button.clicked.connect(self.select_data_file)
        self.layout.addWidget(self.data_browse_button)

        # 2) Key file (CSV)
        self.key_file_input = QLineEdit()
        self.key_file_input.setPlaceholderText("Choose key file (.csv)...")
        self.layout.addWidget(self.key_file_input)

        self.key_browse_button = QPushButton("Browse Key File...")
        self.key_browse_button.clicked.connect(self.select_key_file)
        self.layout.addWidget(self.key_browse_button)

        # 3) Save folder
        self.save_folder_input = QLineEdit()
        self.save_folder_input.setPlaceholderText("Choose save folder...")
        self.layout.addWidget(self.save_folder_input)

        self.save_folder_browse_button = QPushButton("Browse Save Folder...")
        self.save_folder_browse_button.clicked.connect(self.select_save_folder)
        self.layout.addWidget(self.save_folder_browse_button)

        # Open button
        self.open_button = QPushButton("Open")
        self.open_button.clicked.connect(self.open_app)
        self.layout.addWidget(self.open_button)

    def select_data_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Data File",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if file_path:
            self.data_file_input.setText(file_path)

    def select_key_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Key File",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if file_path:
            self.key_file_input.setText(file_path)

    def select_save_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Folder")
        if folder:
            self.save_folder_input.setText(folder)

    def open_app(self):
        data_file = self.data_file_input.text().strip()
        key_file = self.key_file_input.text().strip()
        save_folder = self.save_folder_input.text().strip()

        # Basic sanity check: require at least data and save folder
        if not data_file or not save_folder:
            # Silent no-op if incomplete; could be enhanced with a message box
            return

        self.filter_window = FilterApp(data_file, key_file, save_folder)
        self.filter_window.show()
 
class TableModel(QAbstractTableModel):

    def __init__(self, data):
        super().__init__()
        self._data = data

    def data(self, index, role):
        if role == Qt.DisplayRole:
            value = self._data.iloc[index.row(), index.column()]
            return str(value)

    def rowCount(self, index):
        return self._data.shape[0]

    def columnCount(self, index):
        return self._data.shape[1]

    def headerData(self, section, orientation, role):
        # section is the index of the column/row.
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])

            if orientation == Qt.Vertical:
                return str(self._data.index[section])

class CollapsibleGroupBox(QWidget):
    def __init__(self, title):
        super().__init__()

        self.layout = QVBoxLayout(self)

        title_layout = QHBoxLayout()

        self.title_label = QLabel(title)
        title_layout.addWidget(self.title_label)

        self.arrow_label = QLabel("▶")
        font = QFont()
        font.setPointSize(16)
        self.arrow_label.setFont(font)
        self.arrow_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        title_layout.addWidget(self.arrow_label)

        # Add the title layout to the main layout
        self.layout.addLayout(title_layout)

        # Create the content area (initially hidden)
        self.content_area = QVBoxLayout()
        self.content_widget = QWidget()
        self.content_widget.setLayout(self.content_area)
        self.layout.addWidget(self.content_widget)

        # Add a spacer item for better alignment
        self.layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Connect the title label click event
        self.arrow_label.mousePressEvent = self.toggle_content

        self.content_widget.setVisible(False)

    def toggle_content(self, event):
        is_visible = self.content_widget.isVisible()
        self.content_widget.setVisible(not is_visible)
        
        # Change the arrow direction
        if is_visible:
            self.arrow_label.setText("▶")  # Point right when collapsed
            font = QFont()
            font.setPointSize(16)
            self.arrow_label.setFont(font)
        else:
            self.arrow_label.setText("▼")  # Point down when expanded
            font = QFont()
            font.setPointSize(8)
            self.arrow_label.setFont(font)

    def add_content(self, layout):
        self.content_area.addLayout(layout)

class FilterApp(QMainWindow):
    def __init__(self, data_path: str, key_path: str | None = None, save_folder: str | None = None):
        super().__init__()

        self.setWindowTitle("Filter Application")
        self.setGeometry(200, 200, 400, 300)

        self.central_widget = QWidget()
        self.main_layout = QHBoxLayout()
        self.layout_ = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.central_widget)

        # Store paths
        self.data_path = data_path
        self.key_path = key_path
        self.save_folder = save_folder

        # Load data (file or directory)
        self.process_dfs(self.data_path)

        self.default_state = {}

        self.make_ui()
        
class FilterApp(QMainWindow):
    def __init__(self, data_path: str, key_path: str | None = None, save_folder: str | None = None):
        super().__init__()

        self.setWindowTitle("Filter Application")
        self.setGeometry(200, 200, 400, 300)

        self.central_widget = QWidget()
        self.main_layout = QHBoxLayout()
        self.layout_ = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.central_widget)

        # Store paths
        self.data_path = data_path
        self.key_path = key_path
        self.save_folder = save_folder

        # Load data (file or directory)
        self.process_dfs(self.data_path)

        self.default_state = {}

        self.make_ui()

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, save_folder: str | None = None):
        self = cls.__new__(cls)
        super(cls, self).__init__()

        # same UI setup as in __init__
        self.setWindowTitle("Filter Application")
        self.setGeometry(200, 200, 400, 300)

        self.central_widget = QWidget()
        self.main_layout = QHBoxLayout()
        self.layout_ = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.central_widget)

        self.df = df.copy()
        self.save_folder = save_folder

        self.max_trials = {'s': 0, 'p': 0, 'c': 0}
        data_cols = [c for c in self.df.columns if "_s_" in c or "_p_" in c or "_c_" in c]
        self.metadata_cols = list(set(self.df.columns) - set(data_cols))

        self.default_state = {}
        self.make_ui()
        return self

    def process_dfs(self, filepath):
        self.max_trials = {'s': 0,
                           'p': 0,
                           'c': 0}

        # Decide whether we were given a directory or a single file
        if os.path.isdir(filepath):
            self.files = os.listdir(filepath)
        else:
            # Treat as a single data file
            self.files = [os.path.basename(filepath)]
            filepath = os.path.dirname(filepath)

        trial_meta_data_cols = []
        for file in self.files:
            full_path = os.path.join(filepath, file)

            # Skip directories or non-CSV files
            if not os.path.isfile(full_path):
                continue
            if not file.lower().endswith(".csv"):
                continue

            # Robust CSV loading: skip files we can't read or parse
            try:
                # on_bad_lines='skip' skips malformed rows (pandas >= 1.3)
                df = pd.read_csv(full_path, on_bad_lines='skip')
            except PermissionError as e:
                # No permission to read this file – log to console and continue
                print(f"Skipping file due to permissions: {full_path} ({e})")
                continue
            except pd.errors.ParserError as e:
                # Malformed CSV – log to console and continue
                print(f"Skipping malformed CSV file: {full_path} ({e})")
                continue
            except Exception as e:
                # Any other unexpected error – do not crash the GUI
                print(f"Skipping file due to unexpected error: {full_path} ({e})")
                continue

            df = self.clean_df(df)

            data_cols = [col for col in df.columns if "_s_" in col or "_p_" in col or "_c_" in col]
            trial_meta_data_cols.append(list(set(df.columns) - set(data_cols)))

            if hasattr(self, 'df'):
                self.df = pd.concat((self.df, df), axis=0)
                self.df = self.df.reset_index(drop=True)
            else:
                self.df = df
        self.metadata_cols = list(itertools.chain.from_iterable(trial_meta_data_cols))

    def make_ui(self): 

        self.reset_filters_button = QPushButton("Reset Filters")
        self.reset_filters_button.clicked.connect(self.reset_filters)
        self.layout_.addWidget(self.reset_filters_button)

        ########### Create a collapsible group box for Rat Metadata filters###################
        self.rat_metadata_filter = CollapsibleGroupBox("Rat Metadata")
        self.fill_in_metadata_group_box()
        self.layout_.addWidget(self.rat_metadata_filter)

        ########### Create a collapsible group box for Protocol Metadata filters###############
        self.protocol_metadata_filter = CollapsibleGroupBox("Protocol Metadata")
        self.fill_in_protocol_group_box()
        self.layout_.addWidget(self.protocol_metadata_filter)

        ########### Create a collapsible group box for Trial Metadata filters##################

        self.trial_metadata_filter = CollapsibleGroupBox("Trial Metadata")
        self.fill_in_trial_group_box()
        self.layout_.addWidget(self.trial_metadata_filter)

        ########### Create a collapsible group box for Plot ##################
        self.plot_filter = CollapsibleGroupBox("Plot")
        self.fill_in_plot_group_box()
        self.layout_.addWidget(self.plot_filter)

        # Button to check the count of rows
        self.check_button = QPushButton("Filter")
        self.check_button.clicked.connect(self.show_count)
        self.layout_.addWidget(self.check_button)

        # Output label for showing count
        self.count_label = QLabel(f"Animals: {self.df.shape[0]}")
        self.layout_.addWidget(self.count_label)

        self.columns_label = QLabel(f"Columns: {self.df.shape[1]}")
        self.layout_.addWidget(self.columns_label)

        self.save_button = QPushButton("Save to .csv")
        self.save_button.clicked.connect(self.save)
        self.layout_.addWidget(self.save_button)

        # Put filters in a fixed-width panel so the table gets most of the space
        self.filter_panel = QWidget()
        self.filter_panel.setLayout(self.layout_)
        self.filter_panel.setMaximumWidth(320)
        self.filter_panel.setMinimumWidth(260)
        self.main_layout.addWidget(self.filter_panel)
        self.table = QTableView()
        self.make_table(self.df)
        # Prevent table from forcing window width = sum of all column widths (e.g. 758622px)
        self.table.setMinimumSize(0, 0)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Put table in scroll area so many columns don't force window to 700k+ pixels wide
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(self.table)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.main_layout.addWidget(scroll)
        self.setLayout(self.main_layout)
        self.setMinimumSize(400, 300)

    def reset_filters(self):
        for widget, default_value in self.default_state.items():
            widget_type = str(widget.__class__).strip("''").split(sep='.')[-1]
            if 'Line' in widget_type:
                widget.setText(default_value)
            elif 'Check' in widget_type:
                widget.setChecked(True)
            elif 'Date' in widget_type:
                widget.setDate(default_value)
            elif 'Time' in widget_type:
                widget.setTime(default_value)
        # After restoring all UI defaults, recompute and show the full (unfiltered) dataset
        self.show_count()
    
    def save(self):
        df = pd.DataFrame(self.model._data)
        self.save_window = save(df, default_folder=self.save_folder)
        self.save_window.show()

    def fill_in_metadata_group_box(self):
        # Age input field
        self.age_h = QHBoxLayout()
        self.min_age_input, self.max_age_input = self.make_line_edit(self.age_h, 'age')
        self.rat_metadata_filter.add_content(self.age_h)
        
        # Sex input field
        self.Sex_h = QHBoxLayout()
        self.sexes = {}
        self.make_multiselect_field(self.sexes, self.Sex_h, 'sex')
        self.rat_metadata_filter.add_content(self.Sex_h)
    
        # Strain input field
        self.Strain_h = QHBoxLayout()
        self.strains = {}
        self.make_multiselect_field(self.strains, self.Strain_h, 'strain')
        self.rat_metadata_filter.add_content(self.Strain_h)

        # Genotype input field
        self.Genotype_h = QHBoxLayout()
        self.genotypes = {}
        self.make_multiselect_field(self.genotypes, self.Genotype_h, 'genotype')
        self.rat_metadata_filter.add_content(self.Genotype_h)
        
        # Add the Rat Metadata group box to the main layout
    
    def fill_in_protocol_group_box(self):
        # Pi Mame input field
        self.PI_Name_h = QHBoxLayout()
        self.PIs = {}
        self.make_multiselect_field(self.PIs, self.PI_Name_h, 'pi')
        self.protocol_metadata_filter.add_content(self.PI_Name_h)
        
        # Animal Source input field
        self.Animal_Source_h = QHBoxLayout()
        self.animal_source = {}
        self.make_multiselect_field(self.animal_source, self.Animal_Source_h, 'source')
        self.protocol_metadata_filter.add_content(self.Animal_Source_h)

        # Housing Type input field
        self.Housing_Type_h = QHBoxLayout()
        self.housing_type = {}
        self.make_multiselect_field(self.housing_type, self.Housing_Type_h, 'housing')
        self.protocol_metadata_filter.add_content(self.Housing_Type_h)

        # Pool Diameter input field
        self.Pool_Diameter_h = QHBoxLayout()
        self.min_pool_diam, self.max_pool_diam = self.make_line_edit(self.Pool_Diameter_h, 'pool_diam')
        self.protocol_metadata_filter.add_content(self.Pool_Diameter_h)

        # Start Date input field
        self.Start_Date_h = QHBoxLayout()
        self.min_Start_Date_label = QLabel("Min Start Date")
        self.max_Start_Date_label = QLabel("Max Start Date")
        self.min_Start_Date_input = QDateEdit()
        self.max_Start_Date_input = QDateEdit()

        # Default dates if column missing or parsing fails (QDate(year, month, day))
        default_min_date = QDate(2000, 1, 1)
        default_max_date = QDate(2030, 12, 31)

        if "watermaze_date" in self.df.columns:
            dates_series = self.df["watermaze_date"].dropna()
            if len(dates_series) > 0:
                for sep in ["-", "/", "."]:
                    try:
                        min_str = str(dates_series.min()).strip()[:10]
                        max_str = str(dates_series.max()).strip()[:10]
                        min_parts = min_str.split(sep)
                        max_parts = max_str.split(sep)
                        if len(min_parts) == 3 and len(max_parts) == 3:
                            # Assume MM-DD-YYYY or YYYY-MM-DD: try both orders
                            def to_qdate(parts):
                                a, b, c = int(parts[0]), int(parts[1]), int(parts[2])
                                if a > 31:  # year first (YYYY-MM-DD)
                                    return QDate(a, b, c)
                                if c > 31:  # year last (MM-DD-YYYY)
                                    return QDate(c, a, b)
                                return QDate(c, a, b)  # default MM-DD-YYYY
                            min_date = to_qdate(min_parts)
                            max_date = to_qdate(max_parts)
                            self.min_Start_Date_input.setDate(min_date)
                            self.max_Start_Date_input.setDate(max_date)
                            self.default_state[self.min_Start_Date_input] = min_date
                            self.default_state[self.max_Start_Date_input] = max_date
                            self.min_Start_Date_input.setToolTip(f"Min Date: {min_str}")
                            self.max_Start_Date_input.setToolTip(f"Max Date: {max_str}")
                            break
                    except (ValueError, IndexError):
                        continue
                else:
                    self.min_Start_Date_input.setDate(default_min_date)
                    self.max_Start_Date_input.setDate(default_max_date)
                    self.default_state[self.min_Start_Date_input] = default_min_date
                    self.default_state[self.max_Start_Date_input] = default_max_date
            else:
                self.min_Start_Date_input.setDate(default_min_date)
                self.max_Start_Date_input.setDate(default_max_date)
                self.default_state[self.min_Start_Date_input] = default_min_date
                self.default_state[self.max_Start_Date_input] = default_max_date
        else:
            self.min_Start_Date_input.setDate(default_min_date)
            self.max_Start_Date_input.setDate(default_max_date)
            self.default_state[self.min_Start_Date_input] = default_min_date
            self.default_state[self.max_Start_Date_input] = default_max_date

        self.Start_Date_h.addWidget(self.min_Start_Date_label)
        self.Start_Date_h.addWidget(self.min_Start_Date_input)
        self.Start_Date_h.addWidget(self.max_Start_Date_label)
        self.Start_Date_h.addWidget(self.max_Start_Date_input)
        self.protocol_metadata_filter.add_content(self.Start_Date_h)

        # Light On input field
        self.Light_On_h = QHBoxLayout()
        self.light_on = {}
        self.min_light_on, self.max_light_on = self.make_time_field(self.Light_On_h, 'lights_on')
        self.protocol_metadata_filter.add_content(self.Light_On_h)
        
        # Light Off input field
        self.Light_Off_h = QHBoxLayout()
        self.min_light_off, self.max_light_off = self.make_time_field(self.Light_Off_h, 'lights_off')
        self.protocol_metadata_filter.add_content(self.Light_Off_h)

    def fill_in_trial_group_box(self):
        # Trial Type input field
        self.Trial_Type_h = QHBoxLayout()
        self.Trial_Type_label = QLabel("Trial Type")
        self.trial_types= {}
        for trial_type in ['s', 'p', 'c']:
            label = QLabel(f"{trial_type}")
            self.trial_types[f"{trial_type}"] = QCheckBox(checked=True)
            self.Trial_Type_h.addWidget(label)
            self.Trial_Type_h.addWidget(self.trial_types[f"{trial_type}"])
            self.default_state[self.trial_types[f"{trial_type}"]] = True
        self.trial_metadata_filter.add_content(self.Trial_Type_h)

        # Speed input field
        self.speed_h = QHBoxLayout()
        self.min_speed_input, self.max_speed_input = self.make_line_edit(self.speed_h, 'ttr_mean_speed_')
        self.trial_metadata_filter.add_content(self.speed_h)

        # Distance input field
        self.Distance_h = QHBoxLayout()
        self.min_distance_input, self.max_distance_input = self.make_line_edit(self.Distance_h, "ttr_dist_")
        self.trial_metadata_filter.add_content(self.Distance_h)

        # Cumalative Distance input field
        self.cum_Distance_h = QHBoxLayout()
        self.min_cum_dist, self.max_cum_dist = self.make_line_edit(self.cum_Distance_h, "ttr_cum_dist_")
        self.trial_metadata_filter.add_content(self.cum_Distance_h)

        # Trial Duration input field
        self.Duration_h = QHBoxLayout()
        self.min_duration, self.max_duration = self.make_line_edit(self.Duration_h, "ttr_duration_")
        self.trial_metadata_filter.add_content(self.Duration_h)

        # Trial Number input field
        self.S_Trial_Num_h = QHBoxLayout()
        S_Trial_Num_label = QLabel("S Trial Number")
        self.S_min_Trial_Num_input = QLineEdit()
        self.S_min_Trial_Num_input.setText(f"1")
        self.default_state[self.S_min_Trial_Num_input] = '1'
        self.S_max_Trial_Num_input = QLineEdit()
        self.S_max_Trial_Num_input.setText(f"{self.max_trials['s']}")
        self.default_state[self.S_max_Trial_Num_input] = f"{self.max_trials['s']}"
        self.S_Trial_Num_h.addWidget(S_Trial_Num_label)
        self.S_Trial_Num_h.addWidget(self.S_min_Trial_Num_input)
        self.S_Trial_Num_h.addWidget(self.S_max_Trial_Num_input)
        self.trial_metadata_filter.add_content(self.S_Trial_Num_h)

        self.p_Trial_Num_h = QHBoxLayout()
        p_Trial_Num_label = QLabel("P Trial Number")
        self.p_min_Trial_Num_input = QLineEdit()
        self.p_min_Trial_Num_input.setText(f"1")
        self.default_state[self.p_min_Trial_Num_input] = '1'
        self.p_max_Trial_Num_input = QLineEdit()
        self.p_max_Trial_Num_input.setText(f"{self.max_trials['p']}")
        self.default_state[self.p_max_Trial_Num_input] = f"{self.max_trials['p']}"
        self.p_Trial_Num_h.addWidget(p_Trial_Num_label)
        self.p_Trial_Num_h.addWidget(self.p_min_Trial_Num_input)
        self.p_Trial_Num_h.addWidget(self.p_max_Trial_Num_input)
        self.trial_metadata_filter.add_content(self.p_Trial_Num_h)

        self.c_Trial_Num_h = QHBoxLayout()
        c_Trial_Num_label = QLabel("C Trial Number")
        self.c_min_Trial_Num_input = QLineEdit()
        self.c_min_Trial_Num_input.setText(f"1")
        self.default_state[self.c_min_Trial_Num_input] = '1'
        self.c_max_Trial_Num_input = QLineEdit()
        self.c_max_Trial_Num_input.setText(f"{self.max_trials['c']}")
        self.default_state[self.c_max_Trial_Num_input] = f"{self.max_trials['c']}"
        self.c_Trial_Num_h.addWidget(c_Trial_Num_label)
        self.c_Trial_Num_h.addWidget(self.c_min_Trial_Num_input)
        self.c_Trial_Num_h.addWidget(self.c_max_Trial_Num_input)
        self.trial_metadata_filter.add_content(self.c_Trial_Num_h)

    def fill_in_plot_group_box(self):
        # Time axis: protocol_time or datetime_trial
        self.plot_time_h = QHBoxLayout()
        self.plot_time_label = QLabel("Time column")
        self.plot_time_combo = QComboBox()
        time_options = []
        for name in ["protocol_time", "datetime_trial", "cumulative_time", "trial_num"]:
            if any(name in c for c in self.df.columns):
                time_options.append(name)
        if not time_options:
            time_options = ["protocol_time", "datetime_trial", "cumulative_time", "trial_num"]
        self.plot_time_combo.addItems(time_options)
        self.plot_time_h.addWidget(self.plot_time_label)
        self.plot_time_h.addWidget(self.plot_time_combo)
        self.plot_filter.add_content(self.plot_time_h)

        # Trial variable selector
        self.plot_var_h = QHBoxLayout()
        self.plot_var_label = QLabel("Trial variable")
        self.plot_var_combo = QComboBox()
        self.plot_var_combo.addItems(self._get_trial_variable_options(self.df))
        self.plot_var_h.addWidget(self.plot_var_label)
        self.plot_var_h.addWidget(self.plot_var_combo)
        self.plot_filter.add_content(self.plot_var_h)

        # Shaded area statistic (around mean cumulative curve)
        self.plot_shade_h = QHBoxLayout()
        self.plot_shade_label = QLabel("Shaded area")
        self.plot_shade_combo = QComboBox()
        self.plot_shade_combo.addItems(
            [
                "95% confidence interval",
                "Standard error of the mean",
                "Standard deviation",
            ]
        )
        self.plot_shade_h.addWidget(self.plot_shade_label)
        self.plot_shade_h.addWidget(self.plot_shade_combo)
        self.plot_filter.add_content(self.plot_shade_h)

        # Trial types to plot: S, P, C
        self.plot_trial_type_h = QHBoxLayout()
        self.plot_trial_type_label = QLabel("Trial types")
        self.plot_trial_types = {}
        for trial_type, label in [("s", "S (spatial)"), ("p", "P (probe)"), ("c", "C (visible)")]:
            self.plot_trial_types[trial_type] = QCheckBox(label)
            self.plot_trial_types[trial_type].setChecked(True)
        self.plot_trial_type_h.addWidget(self.plot_trial_type_label)
        for t in ["s", "p", "c"]:
            self.plot_trial_type_h.addWidget(self.plot_trial_types[t])
        self.plot_filter.add_content(self.plot_trial_type_h)
        self.plot_button = QPushButton("Plot trials vs time")
        self.plot_button.clicked.connect(self.show_plot)
        plot_btn_layout = QHBoxLayout()
        plot_btn_layout.addWidget(self.plot_button)
        self.plot_filter.add_content(plot_btn_layout)

    def _get_trial_variable_options(self, df: pd.DataFrame):
        """Return selectable trial-variable stems for columns like '<stem>_s_1' or '<stem>_s1'."""
        trial_pat = re.compile(r"^(.*)_([spc])_?(\d+)$", re.IGNORECASE)
        excluded_tokens = ("date", "time", "trial", "protocol", "block")
        stems = {}
        for c in df.columns:
            m = trial_pat.search(str(c))
            if not m:
                continue
            stem = m.group(1)
            if any(tok in stem.lower() for tok in excluded_tokens):
                continue
            stems.setdefault(stem, []).append(c)

        numeric_stems = []
        for stem, cols in stems.items():
            vals = pd.to_numeric(df[cols].stack(), errors="coerce")
            if vals.notna().any():
                numeric_stems.append(stem)

        return sorted(numeric_stems)

    def show_plot(self):
        """Plot cumulative variable vs time, split by selected trial types."""
        df = pd.DataFrame(self.model._data)
        if df.empty:
            print("Cannot plot: no data after filtering.")
            return

        selected_types = [t for t, cb in self.plot_trial_types.items() if cb.isChecked()]
        if not selected_types:
            print("Cannot plot: select at least one trial type (S/P/C).")
            return

        time_prefix = self.plot_time_combo.currentText()
        trial_pat = re.compile(r"^(.*)_([spc])_?(\d+)$", re.IGNORECASE)

        def _split_trial_col(col_name: str):
            m = trial_pat.search(str(col_name))
            if not m:
                return None, None, None
            return m.group(1), m.group(2).lower(), int(m.group(3))

        # Refresh trial-variable options from currently filtered data.
        current_var = self.plot_var_combo.currentText().strip()
        options = self._get_trial_variable_options(df)
        self.plot_var_combo.blockSignals(True)
        self.plot_var_combo.clear()
        self.plot_var_combo.addItems(options)
        if current_var in options:
            self.plot_var_combo.setCurrentText(current_var)
        elif options:
            self.plot_var_combo.setCurrentIndex(0)
        self.plot_var_combo.blockSignals(False)

        def _trial_stem(col_name: str):
            m = trial_pat.fullmatch(str(col_name).strip())
            return m.group(1).lower() if m else None

        # Match time columns by trial stem (case-insensitive). Plain "prefix in col" breaks for
        # Datetime_Trial vs datetime_trial and for stems like ttr_protocol_time_s_1.
        def _has_typed_time_cols(prefix: str) -> bool:
            pl = prefix.strip().lower()
            for c in df.columns:
                stem = _trial_stem(c)
                if stem is None:
                    continue
                if stem == pl or pl in stem or stem.endswith(pl):
                    return True
            return False

        def _discover_time_stems() -> list[str]:
            """Unique trial stems that look like time axes (present in filtered df)."""
            markers = ("datetime_trial", "cumulative_time", "protocol_time")
            keys = set()
            out = []
            for c in df.columns:
                stem = _trial_stem(c)
                if stem is None:
                    continue
                if any(stem == m or m in stem for m in markers):
                    if stem not in keys:
                        keys.add(stem)
                        out.append(stem)
            return out

        time_candidates = [time_prefix, "cumulative_time", "datetime_trial", "protocol_time", "trial_num"]
        time_candidates = list(dict.fromkeys(time_candidates))
        time_candidates = [tp for tp in time_candidates if _has_typed_time_cols(tp)]
        if not time_candidates:
            time_candidates = _discover_time_stems()
        if not time_candidates:
            print("Cannot plot: no typed trial time columns found.")
            return

        # Auto-detect a numeric variable stem from typed trial columns.
        excluded_tokens = ("date", "time", "trial", "protocol", "block")
        stem_candidates = {}
        for c in df.columns:
            stem, ttype, _ = _split_trial_col(str(c))
            if stem is None or ttype not in selected_types:
                continue
            if any(tok in stem.lower() for tok in excluded_tokens):
                continue
            stem_candidates.setdefault(stem, []).append(c)

        selected_var = self.plot_var_combo.currentText().strip()
        numeric_stems = []
        for stem, cols in sorted(stem_candidates.items(), key=lambda kv: -len(kv[1])):
            vals = pd.to_numeric(df[cols].stack(), errors="coerce")
            if vals.notna().any():
                numeric_stems.append(stem)

        if not numeric_stems:
            print("Cannot plot: no numeric trial variable columns found for selected trial types.")
            return
        if not selected_var:
            print("Cannot plot: select a trial variable.")
            return
        if selected_var not in numeric_stems:
            print(f"Cannot plot: selected trial variable '{selected_var}' has no numeric data for selected trial types.")
            return
        variable_candidates = [selected_var]

        id_col = "animal" if "animal" in df.columns else ("subject_id" if "subject_id" in df.columns else None)
        if id_col is None:
            print("Cannot plot: need an id column ('animal' or 'subject_id').")
            return

        shade_keys = ("ci95", "sem", "std")
        si = self.plot_shade_combo.currentIndex()
        shade_stat = shade_keys[si] if 0 <= si < len(shade_keys) else "ci95"

        fig, ax = plt.subplots(figsize=(10, 6))
        plotted = False
        used_var = selected_var
        used_time = None
        for vp in variable_candidates:
            for tp in time_candidates:
                plotted = self._plot_var_vs_time_melt(
                    df=df,
                    variable_prefix=vp,
                    time_prefix=tp,
                    subjects_to_plot=None,
                    selected_trial_types=selected_types,
                    id_col=id_col,
                    ax=ax,
                    color="tab:blue",
                    marker="o",
                    label="",
                    shade_stat=shade_stat,
                )
                if plotted:
                    used_time = tp
                    break
            if plotted:
                break
        if not plotted:
            plt.close(fig)
            print("Cannot plot: no overlapping non-NaN trial data found for selected variable/time/trial types.")
            return
        if str(used_time).strip().lower() == "trial_num":
            ax.set_xlabel("Trial number")
        else:
            ax.set_xlabel(f"{used_time} (seconds from start)")
        ax.set_ylabel(f"Cumulative {used_var}")
        ax.grid(alpha=0.3)
        handles, labels = ax.get_legend_handles_labels()
        by_age = bool(labels) and any("·" in str(L) and " mo" in str(L) for L in labels)
        shade_title = {
            "ci95": "95% CI of mean",
            "sem": "± SEM",
            "std": "± SD",
        }.get(shade_stat, "95% CI of mean")
        base_title = (
            f"{used_var} vs {used_time} by trial type and age"
            if by_age
            else f"{used_var} vs {used_time} by trial type"
        )
        ax.set_title(f"{base_title} (shaded: {shade_title})")
        if labels:
            leg_title = "Trial type · Age (mo)" if by_age else "Trial type"
            ax.legend(
                title=leg_title,
                loc="center left",
                bbox_to_anchor=(1.02, 0.5),
                frameon=True,
                borderaxespad=0,
                fontsize=8,
            )
            # Reserve a modest right margin for the legend (~20% width; was ~28%).
            fig.tight_layout(rect=[0, 0, 0.95, 1])
        else:
            fig.tight_layout()
        plt.show()

    def show_age_cumdist_plot(self):
    # Use current table contents (includes any filters)
        df = pd.DataFrame(self.model._data)

        try:
            df_aq, df_probe, ages = self._prepare_cumulative_distance_inputs(
                df,
                cum_prefix="dist_cum_",  # adjust if your prefix differs
                age_col="age_mo",
            )
        except ValueError as e:
            print(f"Cannot plot cumulative distance: {e}")
            return

        combine_data.plot_cumulative_distance(
            df_aq=df_aq,
            df_probe=df_probe,
            ages=ages,
            title="Mean Cumulative Distance by Age Group (SEM)",
            stat="sem",
        )

    def _plot_var_vs_time_melt(
        self,
        df: pd.DataFrame,
        variable_prefix: str,
        time_prefix: str,
        subjects_to_plot,
        selected_trial_types,
        id_col: str,
        ax,
        color: str,
        marker: str,
        label: str,
        shade_stat: str = "ci95",
    ) -> bool:
        """Reshape wide trial columns to long and plot cumulative value vs time per subject."""
        if id_col not in df.columns:
            return False

        trial_pat = re.compile(r"^(.*)_([spc])_?(\d+)$", re.IGNORECASE)
        v_stem = str(variable_prefix).strip().lower()
        t_stem = str(time_prefix).strip().lower()

        def _stem_match(col_name: str, want: str) -> bool:
            m = trial_pat.fullmatch(str(col_name).strip())
            if not m:
                return False
            return m.group(1).strip().lower() == want

        var_cols = [c for c in df.columns if _stem_match(c, v_stem)]
        time_cols = [c for c in df.columns if _stem_match(c, t_stem)]
        if not var_cols or not time_cols:
            return False

        variable_long = pd.melt(
            df,
            id_vars=[id_col],
            value_vars=var_cols,
            var_name="trial",
            value_name="value",
        )
        trial_meta = variable_long["trial"].astype(str).str.extract(r"_([spc])_?(\d+)$", flags=re.IGNORECASE)
        variable_long["trial_type"] = trial_meta[0].str.lower()
        variable_long["trial_number"] = pd.to_numeric(trial_meta[1], errors="coerce").astype("Int64")

        time_long = pd.melt(
            df,
            id_vars=[id_col],
            value_vars=time_cols,
            var_name="trial",
            value_name="time",
        )
        trial_meta_t = time_long["trial"].astype(str).str.extract(r"_([spc])_?(\d+)$", flags=re.IGNORECASE)
        time_long["trial_type"] = trial_meta_t[0].str.lower()
        time_long["trial_number"] = pd.to_numeric(trial_meta_t[1], errors="coerce").astype("Int64")

        merged_df = pd.merge(variable_long, time_long, on=[id_col, "trial_type", "trial_number"])
        if merged_df.empty:
            return False

        merged_df["value"] = pd.to_numeric(merged_df["value"], errors="coerce")
        time_num = pd.to_numeric(merged_df["time"], errors="coerce")
        if time_num.notna().sum() > 0:
            merged_df["time"] = time_num
        else:
            merged_df["time"] = pd.to_datetime(merged_df["time"], errors="coerce")
        merged_df = merged_df.dropna(subset=["value", "time"])
        if merged_df.empty:
            return False

        # Filter to requested subjects (if provided)
        if subjects_to_plot:
            merged_df = merged_df[merged_df[id_col].isin(subjects_to_plot)]
        if merged_df.empty:
            return False
        merged_df = merged_df.dropna(subset=["trial_type", "trial_number"])
        if merged_df.empty:
            return False
        if selected_trial_types:
            merged_df = merged_df[merged_df["trial_type"].isin(selected_trial_types)]
        if merged_df.empty:
            return False

        # Optional: age in months — one line per (trial_type, age) when column exists.
        age_col = next((c for c in ("age", "age_mo") if c in df.columns), None)
        if age_col is not None:
            age_map = df[[id_col, age_col]].drop_duplicates(subset=[id_col], keep="first")
            merged_df = merged_df.merge(age_map, on=id_col, how="left")
            merged_df["_age_mo"] = (
                pd.to_numeric(merged_df[age_col], errors="coerce")
                .round()
                .astype("Int64")
            )
            merged_df = merged_df.dropna(subset=["_age_mo"])
            if merged_df.empty:
                return False

        type_labels = {"s": "Spatial", "p": "Probe", "c": "Visible"}
        type_styles = {
            "s": {"marker": "o"},
            "p": {"marker": "s"},
            "c": {"marker": "^"},
        }
        plotted_any = False

        def _plot_cumulative_mean_shade(sub, line_color, plot_label, mkr):
            """
            Per subject: cumulative sum of value along sorted time; then mean and shaded band
            (95% CI, ±SEM, or ±SD) of those cumulative values at each time point.
            """
            if sub.empty:
                return False
            try:
                pivot = sub.pivot_table(
                    index=id_col, columns="time", values="value", aggfunc="first"
                )
            except ValueError:
                return False
            if pivot.empty or pivot.shape[1] == 0:
                return False
            tcols = list(pivot.columns)
            try:
                tcols = sorted(tcols)
            except TypeError:
                tcols = sorted(tcols, key=lambda x: (str(type(x)), str(x)))
            pivot = pivot.reindex(columns=tcols)
            cum_pivot = pivot.fillna(0).cumsum(axis=1)
            xs, means, lows, highs = [], [], [], []
            for c in cum_pivot.columns:
                vals = pd.to_numeric(cum_pivot[c], errors="coerce").dropna().to_numpy()
                n = len(vals)
                if n == 0:
                    continue
                m = float(np.mean(vals))
                if n < 2:
                    lo = hi = m
                else:
                    se = float(stats.sem(vals, nan_policy="omit"))
                    std = float(np.std(vals, ddof=1))
                    if shade_stat == "ci95":
                        h = float(stats.t.ppf(0.975, n - 1) * se)
                    elif shade_stat == "sem":
                        h = se
                    else:
                        h = std
                    lo, hi = m - h, m + h
                xs.append(c)
                means.append(m)
                lows.append(lo)
                highs.append(hi)
            if not xs:
                return False
            ax.fill_between(
                xs, lows, highs, color=line_color, alpha=0.25, linewidth=0, zorder=1
            )
            ax.plot(
                xs,
                means,
                color=line_color,
                marker=mkr,
                alpha=0.95,
                label=plot_label,
                zorder=2,
            )
            return True

        if age_col is not None and "_age_mo" in merged_df.columns and merged_df["_age_mo"].notna().any():
            uniq_ages = sorted(int(a) for a in merged_df["_age_mo"].dropna().unique())
            n_ages = len(uniq_ages)
            for i, age_val in enumerate(uniq_ages):
                line_color = plt.cm.viridis(i / max(n_ages - 1, 1))
                for trial_type, type_df in merged_df.groupby("trial_type"):
                    sub = type_df[type_df["_age_mo"] == age_val]
                    style = type_styles.get(trial_type, {"marker": marker})
                    if _plot_cumulative_mean_shade(
                        sub,
                        line_color,
                        f"{type_labels.get(trial_type, str(trial_type))} · {age_val} mo",
                        style["marker"],
                    ):
                        plotted_any = True
        else:
            type_colors = {
                "s": "tab:blue",
                "p": "tab:orange",
                "c": "tab:green",
            }
            for trial_type, type_df in merged_df.groupby("trial_type"):
                style = type_styles.get(trial_type, {"marker": marker})
                if _plot_cumulative_mean_shade(
                    type_df,
                    type_colors.get(trial_type, color),
                    type_labels.get(trial_type, str(trial_type)),
                    style["marker"],
                ):
                    plotted_any = True
        return plotted_any

    def _prepare_cumulative_distance_inputs(
        self,
        df: pd.DataFrame,
        cum_prefix: str = "ttr_cum_dist_",
        age_col: str = "age_mo",
    ):
        """
        From a wide trial DataFrame, construct df_aq, df_probe, ages
        for plot_cumulative_distance.
        """
        if age_col not in df.columns:
            raise ValueError(f"Age column '{age_col}' not found")

        spatial_cols = [c for c in df.columns if cum_prefix in c and "_s_" in c]
        probe_cols   = [c for c in df.columns if cum_prefix in c and "_p_" in c]

        if not spatial_cols or not probe_cols:
            raise ValueError("No spatial or probe cumulative-distance columns found")

        def trial_key(col: str) -> int:
            m = re.search(r"_(s|p)_(\d+)$", col)
            return int(m.group(2)) if m else 0

        spatial_cols = sorted(spatial_cols, key=trial_key)
        probe_cols   = sorted(probe_cols,   key=trial_key)

        spatial_raw = df[spatial_cols]          # n_subjects x n_trials
        df_aq = spatial_raw.cumsum(axis=1)      # cumulative across trials

        df_probe = df[probe_cols[-1]]           # Series: final probe distance
        ages = df[age_col]

        return df_aq, df_probe, ages

    def show_count(self):
        # Start from the full dataframe
        subset = self.df.copy().reset_index(drop=True)

        # Age filter (only if the column exists)
        # In the data this column is named 'age_mo'
        if "age_mo" in subset.columns:
            try:
                min_age = float(self.min_age_input.text())
                max_age = float(self.max_age_input.text())
                mask_valid = subset["age_mo"].between(min_age, max_age)
                mask_nan = subset["age_mo"].isna()
                subset = subset[mask_valid | mask_nan].reset_index(drop=True)
            except ValueError:
                # If inputs are not valid numbers, ignore age filter
                pass
        
        subset = self.apply_multiselect_filter(subset, self.sexes, 'sex')
        subset = self.apply_multiselect_filter(subset, self.strains, 'strain')
        subset = self.apply_multiselect_filter(subset, self.genotypes, 'genotype')
        subset = self.apply_multiselect_filter(subset, self.PIs, 'pi')
        subset = self.apply_multiselect_filter(subset, self.housing_type, 'housing')
        subset = self.apply_multiselect_filter(subset, self.animal_source, 'source')

        # Pool diameter filter (only if the column exists)
        if "pool_diam" in subset.columns:
            try:
                min_pool = float(self.min_pool_diam.text())
                max_pool = float(self.max_pool_diam.text())
                mask_valid = subset["pool_diam"].between(min_pool, max_pool)
                mask_nan = subset["pool_diam"].isna()
                subset = subset[mask_valid | mask_nan].reset_index(drop=True)
            except ValueError:
                pass

        #separator = '\\' if "\\" in self.df['watermaze_date'].min() else '/'
        separator = '-'
        min_date = self.min_Start_Date_input.date().getDate()
        min_date_str = str(min_date[1]) + separator + str(min_date[2]) + separator + str(min_date[0])
        max_date = self.max_Start_Date_input.date().getDate()
        max_date_str = str(max_date[1]) + separator + str(max_date[2]) + separator + str(max_date[0])
        # Date filter (only if the column exists)
        if "watermaze_date" in subset.columns:
            mask_valid = subset["watermaze_date"].between(min_date_str, max_date_str)
            mask_nan = subset["watermaze_date"].isna()
            subset = subset[mask_valid | mask_nan].reset_index(drop=True)

        # Lights on/off time filters (only if the columns exist)
        if "lights_on" in subset.columns:
            series = subset["lights_on"]
            mask_nan = series.isna()
            mask_valid = pd.to_datetime(series, format='%H:%M', errors="coerce").dt.time.between(
                self.min_light_on.time(), self.max_light_on.time()
            )
            subset = subset[mask_valid | mask_nan].reset_index(drop=True)
        
        if "lights_off" in subset.columns:
            series = subset["lights_off"]
            mask_nan = series.isna()
            mask_valid = pd.to_datetime(series, format='%H:%M', errors="coerce").dt.time.between(
                self.min_light_off.time(), self.max_light_off.time()
            )
            subset = subset[mask_valid | mask_nan].reset_index(drop=True)

        
        columns_to_keep = []
        for type, check_box in self.trial_types.items():
            if check_box.isChecked(): 
                columns_to_keep.append([col for col in subset.columns if f"_{type}_" in col])
        columns_to_keep = list(itertools.chain.from_iterable(columns_to_keep))

        columns_to_keep = self.metadata_cols + columns_to_keep
        column_reduced_subset = subset[subset.columns[subset.columns.isin(columns_to_keep)]].reset_index(drop=True)
        column_reduced_subset = self.clean_df(column_reduced_subset)
        
        self.count_label.setText(f"Animals: {column_reduced_subset.shape[0]}")
        self.columns_label.setText(f"Columns: {column_reduced_subset.shape[1]}")
        self.make_table(column_reduced_subset)
    
    def make_multiselect_field(self, dict, layout, column):
        label = QLabel(column)
        layout.addWidget(label)
        data_cols = [col for col in self.df.columns if column in col]
        for data_col in data_cols:
            for temp in np.unique(self.df[data_col].dropna().to_numpy()):
                temp_chkbox = QCheckBox(checked=True)
                dict[temp] = temp_chkbox
                layout.addWidget(QLabel(temp))
                layout.addWidget(dict[temp])
                self.default_state[temp_chkbox] = True
    
    def apply_multiselect_filter(self, subset, filters_dict, column_name):
        """Apply multiselect filters based on checkboxes."""
        selected_values = [key for key, cb in filters_dict.items() if cb.isChecked()]
        data_cols = [col for col in self.df.columns if column_name in col]
        # Determine if user actually changed this filter from its default state.
        # If all checkboxes are still at their default (usually True), treat filter as inactive.
        filter_active = any(
            cb.isChecked() != self.default_state.get(cb, True)
            for cb in filters_dict.values()
        )
        # If filter is not active or there are no matching columns, skip it
        if not filter_active or not data_cols or not selected_values:
            return subset.reset_index(drop=True)

        # Keep only rows that match selected values in at least one of the matching columns
        mask_match = subset[data_cols].isin(selected_values).any(axis=1)
        subset = subset[mask_match]
        return subset.reset_index(drop=True)
    
    def make_line_edit(self, layout, column):
        label = QLabel(column)
        data_cols = [col for col in self.df.columns if column in col]

        layout.addWidget(label)

        # If no matching columns, return empty inputs
        if not data_cols:
            min_input = QLineEdit()
            max_input = QLineEdit()
            layout.addWidget(min_input)
            layout.addWidget(max_input)
            self.default_state[min_input] = ""
            self.default_state[max_input] = ""
            return min_input, max_input

        # Coerce to numeric and ignore non-numeric values to avoid str/int comparison errors
        numeric_values = pd.to_numeric(self.df[data_cols].to_numpy().ravel(), errors="coerce")
        numeric_values = numeric_values[~np.isnan(numeric_values)]
        if numeric_values.size == 0:
            min_val = ""
            max_val = ""
        else:
            min_val = float(np.nanmin(numeric_values))
            max_val = float(np.nanmax(numeric_values))

        min_input = QLineEdit(text=f"{min_val}")
        if min_val != "":
            min_input.setToolTip(f"Min: {min_val}")
        max_input = QLineEdit(text=f"{max_val}")
        if max_val != "":
            max_input.setToolTip(f"Max: {max_val}")
        layout.addWidget(min_input)
        layout.addWidget(max_input)
        self.default_state[min_input] = f"{min_val}"
        self.default_state[max_input] = f"{max_val}"
        return min_input, max_input

    def make_time_field(self, layout, column):
        min_label = QLabel(f"Earliest {column}")
        min_time_input = QTimeEdit()
        max_label = QLabel(f"Latest {column}")
        max_time_input = QTimeEdit()

        min_time = pd.to_datetime(self.df[column].dropna(), format='%H:%M').min()
        time_seperated = [min_time.time().hour, min_time.time().minute]
        min_time_input.setToolTip(f"Min: {time_seperated[0]}:" + f"{time_seperated[1]}".zfill(2))
        time = QTime(int(time_seperated[0]), int(time_seperated[1]))
        min_time_input.setTime(time)
        self.default_state[min_time_input] = time

        max_time = pd.to_datetime(self.df[column].dropna(), format='%H:%M').max()
        time_seperated = [max_time.time().hour, max_time.time().minute]
        max_time_input.setToolTip(f"Min: {time_seperated[0]}:" + f"{time_seperated[1]}".zfill(2))
        time = QTime(int(time_seperated[0]), int(time_seperated[1]))
        max_time_input.setTime(time)
        self.default_state[max_time_input] = time

        layout.addWidget(min_label)
        layout.addWidget(min_time_input)
        layout.addWidget(max_label)
        layout.addWidget(max_time_input)

        return min_time_input, max_time_input

    def get_columns_to_keep(self):
        types_to_use = []
        for type, check_box in self.trial_types.items():
            if check_box.isChecked():
                types_to_use.append(type.removesuffix("_button"))

        suffixes = []
        for trial_type in types_to_use:
            for trial_number in range(1, self.max_trials[trial_type]+1):
                if trial_type == 's':
                    if (trial_number >= int(self.S_min_Trial_Num_input.text())) & (trial_number <= int(self.S_max_Trial_Num_input.text())):
                        suffixes.append(f"{trial_type}_{trial_number}")
                elif trial_type == 'p':
                    if (trial_number >= int(self.p_min_Trial_Num_input.text())) & (trial_number <= int(self.p_max_Trial_Num_input.text())):
                        suffixes.append(f"{trial_type}_{trial_number}")
                elif trial_type == 'c':
                    if (trial_number >= int(self.c_min_Trial_Num_input.text())) & (trial_number <= int(self.c_max_Trial_Num_input.text())):
                        suffixes.append(f"{trial_type}_{trial_number}")

        suffixes = list(set(suffixes))
        columns_to_keep = []
        for suffix in suffixes:
            for column_prefix in ["ttr_duration_", "ttr_mean_speed_", "ttr_dist_", "ttr_cum_dist_"]:
                columns_to_keep.append(column_prefix+suffix)
        
        return columns_to_keep

    def make_table(self, df):
        self.model = TableModel(df)
        self.table.setModel(self.model)

    def clean_df(self, df):
        df.columns = [x.lower().strip() for x in df.columns]
        if df["pool_diam"].dtype != int and df["pool_diam"].dtype != float:
            df['pool_diam'] = [(float(value[:-2]) / 100) for value in df['pool_diam']]
        df = df.loc[:,~df.columns.duplicated()].copy()
        columns_all_nan = df.columns[df.isna().all()].tolist()
        df = df.drop(columns_all_nan, axis=1)
        columns_day_of_week = [column for column in df.columns.to_numpy() if "day of week" in column]
        df = df.drop(columns_day_of_week, axis=1)
        file_location_columns = [column for column in df.columns.to_numpy() if (df[column].dtype == 'object') if ".szv" in str(df[column][0])]
        df = df.drop(file_location_columns, axis=1)
        return df

if __name__ == "__main__":
    combined_df = pd.concat(
        combine_data.dataframes.values(),
        axis=0,
        ignore_index=True,
    )

    # Reuse existing QApplication if matplotlib/Qt already created one
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    window = FilterApp.from_dataframe(
        combined_df,
        save_folder=None,          # or a default
    )
    window.show()
    sys.exit(app.exec())