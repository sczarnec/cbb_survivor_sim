import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
from datetime import datetime
from zoneinfo import ZoneInfo
import random
from pathlib import Path
import yaml


# initialize data class for config
@dataclass
class SimConfig:

    def __init__(self, sim_id, n_iter, season, survivor_policies, initial_data_dict, still_alive_arr_orig, days_by_round):


        self.store_tourney_results: bool = True

        self.run_survivor : bool = True

        self.store_picked_teams : bool = True

        self.sim_id: str = sim_id

        self.n_iter: int = n_iter

        self.season: str = season

        self.survivor_policies: list = survivor_policies

        self.first4_pair_list: list = initial_data_dict["first4_pair_list"]
        self.wp_arr_orig: np.array = initial_data_dict["wp_arr_orig"]
        self.bracket_arr_orig: np.array = initial_data_dict["bracket_arr_orig"]
        self.game_match_arr_orig: np.array = initial_data_dict["game_match_arr_orig"]
        self.still_alive_arr_orig: np.array = still_alive_arr_orig
        self.potential_opps_arr_orig: list = initial_data_dict["potential_opps_arr_orig"]
        self.team_seed_arr_orig: np.array = initial_data_dict["team_seed_arr_orig"]

        self.groups_ff_orig: list = initial_data_dict["groups_ff_orig"]
        self.groups_ee_orig: list = initial_data_dict["groups_ee_orig"]

        self.team_day_list: list = initial_data_dict["team_day_list"]
        self.unique_games_comb: list = initial_data_dict["unique_games_comb"]

        self.days_by_round: list = days_by_round






## Simulator Object ##

