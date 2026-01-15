# %%
import base64
import io
import tempfile

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback, dcc, html, no_update
from dash.dash_table import DataTable
from plotly.subplots import make_subplots

import phroc
from phroc import UpdatingSummaryDataset, read_agilent_pH, read_excel, read_phroc


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
    {
        "id": "pH_std",
        "name": "SD(pH)",
        "type": "numeric",
        "format": {"specifier": "0.3f"},
    },
]


@callback(
    Output("fig_samples", "figure"),
    Input("store", "data"),
)
def plot_samples(store):
    measurements = pd.DataFrame.from_records(store[0])
    usd = UpdatingSummaryDataset(measurements)
    samples = usd.samples
    print(samples)
    sc_pH_s = go.Scatter(
        x=samples.index,
        y=samples.pH,
        name="pH",
        mode="markers",
    )
    sc_pH_m = go.Scatter(
        x=measurements.xpos[measurements.pH_good],
        y=measurements.pH[measurements.pH_good],
        name="pH",
        mode="markers",
    )
    sc_s = go.Scatter(
        x=samples.index,
        y=samples.salinity,
        name="Salinity",
        mode="markers",
    )
    sc_t = go.Scatter(
        x=samples.index,
        y=samples.temperature,
        name="Temperature",
        mode="markers",
    )
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.5, 0.25, 0.25],
    )
    fig.add_trace(sc_pH_m, row=1, col=1)
    fig.add_trace(sc_pH_s, row=1, col=1)
    fig.add_trace(sc_s, row=2, col=1)
    fig.add_trace(sc_t, row=3, col=1)
    fig.update_yaxes(title="pH", row=1, col=1)
    fig.update_yaxes(title="Salinity", row=2, col=1)
    fig.update_yaxes(title="Temperature / °C", row=3, col=1)
    fig.update_xaxes(title="Sample number", row=3, col=1)
    fig.update_xaxes(
        tickmode="array",
        tickvals=samples.index,
        ticktext=samples.sample_name,
        tickangle=90,
        range=[samples.index[0] - 1, samples.index[-1] + 1],
    )
    fig.update_layout(
        showlegend=False,
        height=900,
    )
    return fig


@callback(
    Output("current_file", "children"),
    Output("store", "data"),
    Output("samples", "data"),
    Input("upload", "filename"),
    State("upload", "contents"),
)
def update_current_file(filenames, contents):
    # TODO expand this function to import the current file, populate DataTable,
    # draw figures
    print("update_current_file()")
    if contents is not None:
        if len(contents) == 1:
            content_type, content_string = contents[0].split(",")
            decoded = base64.b64decode(content_string)
            filename = filenames[0]
            if filename.lower().endswith(".xlsx"):
                usd = read_excel(io.BytesIO(decoded))
            elif filename.lower().endswith(".phroc"):
                usd = read_phroc(io.BytesIO(decoded))
            else:
                # Fail because 1 file uploaded neither .xlsx nor .phroc
                return "none", no_update, no_update
        elif len(contents) == 2:
            files = {}
            for i, filename in enumerate(filenames):
                if filename.lower().endswith(".txt"):
                    content_type, content_string = contents[i].split(",")
                    decoded = base64.b64decode(content_string)
                    with tempfile.NamedTemporaryFile(
                        mode="wb",
                        delete=False,
                        suffix=filename,
                    ) as tmp_file:
                        tmp_file.write(decoded)
                        if filename.lower().endswith("-comments.txt"):
                            files["comments"] = tmp_file.name
                        else:
                            files["standard"] = tmp_file.name
                else:
                    # Fail because at least 1 of 2 files uploaded not .txt
                    return "none", no_update, no_update
            if "comments" not in files or "standard" not in files:
                # Fail because both files were (not) comments files
                return "none", no_update, no_update
            measurements = read_agilent_pH(
                files["standard"],
                filename_comments=files["comments"],
            )
            usd = UpdatingSummaryDataset(measurements)
        else:
            # Fail because more than 2 files were uploaded
            return "none", no_update, no_update
        return (
            filename,
            (
                usd.measurements.to_dict("records"),
                usd.samples.to_dict("records"),
                usd.dye_intercept,
                usd.dye_slope,
                usd.pH_equation,
            ),
            usd.samples.to_dict("records"),
        )
    else:
        # Fail because no files uploaded (happens at program startup)
        return "none", no_update, no_update


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
                        html.A("select file(s)", className="alert-link"),
                    ],
                    className="alert-info",
                    style={
                        "textAlign": "center",
                    },
                ),
                filename="none",
                multiple=True,
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
            DataTable(
                id="samples",
                columns=cols,
                style_table={"height": "700px", "overflowY": "auto"},
            ),
        ),
    ),
]
samples_right = [
    dbc.Row(
        dbc.Col(
            dcc.Graph(id="fig_samples"),
        )
    )
]


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
