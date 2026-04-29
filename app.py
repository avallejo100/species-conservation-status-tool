#!/usr/bin/env python3

from dash import Dash, html, dcc, Input, Output, State  # type: ignore
import dash_ag_grid as dag  # type: ignore
import pandas as pd  # type: ignore
import plotly.express as px  # type: ignore

from conservation_status import get_species_info

app = Dash(__name__)

# cards
CARD_STYLE = {
    "padding": "20px",
    "borderRadius": "18px",
    "boxShadow": "0 3px 10px rgba(0,0,0,.08)",
    "backgroundColor": "white",
    "textAlign": "center"
}

# layout
app.layout = html.Div([

    html.H1(
        "Threatened Species Conservation Explorer",
        style={"textAlign": "center", "marginBottom": "30px"}
    ),

    # search
    html.Div([

        dcc.Input(
            id="place-input",
            value="Texas",
            type="text",
            style={
                "width": "300px",
                "padding": "10px",
                "marginRight": "10px"
            }
        ),

        html.Button(
            "Load",
            id="load-button",
            n_clicks=0,
            style={"padding": "10px 20px"}
        )

    ], style={
        "display": "flex",
        "justifyContent": "center",
        "marginBottom": "30px"
    }),

    # filter
    html.Div([

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
            value="all",
            style={"width": "300px"}
        )

    ], style={"marginBottom": "30px"}),

    dcc.Loading(

        type="circle",
        children=[

            html.Div(id="summary"),

             # histogram + pie   
            html.Div([

                html.Div(
                    dcc.Graph(id="status-plot"),
                    style={
                        "border": "2px solid #ddd",
                        "borderRadius": "10px",
                        "padding": "10px"
                    }
                ),

                html.Div(
                    dcc.Graph(id="taxa-pie"),
                    style={
                        "border": "2px solid #ddd",
                        "borderRadius": "10px",
                        "padding": "10px"
                    }
                )

            ], style={
                "display": "grid",
                "gridTemplateColumns": "1fr 1fr",
                "gap": "20px",
                "marginBottom": "30px"
            }),

            # table
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

        ]
    )

], style={
    "maxWidth": "1200px",
    "margin": "0 auto",
    "padding": "20px"
})

@app.callback(
    Output("summary", "children"),
    Output("status-plot", "figure"),
    Output("taxa-pie", "figure"),
    Output("species-table", "rowData"),
    Output("species-table", "columnDefs"),
    Input("load-button", "n_clicks"),
    Input("status-filter", "value"),
    State("place-input", "value")
)
def update_dashboard(n_clicks, status_filter, place_name):

    species = get_species_info(place_name)

    empty_fig = px.bar(title="No data available")
    empty_pie = px.pie(title="No data available")

    if not species:

        return (
            f"No data found for '{place_name}'",
            empty_fig,
            empty_pie,
            [],
            []
        )

    df = pd.DataFrame(species)

    df_all = df.copy()
    df_table = df.copy()


    # Filter
    if status_filter != "all":
        df_table = df_table[df_table["statuses"] == status_filter]

    if df.empty:
        empty_fig = px.bar(title="No matching results")
        empty_pie = px.pie(title="No matching results")

        return (
            "No species match selected filter",
            empty_fig,
            empty_pie,
            [],
            []
        )

    # Histogram status distribution
    status_counts = (
        df_all["statuses"]
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

    # Taxa pie chart
    taxa_counts = (
        df_all["taxon_name"]
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

    # table columns

    columns = [
        {"field": "common_name", "headerName": "Common Name"},
        {"field": "scientific_name", "headerName": "Scientific Name"},
        {"field": "taxon_name", "headerName": "Taxonomic Group"},
        {"field": "statuses", "headerName": "Status"}
    ]

    return (
        f"{len(df)} species found in {place_name}",
        status_fig,
        taxa_fig,
        df_table.to_dict("records"),
        columns
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=True)