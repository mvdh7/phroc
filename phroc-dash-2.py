# %%
import base64
import io
import os
import tempfile
from pathlib import Path

import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback, ctx, dcc, html, no_update
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
cols_samples = [
    {
        "id": "sample_name",
        "name": "Name",
        "editable": True,
    },
    {
        "id": "txt_is_tris",
        "name": "Tris?",
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
cols_measurements = [
    {
        "id": "order",
        "name": "Order",
        "type": "numeric",
    },
    {
        "id": "pH",
        "name": "pH",
        "type": "numeric",
        "format": {"specifier": "0.4f"},
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
    Input("tabs", "active_tab"),
)
def plot_samples(store_measurements, active_tab):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > plot_samples()")
    if store_measurements is not None and active_tab == "tab_samples":
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
    else:
        print(" - no update")
        return no_update


@callback(
    Output("span_current_file", "children"),
    Output("store_measurements", "data"),
    Output("store_settings", "data"),
    Output("current_file_status", "className"),
    Output("span_current_file_origin", "children"),
    Output("dropdown_sample", "options"),
    Output("dropdown_sample", "value"),
    Input("upload", "filename"),
    State("upload", "contents"),
)
def update_current_file(filenames, contents):
    try:
        print(f"{list(ctx.triggered_prop_ids.keys())[0]} > update_current_file()")
    except IndexError:
        print(f"{ctx.triggered_id} > update_current_file()")
    failed = "none", no_update, no_update, "alert-warning", "", no_update, no_update
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
                print(" - no update")
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
                    print(" - no update")
                    return failed
            if "comments" not in files or "standard" not in files:
                # Fail because both files were (not) comments files
                print(" - no update")
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
            print(" - no update")
            return failed
        return (
            filename,
            usd.measurements.to_dict("records"),
            [
                usd.dye_intercept,
                usd.dye_slope,
                usd.pH_equation,
            ],
            "alert-success",
            "",
            [{"value": i, "label": v} for i, v in usd.samples.sample_name.items()],
            1,
        )
    else:
        # Fail because no files uploaded (happens at program startup)
        print(" - no update")
        return failed


@callback(
    Output("table_samples", "data"),
    Input("store_measurements", "data"),
    Input("tabs", "active_tab"),
)
def update_table_samples(store_measurements, active_tab):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > update_table_samples()")
    if store_measurements is not None and active_tab == "tab_samples":
        measurements = pd.DataFrame.from_records(store_measurements)
        usd = UpdatingSummaryDataset(measurements)
        return usd.samples.to_dict("records")
    else:
        print(" - no update")
        return no_update


@callback(
    Output("store_measurements", "data", allow_duplicate=True),
    Input("table_samples", "data"),
    State("store_measurements", "data"),
    State("table_samples", "active_cell"),
    State("tabs", "active_tab"),
    prevent_initial_call=True,
)
def get_samples_table_user_changes(
    samples_data, store_measurements, active_cell, active_tab
):
    print(
        f"{list(ctx.triggered_prop_ids.keys())[0]} > get_samples_table_user_changes()"
    )
    if (
        samples_data is not None
        and active_cell is not None
        and active_tab == "tab_samples"
    ):
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
        # Deal with columns that don't just display their raw value in the table
        if col == "txt_is_tris":
            if isinstance(samples_df.iloc[r][col], str):
                is_tris = samples_df.iloc[r][col].upper().startswith("T")
            else:
                is_tris = False
            usd.set_sample(r + 1, is_tris=is_tris)
        # Otherwise, just adjust the edited column directly
        else:
            usd.set_sample(r + 1, **{col: samples_df.iloc[r][col]})
        return usd.measurements.to_dict("records")
    else:
        print(" - no update")
        return no_update


@callback(
    Output("store_measurements", "data", allow_duplicate=True),
    Output("table_samples", "active_cell"),
    Input("btn_autodetect", "n_clicks"),
    State("store_measurements", "data"),
    prevent_initial_call=True,
)
def autodetect_windows(n_clicks, store_measurements):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > autodetect_windows()")
    if store_measurements is not None:
        usd = UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements))
        usd.find_windows(cutoff=0.001, minimum_values=3)
        return usd.measurements.to_dict("records"), None
    else:
        print(" - no update")
        return no_update, no_update


@callback(
    Input("store_measurements", "data"),
    State("span_current_file", "children"),
)
def update_backup(store_measurements, current_file):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > update_backup()")
    if store_measurements is not None:
        phroc_path = f"{Path.home()}/.phroc"
        Path(phroc_path).mkdir(exist_ok=True)
        write_phroc(
            str(Path(f"{phroc_path}/last_session.phroc")),
            UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements)),
        )
        with open(Path(f"{phroc_path}/last_filename.txt"), "w") as f:
            f.write(current_file)
    else:
        print(" - no update")


