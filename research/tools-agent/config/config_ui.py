import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State, ALL
import flask

from config.config import DynamicConfig
from config.config_structure import CONFIG_STRUCTURE

# Initialize Flask and Dash
server = flask.Flask(__name__)
config_ui_app = dash.Dash(__name__, server=server)

# Load configuration
config = DynamicConfig(CONFIG_STRUCTURE)


# Create UI elements dynamically
def generate_ui(structure, _config, prefix=""):
    elements = []
    for key, value in structure.items():
        full_key = f"{prefix}{key}" if prefix else key
        if value["type"] == "bool":
            elements.append(
                html.Div([
                    html.Label(value["label"], style={"fontWeight": "bold", "marginBottom": "5px"}),
                    dcc.Checklist(
                        options=[{"label": "", "value": "on"}],
                        value=["on"] if _config[key] else [],
                        id={"type": "config-input", "key": full_key},
                        style={"marginBottom": "15px"}
                    )
                ], style={"marginBottom": "20px"})
            )
        elif value["type"] == "int" or value["type"] == "float":
            elements.append(
                html.Div([
                    html.Label(value["label"], style={"fontWeight": "bold", "marginBottom": "5px"}),
                    dcc.Input(value=_config[key], type="number", id={"type": "config-input", "key": full_key},
                              style={"width": "200px", "marginBottom": "15px"})
                ], style={"marginBottom": "20px"})
            )
        elif value["type"] == "str":
            elements.append(
                html.Div([
                    html.Label(value["label"], style={"fontWeight": "bold", "marginBottom": "5px"}),
                    dcc.Input(value=_config[key], type="text", id={"type": "config-input", "key": full_key},
                              style={"width": "200px", "marginBottom": "15px"})
                ], style={"marginBottom": "20px"})
            )
        elif value["type"] == "group":
            elements.append(
                html.Div([
                    html.H3(value["label"], style={"marginTop": "30px", "fontWeight": "bold"}),
                    html.Div(generate_ui(value["children"], _config[key], prefix=full_key + "__"),
                             style={"marginLeft": "30px"})
                ], style={"marginBottom": "40px"})
            )

    return elements


# Layout
config_ui_app.layout = html.Div([
    html.H1("Configuration Editor", style={"textAlign": "center", "marginBottom": "30px"}),
    html.Div(generate_ui(CONFIG_STRUCTURE, config.config)),
    html.Button("Save", id="save-btn",
                style={"padding": "10px 20px", "fontSize": "16px", "cursor": "pointer", "backgroundColor": "#28a745",
                       "color": "white", "border": "none"}),
    html.Button("Restore Defaults", id="restore-btn",
                style={"padding": "10px 20px", "fontSize": "16px", "cursor": "pointer", "backgroundColor": "#d9534f",
                       "color": "white", "border": "none"}),
    html.Div(id="status-msg", style={"textAlign": "center", "marginTop": "20px", "fontSize": "18px"})
], style={"padding": "20px"})


# Helper function to collect only non-group keys
def get_input_keys(structure, prefix=""):
    keys = []
    for key, value in structure.items():
        full_key = f"{prefix}{key}" if prefix else key
        if value["type"] == "group":
            keys.extend(get_input_keys(value["children"], prefix=full_key + "__"))
        else:
            keys.append(full_key)
    return keys


# Get only the actual input keys
input_keys = get_input_keys(CONFIG_STRUCTURE)


# Single Callback to Handle Save and Restore
@config_ui_app.callback(
    [
        Output({"type": "config-input", "key": ALL}, "value"),
        Output("status-msg", "children")
    ],
    [
        Input("save-btn", "n_clicks"),
        Input("restore-btn", "n_clicks")
    ],
    [
        State({"type": "config-input", "key": ALL}, "id"),
        State({"type": "config-input", "key": ALL}, "value")
    ],
    prevent_initial_call=True
)
def update_config(save_clicks, restore_clicks, input_ids, input_values):
    ctx = dash.callback_context
    if not ctx.triggered:
        return [dash.no_update]

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if triggered_id == "restore-btn":
        # Restore default values
        config.restore_defaults()
        values = []
        for i, input_id in enumerate(input_ids):
            key = input_id["key"]
            if config.get_type(key) is bool:
                values.append(["on"] if config.get(key) else [])
            else:
                values.append(config.get(key))
        return values, "Defaults restored!"

    elif triggered_id == "save-btn":
        for i, input_id in enumerate(input_ids):
            key = input_id["key"]
            value = input_values[i]
            if config.get_type(key) is bool:
                config.set(key, "on" in value)  # Convert checklist to bool
            else:
                config.set(key, value)
        config.save_config()
        return [dash.no_update] * len(input_ids), "Configuration saved!"

    return [dash.no_update] * len(input_ids), dash.no_update
