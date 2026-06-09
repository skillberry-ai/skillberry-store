# skillberry_store_sdk.PluginsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_plugin_info_plugins_plugin_name_get**](PluginsApi.md#get_plugin_info_plugins_plugin_name_get) | **GET** /plugins/{plugin_name} | Get plugin information
[**list_plugins_plugins_get**](PluginsApi.md#list_plugins_plugins_get) | **GET** /plugins/ | List all plugins


# **get_plugin_info_plugins_plugin_name_get**
> Dict[str, object] get_plugin_info_plugins_plugin_name_get(plugin_name)

Get plugin information

Get detailed information about a specific plugin.

Args:
    plugin_name: Name/slug of the plugin

Returns:
    Plugin info dictionary with metadata and status

Raises:
    HTTPException: 404 if plugin not found

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = skillberry_store_sdk.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with skillberry_store_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    plugin_name = 'plugin_name_example' # str | 

    try:
        # Get plugin information
        api_response = api_instance.get_plugin_info_plugins_plugin_name_get(plugin_name)
        print("The response of PluginsApi->get_plugin_info_plugins_plugin_name_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->get_plugin_info_plugins_plugin_name_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **plugin_name** | **str**|  | 

### Return type

**Dict[str, object]**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_plugins_plugins_get**
> List[Optional[Dict[str, object]]] list_plugins_plugins_get()

List all plugins

List all discovered plugins with their metadata and status.

Returns:
    List of plugin info dictionaries containing:
    - name: Display name
    - description: What the plugin does
    - version: Plugin version
    - plugin_type: Type of plugin (creator, evaluator, optimizer)
    - author: Plugin author (optional)
    - homepage: Plugin homepage URL (optional)
    - enabled: Whether plugin is enabled
    - has_router: Whether plugin provides API routes
    - has_cli: Whether plugin provides CLI commands
    - has_ui: Whether plugin provides UI configuration

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = skillberry_store_sdk.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with skillberry_store_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = skillberry_store_sdk.PluginsApi(api_client)

    try:
        # List all plugins
        api_response = api_instance.list_plugins_plugins_get()
        print("The response of PluginsApi->list_plugins_plugins_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->list_plugins_plugins_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**List[Optional[Dict[str, object]]]**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