@callback(
    Output("span_current_file", "children", allow_duplicate=True),
    Output("store_measurements", "data", allow_duplicate=True),
    Output("store_settings", "data", allow_duplicate=True),
    Output("current_file_status", "className", allow_duplicate=True),
    Output("span_current_file_origin", "children", allow_duplicate=True),
    Output("dropdown_sample", "options", allow_duplicate=True),
    Output("dropdown_sample", "value", allow_duplicate=True),
    Input("btn_restore", "n_clicks"),
    prevent_initial_call=True,
)
def restore_session(n_clicks):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > restore_session()")
    try:
        usd = read_phroc(Path(f"{Path.home()}/.phroc/last_session.phroc"))
        with open(Path(f"{Path.home()}/.phroc/last_filename.txt"), "r") as f:
            filename = f.read()
        return (
            filename,
            usd.measurements.to_dict("records"),
            [
                usd.dye_intercept,
                usd.dye_slope,
                usd.pH_equation,
            ],
            "alert-success",
            " (from backup)",
            [{"value": i, "label": v} for i, v in usd.samples.sample_name.items()],
            1,
        )
    except FileNotFoundError as e:
        print(" - no update")
        print(e)
        return "none", no_update, no_update, "alert-warning", "", no_update, no_update


@callback(
    Output("download_phroc", "data"),
    Input("btn_export_phroc", "n_clicks"),
    State("span_current_file", "children"),
    prevent_initial_call=True,
)
def download_phroc(n_clicks, current_file):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > download_phroc()")
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
        print(" - no update")
        return no_update


@callback(
    Output("download_excel", "data"),
    Input("btn_export_excel", "n_clicks"),
    State("span_current_file", "children"),
    State("store_measurements", "data"),
    prevent_initial_call=True,
)
def download_excel(n_clicks, current_file, store_measurements):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > download_excel()")
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
        print(" - no update")
        return no_update


@callback(
    Output("fig_measurements", "figure"),
    Input("store_measurements", "data"),
    Input("dropdown_sample", "value"),
    Input("tabs", "active_tab"),
    prevent_initial_call=True,
)
def plot_measurements(store_measurements, which_sample, active_tab):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > plot_measurements()")
    if store_measurements is not None and active_tab == "tab_measurements":
        usd = UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements))
        # sample = usd.samples.loc[which_sample]
        measurements = usd.measurements
        M = measurements.order_analysis == which_sample
        Mg = M & measurements.pH_good
        Mb = M & ~measurements.pH_good
        sc_good = go.Scatter(
            x=measurements[Mg].order,
            y=measurements[Mg].pH,
            mode="markers",
            name="Used",
            marker_size=20,
        )
        sc_bad = go.Scatter(
            x=measurements[Mb].order,
            y=measurements[Mb].pH,
            mode="markers",
            name="Ignored",
            marker_size=20,
        )
        fig = go.Figure(
            [sc_good, sc_bad],
            layout=go.Layout(xaxis_dtick=1),
        )
        return fig
    else:
        print(" - no update")
        return no_update


@callback(
    Output("dropdown_sample", "value", allow_duplicate=True),
    Input("move_first", "n_clicks"),
    State("dropdown_sample", "value"),
    State("dropdown_sample", "options"),
    prevent_initial_call=True,
)
def move_first(n_clicks, which_sample, options):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > move_first()")
    if options is not None:
        return 1
    else:
        print(" - no update")
        return no_update


@callback(
    Output("dropdown_sample", "value", allow_duplicate=True),
    Input("move_previous", "n_clicks"),
    State("dropdown_sample", "value"),
    State("dropdown_sample", "options"),
    prevent_initial_call=True,
)
def move_previous(n_clicks, which_sample, options):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > move_previous()")
    if options is not None and which_sample > 1:
        return which_sample - 1
    else:
        print(" - no update")
        return no_update


@callback(
    Output("dropdown_sample", "value", allow_duplicate=True),
    Input("move_next", "n_clicks"),
    State("dropdown_sample", "value"),
    State("dropdown_sample", "options"),
    prevent_initial_call=True,
)
def move_next(n_clicks, which_sample, options):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > move_next()")
    if options is not None and which_sample < len(options):
        return which_sample + 1
    else:
        print(" - no update")
        return no_update


