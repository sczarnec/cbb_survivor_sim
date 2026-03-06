import pandas as pd
import numpy as np


def prep_data(season: int):
    """
    Function to prep data from initial inputs

    Args
    - season = season

    Output
    - team_seed_arr_orig: array with (team id) as index and val = seed
    - first4_pair_list: four lists of two-item lists with pairs of first4 teams
    - bracket_arr_orig: array with (team id, round id) and val = game_id
    - team_day_list: list[rd][day], with team id index and 0/1 day value
    - potential_opps_arr_orig: list of arrays (list[rd]) containing arrays with (team id, team id) and val = 0/1 can play each other
    - game_match_arr_orig: array with (team id, game id) and val = 0/1 can play in that game
    - unique_games_comb: list of game_ids for each day
    - wp_arr_orig: array with (team id, team id) and val = win prob
    - groups_ff_orig: two lists representing a potential final four matchup with team ids in that one
    - groups_ee_orig: four lists representing a potential elite eight matchup with team ids in that one
    """

    # load data in
    bracket_df, win_prob_df, dates_df = _load_data(season)

    # structure the initial data
    bracket_df_struct, first4_teams, bracket_df_first4, team_seed_arr_orig = _structure_bracket(bracket_df)

    # structure first 4 teams
    first4_pair_list = _create_first4_pairs(bracket_df_struct, first4_teams, bracket_df_first4)

    # structure bracket and games
    bracket_arr_orig, unique_games_all = _create_bracket_arr(bracket_df_struct)

    # structure day info
    dates_arr, team_day_list = _create_dates_and_days(dates_df, bracket_df_struct)

    # structure potential opponent info
    potential_opps_arr_orig = _create_potential_opps_arr(bracket_arr_orig)

    # structure team, game_id info
    game_match_arr_orig = _create_game_match_arr(bracket_df_struct)

    # structure unique games
    unique_games_comb = _create_unique_games_comb(dates_arr, unique_games_all)

    # structure win prob combination array
    wp_arr_orig = _create_wp_arr(win_prob_df)

    # separate teams into different potential ff and ee games
    groups_ff_orig, groups_ee_orig = _create_ff_ee_groups(bracket_arr_orig)

    initial_data_dict = {
        "season": str(season),
        "team_seed_arr_orig": team_seed_arr_orig,
        "first4_pair_list": first4_pair_list,
        "bracket_arr_orig": bracket_arr_orig,
        "team_day_list": team_day_list,
        "potential_opps_arr_orig": potential_opps_arr_orig,
        "game_match_arr_orig": game_match_arr_orig,
        "unique_games_comb": unique_games_comb,
        "wp_arr_orig": wp_arr_orig,
        "groups_ff_orig": groups_ff_orig,
        "groups_ee_orig": groups_ee_orig
    }


    return initial_data_dict





def _load_data(season: int):

    """
    Load in initial inputs

    Output:
    - bracket_df: loaded in df with bracket info, filtered for season
    - win_prob: loaded in df with win prob combination info, filtered for season
    - dates_df: loaded in df with dates of game ids info, filtered for season
    """

    # load in df with all bracket info
    bracket_df = pd.read_csv("input_data/final_bracket_df_w_seed.csv").iloc[:, 1:].copy()
    bracket_df = bracket_df.loc[bracket_df["season"]==season]

    # load in df with all win prob combinations
    win_prob_df = pd.read_csv("input_data/final_pairs_final.csv").iloc[:, 1:].copy()
    win_prob_df = win_prob_df.loc[win_prob_df["season"]==season]

    # load in df with days and round info
    dates_df = pd.read_csv("input_data/date_final_all.csv").iloc[:, 1:].copy()
    dates_df = dates_df.loc[dates_df["season"]==season]

    return bracket_df, win_prob_df, dates_df


def _structure_bracket(bracket_df: pd.DataFrame):

    """
    Initial structuring of the bracket, some first four logic

    Output:
    - bracket_df_struct: bracket_df with the first round and on games (including duplicates if could be one of two first four teams), sorted by team name
    - first4_teams: unique first four teams as a list
    - bracket_df_first4: bracket_df filtered for just first4 teams
    - team_seed_arr_orig: arr with (team id) as index and val = seed
    """

    # pull out first four teams
    bracket_df_first4 = bracket_df.loc[bracket_df["round"]=="First Four",["team1_name", "next_game_id1"]]
    bracket_df_first4 = bracket_df_first4.rename(columns = {"team1_name":"new_team", "next_game_id1":"next_game_id0"})
    bracket_df_first4["join_term"] = "Winner"
    first4_teams = bracket_df_first4["new_team"].unique()

    # bring in potential ff winners to r1 games
    bracket_join = bracket_df.copy()
    bracket_join["join_term"] = bracket_join["team1_name"].str[:6]
    bracket_df2 = bracket_join.merge(bracket_df_first4, on = ["next_game_id0","join_term"], how = "left")

    mask = (bracket_df2["join_term"]=="Winner")
    bracket_df2.loc[mask, "team1_name"] = bracket_df2.loc[mask, "new_team"]
    bracket_df2 = bracket_df2.drop(["join_term","new_team"], axis=1)
    bracket_df2 = bracket_df2.loc[bracket_df2["round"]=="Round of 64"]

    # sort teams
    bracket_df2 = bracket_df2.sort_values("team1_name")

    # pull out team id/seed
    team_seed_arr_orig = bracket_df2["team1_seed"].to_numpy(dtype = int)
    bracket_df_struct = bracket_df2.drop(columns=["team1_seed"], axis = 1)


    return bracket_df_struct, first4_teams, bracket_df_first4, team_seed_arr_orig


