import dash
from dash import dcc, html, Input, Output, dash_table
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pathlib import Path


SIM_SAVES_DIR = Path(__file__).parent.parent / "sim_saves"
TEAM_ID_MAP_PATH = Path(__file__).parent / "teams_id_map.csv"

# Load team id map: index=team_idx (0-67), columns=season years
_team_id_map = pd.read_csv(TEAM_ID_MAP_PATH, index_col=0) if TEAM_ID_MAP_PATH.exists() else None


def get_team_names(season: str) -> list[str] | None:
    """Return list of 68 team names for the given season, or None if unavailable."""
    if _team_id_map is None or season == "All":
        return None
    col = str(season)
    if col not in _team_id_map.columns:
        return None
    return _team_id_map[col].tolist()

# Day number -> label. Day 6 = both EE picks lost (day_cum - 1), day 7 = one EE pick lost
DAY_LABELS = {
    0: "R64 D1", 1: "R64 D2",
    2: "R32 D1", 3: "R32 D2",
    4: "S16 D1", 5: "S16 D2",
    6: "EE (both)", 7: "EE (one)",
    8: "Final Four", 9: "Championship",
    10: "Survived",
}

ROUND_LABELS = {
    0: "Play-in loss", 1: "R64", 2: "R32", 3: "S16",
    4: "Elite 8", 5: "Final Four", 6: "Runner-up", 7: "Champion",
}


def get_runs():
    if not SIM_SAVES_DIR.exists():
        return []
    return sorted([d.name for d in SIM_SAVES_DIR.iterdir() if d.is_dir()], reverse=True)


def get_seasons(run_id):
    path = SIM_SAVES_DIR / run_id / "survivor_results"
    seasons = sorted([f.stem.split("_")[-1] for f in path.glob("*.csv")])
    return ["All"] + seasons if len(seasons) > 1 else seasons


def _load_and_concat(run_id, subdir, season):
    path = SIM_SAVES_DIR / run_id / subdir
    if season == "All":
        files = sorted(path.glob("*.csv"))
    else:
        files = list(path.glob(f"*{season}.csv"))
    if not files:
        return None
    dfs = [pd.read_csv(f, index_col=0) for f in files]
    if len(dfs) == 1:
        return dfs[0]
    combined = pd.concat(dfs, axis=1, ignore_index=True)
    return combined


def load_survivor(run_id, season):
    return _load_and_concat(run_id, "survivor_results", season)


def load_tourney(run_id, season):
    return _load_and_concat(run_id, "tourney_results", season)


def load_chosen(run_id, season):
    return _load_and_concat(run_id, "chosen_teams", season)


STAT_CONFIG = {
    "Avg Day":  {"threshold": None, "is_pct": False},
    "% R64 D1": {"threshold": 0,    "is_pct": True},
    "% R64 D2": {"threshold": 1,    "is_pct": True},
    "% R32 D1": {"threshold": 2,    "is_pct": True},
    "% R32 D2": {"threshold": 3,    "is_pct": True},
    "% S16 D1": {"threshold": 4,    "is_pct": True},
    "% S16 D2": {"threshold": 5,    "is_pct": True},
    "% EE D1":  {"threshold": 6,    "is_pct": True},
    "% EE D2":  {"threshold": 7,    "is_pct": True},
    "% FF":     {"threshold": 8,    "is_pct": True},
    "% Won":    {"threshold": 9,    "is_pct": True},
}

app = dash.Dash(__name__, title="CBB Survivor Sim")

runs = get_runs()
default_run = runs[0] if runs else None
default_seasons = get_seasons(default_run) if default_run else []
default_season = default_seasons[0] if default_seasons else None

