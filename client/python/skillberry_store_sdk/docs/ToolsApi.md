# skillberry_store_sdk.ToolsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**add_tool_from_python_tools_add_post**](ToolsApi.md#add_tool_from_python_tools_add_post) | **POST** /tools/add | Add Tool From Python
[**create_tool_tools_post**](ToolsApi.md#create_tool_tools_post) | **POST** /tools/ | Create Tool
[**delete_tool_tools_name_delete**](ToolsApi.md#delete_tool_tools_name_delete) | **DELETE** /tools/{name} | Delete Tool
[**execute_tool_tools_name_execute_post**](ToolsApi.md#execute_tool_tools_name_execute_post) | **POST** /tools/{name}/execute | Execute Tool
[**get_tool_module_tools_name_module_get**](ToolsApi.md#get_tool_module_tools_name_module_get) | **GET** /tools/{name}/module | Get Tool Module
[**get_tool_tools_name_get**](ToolsApi.md#get_tool_tools_name_get) | **GET** /tools/{name} | Get Tool
[**list_tools_tools_get**](ToolsApi.md#list_tools_tools_get) | **GET** /tools/ | List Tools
[**search_tools_search_tools_get**](ToolsApi.md#search_tools_search_tools_get) | **GET** /search/tools | Search Tools
[**update_tool_tools_name_put**](ToolsApi.md#update_tool_tools_name_put) | **PUT** /tools/{name} | Update Tool


# **add_tool_from_python_tools_add_post**
> Dict[str, object] add_tool_from_python_tools_add_post(tool, tool_name=tool_name, update=update)

Add Tool From Python

Add a tool by automatically extracting parameters from Python code docstring.

This endpoint uploads a Python file and automatically generates a tool manifest
by parsing the function's docstring. The docstring must follow standard Python
documentation conventions (Google, NumPy, or Sphinx style).

Args:
    tool: The Python file to upload containing the function.
    tool_name: Optional name of the specific function to extract. If not provided,
              the first function in the file will be used.
    update: Whether to update if a tool with the same name already exists.

Returns:
    dict: Success message with the tool name, uuid, and module_name.

Raises:
    HTTPException: If file is not Python (400), tool already exists (409),
                  or any other error occurs (500).

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
    api_instance = skillberry_store_sdk.ToolsApi(api_client)
    tool = None # bytearray | 
    tool_name = 'tool_name_example' # str |  (optional)
    update = False # bool |  (optional) (default to False)

    try:
        # Add Tool From Python
        api_response = api_instance.add_tool_from_python_tools_add_post(tool, tool_name=tool_name, update=update)
        print("The response of ToolsApi->add_tool_from_python_tools_add_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->add_tool_from_python_tools_add_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **tool** | **bytearray**|  | 
 **tool_name** | **str**|  | [optional] 
 **update** | **bool**|  | [optional] [default to False]

### Return type

**Dict[str, object]**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **create_tool_tools_post**
> Dict[str, object] create_tool_tools_post(module, name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, created_at=created_at, modified_at=modified_at, module_name=module_name, programming_language=programming_language, packaging_format=packaging_format, params=params, returns=returns, dependencies=dependencies)

Create Tool

Create a new tool with required file upload.

The form fields are dynamically generated from ToolSchema.
Any changes to ToolSchema will automatically reflect in this API.

Args:
    tool: Tool schema with all fields (auto-generated from ToolSchema).
    module: Required file upload for the tool module (e.g., Python file).

Returns:
    dict: Success message with the tool name and uuid.

Raises:
    HTTPException: If tool already exists (409) or creation fails (500).

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
    api_instance = skillberry_store_sdk.ToolsApi(api_client)
    module = None # bytearray | 
    name = 'name_example' # str | Name (optional)
    uuid = 'uuid_example' # str | A UUID. If not provided, a UUID will be automatically generated. (optional)
    version = 'version_example' # str | Version (optional)
    description = 'description_example' # str | Short description (optional)
    state = skillberry_store_sdk.ManifestState() # ManifestState | Lifecycle state (optional)
    tags = ['tags_example'] # List[str] | List of tags for categorizing (optional)
    extra = None # Dict[str, object] | Optional dictionary for additional flexible information (optional)
    created_at = 'created_at_example' # str | ISO 8601 timestamp when created (optional)
    modified_at = 'modified_at_example' # str | ISO 8601 timestamp when last modified (optional)
    module_name = 'module_name_example' # str | Name of the module containing the tool (optional)
    programming_language = 'python' # str | Programming language of the tool (optional) (default to 'python')
    packaging_format = 'code' # str | Packaging format of the tool (optional) (default to 'code')
    params = skillberry_store_sdk.ToolParamsSchema() # ToolParamsSchema | Parameters schema for the tool (optional)
    returns = skillberry_store_sdk.ToolReturnsSchema() # ToolReturnsSchema | Return value schema for the tool (optional)
    dependencies = ['dependencies_example'] # List[str] | List of tool names that this tool depends on (optional)

    try:
        # Create Tool
        api_response = api_instance.create_tool_tools_post(module, name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, created_at=created_at, modified_at=modified_at, module_name=module_name, programming_language=programming_language, packaging_format=packaging_format, params=params, returns=returns, dependencies=dependencies)
        print("The response of ToolsApi->create_tool_tools_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->create_tool_tools_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **module** | **bytearray**|  | 
 **name** | **str**| Name | [optional] 
 **uuid** | **str**| A UUID. If not provided, a UUID will be automatically generated. | [optional] 
 **version** | **str**| Version | [optional] 
 **description** | **str**| Short description | [optional] 
 **state** | [**ManifestState**](.md)| Lifecycle state | [optional] 
 **tags** | [**List[str]**](str.md)| List of tags for categorizing | [optional] 
 **extra** | [**Dict[str, object]**](object.md)| Optional dictionary for additional flexible information | [optional] 
 **created_at** | **str**| ISO 8601 timestamp when created | [optional] 
 **modified_at** | **str**| ISO 8601 timestamp when last modified | [optional] 
 **module_name** | **str**| Name of the module containing the tool | [optional] 
 **programming_language** | **str**| Programming language of the tool | [optional] [default to &#39;python&#39;]
 **packaging_format** | **str**| Packaging format of the tool | [optional] [default to &#39;code&#39;]
 **params** | [**ToolParamsSchema**](.md)| Parameters schema for the tool | [optional] 
 **returns** | [**ToolReturnsSchema**](.md)| Return value schema for the tool | [optional] 
 **dependencies** | [**List[str]**](str.md)| List of tool names that this tool depends on | [optional] 

### Return type

**Dict[str, object]**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_tool_tools_name_delete**
> Dict[str, object] delete_tool_tools_name_delete(name)

Delete Tool

Delete a tool by name.

Args:
    name: The name of the tool to delete.
          Also deletes the associated module file if it exists.

Returns:
    dict: Success message.

Raises:
    HTTPException: If tool not found (404) or deletion fails (500).

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
    api_instance = skillberry_store_sdk.ToolsApi(api_client)
    name = 'name_example' # str | 

    try:
        # Delete Tool
        api_response = api_instance.delete_tool_tools_name_delete(name)
        print("The response of ToolsApi->delete_tool_tools_name_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->delete_tool_tools_name_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**|  | 

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

# **execute_tool_tools_name_execute_post**
> Dict[str, object] execute_tool_tools_name_execute_post(name, request_body=request_body)

Execute Tool

Execute a tool by name with the provided parameters.

This endpoint mirrors the functionality of /manifests/execute/{uid} but works
with tool names instead of manifest UIDs.

Args:
    name: The name of the tool to execute.
    request: Represents an incoming fast api request object.
    parameters: Dictionary of key/value pairs to be passed to the tool execution (Optional).

Returns:
    dict: Tool execution output.

Raises:
    HTTPException: If tool not found (404) or execution fails (500).

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
    api_instance = skillberry_store_sdk.ToolsApi(api_client)
    name = 'name_example' # str | 
    request_body = None # Dict[str, object] |  (optional)

    try:
        # Execute Tool
        api_response = api_instance.execute_tool_tools_name_execute_post(name, request_body=request_body)
        print("The response of ToolsApi->execute_tool_tools_name_execute_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->execute_tool_tools_name_execute_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**|  | 
 **request_body** | [**Dict[str, object]**](object.md)|  | [optional] 

### Return type

**Dict[str, object]**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_tool_module_tools_name_module_get**
> str get_tool_module_tools_name_module_get(name)

Get Tool Module

Get the module file content for a specific tool.

Note: For MCP tools, this returns the generated function signature.
For code tools, this returns the actual module file content.

Args:
    name: The name of the tool.

Returns:
    PlainTextResponse: The module file content as plain text.

Raises:
    HTTPException: If tool not found (404), module not specified (404),
                  module file not found (404), or retrieval fails (500).

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
    api_instance = skillberry_store_sdk.ToolsApi(api_client)
    name = 'name_example' # str | 

    try:
        # Get Tool Module
        api_response = api_instance.get_tool_module_tools_name_module_get(name)
        print("The response of ToolsApi->get_tool_module_tools_name_module_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->get_tool_module_tools_name_module_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**|  | 

### Return type

**str**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: text/plain, application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_tool_tools_name_get**
> Dict[str, object] get_tool_tools_name_get(name)

Get Tool

Get a specific tool by name.

Args:
    name: The name of the tool.

Returns:
    dict: The tool object.

Raises:
    HTTPException: If tool not found (404) or retrieval fails (500).

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
    api_instance = skillberry_store_sdk.ToolsApi(api_client)
    name = 'name_example' # str | 

    try:
        # Get Tool
        api_response = api_instance.get_tool_tools_name_get(name)
        print("The response of ToolsApi->get_tool_tools_name_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->get_tool_tools_name_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**|  | 

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

# **list_tools_tools_get**
> List[Dict[str, object]] list_tools_tools_get()

List Tools

List all tools.

Returns:
    list: A list of all tool objects.

Raises:
    HTTPException: If listing fails (500).

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
    api_instance = skillberry_store_sdk.ToolsApi(api_client)

    try:
        # List Tools
        api_response = api_instance.list_tools_tools_get()
        print("The response of ToolsApi->list_tools_tools_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->list_tools_tools_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**List[Dict[str, object]]**

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

# **search_tools_search_tools_get**
> List[object] search_tools_search_tools_get(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)

Search Tools

Return a list of tools that are similar to the given search term.

Returns tools that are below the similarity threshold and match the filters.

Args:
    search_term: Search term.
    max_number_of_results: Number of results to return.
    similarity_threshold: Threshold to be used.
    manifest_filter: Manifest properties to filter (e.g., "tags:python", "state:approved").
    lifecycle_state: State to filter by (e.g., LifecycleState.APPROVED).

Returns:
    list: A list of matched tool names and similarity scores.

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
    api_instance = skillberry_store_sdk.ToolsApi(api_client)
    search_term = 'search_term_example' # str | 
    max_number_of_results = 5 # int |  (optional) (default to 5)
    similarity_threshold = 1 # float |  (optional) (default to 1)
    manifest_filter = '.' # str |  (optional) (default to '.')
    lifecycle_state = skillberry_store_sdk.LifecycleState() # LifecycleState |  (optional)

    try:
        # Search Tools
        api_response = api_instance.search_tools_search_tools_get(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)
        print("The response of ToolsApi->search_tools_search_tools_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->search_tools_search_tools_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **search_term** | **str**|  | 
 **max_number_of_results** | **int**|  | [optional] [default to 5]
 **similarity_threshold** | **float**|  | [optional] [default to 1]
 **manifest_filter** | **str**|  | [optional] [default to &#39;.&#39;]
 **lifecycle_state** | [**LifecycleState**](.md)|  | [optional] 

### Return type

**List[object]**

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

# **update_tool_tools_name_put**
> Dict[str, Optional[str]] update_tool_tools_name_put(name, tool_schema)

Update Tool

Update an existing tool.

Args:
    name: The name of the tool to update.
    tool: The updated tool schema.

Returns:
    dict: Success message.

Raises:
    HTTPException: If tool not found (404) or update fails (500).

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.tool_schema import ToolSchema
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
    api_instance = skillberry_store_sdk.ToolsApi(api_client)
    name = 'name_example' # str | 
    tool_schema = skillberry_store_sdk.ToolSchema() # ToolSchema | 

    try:
        # Update Tool
        api_response = api_instance.update_tool_tools_name_put(name, tool_schema)
        print("The response of ToolsApi->update_tool_tools_name_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->update_tool_tools_name_put: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**|  | 
 **tool_schema** | [**ToolSchema**](ToolSchema.md)|  | 

### Return type

**Dict[str, Optional[str]]**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

