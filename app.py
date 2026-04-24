from dash import Dash, html, dcc
from dash import Input, Output, State
import dash_ag_grid as dag
import pandas as pd
import plotly.express as px

from conservation_status import get_species_info

app = Dash(__name__)

app.layout = html.Div([

    html.H1("Endangered Species Dashboard"),

    dcc.Input(
        id="place-input",
        value="Texas",
        type="text"
    ),

    html.Button(
        "Load",
        id="load-button",
        n_clicks=0
    ),

    html.Br(),
    html.Br(),

    html.Div(id="summary"),
    dcc.Loading(
    type="circle",
    children=[
        dcc.Graph(id="status-plot"),
        dag.AgGrid(
            id="species-table",
            rowData=[],
            columnDefs=[],
            defaultColDef={
                "sortable": True,
                "filter": True
            }
        )
    ]
    )
])


@app.callback(
    Output("summary","children"),
    Output("status-plot","figure"),
    Output("species-table","rowData"),
    Output("species-table","columnDefs"),
    Input("load-button","n_clicks"),
    State("place-input","value")
)
def update_dashboard(n_clicks, place_name):

    species = get_species_info(place_name)

    if not species:
        return (
            "No data found",
            {},
            [],
            []
        )

    df = pd.DataFrame(species)


    status_counts = (
        df["statuses"]
        .fillna("Unknown")
        .value_counts()
        .reset_index()
    )

    status_counts.columns = [
        "Status",
        "Count"
    ]


    fig = px.bar(
        status_counts,
        x="Status",
        y="Count",
        title=f"Conservation Status Distribution: {place_name}"
    )


    columns = [
        {"field":"name"},
        {"field":"id"},
        {"field":"statuses"}
    ]


    return (
        f"{len(df)} endangered species found in {place_name}",
        fig,
        df.to_dict("records"),
        columns
    )


if __name__ == "__main__":
    app.run(debug=True)