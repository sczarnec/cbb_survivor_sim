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
from utils.run_sim_funcs import SimConfig, TournamentSimulator


days_by_round = [2,2,2,1,1,1,]

still_alive_arr_orig = np.ones((68,), dtype=int)


with open(Path(__file__).parent.parent / "config" / "sim_params.yml", "r") as f:
    sim_params = yaml.safe_load(f)


def run_full_sim(seasons: list[int], n_iter: int, still_alive_arr_orig: np.array, days_by_round: list, policy_list: dict):

    sim_id = datetime.now(ZoneInfo("America/New_York")).strftime("%Y%m%d_%H.%M.%S_%f")


    for s in seasons:


        initial_data_dict = prep_data(s)

        cfg = SimConfig(sim_id=sim_id, n_iter=n_iter, season=s, survivor_policies=policy_list, initial_data_dict=initial_data_dict, still_alive_arr_orig=still_alive_arr_orig, days_by_round=days_by_round)
        sim = TournamentSimulator(cfg)

        sim.run_sim()


run_full_sim(
    seasons=sim_params["seasons"],
    n_iter=sim_params["n_iter"],
    still_alive_arr_orig=still_alive_arr_orig,
    days_by_round=days_by_round,
    policy_list=sim_params["policy_list"],
)

