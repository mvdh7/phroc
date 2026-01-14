# %%
import base64
import io

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, callback, dcc, html, no_update
from dash.dash_table import DataTable

# from dash.dash_table.Format import Format
import phroc
from phroc import UpdatingSummaryDataset, read_excel, read_phroc


df = phroc.UpdatingSummaryDataset(
    phroc.read_agilent_pH(
        "tests/data/2024-04-27-CTD1.TXT",
        dye_intercept=0,
        dye_slope=0,
        find_windows_auto=False,
        pH_equation="NIOZ",
    )
)
cols = [
    {
        "id": "sample_name",
        "name": "Name",
    },
    {
        "id": "temperature",
        "name": "Temperature / °C",
        "type": "numeric",
    },
    {
        "id": "salinity",
        "name": "Salinity",
        "type": "numeric",
    },
    {
        "id": "pH",
        "name": "pH",
        "type": "numeric",
        "format": {"specifier": "0.3f"},
    },
]


@callback(
    Output("current_file", "children"),
    Output("store", "data"),
    Input("upload", "filename"),
    State("upload", "contents"),
)
def update_current_file(filename, contents):
    # TODO expand this function to import the current file, populate DataTable,
    # draw figures
    if filename.lower().endswith(".xlsx"):
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)
        usd = read_excel(io.BytesIO(decoded))
        print(usd)
        return (
            filename,
            (
                usd.measurements.to_dict("records"),
                usd.samples.to_dict("records"),
            ),
        )

    #     usd = UpdatingSummaryDataset(uploaded)
    # elif filename.lower().endswith(".phroc"):
    #     usd = read_phroc(uploaded)
    # elif filename.lower().endswith(".xlsx"):
    #     usd = read_excel(uploaded)
    else:
        return "none", no_update


@callback(
    Input("autodetect", "n_clicks"),
    State("store", "data"),  # NOTE this is how to access the current dataset!
)
def print_store(n_clicks, store):
    # NOTE use `pd.DataFrame.from_records(...)`
    # to reverse `df.to_dict("records")`
    # NOTE I will not be able to use the USD very easily to do the processing
    # now, but it was probably an overcomplication anyway...(?)
    # Unless it's super quick to compute an USD from the measurements table,
    # then it might still be the way to go.
    print(store)


# %%
app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

samples_left = [
    dbc.Row(
        dbc.Col(
            dcc.Upload(
                id="upload",
                children=dbc.Alert(
                    [
                        "Drag and drop or ",
                        html.A("select files", className="alert-link"),
                    ],
                    className="alert-info",
                    style={
                        "textAlign": "center",
                    },
                ),
                filename="none",
            ),
        ),
    ),
    dbc.Row(
        [
            dbc.Col(
                dbc.Button(
                    "Auto-detect windows",
                    id="autodetect",
                    className="btn-success",
                ),
                style={"textAlign": "right"},
            ),
            dbc.Col(
                dbc.Button(
                    "Export to .phroc",
                    id="export_phroc",
                    className="btn-dark",
                ),
                style={"textAlign": "center"},
            ),
            dbc.Col(
                dbc.Button(
                    "Export to .xlsx",
                    id="export_excel",
                    className="btn-dark",
                ),
                style={"textAlign": "left"},
            ),
        ],
    ),
    dbc.Row(
        dbc.Col(
            html.P(["Current file: ", html.Span(id="current_file")]),
        ),
    ),
    dbc.Row(
        dbc.Col(
            DataTable(id="samples"),
        ),
    ),
]
samples_right = ["Samples right (figures)"]


app.layout = html.Div(
    [
        dbc.Tabs(
            [
                dbc.Tab(
                    dbc.Container(
                        dbc.Row(
                            [
                                dbc.Col(samples_left),
                                dbc.Col(samples_right),
                            ]
                        ),
                        fluid=True,
                    ),
                    label="Samples",
                ),
                dbc.Tab(
                    "Tab 2",
                    label="Measurements",
                ),
            ],
        ),
        dcc.Store(id="store"),
    ]
)

# app.layout = dbc.Container(
#     DataTable(
#         data=df.measurements.to_dict("records"),
#         columns=cols,
#         # page_size=10,
#         # fixed_rows={"headers": True},
#         style_table={"height": "350px", "overflowY": "auto"},
#     ),
#     fluid=True,
# )

if __name__ == "__main__":
    app.run(debug=True)
