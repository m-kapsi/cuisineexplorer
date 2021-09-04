# -*- coding: utf-8 -*-
"""
Module doc string
"""
import pathlib
import re
import flask
import dash
import dash_table
import matplotlib.colors as mcolors
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
from dash.dependencies import Output, Input, State
from wordcloud import WordCloud
import ast

ingredients_df = pd.read_csv("data/ingredient_counts_data.csv", index_col=0)
kmeans = pd.read_csv('data/kmeans.csv')
DATA_PATH = pathlib.Path(__file__).parent.resolve()
EXTERNAL_STYLESHEETS = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]
FILENAME = "data/cleaned_data.csv"
GLOBAL_DF = pd.read_csv('data/cleaned_data.csv', sep=',',
                   converters={'ingredients':ast.literal_eval,
                               'ingredientLines': ast.literal_eval})

"""
#  Somewhat helpful functions
"""

def make_bubble(dataframe):
    """ Helper function to get recipe counts for cuisines """
    fig = px.scatter(dataframe, x="PC1", y="PC2", color="kmeans",
                text = "cuisine",
                template="plotly_white",
                size = [10000]*18,
                opacity = [.3]*18)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible = False)
    fig.update(layout_coloraxis_showscale=False)
    fig.update_traces(hovertemplate=None, hoverinfo='skip')
    return fig

def plotly_wordcloud(selected_cuisine):
    """A wonderful function that returns figure data for three equally
    wonderful plots: wordcloud, frequency histogram and treemap"""

    local_df = GLOBAL_DF[GLOBAL_DF['cuisine']==selected_cuisine]
    ingredients_freq = local_df["ingredients"].explode().value_counts()


    word_cloud = WordCloud(max_words=100, max_font_size=90)
    word_cloud.generate_from_frequencies(ingredients_freq)

    word_list = []
    freq_list = []
    fontsize_list = []
    position_list = []
    orientation_list = []
    color_list = []

    for (word, freq), fontsize, position, orientation, color in word_cloud.layout_:
        word_list.append(word)
        freq_list.append(freq)
        fontsize_list.append(fontsize)
        position_list.append(position)
        orientation_list.append(orientation)
        color_list.append(color)

    # get the positions
    x_arr = []
    y_arr = []
    for i in position_list:
        x_arr.append(i[0])
        y_arr.append(i[1])

    # get the relative occurence frequencies
    new_freq_list = []
    for i in freq_list:
        new_freq_list.append(i * 80)

    trace = go.Scatter(
        x=x_arr,
        y=y_arr,
        textfont=dict(size=new_freq_list, color=color_list),
        hoverinfo="text",
        textposition="top center",
        hovertext=["{0} - {1}".format(w, f) for w, f in zip(word_list, freq_list)],
        mode="text",
        text=word_list,
    )

    layout = go.Layout(
        {
            "xaxis": {
                "showgrid": False,
                "showticklabels": False,
                "zeroline": False,
                "automargin": True,
                "range": [-100, 250],
            },
            "yaxis": {
                "showgrid": False,
                "showticklabels": False,
                "zeroline": False,
                "automargin": True,
                "range": [-100, 450],
            },
            "margin": dict(t=20, b=20, l=10, r=10, pad=4),
            "hovermode": "closest",
        }
    )

    wordcloud_figure_data = {"data": [trace], "layout": layout}

    # frequency figure
    dishes = GLOBAL_DF[['cuisine', 'ingredients']]
    dishes = dishes.explode('ingredients')
    cuisine = selected_cuisine

    # unique ingredients
    unique_ingredients = (dishes.groupby(['ingredients', 'cuisine']).size() /
            dishes.groupby('ingredients').size()).reset_index(name='relative_usage') #reset_index naturally creates df
    unique_ingredients['relative_usage'] = unique_ingredients['relative_usage']*100
        # exclude relative usage < 90% - the top rarest
    unique_ingredients = unique_ingredients[unique_ingredients['relative_usage'] < 90]
    top20unique = unique_ingredients[unique_ingredients['cuisine'] == cuisine].sort_values(by='relative_usage', ascending = False)[:20]

    frequency_figure_data = {
        "data": [
            {
                "y": top20unique.ingredients,
                "x": top20unique.relative_usage,
                "type": "bar",
                "name": "",
                "orientation": "h"
            }
        ],
        "layout": {"height": "550",
                    "yaxis":dict(autorange="reversed"),
                    "margin": dict(t=20, b=20, l=150, r=20, pad=4)},
    }


    word_list_top = word_list[:25]
    word_list_top.reverse()
    freq_list_top = freq_list[:25]
    freq_list_top.reverse()

    treemap_trace = go.Treemap(
        labels=word_list_top, parents=[""] * len(word_list_top), values=freq_list_top
    )
    treemap_layout = go.Layout({"margin": dict(t=10, b=10, l=5, r=5, pad=4)})
    treemap_figure = {"data": [treemap_trace], "layout": treemap_layout}
    return wordcloud_figure_data, frequency_figure_data, treemap_figure


