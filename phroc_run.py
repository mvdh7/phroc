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

# from dash_extensions import Keyboard
from phroc import (
    UpdatingSummaryDataset,
    read_agilent_pH,
    read_excel,
    read_phroc,
    write_excel,
    write_phroc,
)
from phroc.meta import __version__


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
        "id": "txt_extra_mcp",
        "name": "+20 mCP?",
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
            marker_size=10,
            marker_color="#703be7",
        )
        sc_s = go.Scatter(
            x=samples.index,
            y=samples.salinity,
            name="Salinity",
            mode="markers",
            marker_size=10,
            marker_color="#76cd26",
        )
        sc_t = go.Scatter(
            x=samples.index,
            y=samples.temperature,
            name="Temperature",
            mode="markers",
            marker_size=10,
            marker_color="#f10c45",
        )
        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            row_heights=[0.5, 0.25, 0.25],
        )
        # fig.add_trace(sc_pH_m, row=1, col=1)
        fig.add_trace(sc_pH_s, row=1, col=1)
        fig.add_trace(sc_t, row=2, col=1)
        fig.add_trace(sc_s, row=3, col=1)
        fig.update_yaxes(title="pH", row=1, col=1)
        fig.update_yaxes(title="Temperature / °C", row=2, col=1)
        fig.update_yaxes(title="Salinity", row=3, col=1)
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
                is_tris = samples_df.iloc[r][col].upper().startswith("Y")
            else:
                is_tris = False
            usd.set_sample(r + 1, is_tris=is_tris)
        elif col == "txt_extra_mcp":
            if isinstance(samples_df.iloc[r][col], str):
                extra_mcp = samples_df.iloc[r][col].upper().startswith("Y")
            else:
                extra_mcp = False
            usd.set_sample(r + 1, extra_mcp=extra_mcp)
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
            marker_color="#0485d1",
        )
        sc_bad = go.Scatter(
            x=measurements[Mb].order,
            y=measurements[Mb].pH,
            mode="markers",
            name="Ignored",
            marker_size=20,
            marker_symbol="x",
            marker_color="#FE2C54",
        )
        fig = go.Figure(
            [sc_good, sc_bad],
            layout=go.Layout(
                height=500,
                xaxis_dtick=1,
                xaxis_range=[
                    measurements[M].order.min() - 0.5,
                    measurements[M].order.max() + 0.5,
                ],
            ),
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
    Input("store_split_count", "data"),
    prevent_initial_call=True,
)
def update_dropdown(
    store_measurements,
    which_sample,
    active_tab,
    dropdown_options,
    split_count,
):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > update_dropdown()")
    if store_measurements is not None and active_tab == "tab_measurements":
        usd = UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements))
        which_sample__new = min(which_sample, len(usd.samples.sample_name))
        # ^ in case samples were merged and which_sample is now higher than possible
        dropdown_options__new = []
        dropdown_options__changed = False
        for n, (v, lb) in enumerate(usd.samples.sample_name.items()):
            try:
                dropdown_options__new.append({"value": v, "label": lb})
                dropdown_options__changed |= dropdown_options[n]["value"] != v
                dropdown_options__changed |= dropdown_options[n]["label"] != lb
            except IndexError:
                dropdown_options__changed = True
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
    Output("check_is_tris", "value"),
    Output("check_extra_mcp", "value"),
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
    State("check_is_tris", "value"),
    State("check_extra_mcp", "value"),
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
    check_is_tris,
    check_extra_mcp,
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
        if len(check_is_tris) == 1:
            is_tris = [" Tris?"]
        else:
            is_tris = []
        if usd.samples.loc[which_sample].is_tris:
            is_tris__new = [" Tris?"]
        else:
            is_tris__new = []
        if len(check_extra_mcp) == 1:
            extra_mcp = [" +20 mCP?"]
        else:
            extra_mcp = []
        if usd.samples.loc[which_sample].extra_mcp:
            extra_mcp__new = [" +20 mCP?"]
        else:
            extra_mcp__new = []
        new_sample_info = [
            test_for_change(b_sample_number, b_sample_number__new),
            test_for_change(b_total_samples, b_total_samples__new),
            test_for_change(col_pH, col_pH__new),
            test_for_change(col_pH_range, col_pH_range__new),
            test_for_change(value_pH_std, value_pH_std__new),
            test_for_change(input_temperature, input_temperature__new),
            test_for_change(input_salinity, input_salinity__new),
            test_for_change(input_comment, input_comment__new),
            test_for_change(is_tris, is_tris__new),
            test_for_change(extra_mcp, extra_mcp__new),
        ]
        return new_sample_info
    else:
        print(" - no update")
        return [no_update] * 10


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
    Output("store_measurements", "data", allow_duplicate=True),
    Input("check_is_tris", "value"),
    State("dropdown_sample", "value"),
    State("store_measurements", "data"),
    Input("tabs", "active_tab"),
    prevent_initial_call=True,
)
def update_is_tris(check_is_tris, which_sample, store_measurements, active_tab):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > update_is_tris()")
    if store_measurements is not None and active_tab == "tab_measurements":
        usd = UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements))
        is_tris = len(check_is_tris) == 1
        if is_tris != usd.samples.is_tris.loc[which_sample]:
            usd.set_sample(which_sample, is_tris=is_tris)
            return usd.measurements.to_dict("records")
        else:
            print(" - no update")
            return no_update
    else:
        print(" - no update")
        return no_update