def _create_first4_pairs(bracket_df_struct, first4_teams, bracket_df_first4):

    """
    Find pairs for first four teams

    Output:
    - first4_pair_list: four lists of two-item lists with pairs of first4 teams
    """


    # pull out first four matchup pairs of team indices
    first4_indices_df = bracket_df_struct["team1_name"].isin(first4_teams).reset_index()
    first4_indices = first4_indices_df[first4_indices_df["team1_name"]==True].index.to_list()

    bracket_df_first4_short = bracket_df_first4.sort_values("new_team")
    bracket_df_first4_short["id"] = first4_indices

    first4_game_ids = list(bracket_df_first4_short["next_game_id0"].unique())

    first4_pair_list = []
    for gid in first4_game_ids:
        pair = list(bracket_df_first4_short.loc[bracket_df_first4_short["next_game_id0"]==gid, "id"].unique())
        first4_pair_list.append(pair)


    return first4_pair_list


def _create_bracket_arr(bracket_df_struct):
    """
    Create team, round array

    Outputs:
    - bracket_arr_orig: array with (team id, round id) and val = game_id
    - unique_games_all: list of all unique game ids
    """


    # initialize unique game ids for each round
    unique_games_r0 = bracket_df_struct["next_game_id0"].unique().tolist()
    unique_games_r1 = bracket_df_struct["next_game_id1"].unique().tolist()
    unique_games_r2 = bracket_df_struct["next_game_id2"].unique().tolist()
    unique_games_r3 = bracket_df_struct["next_game_id3"].unique().tolist()
    unique_games_r4 = bracket_df_struct["next_game_id4"].unique().tolist()
    unique_games_r5 = bracket_df_struct["next_game_id5"].unique().tolist()


    # map alphabetical-ordered IDs to numeric indices for matchups
    unique_game_ids = unique_games_r0 + unique_games_r1 + unique_games_r2 + unique_games_r3 + unique_games_r4 + unique_games_r5
    unique_game_ids.sort()

    unique_game_nums = list(range(0,len(unique_game_ids)))
    id_map = dict(zip(unique_game_ids, unique_game_nums))

    new_bracket_df = bracket_df_struct.replace(id_map).sort_values("team1_name").drop(columns=["round", "team1_name", "season"])

    unique_games_r0 = [id_map.get(x, x) for x in unique_games_r0]
    unique_games_r1 = [id_map.get(x, x) for x in unique_games_r1]
    unique_games_r2 = [id_map.get(x, x) for x in unique_games_r2]
    unique_games_r3 = [id_map.get(x, x) for x in unique_games_r3]
    unique_games_r4 = [id_map.get(x, x) for x in unique_games_r4]
    unique_games_r5 = [id_map.get(x, x) for x in unique_games_r5]


    # change unique game lists to list of lists structure
    unique_games_all = [unique_games_r0, unique_games_r1, unique_games_r2, unique_games_r3, unique_games_r4, unique_games_r5]

    # change team, round df to array
    bracket_arr_orig = new_bracket_df.to_numpy(dtype=float)


    return bracket_arr_orig, unique_games_all




def _create_dates_and_days(dates_df, bracket_df_struct):

    """
    Grab game days for the games

    Outputs:
    - dates_arr: array with (game_id) and val = day_num
    - team_dat_list: list[rd][day], with team id index and 0/1 day value
    """


    # create list of round days that corresponds with unique game_id indices
    dates_df_short = dates_df[["game_id", "day_num"]].sort_values("game_id")
    dates_arr = dates_df_short["day_num"].to_numpy(dtype=int)

    # map game ids and day nums, replace game_ids with day nums
    game_day_map = dict(zip(dates_df_short["game_id"], dates_df_short["day_num"]))

    bracket_day_arr_orig = bracket_df_struct.replace(game_day_map).sort_values("team1_name").drop(columns=["round", "team1_name", "season"]).to_numpy()


    # create list for if teams could play in a certain round/day combo
    team_day_list = []
    for c in range(3):

        cur_list = bracket_day_arr_orig[:, c]

        cur_list_d1 = (cur_list == 1).astype(int)
        cur_list_d2 = (cur_list == 2).astype(int)

        cur_list_full= [cur_list_d1, cur_list_d2]


        team_day_list.append(cur_list_full)


    return dates_arr, team_day_list