app.layout = html.Div([

    html.H2("CBB Survivor Sim Dashboard", style={"marginBottom": "4px"}),

    html.Div([
        html.Div([
            html.Label("Run"),
            dcc.Dropdown(
                id="run-dropdown",
                options=[{"label": r, "value": r} for r in runs],
                value=default_run,
                clearable=False,
            ),
        ], style={"width": "360px", "marginRight": "20px"}),
        html.Div([
            html.Label("Season"),
            dcc.Dropdown(
                id="season-dropdown",
                options=[{"label": s, "value": s} for s in default_seasons],
                value=default_season,
                clearable=False,
            ),
        ], style={"width": "120px", "marginRight": "20px"}),
        html.Div([
            html.Label("Policies"),
            dcc.Dropdown(
                id="policy-filter",
                multi=True,
                placeholder="All policies",
            ),
        ], style={"width": "300px", "marginRight": "20px"}),
        html.Div([
            html.Label("Teams (Advancement & Pick Freq)"),
            dcc.Dropdown(
                id="team-filter",
                multi=True,
                placeholder="All teams",
            ),
        ], style={"width": "400px"}),
    ], style={"display": "flex", "alignItems": "flex-end", "margin": "16px 0"}),

    dcc.Tabs([
        dcc.Tab(label="Policy Summary Table", children=[
            html.Div(id="summary-table", style={"margin": "20px 0"}),
        ]),
        dcc.Tab(label="Policy Bar Chart", children=[
            html.Div([
                html.Label("Stat"),
                dcc.Dropdown(
                    id="policy-bar-stat",
                    options=[{"label": k, "value": k} for k in STAT_CONFIG],
                    value="Avg Day",
                    clearable=False,
                    style={"width": "200px"},
                ),
            ], style={"margin": "16px 0 8px"}),
            dcc.Graph(id="policy-bar-chart", style={"height": "520px"}),
        ]),
        dcc.Tab(label="Survival Curves", children=[dcc.Graph(id="survival-curve", style={"height": "520px"})]),
        dcc.Tab(label="Team Advancement", children=[
            html.Div(id="tourney-results", style={"margin": "20px 0"}),
        ]),
        dcc.Tab(label="Team Bar Chart", children=[
            html.Div([
                html.Label("Stat"),
                dcc.Dropdown(
                    id="team-bar-stat",
                    options=[
                        {"label": "Avg Round", "value": "Avg Round"},
                        {"label": "% R64",     "value": "% R64"},
                        {"label": "% R32",     "value": "% R32"},
                        {"label": "% S16",     "value": "% S16"},
                        {"label": "% EE",      "value": "% EE"},
                        {"label": "% FF",      "value": "% FF"},
                        {"label": "% Champ",   "value": "% Champ"},
                        {"label": "% Won",     "value": "% Won"},
                    ],
                    value="Avg Round",
                    clearable=False,
                    style={"width": "200px"},
                ),
            ], style={"margin": "16px 0 8px"}),
            dcc.Graph(id="team-bar-chart", style={"height": "520px"}),
        ]),
        dcc.Tab(label="Team Pick Frequency", children=[dcc.Graph(id="pick-heatmap", style={"height": "560px"})]),
    ]),

], style={"fontFamily": "sans-serif", "maxWidth": "1200px", "margin": "0 auto", "padding": "20px"})


@app.callback(
    Output("season-dropdown", "options"),
    Output("season-dropdown", "value"),
    Input("run-dropdown", "value"),
)
def update_seasons(run_id):
    if not run_id:
        return [], None
    seasons = get_seasons(run_id)
    options = [{"label": s, "value": s} for s in seasons]
    return options, seasons[0] if seasons else None


@app.callback(
    Output("policy-filter", "options"),
    Output("policy-filter", "value"),
    Input("run-dropdown", "value"),
    Input("season-dropdown", "value"),
)
def update_policy_filter(run_id, season):
    df = load_survivor(run_id, season)
    if df is None:
        return [], []
    options = [{"label": f"Policy {p}", "value": p} for p in df.index]
    return options, list(df.index)


@app.callback(
    Output("team-filter", "options"),
    Output("team-filter", "value"),
    Input("season-dropdown", "value"),
)
def update_team_filter(season):
    team_names = get_team_names(season)
    if team_names is None:
        options = [{"label": f"Team {i}", "value": i} for i in range(68)]
        return options, list(range(68))
    options = [{"label": name, "value": i} for i, name in enumerate(team_names)]
    return options, list(range(len(team_names)))


@app.callback(
    Output("survival-curve", "figure"),
    Input("run-dropdown", "value"),
    Input("season-dropdown", "value"),
    Input("policy-filter", "value"),
)
def survival_curve(run_id, season, policies):
    df = load_survivor(run_id, season)
    if df is None:
        return go.Figure()

    if policies:
        df = df.loc[df.index.isin(policies)]

    days = list(DAY_LABELS.keys())
    # Start at 100% before any day, then show % surviving past each day
    x_labels = ["Start"] + [DAY_LABELS[d] for d in days]

    fig = go.Figure()
    for policy_idx in df.index:
        row = df.loc[policy_idx].values.astype(int)
        pct = [100.0] + [float(np.mean(row > d) * 100) for d in days]
        fig.add_trace(go.Scatter(
            x=x_labels,
            y=pct,
            mode="lines+markers",
            name=f"Policy {policy_idx}",
        ))

    fig.update_layout(
        title=f"Survival Curves — {season}",
        xaxis_title="Tournament Day",
        yaxis_title="% Still Alive",
        yaxis=dict(range=[0, 105]),
        legend_title="Policy",
        hovermode="x unified",
    )
    return fig



