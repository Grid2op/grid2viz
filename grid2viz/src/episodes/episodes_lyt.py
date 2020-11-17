import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import plotly.figure_factory as ff
import seaborn as sn

from grid2viz.src.manager import survival_df


# This is to improve readability of the heatmap of survival steps for agents
def get_heatmap_survival_score(survival_df):
    if (survival_df.shape[0] >= 2) and (survival_df.shape[1] >= 2):
        clustered_df = sn.clustermap(survival_df)
        reordered_scenarios = clustered_df.dendrogram_row.reordered_ind
        reordered_agents = clustered_df.dendrogram_col.reordered_ind
        return survival_df.iloc[reordered_scenarios, reordered_agents]
    else:
        return survival_df


clustered_survival_df = get_heatmap_survival_score(survival_df)

z_text = clustered_survival_df.copy().astype(str)
z_text[z_text == "-1"] = ""

heatmap_figure = ff.create_annotated_heatmap(  # go.Figure(data=go.Heatmap(
    z=clustered_survival_df.values,  # survival_df.values,#z=pd.concat([survival_df, survival_df]))),
    x=clustered_survival_df.columns.tolist(), y=clustered_survival_df.index.tolist(),
    colorscale='RdYlGn',
    zmid=50,
    annotation_text=z_text.values
)

heatmap_div = html.Div(children=[
    html.H5("Heatmap"),
    dcc.Graph(
        id="heatmap",
        figure=heatmap_figure,
    )], style={'textAlign': 'center'}, className="col-xl-12 align-self-center")

SurvivalHeatmap_div = html.Div(id="h", children=[
    html.H4("h"),
    html.Div(children=[
        html.Details([
            html.Summary('Heatmap'),
            heatmap_div
        ])
    ], className='card-body row'),
], className="lineBlock card")

cards = dbc.Row(id='cards_container', className="m-1")

layout = html.Div(
    id="scenario_page",
    children=[dcc.Store(id="relayoutStoreScenario"),
              SurvivalHeatmap_div,
              cards]
)
