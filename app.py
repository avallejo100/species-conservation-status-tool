#!/usr/bin/env python3

from dash import Dash, html, dcc, Input, Output, State  # type: ignore
import dash_ag_grid as dag  # type: ignore
import pandas as pd  # type: ignore
import plotly.express as px  # type: ignore
import dash_bootstrap_components as dbc  # type: ignore

from conservation_status import get_species_info


app = Dash(__name__, external_stylesheets=[dbc.themes.MINTY])

# -------------------------------------------------
# Layout
# -------------------------------------------------

app.layout = dbc.Container([

    # Title
    dbc.Row([
        dbc.Col(
            html.Div(
    [
        html.H1(
            "Threatened Species Conservation Explorer",
            style={
                "fontWeight": "700",
                "letterSpacing": "1px",
                "color": "#1b4332",
                "marginBottom": "5px"
            }
        ),

        html.Div(
            "Interactive biodiversity & conservation analytics dashboard",
            style={
                "fontSize": "16px",
                "color": "#6c757d",
                "marginBottom": "10px"
            }
        )
    ],
    style={
        "textAlign": "center",
        "paddingTop": "20px"
    }
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
                style={"width": "350px",
                       "fontSize": "18px",
                       "padding": "10px"}
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
    html.Div(id="summary", className="fw-bold fs-5 mb-3 text-dark"),

    # Charts
    dbc.Row([
        # Histogram
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    dcc.Graph(id="status-plot")
                ),
                className="mb-4"
            ),
            md=6
        ),
        # Pie chart
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    dcc.Graph(id="taxa-pie")
                ),
                className="mb-4"
            ),
            md=6
        ),
    ],
    justify="center",
    className="mb-4"
),

    # Filter
    dbc.Row([
        dbc.Col([

            html.Div([

                html.Label(
                    "Conservation Status Filter:",
                    className="fw-bold mb-1 text-dark"
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
                className="ag-theme-quartz",
                style={"height": "700px",
                       "width": "100%",
                       "border": "1px solid #e0e0e0",
                       "borderRadius": "10px",
                       "overflow": "hidden",
                       "boxShadow": "0 2px 10px rgba(0,0,0,0.08)"}
            )

        )
    ])
],  fluid=True,
    style={"backgroundColor": "#eff6e1",
           "paddingBottom": "30px",
           "paddingLeft": "30px",
           "paddingRight": "30px"}
    )


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
        title="Taxonomic Group Breakdown"
    )

    # Table
    columns = [
        {"field": "common_name", "headerName": "Common Name"},
        {"field": "scientific_name", "headerName": "Scientific Name"},
        {"field": "taxon_name", "headerName": "Taxonomic Group"},
        {"field": "statuses", "headerName": "Status"},
        {
    "field": "statuses",
    "headerName": "Status",
    "cellStyle": {
        "styleConditions": [
            {
                "condition": "params.value == 'Critically Endangered'",
                "style": {"backgroundColor": "#f8d7da"}
            },
            {
                "condition": "params.value == 'Endangered'",
                "style": {"backgroundColor": "#fce5cd"}
            },
            {
                "condition": "params.value == 'Vulnerable'",
                "style": {"backgroundColor": "#fff3cd"}
            },
            {
                "condition": "params.value == 'Imperiled'",
                "style": {"backgroundColor": "#d1ecf1"}
            },
            {
                "condition": "params.value == 'Critically Imperiled'",
                "style": {"backgroundColor": "#e2d6f3"}
            },
            {
                "condition": "params.value == 'Other'",
                "style": {"backgroundColor": "#e2e3e5"}
            }
        ]
    }
}
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
    app.run(host="127.0.0.1", port=8050, debug=True)