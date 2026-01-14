from dash import Dash, Input, Output, callback, dcc, html


data = [0]

app = Dash()
app.layout = html.Div(
    [
        html.Div("0", id="text"),
        html.Button("Increase", id="increase", n_clicks=0),
    ]
)


@callback(
    Output("text", "children"),
    Input("increase", "n_clicks"),
)
def update_text(n):
    # data += 1
    data.append(1)
    print(data)
    return f"n_clicks = {n}, data = {data}"


if __name__ == "__main__":
    app.run(debug=True)
