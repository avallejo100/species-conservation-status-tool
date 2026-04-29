#!/usr/bin/env python3

from dash import Dash, html, dcc, Input, Output, State  # type: ignore
import dash_ag_grid as dag  # type: ignore
import pandas as pd  # type: ignore
import plotly.express as px  # type: ignore
import dash_bootstrap_components as dbc  # type: ignore

from conservation_status import get_species_info


app = Dash(__name__, external_stylesheets=[dbc.themes.MORPH, dbc.icons.FONT_AWESOME])

# -------------------------------------------------
# Layout
# -------------------------------------------------

app.layout = dbc.Container([

    # Title
    dbc.Row([
        dbc.Col(
            html.H1(
                "Species Conservation Dashboard",
                className="text-center fw-bold display-6 mt-4 mb-6",
                style={"color": "#163534"}
            )
        )
    ], className="mb-4"),

    # Search
    dbc.Row([

        dbc.Col([
            dbc.Input(
                id="place-input",
                value="Texas",
                type="text",
                style={"maxWidth": "300px"}
            )
        ], width="auto"),

        dbc.Col([
            dbc.Button(
                "Load",
                id="load-button",
                n_clicks=0,
                color="primary"
            )
        ], width="auto")

    ], justify="center", className="mb-4"),

    # summary
    html.Div(id="summary", className="mb-3"),

    # Charts
    dbc.Row([

        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    dcc.Graph(id="status-plot")
                ),
                className="mb-4"
            ),
            md=6
        ),

        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    dcc.Graph(id="taxa-pie")
                ),
                className="mb-4"
            ),
            md=6
        ),

    ]),

    # Filter
    dbc.Row([
        dbc.Col([

            html.Div([

                html.Label(
                    "Filter Table",
                    className="fw-bold mb-1"
                ),

                dcc.Dropdown(
                    id="status-filter",
                    options=[
                        {"label": "All", "value": "all"},
                        {"label": "Critically Endangered", "value": "Critically Endangered"},
                        {"label": "Endangered", "value": "Endangered"},
                        {"label": "Vulnerable", "value": "Vulnerable"},
                        {"label": "Imperiled", "value": "Imperiled"},
                        {"label": "Critically Imperiled", "value": "Critically Imperiled"},
                    ],
                    value="all"
                )

            ])

        ], width=4)
    ], className="mb-3"),

    # Table
    dbc.Row([

        dbc.Col(

            dag.AgGrid(
                id="species-table",
                rowData=[],
                columnDefs=[],
                defaultColDef={
                    "sortable": True,
                    "filter": True,
                    "resizable": True,
                    "flex": 1
                },
                dashGridOptions={
                    "pagination": True,
                    "paginationPageSize": 15
                },
                style={"height": "700px", "width": "100%"}
            )

        )

    ])

], fluid=True)


# -------------------------------------------------
# Callback
# -------------------------------------------------

@app.callback(
    Output("summary", "children"),
    Output("status-plot", "figure"),
    Output("taxa-pie", "figure"),
    Output("species-table", "rowData"),
    Output("species-table", "columnDefs"),
    Input("load-button", "n_clicks"),
    State("place-input", "value"),
    Input("status-filter", "value")
)
def update_dashboard(n_clicks, place_name, status_filter):

    species = get_species_info(place_name)

    if not species:
        empty_fig = px.bar(title="No data available")
        return (
            f"No data found for '{place_name}'",
            empty_fig,
            empty_fig,
            [],
            []
        )

    df = pd.DataFrame(species)

    # filter for conservation status
    df_table = df.copy()

    if status_filter != "all":
        df_table = df_table[df_table["statuses"] == status_filter]

    if df_table.empty:
        empty_fig = px.bar(title="No matching results")
        return (
            "No species match selected filter",
            empty_fig,
            empty_fig,
            [],
            []
        )

    # Histogram
    status_counts = (
        df["statuses"]
        .fillna("Unknown")
        .value_counts()
        .reset_index()
    )
    status_counts.columns = ["Status", "Count"]

    status_fig = px.bar(
        status_counts,
        x="Status",
        y="Count",
        color="Status",
        title="Conservation Status Distribution"
    )

    # Pie chart
    taxa_counts = (
        df["taxon_name"]
        .fillna("Unknown")
        .value_counts()
        .reset_index()
    )
    taxa_counts.columns = ["Taxonomic Group", "Count"]

    taxa_fig = px.pie(
        taxa_counts,
        names="Taxonomic Group",
        values="Count",
        title="Taxonomic Group Breakdown",
        hole=0.35
    )

    # Table
    columns = [
        {"field": "common_name", "headerName": "Common Name"},
        {"field": "scientific_name", "headerName": "Scientific Name"},
        {"field": "taxon_name", "headerName": "Taxonomic Group"},
        {"field": "statuses", "headerName": "Status"}
    ]

    return (
        f"{len(df_table)} species shown from {place_name}",
        status_fig,
        taxa_fig,
        df_table.to_dict("records"),
        columns
    )


# -------------------------------------------------
# Run
# -------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=True)