@callback(
    Output("store_measurements", "data", allow_duplicate=True),
    Input("check_extra_mcp", "value"),
    State("dropdown_sample", "value"),
    State("store_measurements", "data"),
    Input("tabs", "active_tab"),
    prevent_initial_call=True,
)
def update_extra_mcp(check_extra_mcp, which_sample, store_measurements, active_tab):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > update_extra_mcp()")
    if store_measurements is not None and active_tab == "tab_measurements":
        usd = UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements))
        extra_mcp = len(check_extra_mcp) == 1
        if extra_mcp != usd.samples.extra_mcp.loc[which_sample]:
            usd.set_sample(which_sample, extra_mcp=extra_mcp)
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
    Input("store_measurements", "data"),
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


def move_measurement(direction, which_sample, store_measurements):
    print(f"move_measurement({direction})")
    usd = UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements))
    # Direction is -1 to move measurement backwards or +1 for forwards
    assert direction in [-1, 1]
    s = which_sample
    s_new = s + direction
    # Only do anything if we're not already on the first (-1) or last (+1) sample
    if direction == -1:
        neither_first_nor_last = s_new > 0
        m_ix = 0  # the iloc in the subset of the measurements table to move (first)
    elif direction == 1:
        neither_first_nor_last = s_new < usd.samples.shape[0]
        m_ix = -1  # the iloc in the subset of the measurements table to move (last)
    if neither_first_nor_last:
        M = usd.measurements.order_analysis == s
        m = usd.measurements[M].index[m_ix]  # the measurement to move
        # Move the sample by renaming
        usd.set_measurement(m, sample_name=usd.samples.sample_name.loc[s_new])
    return usd


@callback(
    Output("store_measurements", "data", allow_duplicate=True),
    Output("dropdown_sample", "value", allow_duplicate=True),
    Output("store_split_count", "data", allow_duplicate=True),
    Input("btn_first_to_prev", "n_clicks"),
    State("dropdown_sample", "value"),
    State("store_measurements", "data"),
    State("store_split_count", "data"),
    State("table_measurements", "data"),
    prevent_initial_call=True,
)
def move_first_to_prev(
    n_clicks,
    which_sample,
    store_measurements,
    split_count,
    data_table_measurements,
):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > move_first_to_prev()")
    if store_measurements is not None and which_sample > 1:
        usd = move_measurement(-1, which_sample, store_measurements)
        # If we completely remove the sample then we want to move to the previous
        # sample (i.e., the one that we have moved the points to)
        if store_measurements[-1]["order_analysis"] > len(usd.samples.index):
            dd = which_sample - 1
        else:
            dd = no_update
        if len(data_table_measurements) == 1:
            split_count += 1
        else:
            split_count = no_update
        return usd.measurements.to_dict("records"), dd, split_count
    else:
        print(" - no_update")
        return no_update, no_update, no_update