# "Made it to round R" means their tourney value > R-1, i.e., they won that round
TEAM_ROUND_THRESHOLDS = [
    ("% R64",   0),
    ("% R32",   1),
    ("% S16",   2),
    ("% EE",    3),
    ("% FF",    4),
    ("% Champ", 5),
    ("% Won",   6),
]


@app.callback(
    Output("tourney-results", "children"),
    Input("run-dropdown", "value"),
    Input("season-dropdown", "value"),
    Input("team-filter", "value"),
)
def tourney_results(run_id, season, teams):
    df = load_tourney(run_id, season)
    if df is None:
        return html.Div("No data.")

    if teams is not None:
        df = df.loc[df.index.isin(teams)]

    team_names = get_team_names(season)

    rows = []
    for team_idx in df.index:
        vals = df.loc[team_idx].values.astype(int)
        name = team_names[team_idx] if team_names else f"Team {team_idx}"
        row = {"Team": name}
        row["Avg Round"] = round(float(np.mean(vals)), 2)
        for label, threshold in TEAM_ROUND_THRESHOLDS:
            row[label] = round(float(np.mean(vals > threshold) * 100), 1)
        rows.append(row)

    table_df = pd.DataFrame(rows).sort_values("Avg Round", ascending=False)

    columns = [{"name": c, "id": c, "type": "numeric" if c != "Team" else "text"}
               for c in table_df.columns]

    return dash_table.DataTable(
        data=table_df.to_dict("records"),
        columns=columns,
        sort_action="native",
        sort_by=[{"column_id": "Avg Round", "direction": "desc"}],
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "center", "padding": "8px"},
        style_cell_conditional=[{"if": {"column_id": "Team"}, "textAlign": "left"}],
        style_header={"fontWeight": "bold", "backgroundColor": "#f0f0f0"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#fafafa"},
        ],
    )


@app.callback(
    Output("pick-heatmap", "figure"),
    Input("run-dropdown", "value"),
    Input("season-dropdown", "value"),
    Input("policy-filter", "value"),
    Input("team-filter", "value"),
)
def pick_heatmap(run_id, season, policies, teams):
    df = load_chosen(run_id, season)
    if df is None:
        return go.Figure()

    if policies:
        df = df.loc[df.index.isin(policies)]

    n_teams = 68
    n_policies = len(df.index)
    counts = np.zeros((n_policies, n_teams), dtype=int)

    for p_i, policy_idx in enumerate(df.index):
        for cell in df.loc[policy_idx].dropna():
            for val in str(cell).split(","):
                val = val.strip()
                if val not in ("None", "1000", ""):
                    try:
                        counts[p_i, int(val)] += 1
                    except ValueError:
                        pass

    team_names = get_team_names(season)
    all_labels = team_names if team_names else [f"T{i}" for i in range(n_teams)]

    # filter to selected teams
    selected = teams if teams is not None else list(range(n_teams))
    counts = counts[:, selected]
    x_labels = [all_labels[i] for i in selected]

    fig = go.Figure(go.Heatmap(
        z=counts,
        x=x_labels,
        y=[f"Policy {p}" for p in df.index],
        colorscale="Blues",
        hovertemplate="Policy %{y}<br>%{x}<br>Times picked: %{z}<extra></extra>",
    ))

    fig.update_layout(
        title=f"Team Pick Frequency by Policy — {season}",
        xaxis_title="Team ID",
        yaxis_title="Policy",
        xaxis=dict(tickangle=-45),
    )
    return fig


# Columns: round name -> (label, min day_out to have "made it to" this round)
# "Made it to R32" means survived R64 (both days) -> round_out > 1
ROUND_THRESHOLDS = [
    ("% R64 D1", 0),
    ("% R64 D2", 1),
    ("% R32 D1", 2),
    ("% R32 D2", 3),
    ("% S16 D1", 4),
    ("% S16 D2", 5),
    ("% EE D1",  6),
    ("% EE D2",  7),
    ("% FF",     8),
    ("% Won",    9),
]


@app.callback(
    Output("summary-table", "children"),
    Input("run-dropdown", "value"),
    Input("season-dropdown", "value"),
    Input("policy-filter", "value"),
)
def summary_table(run_id, season, policies):
    df = load_survivor(run_id, season)
    if df is None:
        return html.Div("No data.")

    if policies:
        df = df.loc[df.index.isin(policies)]

    rows = []
    for policy_idx in df.index:
        vals = df.loc[policy_idx].values.astype(int)
        row = {"Policy": f"Policy {policy_idx}"}
        row["Avg Day"] = round(float(np.mean(vals)), 2)
        for label, threshold in ROUND_THRESHOLDS:
            row[label] = round(float(np.mean(vals > threshold) * 100), 1)
        rows.append(row)

    table_df = pd.DataFrame(rows).sort_values("Avg Day", ascending=False)

    columns = [{"name": c, "id": c, "type": "numeric" if c != "Policy" else "text"}
               for c in table_df.columns]

    return dash_table.DataTable(
        data=table_df.to_dict("records"),
        columns=columns,
        sort_action="native",
        sort_by=[{"column_id": "Avg Day", "direction": "desc"}],
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "center", "padding": "8px"},
        style_cell_conditional=[{"if": {"column_id": "Policy"}, "textAlign": "left"}],
        style_header={"fontWeight": "bold", "backgroundColor": "#f0f0f0"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#fafafa"},
        ],
    )


