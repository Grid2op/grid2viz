import configparser
import itertools
import json
import os
import time

import dill
import numpy as np
import pandas as pd
from grid2op.Episode import EpisodeData
from grid2op.PlotGrid import PlotPlotly, PlotMatplot

from grid2viz.src.kpi.EpisodeAnalytics import EpisodeAnalytics

# refer to https://github.com/rte-france/Grid2Op/blob/master/getting_started/8_PlottingCapabilities.ipynb for better usage

graph = None
graph_matplotlib = None


def make_network(episode):
    """
        Create a Plotly network graph with the layout configuration and the selected episode.

        :param episode: An episode containing targeted data for the graph.
        :return: Network graph
    """
    global graph
    if graph is None:
        graph = PlotPlotly(
            grid_layout=episode.observation_space.grid_layout,
            observation_space=episode.observation_space,
            responsive=True)
    return graph


def make_network_matplotlib(episode):
    global graph_matplotlib
    if graph_matplotlib is None:
        graph_matplotlib = PlotMatplot(
            grid_layout=episode.observation_space.grid_layout,
            observation_space=episode.observation_space,
            line_name=False, gen_name=False, load_name=False)
    return graph_matplotlib


def make_network_agent_overview(episode):
    graph = make_network(episode)

    # modified_lines = actions_model.get_modified_lines(episode)
    # line_values = [None] * episode.n_lines
    # for line in modified_lines.index:
    #    line_values[np.where(episode.line_names == line)[0][0]] = line

    lines_attacked = list(episode.attacks_data_table['id_lines'][episode.attacks_data_table.attack].unique())
    lines_overflowed_ids = list(itertools.chain.from_iterable(episode.total_overflow_ts.line_ids))
    # to color assets on our graph with different colors while not overloading it with information
    # we will use plot_obs instead of plot_info for now
    ####
    # For that we override an observation with the desired values
    obs_colored = episode.observations[0]

    # having a rho with value 1.0 give us a red line while 0.7 gives us an orange line and 0.3 a blue line
    rho_to_color = np.array([float(0.6) if line in lines_attacked else float(0.3) for line in episode.line_names])
    rho_to_color[lines_overflowed_ids] = 1.0
    line_status_colored = np.array([False if line in lines_attacked else True for line in episode.line_names])
    obs_colored.rho = rho_to_color
    obs_colored.line_status = line_status_colored

    # network_graph = make_network(episode).plot_info(
    #    line_values=[ line if line in lines_attacked else None for line in  episode.line_names]
    #    #coloring="line"
    # )

    return graph.plot_obs(obs_colored, line_info=None, gen_info=None, load_info=None)


store = {}


def make_episode(agent, episode_name):
    """
        Load episode from cache. If not already in, compute episode data
        and save it in cache.

        :param agent: Agent Name
        :param episode_name: Name of the studied episode
        :return: Episode with computed data
    """
    if is_in_ram_cache(episode_name, agent):
        return get_from_ram_cache(episode_name, agent)
    elif is_in_fs_cache(episode_name, agent):
        episode = get_from_fs_cache(episode_name, agent)
        save_in_ram_cache(episode_name, agent, episode)
        return episode
    else:
        episode = compute_episode(episode_name, agent)
        save_in_ram_cache(episode_name, agent, episode)
        return episode


def make_episode_without_decorate(agent, episode_name):
    """
        Load episode from cache without decorating with the EpisodeData attributes
        This is needed to use multiprocessing which pickles/unpickles the results.

        :param agent: Agent Name
        :param episode_name: Name of the studied episode
        :return: Episode with computed data (without EpisodeData attributes), EpisodeData instance
    """
    if is_in_ram_cache(episode_name, agent):
        return get_from_ram_cache(episode_name, agent)
    elif is_in_fs_cache(episode_name, agent):
        beg = time.time()
        path = get_fs_cached_file(episode_name, agent)
        with open(path, "rb") as f:
            episode_analytics = dill.load(f)
        end = time.time()
        print(f"end loading scenario file: {(end - beg):.1f} s")
        return episode_analytics
    else:
        episode_data = retrieve_episode_from_disk(episode_name, agent)
        if (episode_data is not None):
            episode_analytics = EpisodeAnalytics(episode_data, episode_name, agent)
            save_in_fs_cache(episode_name, agent, episode_analytics)
            return episode_analytics
        else:
            return None


def clear_fs_cache():
    os.rmdir(cache_dir)


def is_in_fs_cache(episode_name, agent):
    return os.path.isfile(get_fs_cached_file(episode_name, agent))


def get_fs_cached_file(episode_name, agent):
    episode_dir = os.path.join(cache_dir, episode_name)
    if not os.path.exists(episode_dir):
        os.makedirs(episode_dir)
    return os.path.join(episode_dir, agent + ".dill")


def save_in_fs_cache(episode_name, agent, episode):
    path = get_fs_cached_file(episode_name, agent)
    with open(path, "wb") as f:
        dill.dump(episode, f, protocol=4)