@callback(
    Output("dropdown_sample", "value", allow_duplicate=True),
    Input("move_last", "n_clicks"),
    State("dropdown_sample", "value"),
    State("dropdown_sample", "options"),
    prevent_initial_call=True,
)
def move_last(n_clicks, which_sample, options):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > move_last()")
    if options is not None:
        return len(options)
    else:
        print(" - no update")
        return no_update


def test_for_change(current, new):
    if current == new:
        return no_update
    else:
        return new


@callback(
    Output("dropdown_sample", "options", allow_duplicate=True),
    Output("dropdown_sample", "value", allow_duplicate=True),
    State("store_measurements", "data"),
    State("dropdown_sample", "value"),
    Input("tabs", "active_tab"),
    State("dropdown_sample", "options"),
    prevent_initial_call=True,
)
def update_dropdown(store_measurements, which_sample, active_tab, dropdown_options):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > update_dropdown()")
    if store_measurements is not None and active_tab == "tab_measurements":
        usd = UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements))
        which_sample__new = min(which_sample, len(usd.samples.sample_name))
        # ^ in case samples were merged and which_sample is now higher than possible
        dropdown_options__new = []
        dropdown_options__changed = False
        for n, (v, lb) in enumerate(usd.samples.sample_name.items()):
            dropdown_options__new.append({"value": v, "label": lb})
            dropdown_options__changed |= dropdown_options[n]["value"] != v
            dropdown_options__changed |= dropdown_options[n]["label"] != lb
        dropdown_options__changed |= len(dropdown_options) != len(dropdown_options__new)
        if dropdown_options__changed:
            dropdown_options__return = dropdown_options__new
        else:
            dropdown_options__return = no_update
        return (
            dropdown_options__return,
            test_for_change(which_sample, which_sample__new),
        )
    else:
        print(" - no update")
        return no_update, no_update


@callback(
    Output("b_sample_number", "children"),
    Output("b_total_samples", "children"),
    Output("col_pH", "children"),
    Output("col_pH_range", "children"),
    Output("value_pH_std", "children"),
    Output("input_temperature", "value"),
    Output("input_salinity", "value"),
    Output("input_comment", "value"),
    Input("store_measurements", "data"),
    Input("dropdown_sample", "value"),
    Input("tabs", "active_tab"),
    State("b_sample_number", "children"),
    State("b_total_samples", "children"),
    State("col_pH", "children"),
    State("col_pH_range", "children"),
    State("value_pH_std", "children"),
    State("input_temperature", "value"),
    State("input_salinity", "value"),
    State("input_comment", "value"),
)
def update_sample_info(
    store_measurements,
    which_sample,
    active_tab,
    b_sample_number,
    b_total_samples,
    col_pH,
    col_pH_range,
    value_pH_std,
    input_temperature,
    input_salinity,
    input_comment,
):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > update_sample_info()")
    if store_measurements is not None and active_tab == "tab_measurements":
        usd = UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements))
        b_sample_number__new = which_sample
        b_total_samples__new = len(usd.samples.index)
        col_pH__new = f"{usd.samples.loc[which_sample].pH:.3f}"
        col_pH_range__new = f"{usd.samples.loc[which_sample].pH_range:.4f}"
        value_pH_std__new = f"{usd.samples.loc[which_sample].pH_std:.4f}"
        input_temperature__new = usd.samples.loc[which_sample].temperature
        input_salinity__new = usd.samples.loc[which_sample].salinity
        input_comment__new = usd.samples.loc[which_sample].comments
        new_sample_info = [
            test_for_change(b_sample_number, b_sample_number__new),
            test_for_change(b_total_samples, b_total_samples__new),
            test_for_change(col_pH, col_pH__new),
            test_for_change(col_pH_range, col_pH_range__new),
            test_for_change(value_pH_std, value_pH_std__new),
            test_for_change(input_temperature, input_temperature__new),
            test_for_change(input_salinity, input_salinity__new),
            test_for_change(input_comment, input_comment__new),
        ]
        return new_sample_info
    else:
        print(" - no update")
        return [no_update] * 8


