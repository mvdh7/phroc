# %%
import base64
import io
import os
import tempfile
from pathlib import Path

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback, dcc, html, no_update
from dash.dash_table import DataTable
from plotly.subplots import make_subplots

from phroc import (
    UpdatingSummaryDataset,
    read_agilent_pH,
    read_excel,
    read_phroc,
    write_excel,
    write_phroc,
)


df = UpdatingSummaryDataset(
    read_agilent_pH(
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
        "editable": True,
    },
    {
        "id": "temperature",
        "name": "T / °C",
        "type": "numeric",
        "editable": True,
    },
    {
        "id": "salinity",
        "name": "Sal.",
        "type": "numeric",
        "editable": True,
    },
    {
        "id": "pH",
        "name": "pH",
        "type": "numeric",
        "format": {"specifier": "0.3f"},
    },
    {
        "id": "pH_range",
        "name": "Range(pH)",
        "type": "numeric",
        "format": {"specifier": "0.4f"},
    },
    {
        "id": "txt_n_measurements",
        "name": "Used / total",
    },
    {
        "id": "comments",
        "name": "Comments",
        "editable": True,
    },
]
cell_red = {
    "backgroundColor": "#DC3545",
    "color": "white",
}
cell_orange = {
    "backgroundColor": "#FFC107",
}


@callback(
    Output("fig_samples", "figure"),
    Input("store_measurements", "data"),
)
def plot_samples(store_measurements):
    print("plot_samples()")
    measurements = pd.DataFrame.from_records(store_measurements)
    usd = UpdatingSummaryDataset(measurements)
    samples = usd.samples
    sc_pH_s = go.Scatter(
        x=samples.index,
        y=samples.pH,
        name="pH",
        mode="markers",
    )
    # sc_pH_m = go.Scatter(
    #     x=measurements.xpos[measurements.pH_good],
    #     y=measurements.pH[measurements.pH_good],
    #     name="pH",
    #     mode="lines",
    # )
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
    # fig.add_trace(sc_pH_m, row=1, col=1)
    fig.add_trace(sc_pH_s, row=1, col=1)
    fig.add_trace(sc_s, row=2, col=1)
    fig.add_trace(sc_t, row=3, col=1)
    fig.update_yaxes(title="pH", row=1, col=1)
    fig.update_yaxes(title="Salinity", row=2, col=1)
    fig.update_yaxes(title="Temperature / °C", row=3, col=1)
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
    Output("store_measurements", "data"),
    Output("store_samples", "data"),
    Output("store_settings", "data"),
    Output("current_file_status", "className"),
    Output("current_file_origin", "children"),
    Input("upload", "filename"),
    State("upload", "contents"),
)
def update_current_file(filenames, contents):
    print("update_current_file()")
    failed = "none", no_update, no_update, no_update, "alert-warning", ""
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
                return failed
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
                    return failed
            if "comments" not in files or "standard" not in files:
                # Fail because both files were (not) comments files
                return failed
            measurements = read_agilent_pH(
                files["standard"],
                filename_comments=files["comments"],
            )
            # Tidy up temporary files
            os.remove(files["standard"])
            os.remove(files["comments"])
            usd = UpdatingSummaryDataset(measurements)
        else:
            # Fail because more than 2 files were uploaded
            return failed
        # NOTE for testing only below
        usd.samples.loc[1, "comments"] = (
            "Here is a very long comment just for testing purposes"
        )
        return (
            filename,
            usd.measurements.to_dict("records"),
            usd.samples.to_dict("records"),
            [
                usd.dye_intercept,
                usd.dye_slope,
                usd.pH_equation,
            ],
            "alert-success",
            "",
        )
    else:
        # Fail because no files uploaded (happens at program startup)
        return failed


# @callback(
#     Input("autodetect", "n_clicks"),
#     State("store", "data"),  # NOTE this is how to access the current dataset!
# )
# def print_store(n_clicks, store):
#     # NOTE use `pd.DataFrame.from_records(...)`
#     # to reverse `df.to_dict("records")`
#     # NOTE I will not be able to use the USD very easily to do the processing
#     # now, but it was probably an overcomplication anyway...(?)
#     # Unless it's super quick to compute an USD from the measurements table,
#     # then it might still be the way to go.
#     print(store)


@callback(
    Output("table_samples", "data"),
    Input("store_measurements", "data"),
)
def update_table_samples(store_measurements):
    print("update_table_samples()")
    measurements = pd.DataFrame.from_records(store_measurements)
    usd = UpdatingSummaryDataset(measurements)
    return usd.samples.to_dict("records")