class TournamentSimulator:
    def __init__(self, cfg: SimConfig):
        
        # bring in cfg class
        self.cfg = cfg

        # create sim id for data saves
        self.sim_id = self.cfg.sim_id


        # initialize data storages
        if self.cfg.store_tourney_results:
            self.tourney_results = np.full(
                (68, self.cfg.n_iter),
                7,
                dtype=int
            )
        else:
            self.tourney_results = None

        if self.cfg.store_picked_teams:
            chosen_teams_all_save = []

    # helper function to store result of simulated game
    def record_result(self, team_id: int, round_: int, iter_: int):
        if self.cfg.store_tourney_results:
            self.tourney_results[team_id, iter_] = round_

    
    def survivor_choose_team(self, interm_wp_arr, potential_opps_arr, team_seed_arr, r_cur, policies_alive, not_picked, d, still_alive_arr, groups_ff, groups_ee, team_day_list):

        """
        Function for each policy to choose their team for a given round

        Inputs:
        - interm_wp_arr: wp_arr that has been modified with 0s for teams not in the torunament anymore
        - potential_opps_arr: list of arrays (list[rd]) containing arrays with (team id, team id) and val = 0/1 can play each other
        - team_seed_arr: array with (team id) as index and val = seed
        - r_cur: current round in this iteration of sim
        - policies_alive: list with 1 for that policy id alive and 0 for out
        - not_picked: list of arrays for each policy id, array with (team id) and val = 1/0 for if available for that policy to choose
        - d: day in this round (0/1)
        - still_alive_arr: array with (team id) as indices and val = 1/0 for if still alive in tourney
        - groups_ff: two lists representing a potential final four matchup with team ids in that one
        - groups_ee: four lists representing a potential elite eight matchup with team ids in that one
        - team_day_list: list[rd][day], with team id index and 0/1 day value
        """

        # how many opps for each round
        opps_by_nr = [1, 2, 4, 8, 16, 32]

        # initialize things for loop
        it=-1
        all_rd_wps = []

        # for each round from current until final
        for r in range(r_cur,6):

            it+=1

            # zero out opponents that teams can't play this round
            next_wp_arr = potential_opps_arr[r] * interm_wp_arr

            # if this is a future round, gotta grab the last to weight each potential opponent by their chances of advancing to this currently evaluated round
            if it > 0:
                all_rd_wps_arr_cp_cur = all_rd_wps_arr_cp[:,it-1]
                final_wp_arr = next_wp_arr * all_rd_wps_arr_cp_cur[None, :]
            else:
                final_wp_arr = next_wp_arr.copy()

            # sum the weighted win probs vs opponents, represents each team id's prob of winning this round given they made it there
            row_sums = final_wp_arr.sum(axis=1)

            # add this given round win prob to the list, stack the columns next to each other
            all_rd_wps.append(row_sums)
            all_rd_wps_arr = np.column_stack(all_rd_wps)

            # find cumprod to be used in next round (informs those opponent weights from a few lines above)
            all_rd_wps_arr_cp = np.cumprod(all_rd_wps_arr, axis=1)

        

        # for each policy, choose a team for the round
        chosen_teams = []
        for p_iter in range(len(policies_alive)):

            # if this policy isn't alive, add None as the choice and call it a day
            if policies_alive[p_iter] == 0:
                if r_cur !=3:
                    chosen_teams.append(None)
                else:
                    chosen_teams.append([None, None])
                continue
            
            # find policy info
            policy = self.cfg.survivor_policies[p_iter]

            # find the weights for this round, create the objective array (still team id index with objective func as value)
            if r_cur < 5:
                weights_list = np.array(policy["next_round_weights"][f"r{r_cur}"])
                obj_arr = (all_rd_wps_arr * weights_list.T).sum(axis=1)
            else:
                obj_arr = all_rd_wps_arr.sum(axis=1)

            # get rid of teams in the objective array who are out of the tourney or have been picked already
            available_arr = still_alive_arr * not_picked[p_iter]
            obj_arr = obj_arr * not_picked[p_iter]

            # if it's one of the first three rounds, gotta also get rid of teams not playing on this current round/day combo
            if r_cur <= 2:
                obj_arr = obj_arr * team_day_list[r_cur][d]

            # if the policy includes seed restrictions for this round, zero those indices out
            if ((r_cur in [0,1]) and (policy["ignore_seeds"][f"r{r_cur}"] is not False)):

                keep_team_seed = (~np.isin(team_seed_arr, policy["ignore_seeds"][f"r{r_cur}"])).astype(int).ravel()
                obj_arr = obj_arr * keep_team_seed


            # finally, sort objective function
            # obj_vals is the list sorted by vals, team_idx_order sorts the team ids (previous indices) by value
            obj_vals = np.sort(obj_arr)[::-1] 
            team_idx_order = np.argsort(obj_arr)[::-1]

            # get rid of ranked indices if ==0 (means they were zeroed out in those previous lines for some reason)
            team_idx_order = team_idx_order[obj_vals!=0]

            # if there's a minimum team per region restriction for this round, filter those indices out
            if (policy["min_region"] is not False) & (r_cur < 3):
                region_filter = []
                for g_num in [1, 2, 3, 4]:
                    if np.sum(available_arr[groups_ee[f"group{g_num}"]]) <= policy["min_region"][f"r{r_cur}"]:
                        region_filter.extend(groups_ee[f"group{g_num}"])
                if len(region_filter)>0:
                    mask_outside = ~np.isin(team_idx_order, region_filter)
                    if mask_outside.any():
                        team_idx_order = team_idx_order[mask_outside]

            # if there's a smart last round strategy, apply the appropriate filters
            if (policy["smart_last_rounds"] != False) and (r_cur >= 3):
                if r_cur == 3:
                    group_1_idxs = team_idx_order[np.isin(team_idx_order, groups_ff["group1"])]
                    group_2_idxs = team_idx_order[np.isin(team_idx_order, groups_ff["group2"])]

                    if (policy["smart_last_rounds"]["ee_swap"] == True) and (group_1_idxs.size > 1) and (group_2_idxs.size > 1):
                        # pick third and fourth best teams for elite eight and continue
                        chosen_teams.append([int(group_1_idxs[1]), int(group_2_idxs[1])])
                        not_picked[p_iter][group_1_idxs[1]] = 0
                        not_picked[p_iter][group_2_idxs[1]] = 0
                        continue
                if (r_cur == 4) and (policy["smart_last_rounds"]["ff_swap"] == True) and (team_idx_order.size > 1):
                    # pick second best team for final four and continue
                    chosen_team_cur = team_idx_order[1]
                    chosen_teams.append(chosen_team_cur)
                    not_picked[p_iter][team_idx_order[1]] = 0 
                    continue


            # if the list is empty, just call the chosen team 1000, logic will handle downstream
            if team_idx_order.size == 0:
                chosen_teams.append(1000)
                continue


            # if the round is not the EE, pick one team
            if r_cur != 3:
                # if there's randomness for this round, follow the weights to choose the team randomly
                if (r_cur in [0, 1]) and (policy["randomness"][f"r{r_cur}"] is not False):
                    random_weights = policy["randomness"][f"r{r_cur}"][:team_idx_order.size + 1]
                    random_weight_sum = sum(random_weights)
                    random_weights = [num / random_weight_sum for num in random_weights]

                    rand_idx = random.choices(range(len(random_weights)), weights=random_weights, k=1)[0]

                    chosen_team_cur = team_idx_order[rand_idx]
                    chosen_teams.append(chosen_team_cur)
                    not_picked[p_iter][team_idx_order[rand_idx]] = 0

                # else, choose the best team
                else:

                    chosen_team_cur = team_idx_order[0]
                    chosen_teams.append(chosen_team_cur)
                    not_picked[p_iter][team_idx_order[0]] = 0


            # if it is the EE, choose the best 2 teams
            else:
                chosen_teams.append([int(team_idx_order[0]), int(team_idx_order[1])])
                not_picked[p_iter][team_idx_order[0]] = 0
                not_picked[p_iter][team_idx_order[1]] = 0


        # end policy loop, turn chosen teams list into array, return
        chosen_teams_np = np.array(chosen_teams, dtype=object)

        return chosen_teams_np





            


    def run_sim(self):

        """
        Run the simulation!
        """

        # saving initializing
        if self.cfg.run_survivor == True:
            policies_round_out_save = []
        if self.cfg.store_picked_teams == True:
            chosen_teams_all_save = []

        # initialize some data that stays the same
        potential_opps_arr = self.cfg.potential_opps_arr_orig.copy()
        team_seed_arr = self.cfg.team_seed_arr_orig.copy()
        groups_ff = self.cfg.groups_ff_orig.copy()
        groups_ee = self.cfg.groups_ee_orig.copy()
        first4_pair_list = self.cfg.first4_pair_list.copy()
        days_by_round = self.cfg.days_by_round.copy()
        unique_games_comb = self.cfg.unique_games_comb.copy()
        team_day_list = self.cfg.team_day_list.copy()


        # loop through iterations
        for i in range(self.cfg.n_iter):

            # initialize data that needs to be refreshed every iter
            wp_arr = self.cfg.wp_arr_orig.copy()
            bracket_arr = self.cfg.bracket_arr_orig.copy()
            game_match_arr = self.cfg.game_match_arr_orig.copy()
            still_alive_arr = self.cfg.still_alive_arr_orig.copy()


            # initialize stuff for survivor run
            if self.cfg.run_survivor == True:
                policies_alive = np.ones((len(self.cfg.survivor_policies)), dtype=int)
                not_picked = [np.ones(68, dtype=int).copy() for _ in range(len(self.cfg.survivor_policies))]
                policies_round_out = np.full(len(self.cfg.survivor_policies), 10, dtype=int)

                chosen_teams = None
                chosen_teams_all = []


            # sim the first four beforehand
            for g in first4_pair_list:

                # game 
                t1, t2 = g
                # wp of t1
                t1_wp = wp_arr[t1][t2]
                # who wins
                rand_num = random.random()
                # make the loser have 0s for wp_arr and game_match_arr
                if rand_num > t1_wp:
                    still_alive_arr[t1] = 0
                    wp_arr[t1, :] = 0
                    wp_arr[:, t1] = 0
                    game_match_arr[t1, :] = 0
                # record result of loser
                    self.record_result(t1, 0, i)
                else:
                    still_alive_arr[t2] = 0
                    wp_arr[t2, :] = 0
                    wp_arr[:, t2] = 0
                    game_match_arr[t2, :] = 0
                    self.record_result(t2, 0, i)



            # now do the same in the real tourney, for each round
            # count which day of tourney (0-10, which is National Champion)
            day_cum = -1
            for r in list(range(0,6)):

                # for each day of the round
                for d in list(range(0,days_by_round[r])):

                    # add another day if not EE, in which case add two
                    if r !=3:
                        day_cum += 1
                    else:
                        day_cum += 2

                    # choose a team for each policy
                    if self.cfg.run_survivor == True:
                        chosen_teams = self.survivor_choose_team(interm_wp_arr=wp_arr, potential_opps_arr=potential_opps_arr, team_seed_arr=team_seed_arr, r_cur=r, policies_alive=policies_alive, not_picked=not_picked, d=d, still_alive_arr=still_alive_arr, groups_ff=groups_ff, groups_ee=groups_ee, team_day_list=team_day_list)

                    # go thru each game in the round and determine winner
                    for g in unique_games_comb[d][r]:
                        # find teams
                        t1, t2 = np.flatnonzero(game_match_arr[:, g] == 1)
                        # find win probs
                        t1_wp = wp_arr[t1][t2]
                        # determine winner
                        rand_num = random.random()
                        # record loser
                        if rand_num > t1_wp:
                            still_alive_arr[t1] = 0
                            wp_arr[t1, :] = 0
                            wp_arr[:, t1] = 0
                            game_match_arr[t1, :] = 0
                            self.record_result(t1, r+1, i)
                        else:
                            still_alive_arr[t2] = 0
                            wp_arr[t2, :] = 0
                            wp_arr[:, t2] = 0
                            game_match_arr[t2, :] = 0
                            self.record_result(t2, r+1, i)
                    
                    # go thru logic to see which policies survived
                    if self.cfg.run_survivor == True:

                        # if not EE
                        if r != 3:
                            # store this round's chosen teams for eventual write out
                            chosen_teams_all.append(chosen_teams)

                            # look at chosen teams, mark each policy as 1 or 0 for still alive prior to this round (1000s and Nones marked as out)
                            chosen_alive = np.zeros(len(chosen_teams), dtype=int) 
                            mask = (chosen_teams != None) & (chosen_teams != 1000)
                            idx = chosen_teams[mask].astype(int)
                            chosen_alive[mask] = still_alive_arr[idx].astype(int)

                            # mark teams who are out (==1)
                            new_outs = (np.array(policies_alive) + np.array(chosen_alive))
                            # update which policies that are alive (dead zero out)
                            policies_alive = np.array(policies_alive) * np.array(chosen_alive)

                            # record the round for each new dead policy
                            policies_round_out[new_outs == 1] = day_cum
                            
                            # record these things manually for policies that ran out of teams
                            policies_alive[chosen_teams == 1000] = 0
                            policies_round_out[chosen_teams == 1000] = day_cum
                        
                        # if it's the EE
                        else:
                            # add chosen teams to storage
                            chosen_teams_all.append(chosen_teams[:,0])
                            chosen_teams_all.append(chosen_teams[:,1])

                            # go thru marking logic for each chosen team, record new outs
                            chosen_teams0 = chosen_teams[:,0]
                            chosen_alive0 = np.zeros(len(chosen_teams0), dtype=int) 
                            mask0 = chosen_teams0 != None
                            idx0 = chosen_teams0[mask0].astype(int)
                            chosen_alive0[mask0] = still_alive_arr[idx0].astype(int)

                            new_outs0 = (np.array(policies_alive) + np.array(chosen_alive0))


                            # same for second chosen team this round
                            chosen_teams1 = chosen_teams[:,1]
                            chosen_alive1 = np.zeros(len(chosen_teams1), dtype=int) 
                            mask1 = chosen_teams1 != None
                            idx1 = chosen_teams1[mask1].astype(int)
                            chosen_alive1[mask1] = still_alive_arr[idx1].astype(int)

                            new_outs1 = (np.array(policies_alive) + np.array(chosen_alive1))


                            # record if policy is still alive
                            policies_alive = np.array(policies_alive) * np.array(chosen_alive0) * np.array(chosen_alive1)

                            
                            # if round out == 3 then only one lost, if == 2 then both lost and day out should be subtracted by one
                            new_outs = new_outs0 + new_outs1
                            policies_round_out[new_outs == 3] = day_cum
                            policies_round_out[new_outs == 2] = day_cum-1


            # append round for storage
            if self.cfg.run_survivor == True:
                policies_round_out_save.append(list(policies_round_out))

                
            # save picked teams for storage
            if self.cfg.store_picked_teams == True:
                def to_slot_strings(run):
                    arrs = [np.asarray(x, dtype=object).ravel() for x in run]
                    L = len(arrs[0])
                    out = []
                    for j in range(L):
                        vals = []
                        for a in arrs:
                            v = a[j]
                            vals.append("None" if v is None else str(int(v)))
                        out.append(",".join(vals))
                    return out

                chosen_teams_all_mod = to_slot_strings(chosen_teams_all)
                chosen_teams_all_save.append(chosen_teams_all_mod)



        # save all this stuff after the run

        # create save folder
        if (self.cfg.run_survivor == True) or (self.cfg.store_tourney_results == True) or (self.cfg.store_picked_teams == True):
            run_dir = Path(f"sim_saves/run_{self.sim_id}")
            run_dir.mkdir(parents=True, exist_ok=True)

            if self.cfg.run_survivor:
                (run_dir / "survivor_results").mkdir(exist_ok=True)
            if self.cfg.store_tourney_results:
                (run_dir / "tourney_results").mkdir(exist_ok=True)
            if self.cfg.store_picked_teams:
                (run_dir / "chosen_teams").mkdir(exist_ok=True)


        # survivor results, config
        if self.cfg.run_survivor == True:
            survivor_results_df = pd.DataFrame({i: col for i, col in enumerate(policies_round_out_save)})
            survivor_results_df.to_csv(f"sim_saves/run_{self.sim_id}/survivor_results/run_{self.sim_id}_survivor_results_{self.cfg.season}.csv")

            cfg_dict = asdict(self.cfg)
            with open(f"sim_saves/run_{self.sim_id}/run_{self.sim_id}_config.yaml", "w") as f:
                yaml.safe_dump(cfg_dict, f, sort_keys=False)

        # which teams were picked
        if self.cfg.store_picked_teams == True:
            #print(chosen_teams_all_save)
            chosen_team_results_df = pd.DataFrame(chosen_teams_all_save).T
            chosen_team_results_df.to_csv(f"sim_saves/run_{self.sim_id}/chosen_teams/run_{self.sim_id}_chosen_teams_{self.cfg.season}.csv")

        # tourney results
        if self.cfg.store_tourney_results == True:
            tourney_results_pdf = pd.DataFrame(self.tourney_results)
            tourney_results_pdf.to_csv(f"sim_saves/run_{self.sim_id}/tourney_results/run_{self.sim_id}_tourney_results_{self.cfg.season}.csv")

        





