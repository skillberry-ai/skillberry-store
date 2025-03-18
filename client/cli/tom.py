# TOM (TOol Manager) is a CLI client that allows users to directly interact with the Blueberry tool service, as well a integrate tool operations into scripts
from client.modules_json_tools_client import ModulesJsonToolsClient
from modules.lifecycle import LifecycleState
from client.utils import base_client_utils
import click
from configobj import ConfigObj
import logging
import os
import sys
import inspect



def load_file(filename):
    """
    Loads a file that is co-located with the current Python module.

    Args:
        filename (str): The name of the file to load.

    Returns:
        str: The content of the file as a string, or None if an error occurs.
    """
    try:
        # Get the directory of the 
        # module_path = inspect.getfile(inspect.currentframe().f_back)
        module_dir = os.path.dirname(os.path.abspath(__file__))

        # Construct the full path to the config file
        file_path = os.path.join(module_dir, filename)

        # Read the config file content
        with open(file_path, 'r') as f:
            file_content = f.read()

        return file_content

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return None



class CustomHelp(click.Group):
    """Custom Click Group that injects an ASCII logo into the help text."""

    def get_help(self, ctx):
        """Override the default help output to include the TOM logo."""
        tom_logo=load_file('tom.ans')
        click.echo(tom_logo, err=True)
        return super().get_help(ctx)



@click.group(cls=CustomHelp)
@click.option('-f', '--config_file', type=str, help='Override the location of the TOM configuration file', default='~/.blueberry/tomconfig')
@click.option('-p', '--profile', type=str, help='Use a specific configuration profile', default='default')
@click.pass_context
def tom(ctx, config_file, profile):
    config_file = os.path.expanduser(config_file)
    try:
        ctx.obj['config'] = ConfigObj(config_file, file_error=True)
    except IOError:
        print(f"Error loading config from {config_file}", file=sys.stderr)
        ctx.obj['config'] = ConfigObj()
        ctx.obj['load_error'] = True
    ctx.obj['config_file'] = config_file
    ctx.obj['profile'] = profile



@tom.command()
@click.option('-n', '--name', type=str, help='Client name (for logging)', default='tom')
@click.option('-v', '--log_level', type=click.Choice(['debug', 'info', 'warning', 'error', 'critical']), help='Log level: debug, info, etc', default='info')
@click.option('-u', '--url', type=str, help='Tool service URL http[s]://<host>[:<port>]', default='http://0.0.0.0:8000')
@click.option('-j', '--json_base', type=str, help='JSON base path')
@click.pass_context
def config(ctx, name, log_level, url, json_base):
    """Configure TOM: service connection, log level etc. Implies updating/creating config file and profile."""
    configObj = ctx.obj['config']
    profile = ctx.obj['profile']
    configObj[profile] = {'name': name, 'log_level': log_level, 'url': url}
    if json_base:
        configObj[profile]['json_base'] = json_base
    print(f"Writing configuration to profile: {profile} in file: {ctx.obj['config_file']}")
    write_config(configObj, ctx.obj['config_file'])


def write_config(configObj: ConfigObj, filepath: str):
    """
    Write the specified ConfigObj to the specified file path. Create any missing folders if needed.

    Args:
        configObj (ConfigObj): the configuration object to write
        filepath (str): the path to the configuration file
    """
    directory = os.path.dirname(filepath)

    # Create the directory if it doesn't exist.
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)  
    configObj.filename=filepath
    configObj.write()


def client_from_context(ctx) -> ModulesJsonToolsClient:
    """
    Initialize a client from config data in the context. Valid configuration must have loaded without
    error from a config file, and must contain the specified profile. Otherwise, operation will abort.

    Args:
        ctx: the context with config data
    """
    if 'load_error' in ctx.obj or not ctx.obj['profile'] in ctx.obj['config']:
        print(f'Configuration could not be loaded from: {ctx.obj['config_file']} or is missing profile: {ctx.obj['profile']}. Please run `tom profile` to correct')
        sys.exit(-1)

    # Config ok, create client
    client_config = ctx.obj['config'][ctx.obj['profile']]
    client = ModulesJsonToolsClient(name=client_config['name'], log_level=logging.getLevelName(client_config['log_level'].upper()), url=client_config['url'])
    if 'json_base' in client_config:
        client.set_json_base(client_config['json_base'])
    return client


class KeyValueParamType(click.ParamType):
    """
    This class allows click to accept CLI arguments of the format "key=value"
    """
    name = "key=value"

    def convert(self, value, param, ctx):
        try:
            key, val = value.split("=", 1)
            return key, val
        except ValueError:
            self.fail(f"{value} is not in key=value format", param, ctx)