@callback(
    Output("store_measurements", "data", allow_duplicate=True),
    Input("input_comment", "value"),
    State("dropdown_sample", "value"),
    State("store_measurements", "data"),
    Input("tabs", "active_tab"),
    prevent_initial_call=True,
)
def update_comments(comment, which_sample, store_measurements, active_tab):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > update_comments()")
    if store_measurements is not None and active_tab == "tab_measurements":
        usd = UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements))
        if usd.samples.comments.loc[which_sample] != comment:
            usd.set_sample(which_sample, comments=comment)
            return usd.measurements.to_dict("records")
        else:
            print(" - no update")
            return no_update
    else:
        print(" - no update")
        return no_update


@callback(
    Output("store_measurements", "data", allow_duplicate=True),
    Input("input_temperature", "value"),
    State("dropdown_sample", "value"),
    State("store_measurements", "data"),
    Input("tabs", "active_tab"),
    prevent_initial_call=True,
)
def update_temperature(temperature, which_sample, store_measurements, active_tab):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > update_temperature()")
    if store_measurements is not None and active_tab == "tab_measurements":
        usd = UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements))
        if float(usd.samples.temperature.loc[which_sample]) != float(temperature):
            usd.set_sample(which_sample, temperature=temperature)
            return usd.measurements.to_dict("records")
        else:
            print(" - no update")
            return no_update
    else:
        print(" - no update")
        return no_update


@callback(
    Output("store_measurements", "data", allow_duplicate=True),
    Input("input_salinity", "value"),
    State("dropdown_sample", "value"),
    State("store_measurements", "data"),
    Input("tabs", "active_tab"),
    prevent_initial_call=True,
)
def update_salinity(salinity, which_sample, store_measurements, active_tab):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > update_salinity()")
    if store_measurements is not None and active_tab == "tab_measurements":
        usd = UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements))
        if float(usd.samples.salinity.loc[which_sample]) != float(salinity):
            usd.set_sample(which_sample, salinity=salinity)
            return usd.measurements.to_dict("records")
        else:
            print(" - no update")
            return no_update
    else:
        print(" - no update")
        return no_update


@callback(
    Output("table_measurements", "data"),
    Output("table_measurements", "selected_rows"),
    Input("dropdown_sample", "value"),
    State("store_measurements", "data"),
    Input("tabs", "active_tab"),
)
def update_table_measurements(which_sample, store_measurements, active_tab):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > update_table_measurements()")
    if store_measurements is not None and active_tab == "tab_measurements":
        usd = UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements))
        M = usd.measurements.order_analysis == which_sample
        return usd.measurements[M].to_dict("records"), np.nonzero(
            usd.measurements[M].pH_good
        )[0]
    else:
        print(" - no update")
        return no_update, no_update


@callback(
    Output("store_measurements", "data", allow_duplicate=True),
    Input("table_measurements", "selected_rows"),
    State("store_measurements", "data"),
    State("tabs", "active_tab"),
    State("dropdown_sample", "value"),
    prevent_initial_call=True,
)
def change_pH_good(selected_rows, store_measurements, active_tab, which_sample):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > change_pH_good()")
    if store_measurements is not None and active_tab == "tab_measurements":
        usd = UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements))
        M = usd.measurements.order_analysis == which_sample
        selected_rows_prev = np.nonzero(usd.measurements[M].pH_good)[0]
        if len(selected_rows) != len(selected_rows_prev):
            print(usd.measurements.loc[M].pH_good)
            usd.measurements.loc[M, "pH_good"] = False
            usd.measurements.loc[
                usd.measurements.index[M][selected_rows], "pH_good"
            ] = True
            return usd.measurements.to_dict("records")
        else:
            print(" - no update")
            return no_update
    else:
        print(" - no update")
        return no_update


# %%
app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