@callback(
    Output("store_measurements", "data", allow_duplicate=True),
    Output("store_split_count", "data", allow_duplicate=True),
    Input("btn_last_to_next", "n_clicks"),
    State("dropdown_sample", "value"),
    State("store_measurements", "data"),
    State("store_split_count", "data"),
    State("table_measurements", "data"),
    prevent_initial_call=True,
)
def move_last_to_next(
    n_clicks,
    which_sample,
    store_measurements,
    split_count,
    data_table_measurements,
):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > move_last_to_next()")
    if (
        store_measurements is not None
        and which_sample < store_measurements[-1]["order_analysis"]
    ):
        usd = move_measurement(1, which_sample, store_measurements)
        if len(data_table_measurements) == 1:
            split_count += 1
        else:
            split_count = no_update
        return usd.measurements.to_dict("records"), split_count
    else:
        print(" - no_update")
        return no_update, no_update


@callback(
    Output("slider_split", "min"),
    Output("slider_split", "max"),
    Output("slider_split", "value"),
    Input("table_measurements", "data"),
    prevent_initial_call=True,
)
def update_slider_range(data_table_measurements):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > update_slider_range()")
    if data_table_measurements is not None:
        df = pd.DataFrame.from_records(data_table_measurements)
        return (
            df.order.iloc[0],
            df.order.iloc[-1],
            df.order.iloc[0],
        )
    else:
        print(" - no update")
        return no_update, no_update, no_update


@callback(
    Output("store_measurements", "data", allow_duplicate=True),
    Output("dropdown_sample", "value", allow_duplicate=True),
    Output("store_split_count", "data", allow_duplicate=True),
    Input("btn_split", "n_clicks"),
    State("slider_split", "value"),
    State("slider_split", "min"),
    State("slider_split", "max"),
    State("dropdown_sample", "value"),
    State("store_measurements", "data"),
    State("store_split_count", "data"),
    prevent_initial_call=True,
)
def split_sample(
    n_clicks,
    split_at,
    split_min,
    split_max,
    which_sample,
    store_measurements,
    split_count,
):
    print(f"{list(ctx.triggered_prop_ids.keys())[0]} > split_sample()")
    if store_measurements is not None and split_at > split_min and split_at < split_max:
        s = which_sample
        usd = UpdatingSummaryDataset(pd.DataFrame.from_records(store_measurements))
        M = usd.measurements.order_analysis == s
        Mn = M & (usd.measurements.order > split_at)  # the new sample
        # Update by renaming - note that if the following sample already ends with
        # "__SPLIT" then the new split will just add data to that next sample,
        # instead of making a new one - but I think that's not really a problem
        sample_name_new = usd.samples.sample_name.loc[s] + "__SPLIT"
        usd.set_measurements(Mn, sample_name=sample_name_new)
        which_sample += 1
        return (
            usd.measurements.to_dict("records"),
            which_sample,
            split_count + 1,
        )
    else:
        print(" - no update")
        return no_update, no_update, no_update


# @callback(
#     Input("keyboard", "keydown"),
# )
# def print_keypress(keydown):
#     if keydown is not None:
#         key = keydown.get("key", "")
#         print(key)


