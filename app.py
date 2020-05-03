import os
import requests
import dash
import dash_core_components as dcc
import dash_html_components as html

# Data sources

# Dash app configuration
STYLESHEET = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]


# Dash 
app = dash.Dash(__name__, external_stylesheets=STYLESHEET)
server = app.server

app.layout = html.Div(
    [
        html.H2("covid-ontario"),
        html.H6("Follow the rise and fall of COVID-19 in Ontario."),
        html.Div(
            html.P([
                    """This is an independent project to show data from the Ontario Government’s Data Catalog. 
                    For a more detailed analysis, see the #HowsMyFlattening project.""",
                    html.Br(),
                    """Please follow the guidance of Ontario’s public health experts and do your part to stop the spread."""
            ]),                 
        ),
        # Dropdown menu example
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