@callback(
    Output("store_measurements", "data", allow_duplicate=True),
    Input("table_samples", "data"),
    State("store_measurements", "data"),
    State("table_samples", "active_cell"),
    prevent_initial_call=True,
)
def get_changes(samples_data, store_measurements, active_cell):
    print("get_changes()")
    if samples_data is not None and active_cell is not None:
        samples_df = pd.DataFrame.from_records(samples_data)
        usd = UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements))
        col = active_cell["column_id"]
        r = active_cell["row"]
        if samples_df.iloc[r][col] == usd.samples.iloc[r][col]:
            # This bit deals with the fact that if you click off a cell after
            # editing, then active_cell is the cell you edited, but if you hit
            # Enter after editing, then the active_cell is the cell below the
            # one you edited
            r -= 1
        usd.set_sample(r + 1, **{col: samples_df.iloc[r][col]})
        return usd.measurements.to_dict("records")
    else:
        return no_update


@callback(
    Output("store_measurements", "data", allow_duplicate=True),
    Output("table_samples", "active_cell"),
    Input("autodetect", "n_clicks"),
    State("store_measurements", "data"),
    prevent_initial_call=True,
)
def autodetect_windows(n_clicks, store_measurements):
    print("autodetect_windows()")
    if store_measurements is not None:
        usd = UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements))
        usd.find_windows(cutoff=0.001, minimum_values=3)
        return usd.measurements.to_dict("records"), None
    else:
        return no_update, no_update


@callback(
    Input("store_measurements", "data"),
    State("current_file", "children"),
)
def update_backup(store_measurements, current_file):
    print("update_backup()")
    if store_measurements is not None:
        phroc_path = f"{Path.home()}/.phroc"
        Path(phroc_path).mkdir(exist_ok=True)
        write_phroc(
            str(Path(f"{phroc_path}/last_session.phroc")),
            UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements)),
        )
        with open(Path(f"{phroc_path}/last_filename.txt"), "w") as f:
            f.write(current_file)


@callback(
    Output("current_file", "children", allow_duplicate=True),
    Output("store_measurements", "data", allow_duplicate=True),
    Output("store_samples", "data", allow_duplicate=True),
    Output("store_settings", "data", allow_duplicate=True),
    Output("current_file_status", "className", allow_duplicate=True),
    Output("current_file_origin", "children", allow_duplicate=True),
    Input("restore", "n_clicks"),
    prevent_initial_call=True,
)
def restore_session(n_clicks):
    try:
        usd = read_phroc(Path(f"{Path.home()}/.phroc/last_session.phroc"))
        with open(Path(f"{Path.home()}/.phroc/last_filename.txt"), "r") as f:
            filename = f.read()
        return (
            filename,
            usd.measurements.to_dict("records"),
            usd.samples.to_dict("records"),
            [
                usd.dye_intercept,
                usd.dye_slope,
                usd.pH_equation,
            ],
            "alert-success",
            " (from backup)",
        )
    except FileNotFoundError:
        return "none", no_update, no_update, no_update, "alert-warning", ""


@callback(
    Output("download_phroc", "data"),
    Input("export_phroc", "n_clicks"),
    State("current_file", "children"),
    prevent_initial_call=True,
)
def download_phroc(n_clicks, current_file):
    if current_file != "none":
        if current_file.lower().endswith(".txt"):
            filename = current_file[:-4] + ".phroc"
        elif current_file.lower().endswith(".xlsx"):
            filename = current_file[:-5] + ".phroc"
        elif current_file.lower().endswith(".phroc"):
            filename = current_file
        return dcc.send_file(
            Path(f"{Path.home()}/.phroc/last_session.phroc"),
            filename=filename,
        )
    else:
        return no_update


@callback(
    Output("download_excel", "data"),
    Input("export_excel", "n_clicks"),
    State("current_file", "children"),
    State("store_measurements", "data"),
    prevent_initial_call=True,
)
def download_excel(n_clicks, current_file, store_measurements):
    if current_file != "none":
        if current_file.lower().endswith(".txt"):
            filename = current_file[:-4] + ".xlsx"
        elif current_file.lower().endswith(".phroc"):
            filename = current_file[:-6] + ".xlsx"
        elif current_file.lower().endswith(".xlsx"):
            filename = current_file
        usd = UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements))
        with tempfile.TemporaryDirectory() as tdir:
            tpath = Path(f"{tdir}/{filename}")
            write_excel(str(tpath), usd)
            return dcc.send_file(tpath)
    else:
        return no_update


# @callback(
#     Output("table_samples", "style_table"),
#     Input("export_phroc", "n_clicks"),
# )
# def tester(n_clicks):
#     if n_clicks is None:
#         n_clicks = 1
#     print("tester()")
#     return {"height": f"{int(n_clicks * 100)}px", "overflowY": "auto"}