@app.callback(
    Output("policy-bar-chart", "figure"),
    Input("run-dropdown", "value"),
    Input("season-dropdown", "value"),
    Input("policy-filter", "value"),
    Input("policy-bar-stat", "value"),
)
def policy_bar_chart(run_id, season, policies, stat):
    df = load_survivor(run_id, season)
    if df is None:
        return go.Figure()

    if policies:
        df = df.loc[df.index.isin(policies)]

    cfg = STAT_CONFIG[stat]
    x_labels, y_vals, ci_vals = [], [], []

    for policy_idx in df.index:
        vals = df.loc[policy_idx].values.astype(int)
        n = len(vals)
        x_labels.append(f"Policy {policy_idx}")

        if cfg["is_pct"]:
            p = float(np.mean(vals > cfg["threshold"]))
            y_vals.append(round(p * 100, 2))
            ci_vals.append(round(1.96 * np.sqrt(p * (1 - p) / n) * 100, 2))
        else:
            mean = float(np.mean(vals))
            y_vals.append(round(mean, 2))
            ci_vals.append(round(1.96 * float(np.std(vals, ddof=1)) / np.sqrt(n), 2))

    fig = go.Figure(go.Bar(
        x=x_labels,
        y=y_vals,
        error_y=dict(type="data", array=ci_vals, visible=True),
        hovertemplate="%{x}<br>" + stat + ": %{y}<br>±%{error_y.array} (95% CI)<extra></extra>",
    ))

    fig.update_layout(
        title=f"{stat} by Policy — {season}",
        xaxis_title="Policy",
        yaxis_title=stat,
    )
    return fig


TEAM_STAT_CONFIG = {
    "Avg Round": {"threshold": None, "is_pct": False},
    "% R64":     {"threshold": 0,    "is_pct": True},
    "% R32":     {"threshold": 1,    "is_pct": True},
    "% S16":     {"threshold": 2,    "is_pct": True},
    "% EE":      {"threshold": 3,    "is_pct": True},
    "% FF":      {"threshold": 4,    "is_pct": True},
    "% Champ":   {"threshold": 5,    "is_pct": True},
    "% Won":     {"threshold": 6,    "is_pct": True},
}


@app.callback(
    Output("team-bar-chart", "figure"),
    Input("run-dropdown", "value"),
    Input("season-dropdown", "value"),
    Input("team-filter", "value"),
    Input("team-bar-stat", "value"),
)
def team_bar_chart(run_id, season, teams, stat):
    df = load_tourney(run_id, season)
    if df is None:
        return go.Figure()

    if teams is not None:
        df = df.loc[df.index.isin(teams)]

    team_names = get_team_names(season)
    cfg = TEAM_STAT_CONFIG[stat]
    x_labels, y_vals, ci_vals = [], [], []

    for team_idx in df.index:
        vals = df.loc[team_idx].values.astype(int)
        n = len(vals)
        name = team_names[team_idx] if team_names else f"T{team_idx}"
        x_labels.append(name)

        if cfg["is_pct"]:
            p = float(np.mean(vals > cfg["threshold"]))
            y_vals.append(round(p * 100, 2))
            ci_vals.append(round(1.96 * np.sqrt(p * (1 - p) / n) * 100, 2))
        else:
            mean = float(np.mean(vals))
            y_vals.append(round(mean, 2))
            ci_vals.append(round(1.96 * float(np.std(vals, ddof=1)) / np.sqrt(n), 2))

    fig = go.Figure(go.Bar(
        x=x_labels,
        y=y_vals,
        error_y=dict(type="data", array=ci_vals, visible=True),
        hovertemplate="%{x}<br>" + stat + ": %{y}<br>±%{error_y.array} (95% CI)<extra></extra>",
    ))

    fig.update_layout(
        title=f"{stat} by Team — {season}",
        xaxis_title="Team",
        yaxis_title=stat,
        xaxis=dict(tickangle=-45),
    )
    return fig


if __name__ == "__main__":
    app.run(debug=True)