upload_box = dcc.Upload(
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
)
current_file_box = dbc.Alert(
    [
        "Current file: ",
        html.Span(id="span_current_file"),
        html.Span(id="span_current_file_origin"),
    ],
    id="current_file_status",
)
control_buttons = [
    dbc.Row(
        dbc.Col(
            dbc.Button(
                "Restore last session",
                id="btn_restore",
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
                id="btn_autodetect",
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
                    id="btn_export_phroc",
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
                    id="btn_export_excel",
                    className="btn-dark col-12",
                ),
                dcc.Download(id="download_excel"),
            ],
            style={"textAlign": "center"},
            className="p-1",
        ),
    ),
]
samples_left = [
    dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Row(
                        dbc.Col(upload_box),
                    ),
                    dbc.Row(
                        dbc.Col(current_file_box, className="pt-2"),
                    ),
                ],
                width=9,
                align="center",
                className="pt-3",
            ),
            dbc.Col(
                control_buttons,
                align="start",
                className="p-3",
            ),
        ],
    ),
    dbc.Row(
        dbc.Col(
            DataTable(
                id="table_samples",
                columns=cols_samples,
                style_table={"height": "650px", "overflowY": "auto"},
                style_cell={"height": "auto"},
                style_cell_conditional=[
                    {"if": {"column_id": col_id}, "text-align": "left"}
                    for col_id in ["sample_name", "comments"]
                ]
                + [
                    {"if": {"column_id": col_id}, "text-align": "center"}
                    for col_id in ["txt_n_measurements", "txt_is_tris"]
                ],
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
info_measurements = dbc.Alert(
    [
        dcc.Dropdown(id="dropdown_sample", clearable=False),
        dbc.Row(
            [
                dbc.Col(
                    "Sample",
                    style={"textAlign": "right"},
                    width=4,
                ),
                dbc.Col(
                    html.Span(
                        [
                            html.B("0", id="b_sample_number"),
                            " of ",
                            html.B("0", id="b_total_samples"),
                        ],
                    ),
                    width=3,
                ),
                dbc.Col(
                    "pH",
                    style={"textAlign": "right"},
                ),
                dbc.Col(id="col_pH", style={"fontWeight": "bold"}),
            ],
            className="mt-2",
        ),
        dbc.Row(
            [
                dbc.Col(
                    "Temperature / °C",
                    style={"textAlign": "right"},
                    width=4,
                ),
                dbc.Col(
                    dcc.Input(
                        id="input_temperature",
                        type="number",
                        style={"width": "100%"},
                        debounce=True,
                    ),
                    # style={"fontWeight": "bold"},
                    width=3,
                ),
                dbc.Col(
                    "Range",
                    style={"textAlign": "right"},
                ),
                dbc.Col(
                    id="col_pH_range",
                    style={"fontWeight": "bold"},
                ),
            ],
            align="center",
            className="mt-2",
        ),
        dbc.Row(
            [
                dbc.Col(
                    "Salinity",
                    style={"textAlign": "right"},
                    width=4,
                ),
                dbc.Col(
                    dcc.Input(
                        id="input_salinity",
                        type="number",
                        min=0,
                        style={"width": "100%"},
                        debounce=True,
                    ),
                    # style={"fontWeight": "bold"},
                    width=3,
                ),
                dbc.Col(
                    "S.D.",
                    style={"textAlign": "right"},
                ),
                dbc.Col(
                    id="value_pH_std",
                    style={"fontWeight": "bold"},
                ),
            ],
            align="center",
            className="mt-2",
        ),
        dbc.Row(
            dbc.Col(
                dcc.Input(
                    id="input_comment",
                    style={"width": "100%"},
                    placeholder="Comments",
                    debounce=True,
                )
            ),
            className="mt-3",
        ),
    ],
    color="info",
)
table_measurements = DataTable(
    id="table_measurements",
    row_selectable="multi",
    columns=cols_measurements,
    style_cell_conditional=[
        {"if": {"column_id": "order"}, "text-align": "center"},
        {"if": {"column_id": "pH"}, "text-align": "left"},
    ],
)
tab_measurements = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    dcc.Graph(id="fig_measurements"),
                    width={"size": 6, "offset": 2},
                ),
                dbc.Col(
                    table_measurements,
                    width=2,
                ),
            ],
            align="center",
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.ButtonGroup(
                        [
                            dbc.Button(
                                "│←",
                                color="info",
                                outline=True,
                                id="move_first",
                            ),
                            dbc.Button(
                                "←",
                                color="info",
                                outline=True,
                                id="move_previous",
                            ),
                        ],
                        size="lg",
                    ),
                    width={"size": 1, "offset": 3},
                ),
                dbc.Col(info_measurements, width=4),
                dbc.Col(
                    dbc.ButtonGroup(
                        [
                            dbc.Button(
                                "→",
                                color="info",
                                outline=True,
                                id="move_next",
                            ),
                            dbc.Button(
                                "→│",
                                color="info",
                                outline=True,
                                id="move_last",
                            ),
                        ],
                        size="lg",
                    ),
                    width=1,
                ),
            ]
        ),
    ],
    fluid=True,
)

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
                    tab_id="tab_samples",
                ),
                dbc.Tab(
                    tab_measurements,
                    label="Measurements",
                    tab_id="tab_measurements",
                ),
            ],
            id="tabs",
        ),
        dcc.Store(id="store_measurements"),
        dcc.Store(id="store_settings"),
    ]
)
if __name__ == "__main__":
    app.run(debug=True)