KEYVALUE = KeyValueParamType()



@tom.command()
@click.option('-fl', '--filter', type=str, help='jq-style filter on manifests', default='.')
@click.option('-lst', '--lifecycle_state', type=click.Choice(['any', 'new', 'checked', 'approved'], case_sensitive=False), help='Lifecycle state', default='any')
@click.option('--full', is_flag=True, help='Display full manifests (default: display only tool UIDs)')
@click.pass_context
def list(ctx, filter, lifecycle_state, full):
    """List stored tools (UIDs or full manifests) according to options"""
    client = client_from_context(ctx)
    results = client.list_tools(filter, LifecycleState[lifecycle_state.upper()])
    for result in results:
        if full:
            print(f"{base_client_utils.json_pretty_print(result)}\n")
        else:
            print(result['uid'])
    


@tom.command()
@click.argument('uid', required=True)
@click.pass_context
def getman(ctx, uid: str):
    """Retrieve the manifest of a stored tool based on the tool UID"""
    client = client_from_context(ctx)
    print(f"{base_client_utils.json_pretty_print(client.get_tool_manifest(uid))}\n")



@tom.command()
@click.argument('uid', required=True)
@click.pass_context
def getcode(ctx, uid: str):
    """Retrieve the code for a stored tool given the tool UID"""
    client = client_from_context(ctx)
    print(f"{client.get_tool_code(uid)}\n")



@tom.command()
@click.argument('description', required=True)
@click.option('-mr', '--max_results', type=int, help='Maximum number of results', default=5)
@click.option('-st', '--similarity_threshold', type=float, help='Max similarity distance threshold', default=1.0)
@click.option('-lst', '--lifecycle_state', type=click.Choice(['any', 'new', 'checked', 'approved'], case_sensitive=False), help='Lifecycle state', default='approved')
@click.option('--full', is_flag=True, help='Display full manifests (default: display only tool UIDs)')
@click.pass_context
def search(ctx, description: str, max_results: int, similarity_threshold: float, lifecycle_state: str, full:bool):
    """Search for tools matching a given description with optional filtering (see command help)"""
    client = client_from_context(ctx)
    results = client.search_tools(description, max_results, similarity_threshold, LifecycleState[lifecycle_state.upper()])
    for result in results:
        if full:
            print(f"{base_client_utils.json_pretty_print(result)}\n")
        else:
            print(result['filename'])



@tom.command()
@click.argument('module_path', nargs=1)
@click.argument('func_names', nargs=-1)
@click.option('--verify', is_flag=True, help='Verify that the specified code contains each specified function name (default: no verification)')
@click.pass_context
def add(ctx, module_path: str, func_names: tuple[str, ...], verify):
    """Add all functions from the given module as tools. If function names are provided, add only specified functions"""
    client = client_from_context(ctx)
    mod_func_list = []
    func_list = base_client_utils.list_functions_in_module(module_path)
    # If don't we have specific function names, extract all functions from the module
    if not func_names or len(func_names) == 0:
        mod_func_list = [(module_path, func_name) for _, func_name, _ in func_list]
    else: # Otherwise, we may need to verify if required
        for func_name in func_names:
            if (not verify) or (func_name in func_list):
                mod_func_list.append((module_path, func_name))
            else:
                print(f"Verification failed: The function {func_name} is not in {module_path} - SKIPPED\n", file=sys.stderr)
    uids = client.add_tools_from_python_functions(mod_func_list)
    for i in range(len(uids)):
        print(f"{mod_func_list[i][0]}:{mod_func_list[i][1]} ==> {uids[i]}\n")



@tom.command()
@click.argument('uid', nargs=1)
@click.argument('args', nargs=-1, type=KEYVALUE)
@click.pass_context
def exec(ctx, uid: str, args: tuple[(str, str), ...]):
    """Execute a tool given by its UID, using the arguments provided"""
    client = client_from_context(ctx)
    args_dict = {key: val for key, val in args}
    result = client.execute_tool(uid=uid, parameters=args_dict)
    print(f"{base_client_utils.json_pretty_print(result)}\n")



@tom.command()
@click.argument('uid', required=True)
@click.pass_context
def delete(ctx, uid: str):
    """Delete a tool with the given UID"""
    client = client_from_context(ctx)
    result = client.delete_tool(uid=uid)
    print(f"{base_client_utils.json_pretty_print(result)}\n")



def main():
    """
    Dumb entry point function (no arguments) for package purposes
    """
    tom(auto_envvar_prefix='TOM', obj={})



if __name__ == '__main__':
    main()