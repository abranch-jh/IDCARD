# -*- coding: utf-8 -*-
"""
Created on Thu Feb 12 11:04:34 2026

@author: abranch6
"""

import os
from pathlib import Path
import numpy as np
import pandas as pd
from ..gui.import_tools import *

PROJECT_ROOT = Path(__file__).resolve().parents[1]
file = PROJECT_ROOT / "foster" / "foster.csv"
file_loaded = load_df(str(file))
