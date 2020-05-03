import os

import dash
import dash_core_components as dcc
import dash_html_components as html

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

server = app.server

app.layout = html.Div(
    [
        html.H2("Coming soon"),
        html.H6("This is a test dashboard."),
        html.Div("Select a city:"),
        dcc.Dropdown(
            id="dropdown",
            options=[{"label": i, "value": i} for i in ["Toronto", "Ottawa", "Hamilton"]],
            value="Toronto",
        ),
        html.Div(id="display-value"),
    ]
)


@app.callback(
    dash.dependencies.Output("display-value", "children"),
    [dash.dependencies.Input("dropdown", "value")],
)
def display_value(value):
    return 'Selected city: "{}"'.format(value)


if __name__ == "__main__":
    app.run_server(debug=True)
