# %%
import plotly.graph_objects as go
from dash import Dash, Input, Output, Patch, callback, ctx, dcc, html

import phroc


df = phroc.UpdatingSummaryDataset(
    phroc.read_agilent_pH(
        "tests/data/2024-04-27-CTD1.TXT",
        dye_intercept=0,
        dye_slope=0,
        find_windows_auto=False,
        pH_equation="NIOZ",
    )
)

test = []


# @callback(
#     Output("plot_sample", "figure"),
#     Input("sample_name", "value"),
#     prevent_initial_call="initial_duplicate",
# )
def plot_sample(sample_name):
    fmeas = df.measurements[df.measurements.sample_name == sample_name]
    # if ctx.triggered_id == "sample_name":
    marker_color = ["blue" if g else "red" for g in fmeas.pH_good]
    points = go.Scatter(
        x=fmeas.index,
        y=fmeas.pH,
        mode="markers",
        marker_color=marker_color,
        marker_size=30,
    )
    # else:
    #     points = go.Scatter(
    #         x=fmeas.index,
    #         y=fmeas.pH,
    #         mode="markers",
    #         marker_size=30,
    #     )
    fig = go.Figure(points)
    print(fig)
    return fig


df.set_measurement(3, pH_good=False)
# df.set_measurement(4, pH_good=False)


@callback(
    Output("tester", "children"),
    Output("plot_sample", "figure"),
    Output("plot_sample", "clickData"),
    Input("plot_sample", "clickData"),
    # prevent_initial_call="initial_duplicate",
)
def tester(clickData):
    if "points" in clickData:
        order = int(clickData["points"][0]["x"])
        df.set_measurement(order, pH_good=~df.measurements.loc[order].pH_good)
    fmeas = df.measurements[
        df.measurements.sample_name == df.samples.sample_name.iloc[0]
    ]
    patched = Patch()
    patched["data"][0]["marker"]["color"] = [
        "blue" if g else "red" for g in fmeas.pH_good
    ]
    return (
        df.measurements.loc[1:5].pH_good.astype(str),
        patched,
        {},
    )


# %%
app = Dash()
app.layout = [
    html.H1(children="pHroc", style={"textAlign": "center"}),
    dcc.Dropdown(
        df.samples.sample_name,
        df.samples.sample_name.iloc[0],
        id="sample_name",
    ),
    dcc.Graph(
        id="plot_sample",
        clickData={},
        figure=plot_sample(df.samples.sample_name.iloc[0]),
    ),
    html.Div(id="tester"),
]
if __name__ == "__main__":
    app.run(debug=True)