def get_from_fs_cache(episode_name, agent):
    beg = time.time()
    path = get_fs_cached_file(episode_name, agent)
    episode_data = retrieve_episode_from_disk(episode_name, agent)
    with open(path, "rb") as f:
        episode_analytics = dill.load(f)

    episode_analytics.decorate(episode_data)
    end = time.time()
    print(f"end loading scenario file: {(end - beg):.1f} s")
    return episode_analytics


def compute_episode(episode_name, agent):
    episode_data = retrieve_episode_from_disk(episode_name, agent)
    episode_analytics = EpisodeAnalytics(episode_data, episode_name, agent)
    save_in_fs_cache(episode_name, agent, episode_analytics)
    episode_analytics.decorate(episode_data)
    return episode_analytics


def retrieve_episode_from_disk(episode_name, agent):
    path = os.path.join(agents_dir, agent)
    episode_path = os.path.abspath(os.path.join(path, episode_name))
    if os.path.isdir(episode_path):
        episode_data = EpisodeData.from_disk(
            path, episode_name
        )
        return episode_data
    else:
        return None


def is_in_ram_cache(episode_name, agent):
    return make_ram_cache_id(episode_name, agent) in store


def save_in_ram_cache(episode_name, agent, episode):
    store[make_ram_cache_id(episode_name, agent)] = episode


def get_from_ram_cache(episode_name, agent):
    return store[make_ram_cache_id(episode_name, agent)]


def make_ram_cache_id(episode_name, agent):
    return agent + episode_name


def check_all_tree_and_get_meta_and_best(base_dir, agents):
    best_agents = {}
    meta_json = {}
    scenarios = set()
    survival_dic = {}

    for agent in agents:
        survival_dic_agent = {}
        for scenario_name in os.listdir(os.path.join(base_dir, agent)):

            scenario_folder = os.path.join(base_dir, agent, scenario_name)
            if not os.path.isdir(scenario_folder):
                continue
            with open(os.path.join(scenario_folder, "episode_meta.json")) as f:
                episode_meta = json.load(fp=f)
                meta_json[scenario_name] = episode_meta

                survival_dic_agent[scenario_name] = int(
                    int(episode_meta["nb_timestep_played"]) * 100 / int(episode_meta["chronics_max_timestep"]))
                scenarios.add(scenario_name)

                if scenario_name not in best_agents:
                    best_agents[scenario_name] = {
                        "value": -1, "agent": None, "out_of": 0,
                        "cum_reward": -1
                    }
                condition_to_update_best_agent = (
                        best_agents[scenario_name]["value"] < episode_meta["nb_timestep_played"] or
                        (best_agents[scenario_name]["value"] == episode_meta["nb_timestep_played"] and
                         best_agents[scenario_name]['cum_reward'] < episode_meta['cumulative_reward'])
                )
                if condition_to_update_best_agent:
                    best_agents[scenario_name]["value"] = episode_meta["nb_timestep_played"]
                    best_agents[scenario_name]["agent"] = agent
                    best_agents[scenario_name]['cum_reward'] = episode_meta['cumulative_reward']

            best_agents[scenario_name]["out_of"] = best_agents[scenario_name]["out_of"] + 1
        survival_dic[agent] = survival_dic_agent

    survival_df = pd.DataFrame(columns=agents, index=scenarios)
    for agent in agents:
        survival_dic_agent = survival_dic[agent]
        for (scenario, survival_time) in survival_dic_agent.items():
            survival_df.loc[scenario][agent] = survival_time

    survival_df = survival_df.fillna(-1)  # To be able to cast as int below.
    survival_df = survival_df.astype(int)

    return meta_json, best_agents, survival_df


"""
Initialisation routine
"""
''' Parsing of config file'''
path_cfg = os.path.join(os.environ["GRID2VIZ_ROOT"], "config.ini")
parser = configparser.ConfigParser()
print("the config file used is located at: {}".format(path_cfg))
parser.read(path_cfg)

agents_dir = parser.get("DEFAULT", "agents_dir")
print("Agents data used is located at: {}".format(agents_dir))
cache_dir = os.path.join(agents_dir, "_cache")
'''Parsing of agent folder tree'''
agents = sorted([file for file in os.listdir(agents_dir)
                 if os.path.isdir(os.path.join(agents_dir, file)) and not file.startswith("_")])
meta_json, best_agents, survival_df = check_all_tree_and_get_meta_and_best(agents_dir, agents)
scenarios = []
scenarios_agent = {}
agent_scenario = {}

n_cores = int(parser.get("DEFAULT", "n_cores"))

for agent in agents:
    scen_path = os.path.join(agents_dir, agent)
    scens = [file for file in os.listdir(
        scen_path) if os.path.isdir(os.path.join(scen_path, file))]
    scenarios_agent[agent] = scens
    for scen in scens:
        if scen not in agent_scenario:
            agent_scenario[scen] = []
        if agent not in agent_scenario[scen]:
            agent_scenario[scen].append(agent)
    scenarios = scenarios + scens

scenarios = set(scenarios)
