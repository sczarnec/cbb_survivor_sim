import pandas as pd
import numpy as np
import math
import random
from dataclasses import dataclass, asdict
from datetime import datetime
from zoneinfo import ZoneInfo
import yaml
from pathlib import Path

from utils.sim_data_prep import prep_data


days_by_round = [2,2,2,1,1,1,]

still_alive_arr_orig = np.ones((68,), dtype=int)


for season in [2025]:

    prep_data(season)

    print("it worked")
