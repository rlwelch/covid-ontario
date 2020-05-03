import os
import requests
import dash
import dash_core_components as dcc
import dash_html_components as html
from datetime import date

# --- Model: Data ---
# Data sources
API_BASE = "https://data.ontario.ca/api/3/action/"
PACKAGE_IDS = {
    "status": "f4f86e54-872d-43f8-8a86-3892fd3cb5e6",
    "con_pos": "f4112442-bdc8-45d2-be3c-12efae72fb27",
}
PACKAGE_LABELS = {
    "status": "Status of COVID-19 cases in Ontario",
    "con_pos": "Confirmed positive cases of COVID19 in Ontario",
}


def get_resource_id(package_name):
    """
    Return the resource ID and last modified date of the CSV resource belonging to a package name.
    """
    url = f"{API_BASE}package_show?id={PACKAGE_IDS[package_name]}"
    resources = requests.get(url).json()["result"]["resources"]
    resource = [
        r
        for r in resources
        if (r["format"] == "CSV") and (r["name"] == PACKAGE_LABELS[package_name])
    ][0]
    last_modified = resource.get("last_modified")
    id = resource.get("id")
    return id, last_modified


def get_resource_data(resource_id):
    """
    Return the contents of the resource in a Pandas DataFrame.
    """
    url = f"{API_BASE}datastore_search?resource_id={resource_id}&limit=32000"
    pass


# --- View: Plotly ---


# --- Controller: Dash ---
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
            html.P(
                [
                    """This is an independent project to show data from the Ontario Government’s Data Catalog. 
                    For a more detailed analysis, see the #HowsMyFlattening project.""",
                    html.Br(),
                    """Please follow the guidance of Ontario’s public health experts and do your part to stop the spread.""",
                    html.Br(),
                    html.Br(),
                    """When was the data last updated?""",
                ]
            ),
        ),
        # Dropdown menu example
        dcc.Dropdown(
            id="dropdown",
            options=[
                {"label": package_label, "value": package_name}
                for package_name, package_label in PACKAGE_LABELS.items()
            ],
            value="status",
            clearable=False,
        ),
        html.Div(id="display-value"),
    ]
)


@app.callback(
    dash.dependencies.Output("display-value", "children"),
    [dash.dependencies.Input("dropdown", "value")],
)
def display_value(value):
    return 'Most recent update: "{}"'.format(get_resource_id(value)[1])


if __name__ == "__main__":
    app.run_server(debug=True)