"""
#  Page layout and contents

In an effort to clean up the code a bit, we decided to break it apart into
sections. For instance: LEFT_COLUMN is the input controls you see in that gray
box on the top left. The body variable is the overall structure which most other
sections go into. This just makes it ever so slightly easier to find the right
spot to add to or change without having to count too many brackets.
"""

NAVBAR = dbc.Navbar(
    children=[
        html.A(
            # Use row and col to control vertical alignment of logo / brand
            dbc.Row(
                [dbc.Col(
                        dbc.NavbarBrand("Cuisine Exploration", className="ml-2")
                    ),
                ],
                align="center",
                no_gutters=True,
            )
        )
    ],
    color="dark",
    dark=True,
    sticky="top",
)

LEFT_COLUMN = dbc.Jumbotron(
    [
        html.H4(children="Select a cuisine", className="display-5"),
        html.Hr(className="my-2"),
        html.Label("Select a cuisine to explore below", style={"marginTop": 50}, className="lead"),
        dcc.Dropdown(
            id="cuisine-drop",
            clearable=False,
            style={"marginBottom": 50, "font-size": 12},
            options=[ {"label": i, "value": i}
            for i in GLOBAL_DF.cuisine.unique()],
            value="American"
            )
    ]
)

WORDCLOUD_PLOTS = [
    dbc.CardHeader(html.H5("Frequency of ingredients in recipes")),
    dbc.Alert(
        "Not enough data to render these plots, please adjust the filters",
        id="no-data-alert",
        color="warning",
        style={"display": "none"},
    ),
    dbc.CardBody(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Loading(
                            id="loading-frequencies",
                            children=[dcc.Graph(id="frequency_figure")],
                            type="default",
                        )
                    ),
                    dbc.Col(
                        [
                            dcc.Tabs(
                                id="tabs",
                                children=[
                                    dcc.Tab(
                                        label="Treemap",
                                        children=[
                                            dcc.Loading(
                                                id="loading-treemap",
                                                children=[dcc.Graph(id="cuisine-treemap")],
                                                type="default",
                                            )
                                        ],
                                    ),
                                    dcc.Tab(
                                        label="Wordcloud",
                                        children=[
                                            dcc.Loading(
                                                id="loading-wordcloud",
                                                children=[
                                                    dcc.Graph(id="cuisine-wordcloud")
                                                ],
                                                type="default",
                                            )
                                        ],
                                    ),
                                ],
                            )
                        ],
                        md=8,
                    ),
                ]
            )
        ]
    ),
]

CUISINES_PLOT = [
    dbc.CardHeader(html.H5("Cuisine Clustering Based on Ingredients Similarity")),
    dbc.CardBody(
        [
            dcc.Graph(id="cuisine-sample", figure = make_bubble(kmeans)),
                ],
        style={"marginTop": 0, "marginBottom": 0}
        )
        ]