# %%
app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

samples_left = [
    dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Row(
                        dbc.Col(
                            dcc.Upload(
                                id="upload",
                                children=dbc.Alert(
                                    [
                                        html.H5(
                                            [
                                                "Drag and drop or ",
                                                html.A(
                                                    "select file(s)",
                                                    className="alert-link",
                                                ),
                                            ],
                                        ),
                                        html.U("Either"),
                                        " ",
                                        html.B("one"),
                                        " .phroc or .xlsx file generated by pHroc,",
                                        html.Br(),
                                        html.U("or"),
                                        " ",
                                        html.B("a pair"),
                                        " of .txt files generated by the instrument",
                                        html.Br(),
                                        "(the data file and the comments file, ",
                                        "name ending -COMMENTS.TXT)",
                                    ],
                                    className="alert-info mb-0",
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
                        dbc.Col(
                            dbc.Alert(
                                [
                                    "Current file: ",
                                    html.Span(id="current_file"),
                                    html.Span(id="current_file_origin"),
                                ],
                                id="current_file_status",
                            ),
                            className="pt-2",
                        ),
                    ),
                ],
                width=9,
                align="center",
                className="pt-3",
            ),
            dbc.Col(
                [
                    dbc.Row(
                        dbc.Col(
                            dbc.Button(
                                "Restore last session",
                                id="restore",
                                className="btn-secondary col-12",
                            ),
                            style={"textAlign": "center"},
                            className="p-1",
                        ),
                    ),
                    dbc.Row(
                        dbc.Col(
                            dbc.Button(
                                "Auto-detect windows",
                                id="autodetect",
                                className="btn-success col-12",
                            ),
                            style={"textAlign": "center"},
                            className="p-1",
                        ),
                    ),
                    dbc.Row(
                        dbc.Col(
                            [
                                dbc.Button(
                                    "Export to .phroc",
                                    id="export_phroc",
                                    className="btn-dark col-12",
                                ),
                                dcc.Download(id="download_phroc"),
                            ],
                            style={"textAlign": "center"},
                            className="p-1",
                        ),
                    ),
                    dbc.Row(
                        dbc.Col(
                            [
                                dbc.Button(
                                    "Export to .xlsx",
                                    id="export_excel",
                                    className="btn-dark col-12",
                                ),
                                dcc.Download(id="download_excel"),
                            ],
                            style={"textAlign": "center"},
                            className="p-1",
                        ),
                    ),
                ],
                align="start",
                className="p-3",
            ),
        ],
    ),
    dbc.Row(
        dbc.Col(
            DataTable(
                id="table_samples",
                columns=cols,
                style_table={"height": "650px", "overflowY": "auto"},
                style_cell={"height": "auto"},
                style_cell_conditional=[
                    # {"if": {"column_id": "sample_name"}, "width": "30%"},
                    # {"if": {"column_id": "temperature"}, "width": "15%"},
                    # {"if": {"column_id": "salinity"}, "width": "15%"},
                    # {"if": {"column_id": "pH"}, "width": "20%"},
                    {"if": {"column_id": col_id}, "text-align": "left"}
                    for col_id in ["sample_name", "comments"]
                ]
                + [{"if": {"column_id": "txt_n_measurements"}, "text-align": "center"}],
                style_data_conditional=[
                    {
                        "if": {
                            "filter_query": "{pH_range} > 0.001",
                            "column_id": "pH_range",
                        },
                        **cell_orange,
                    },
                    {
                        "if": {
                            "filter_query": "{pH_range} > 0.0012",
                            "column_id": "pH_range",
                        },
                        **cell_red,
                    },
                    {
                        "if": {
                            "filter_query": "{pH_good} < 3",
                            "column_id": "txt_n_measurements",
                        },
                        **cell_orange,
                    },
                    {
                        "if": {
                            "filter_query": "{pH_good} < 1",
                            "column_id": "txt_n_measurements",
                        },
                        **cell_red,
                    },
                    {
                        "if": {
                            "filter_query": "{salinity} < 0",
                            "column_id": "salinity",
                        },
                        **cell_red,
                    },
                    {
                        "if": {"column_editable": False},
                        "cursor": "not-allowed",
                    },
                    {
                        "if": {"column_editable": True},
                        "cursor": "text",
                    },
                ],
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
                                dbc.Col(samples_left, width=7),
                                dbc.Col(samples_right, width=5),
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
        dcc.Store(id="store_measurements"),
        dcc.Store(id="store_samples"),
        dcc.Store(id="store_settings"),
    ]
)
if __name__ == "__main__":
    app.run(debug=True)
