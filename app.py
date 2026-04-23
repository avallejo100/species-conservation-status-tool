import json
import redis
import pandas as pd
import plotly.express as px

from dash import Dash, html, dcc
from dash import Input, Output, State
import dash_ag_grid as dag

from conservation_status import grab_place_id

# -------------------------
# app + redis
# -------------------------

app = Dash(__name__)

r = redis.Redis(
    host="127.0.0.1",
    port=6379,
    db=0,
    decode_responses=True
)

# -------------------------
# layout
# -------------------------

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

    dcc.Graph(id="status-plot"),

    dag.AgGrid(
        id="species-table",
        rowData=[],
        columnDefs=[],
        defaultColDef={"sortable": True, "filter": True}
    )

])


# -------------------------
# callback
# -------------------------

@app.callback(
    Output("summary","children"),
    Output("status-plot","figure"),
    Output("species-table","rowData"),
    Output("species-table","columnDefs"),
    Input("load-button","n_clicks"),
    State("place-input","value")
)
def update_dashboard(n_clicks, place_name):

    place_id = grab_place_id(place_name)

    if place_id is None:
        return (
            "Place not found",
            {},
            [],
            []
        )

    raw = r.get(f"observations_{place_id}")

    if raw is None:
        return (
            f"No cached data for {place_name}",
            {},
            [],
            []
        )

    data = json.loads(raw)

    df = pd.DataFrame(data)

    # If using parsed endangered_taxa data:
    if "statuses" not in df.columns:
        return (
            "Statuses column missing in cached data",
            {},
            [],
            []
        )

    # Bar chart
    counts = (
        df["statuses"]
        .value_counts()
        .reset_index()
    )

    counts.columns = ["Status","Count"]

    fig = px.bar(
        counts,
        x="Status",
        y="Count",
        title=f"Conservation Status in {place_name}"
    )

    columns = [
        {"field":"name"},
        {"field":"id"},
        {"field":"statuses"}
    ]

    return (
        f"{len(df)} endangered species loaded",
        fig,
        df.to_dict("records"),
        columns
    )


if __name__ == "__main__":
    app.run(debug=True)