# TODO use the above in get_samples_table_user_changes() to deal with the click-off
# problem better!

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
                    for col_id in [
                        "txt_n_measurements",
                        "txt_is_tris",
                        "txt_extra_mcp",
                    ]
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
            [
                dbc.Col(
                    dcc.Checklist([" Tris?"], id="check_is_tris", value=[]),
                    style={"textAlign": "center"},
                    width=6,
                ),
                dbc.Col(
                    dcc.Checklist([" +20 mCP?"], id="check_extra_mcp", value=[]),
                    style={"textAlign": "center"},
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
panel_measurements = [
    dbc.Row(
        dbc.Col(
            dbc.Button(
                "Move first to previous",
                color="success",
                outline=True,
                id="btn_first_to_prev",
            )
        ),
        style={"textAlign": "center"},
    ),
    dbc.Row(dbc.Col(table_measurements), className="p-3"),
    dbc.Row(
        dbc.Col(
            dbc.Button(
                "Move last to next",
                color="success",
                outline=True,
                id="btn_last_to_next",
            )
        ),
        style={"textAlign": "center"},
    ),
]
tab_measurements = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    dcc.Graph(id="fig_measurements"),
                    width={"size": 6, "offset": 2},
                ),
                dbc.Col(
                    panel_measurements,
                    width=2,
                ),
            ],
            align="center",
        ),
        dbc.Row(
            [
                dbc.Col(
                    dcc.Slider(0, 1, 1, id="slider_split", value=1),
                    width={"size": 3, "offset": 4},
                ),
                dbc.Col(
                    dbc.Button(
                        "Split sample",
                        color="danger",
                        outline=True,
                        id="btn_split",
                    ),
                    width=1,
                ),
            ],
            className="mb-5",
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
tab_phroc = dbc.Container(
    dbc.Row(
        dbc.Col(
            dbc.Card(
                [
                    dbc.CardHeader("About"),
                    dbc.CardBody(
                        [
                            html.H1("pHroc"),
                            html.H5(f"Version {__version__}"),
                            html.P(
                                [
                                    "GitHub: ",
                                    html.A(
                                        "mvdh7/phroc",
                                        href="https://github.com/mvdh7/phroc",
                                        target="_blank",
                                    ),
                                    html.Br(),
                                    "Zenodo: ",
                                    html.A(
                                        "doi:10.5281/zenodo.13961237",
                                        href="10.5281/zenodo.13961237",
                                        target="_blank",
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            width=3,
        ),
        justify="center",
        className="mt-5",
    ),
    fluid=True,
)


instructions_samples = dcc.Markdown("""
#### 1. Import dataset

##### 1a. Directly from the instrument

You should have two `.TXT` files from the spectrophotometer: one containing the
results and one with the comments, for example:

  * `my_dataset.TXT`
  * `my_dataset-COMMENTS.TXT`

You can either drag and drop these files into the light blue box at the top
left, or you can click on the box to open a file browser window.  **Either way,
you must upload both files together in one go.**

##### 1b. From a previous analysis with pHroc

If you previously worked with a file in pHroc and exported it to either a
`.phroc` or `.xlsx` file, you can import that file in the same way as above
(drag and drop or click the box and find the files in the browser).  In this
case, there will be only one file to upload at a time.

##### 1c. From the internal backup

You can click the grey 'Restore last session' button to reload whatever
analysis you were doing the last time you used pHroc.  *This will mostly be 
useful if you accidentally quit pHroc without exporting your work, which can 
happen if you refresh the web page.*

##### Did it work?

If the upload was successful, you'll see

  * the name of the file in the 'Current file' box, which will turn green
  rather than yellow;
  * a summary of the samples measured in the table;
  * and the mean pH, temperature and salinity for each sample in the figure.

---

#### 2. The samples table

You can directly edit the values in parts of the table.  To do so, click on the
cell you want to edit, type in the new value, then press `Enter` on your
keyboard.  *Unfortunately, you cannot edit the value already in there (e.g., to
change just part of it), you have to write out a complete new value.  And if
you move off the cell with something other than `Enter`, your change might
not be saved.*

The columns in the samples table contain the following information:

|||
| -: | :- |
| `Name` | The name of the sample.  If you edit a sample name so that it is identical to the sample either directly above or below it, then the two samples will be merged into one. *To revert this, you need to use the Split button on the Measurements tab.*    |
| `Tris?` | Whether the sample is tris (`Y`) or not (cell empty). |
| `+20 mCP?` | Whether the sample had a second dose of mCP added (`Y`) or not (cell empty). |
| `T / °C` | Temperature during the measurement in °C. |
| `Sal.` | Practical salinity. |
| `pH` | Mean measured pH for all 'good' measurements of this sample. |
| `Range(pH)` | The range in measured pH for all 'good' measurements of this sample.  The cell background turns orange if the value is from 0.0010 to 0.0012 and red if it is greater than 0.0012. |
| `Used / total` | How many measurements are considered 'good' for this sample and used to calculate its mean pH, out of how many measurements in total were made for the sample.  The 'good' measurements are selected in the Measurements tab.  The cell background turns orange if fewer than 3 samples are used and red if zero samples are used. |
| `Comments` | Analyst comments. |

The columns `pH`, `Range(pH)` and `Used / total` cannot be edited.  Their
values will update if temperature or salinity are modified and when relevant
changes are made in the Measurements tab.

---

#### 3. Samples summary figure

On the right is a figure showing the mean values for pH (top), temperature
(middle) and salinity (bottom) for each sample.  Only measurements marked
as good are included in the mean pH.  The figure will automatically update to
reflect the processing that you do.

The sample names are given on the x-axis for the bottom subplot (salinity), but
you can also see the name of any sample (and its y-axis value) by hovering the
mouse over a data point on any of the three subplots.

---

#### 4. Auto-detect windows

The main task in pHroc is to select which measurements should be considered
'good' for each sample.  One approach is to select three (or more) measurements
that fall within a window of at most 0.001.  Clicking the green 'Auto-detect
windows' button will automatically detect sets of measurements in the dataset
that fulfil this criterion, saving you some work.

**You should always manually check the selections made by the auto-detect tool
by looking through the Measurements tab.**  For some samples, there will be
different groups of measurements that could meet the criterion, and you need to 
make sure you agree with the choice made.  For other samples, it may not be
possible to meet the criterion, so you need to decide what to do.

**Running the auto-detect will overwrite any selections you have already made
manually.**  If using it, you should run it once at the start, and then go
through to check and where necessary adjust the results in the Measurements tab
afterwards.

---

#### 5. Export buttons

When you have finished working with the data file, you can export it to a
`.phroc` file (for use in Python) or an `.xlsx` file (an Excel spreadsheet)
with the black buttons at the top centre.  The file should appear in your
Downloads folder with the name being the same as the imported file.
""")

instructions_measurements = dcc.Markdown("""
#### 1. Measurements figure

At the top left is a figure showing the measurements for the selected sample.
The x-axis shows the measurement number within the complete dataset (this might
start from zero) and the y-axis the pH for each individual measurement.  Points
that have been identified as 'good' will be blue circles and those that are
not, red crosses.

---

#### 2. Measurements table and Move buttons

At the top right, the data from the measurements figure are shown in a table.
The first column contains checkboxes.  This is how you control which of the
measurements are 'good': checkboxes that are ticked are 'good' measurements.

Above and below the table are buttons that allow you to reassign individual
measurements from this sample to a different sample.  These might be needed if
the wrong sample name was entered in the instrument when doing the
measurements.

  * 'Move first to previous' reassigns the first measurement for this sample to
  the previous sample.  *Cannot be used for the first sample in the dataset.*
  * 'Move last to next' reassigns the last measurement for this sample to the
  next sample.  *Cannot be used for the last sample in the dataset.*

If there is only one measurement remaining for this sample and you move it,
then the measurement will be reassigned and this sample will cease to exist.
To reverse this process, use the Split button.

---

#### 3. Split sample button and slider.

If a set of measurements represents two separate samples, they can be split
into two samples by using the red 'Split sample' button.  The slider to the
left of the button should be moved to indicate at which measurement the sample
should be split.  When the button is pressed, a new sample will be created
containing the measurements after the slider value, which will be given the
name of the original sample with `__SPLIT` appended.

The name of the new sample can be modified in the table on the Samples tab.
If the name is returned to match the original name then the two sets of
measurements will be merged together again.

---

#### 4. Sample information box

The blue box at the bottom contains information about the currently selected
sample.  This is the same information as is contained in the table on the
Samples tab.

At the top there is a dropdown showing the name of the sample currently being
viewed.  You can click on the dropdown to select a different sample.  If you
click on the dropdown and start typing a sample name, it works as a search
function to more quickly find what you are looking for.  *You cannot modify
the name of a sample from the Measurements tab - do that in the table on the 
Samples tab.*

The temperature, salinity and comments can be adjusted here - enter the new
value and then press `Enter`.  Whether the sample is tris or has extra mCP can
also be adjusted by (de)selecting the corresponding checkbox.

---

#### 5. Navigation arrows

To the left and right of the sample information box are arrows which can be
clicked to jump to the first, previous, next or last sample in the dataset.
""")

overview_left = dcc.Markdown("""
#### What does pHroc do?

  * Convert raw data files from the spectrophotometer into Excel spreadsheets
  or `.phroc` files for Python analysis.
  * Identify which measurements are 'good' and should be used to calculate pH
  for each sample.
  * Mark which samples are tris and which had extra mCP additions.
  * Fix mistakes in sample names.
  * Update the measurement temperature and salinity for each sample and
  recalculate pH with the new values.
""")
overview_right = dcc.Markdown("""
#### Where do I start?

Your work takes place in the Samples and Measurements tabs.

Usually, you will begin in the Samples tab to import and see an initial
overview of the dataset, then move to the Measurements tab to analyse each
sample in detail, and finish off back in the Samples tab to save (export) your
work.
""")
overview_centre = dcc.Markdown("""
#### Useful to know

When you open a file in pHroc and make changes, this does **not** affect the
original file that you opened.  You can always go back to the start by
re-opening the same file again, and you need to export a `.phroc` or `.xlsx`
file from the Samples tab to save the work you have done.  Even if you open a
`.phroc` or `.xlsx` file and export it again, it will save into a separate
file rather than updating the one you opened.
""")

tab_instructions = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader("Overview"),
                        dbc.CardBody(
                            dbc.Row(
                                [
                                    dbc.Col(
                                        overview_left,
                                        className="mr-5 ml-5",
                                    ),
                                    dbc.Col(
                                        overview_centre,
                                        className="mr-5 ml-5",
                                        style={
                                            "border-left": "1px solid #C6C7C8",
                                            "border-right": "1px solid #C6C7C8",
                                        },
                                    ),
                                    dbc.Col(
                                        overview_right,
                                        className="mr-5 ml-5",
                                    ),
                                ],
                                align="center",
                            ),
                        ),
                    ]
                )
            ),
            className="mt-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Samples tab"),
                            dbc.CardBody(instructions_samples),
                        ],
                    ),
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Measurements tab"),
                            dbc.CardBody(instructions_measurements),
                        ],
                    ),
                ),
            ],
            className="mt-3 mb-3",
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
                    labelClassName="text-primary",
                ),
                dbc.Tab(
                    tab_measurements,
                    label="Measurements",
                    tab_id="tab_measurements",
                    labelClassName="text-primary",
                ),
                dbc.Tab(
                    tab_instructions,
                    label="Instructions",
                    tab_id="tab_instructions",
                    labelClassName="text-info",
                ),
                dbc.Tab(
                    tab_phroc,
                    label=f"pHroc v{__version__}",
                    tab_id="tab_phroc",
                    labelClassName="text-secondary",
                ),
            ],
            id="tabs",
        ),
        dcc.Store(id="store_measurements"),
        dcc.Store(id="store_settings"),
        dcc.Store(id="store_split_count", data=0),
        # Keyboard(id="keyboard"),
    ]
)
app.title = f"pHroc v{__version__}"
if __name__ == "__main__":
    app.run(debug=True)
