import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import flask

from config.config import DynamicConfig
from config.config_structure import CONFIG_STRUCTURE

# Initialize Flask and Dash
server = flask.Flask(__name__)
config_ui_app = dash.Dash(__name__, server=server)

# Load configuration
config = DynamicConfig(CONFIG_STRUCTURE)

# Create UI elements dynamically
def generate_ui(structure, config, prefix=""):
    elements = []
    for key, value in structure.items():
        full_key = f"{prefix}{key}" if prefix else key
        if value["type"] == "bool":
            elements.append(
                html.Div([
                    html.Label(value["label"], style={"fontWeight": "bold", "marginBottom": "5px"}),
                    dcc.Checklist(
                        options=[{"label": "", "value": "on"}],
                        value=["on"] if config[key] else [],
                        id=full_key,
                        style={"marginBottom": "15px"}
                    )
                ], style={"marginBottom": "20px"})
            )
        elif value["type"] == "int":
            elements.append(
                html.Div([
                    html.Label(value["label"], style={"fontWeight": "bold", "marginBottom": "5px"}),
                    dcc.Input(value=config[key], type="number", id=full_key, style={"width": "200px", "marginBottom": "15px"})
                ], style={"marginBottom": "20px"})
            )
        elif value["type"] == "str":
            elements.append(
                html.Div([
                    html.Label(value["label"], style={"fontWeight": "bold", "marginBottom": "5px"}),
                    dcc.Input(value=config[key], type="text", id=full_key, style={"width": "200px", "marginBottom": "15px"})
                ], style={"marginBottom": "20px"})
            )
        elif value["type"] == "group":
            elements.append(
                html.Div([
                    html.H3(value["label"], style={"marginTop": "30px", "fontWeight": "bold"}),
                    html.Div(generate_ui(value["children"], config[key], prefix=full_key + "."), style={"marginLeft": "30px"})
                ], style={"marginBottom": "40px"})
            )

    return elements

# Layout
config_ui_app.layout = html.Div([
    html.H1("Configuration Editor", style={"textAlign": "center", "marginBottom": "30px"}),
    html.Div(generate_ui(CONFIG_STRUCTURE, config.config)),
    html.Button("Save", id="save-btn", style={"padding": "10px 20px", "fontSize": "16px", "cursor": "pointer", "marginTop": "30px"}),
    html.Div(id="status-msg", style={"textAlign": "center", "marginTop": "20px", "fontSize": "18px"})
], style={"padding": "20px"})

# Callbacks to update config
@config_ui_app.callback(
    Output("status-msg", "children"),
    Input("save-btn", "n_clicks"),
    *[Input(key, "value") for key in config.config.keys()]
)
def save_config(n_clicks, *values):
    if n_clicks:
        keys = list(config.config.keys())
        for i, val in enumerate(values):
            if keys[i] in config.config:
                if isinstance(config.config[keys[i]], bool):
                    config.update_config(keys[i], "on" in val)
                else:
                    config.update_config(keys[i], val)
        return "Configuration saved!"
    return ""