TOP_INGREDIENTS_COMPS = [
    dbc.CardHeader(html.H5("Compare Popular ingredients for two cuisines")),
    dbc.CardBody(
        [
            dcc.Loading(
                id="loading-ingredient-comps",
                children=[
                    dbc.Alert(
                        "Something's gone wrong! Give us a moment, but try loading this page again if problem persists.",
                        id="no-data-alert-ingredients_comp",
                        color="warning",
                        style={"display": "none"},
                    ),
                    dbc.Row(
                        [
                            dbc.Col(html.P("Choose two cuisines to compare:"), md=12),
                            dbc.Col(
                                [
                                    dcc.Dropdown(
                                        id="ingredients-comp_1",
                                        options=[
                                            {"label": i, "value": i}
                                            for i in ingredients_df.cuisine.unique()
                                        ],
                                        value="Thai",
                                    )
                                ],
                                md=6,
                            ),
                            dbc.Col(
                                [
                                    dcc.Dropdown(
                                        id="ingredients-comp_2",
                                        options=[
                                            {"label": i, "value": i}
                                            for i in ingredients_df.cuisine.unique()
                                        ],
                                        value="American",
                                    )
                                ],
                                md=6,
                            ),
                        ]
                    ),
                    dcc.Graph(id="ingredients-comps"),
                ],
                type="default",
            )
        ],
        style={"marginTop": 0, "marginBottom": 0},
    ),
]

BODY = dbc.Container(
    [
        dbc.Row([dbc.Col(dbc.Card(TOP_INGREDIENTS_COMPS)),], style={"marginTop": 30}),
        dbc.Row(
            [
                dbc.Col(LEFT_COLUMN, md=4, align="center"),
                dbc.Col(dbc.Card(CUISINES_PLOT), md=8),
            ],
            style={"marginTop": 30},
        ),
        dbc.Card(WORDCLOUD_PLOTS)
    ],
    className="mt-12",
)


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server  # for Heroku deployment

app.layout = html.Div(children=[NAVBAR, BODY])

"""
#  Callbacks
"""

@app.callback(
    Output("ingredients-comps", "figure"),
    [Input("ingredients-comp_1", "value"), Input("ingredients-comp_2", "value")],
)
def comp_ingredient_comparisons(comp_first, comp_second):
    comp_list = [comp_first, comp_second]
    temp_df = ingredients_df[ingredients_df.cuisine.isin(comp_list)]
    temp_df.loc[temp_df.cuisine == comp_list[-1], "ingr_count"] = -temp_df[
        temp_df.cuisine == comp_list[-1]
    ].ingr_count.values

    fig = px.bar(
        temp_df,
        title="Comparison: " + comp_first + " | " + comp_second,
        x="ingredient",
        y="ingr_count",
        color="cuisine",
        template="plotly_white",
        color_discrete_sequence=px.colors.qualitative.Bold,
        labels={"cuisine": "Cuisine:", "ingredients": "Ingredients"},
        hover_data="",
    )
    fig.update_layout(legend=dict(x=0.1, y=1.1), legend_orientation="h")
    fig.update_yaxes(title="", showticklabels=False)
    fig.data[0]["hovertemplate"] = fig.data[0]["hovertemplate"][:-14]
    return fig


@app.callback(
    [
        Output("cuisine-wordcloud", "figure"),
        Output("frequency_figure", "figure"),
        Output("cuisine-treemap", "figure"),
        Output("no-data-alert", "style"),
    ],
    [
        Input("cuisine-drop", "value")
    ],
)
def update_wordcloud_plot(value_drop):
    """ Callback to rerender wordcloud plot """
    wordcloud, frequency_figure, treemap = plotly_wordcloud(value_drop)
    alert_style = {"display": "none"}
    if (wordcloud == {}) or (frequency_figure == {}) or (treemap == {}):
        alert_style = {"display": "block"}
    print("redrawing cuisine-wordcloud...done")
    return (wordcloud, frequency_figure, treemap, alert_style)


if __name__ == "__main__":
    app.run_server(debug=True)