def _create_potential_opps_arr(bracket_arr_orig):

    """
    Create array with potential opponents for each team

    Output
    - potential_opps_arr_orig: arr[rd] with (team id, team id) and val = 0/1 can play each other
    """

    # create initial array
    potential_opps_arr_start = []
    for r in range(6):
        cut = bracket_arr_orig[:, r]
        potential_opps_arr_cur = (cut[:, None] == cut[None, :]).astype(np.int8)
        np.fill_diagonal(potential_opps_arr_cur, 0)

        potential_opps_arr_start.append(potential_opps_arr_cur)


    # you can't play a team you already were lined up to play a previous round, get rid of those
    potential_opps_arr_orig = [potential_opps_arr_start[0].copy()]

    for i in range(1, len(potential_opps_arr_start)):
        if i ==1:
            potential_opps_arr_orig.append(potential_opps_arr_start[i] - potential_opps_arr_orig[i-1])
        else:
            potential_opps_arr_orig.append(potential_opps_arr_start[i] - potential_opps_arr_start[i-1])


    return potential_opps_arr_orig



def _create_game_match_arr(bracket_df_struct):

    """
    Create array with which teams play in which games

    Output
    - game_match_arr_orig: array with (team id, game id) and val = 0/1 can play in that game
    """

    # create a team, game_id df for which teams play in certain games
    id_cols = [c for c in bracket_df_struct.columns if c.startswith("next_game_id")]
    base_cols = ["team1_name"]

    long = (
        bracket_df_struct[base_cols + id_cols]
        .melt(id_vars=base_cols, value_vars=id_cols, value_name="game_id")
        .dropna(subset=["game_id"])
    )

    team_game_matrix = (
        pd.crosstab(long["team1_name"], long["game_id"])
        .astype(int)
    ).sort_values("team1_name")

    # change to array
    game_match_arr_orig = team_game_matrix.to_numpy()


    return game_match_arr_orig



def _create_unique_games_comb(dates_arr, unique_games_all):

    """
    Find unique games for each round

    Output
    - unique_games_comb: list of game_ids for each day
    """

    # create new game_id structure so we know differences between day 1 and day 2 games for simulation
    unique_games_d1 = []
    unique_games_d2 = []

    # find unique games for each round
    for r in list(range(6)):

        if r <= 2:
        
            all_day1 = np.where(dates_arr==1)
            this_round = np.array(unique_games_all[r])

            mask = np.isin(this_round, all_day1)
            this_round_d1 = this_round[mask]
            this_round_d2 = this_round[~mask]

            unique_games_d1.append(this_round_d1)
            unique_games_d2.append(this_round_d2)
        
        else:
            
            this_round = np.array(unique_games_all[r])
            unique_games_d1.append(this_round)

    unique_games_comb = [unique_games_d1, unique_games_d2]


    return unique_games_comb


def _create_wp_arr(win_prob_df):

    """
    Create array w all possible matchup win probs

    Output
    - wp_arr_orig: array with (team id, team id) and val = win prob
    """

    # create array for team, team win probabilities
    df = win_prob_df.drop(columns=["season"], errors="ignore").sort_values("cur_team")

    idx_cols = [c for c in df.columns if c not in ["opponent", "win_prob"]]

    win_prob_wide = (
        df.pivot_table(
            index=idx_cols,
            columns="opponent",
            values="win_prob",
            aggfunc="first"
        )
        .reset_index()
    ).sort_values("cur_team").sort_index(axis=1).drop("cur_team", axis=1)


    wp_arr_orig = np.nan_to_num(win_prob_wide.to_numpy(dtype=float))


    return wp_arr_orig



def _create_ff_ee_groups(bracket_arr_orig):

    """
    Create groups for which teams could play in certain FF/EE games

    Outputs
    - groups_ff_orig: two lists representing a potential final four matchup with team ids in that one
    - groups_ee_orig: four lists representing a potential elite eight matchup with team ids in that one
    """

    # final four
    vals_ff = np.unique(bracket_arr_orig[:, 4])
    groups_ff_orig = {f"group{i+1}": np.where(bracket_arr_orig[:, 4] == v)[0].tolist()
            for i, v in enumerate(vals_ff)}


    # elite eight
    vals_ee = np.unique(bracket_arr_orig[:, 3])
    groups_ee_orig = {f"group{i+1}": np.where(bracket_arr_orig[:, 3] == v)[0].tolist()
            for i, v in enumerate(vals_ee)}
    

    return groups_ff_orig, groups_ee_orig