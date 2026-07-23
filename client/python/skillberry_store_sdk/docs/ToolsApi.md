# skillberry_store_sdk.ToolsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**add_tool_from_code**](ToolsApi.md#add_tool_from_code) | **POST** /tools/add_code | Add Tool From Code
[**add_tool_from_python**](ToolsApi.md#add_tool_from_python) | **POST** /tools/add | Add Tool From Python
[**create_tool**](ToolsApi.md#create_tool) | **POST** /tools/ | Create Tool
[**delete_tool**](ToolsApi.md#delete_tool) | **DELETE** /tools/{uuid_or_name} | Delete Tool
[**execute_tool**](ToolsApi.md#execute_tool) | **POST** /tools/{uuid_or_name}/execute | Execute Tool
[**get_tool**](ToolsApi.md#get_tool) | **GET** /tools/{uuid_or_name} | Get Tool
[**get_tool_module**](ToolsApi.md#get_tool_module) | **GET** /tools/{uuid_or_name}/module | Get Tool Module
[**list_tools**](ToolsApi.md#list_tools) | **GET** /tools/ | List Tools
[**search_tools**](ToolsApi.md#search_tools) | **GET** /search/tools | Search Tools
[**tool_facets**](ToolsApi.md#tool_facets) | **GET** /facets/tools | Tool Facets
[**update_tool**](ToolsApi.md#update_tool) | **PUT** /tools/{uuid_or_name} | Update Tool


# **add_tool_from_code**
> Dict[str, object] add_tool_from_code(add_tool_from_code_request)

Add Tool From Code

Add a tool from Python source passed as a string (MCP-friendly).

Same behavior as ``POST /tools/add`` (auto-extracts the manifest from the
function docstring) but takes the source as a normal JSON ``code`` field
instead of a file upload — so it works over the MCP bridge, which cannot
transmit ``multipart``/octet-stream file bodies.

Args:
    req: ``code`` (the Python source), optional ``selected_func`` (which
        function to extract; defaults to the first), ``update`` (update an
        existing tool of the same name), and ``module_name`` (stored file
        name; defaults to ``tool.py``).

Returns:
    dict: Success message with the tool name, uuid, and module_name.

Raises:
    HTTPException: tool already exists (409), parse/validation error
        (400), or any other error (500).

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.add_tool_from_code_request import AddToolFromCodeRequest
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
    add_tool_from_code_request = skillberry_store_sdk.AddToolFromCodeRequest() # AddToolFromCodeRequest | 

    try:
        # Add Tool From Code
        api_response = api_instance.add_tool_from_code(add_tool_from_code_request)
        print("The response of ToolsApi->add_tool_from_code:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->add_tool_from_code: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **add_tool_from_code_request** | [**AddToolFromCodeRequest**](AddToolFromCodeRequest.md)|  | 

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

# **add_tool_from_python**
> Dict[str, object] add_tool_from_python(tool, selected_func=selected_func, update=update)

Add Tool From Python

Add a tool by automatically extracting parameters from Python code docstring.

This endpoint uploads a Python file and automatically generates a tool manifest
by parsing the function's docstring. The docstring must follow standard Python
documentation conventions (Google, NumPy, or Sphinx style).

Args:
    tool: The Python file to upload containing the function.
    selected_func: Optional name of the specific function to extract. If not provided,
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
    selected_func = 'selected_func_example' # str |  (optional)
    update = False # bool |  (optional) (default to False)

    try:
        # Add Tool From Python
        api_response = api_instance.add_tool_from_python(tool, selected_func=selected_func, update=update)
        print("The response of ToolsApi->add_tool_from_python:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->add_tool_from_python: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **tool** | **bytearray**|  | 
 **selected_func** | **str**|  | [optional] 
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

# **create_tool**
> Dict[str, object] create_tool(module, name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, module_name=module_name, programming_language=programming_language, packaging_format=packaging_format, packaging_params=packaging_params, params=params, returns=returns, dependencies=dependencies)

Create Tool

Create a new tool with its module file.

Creates a new tool entry in the store along with its associated Python module file.
The tool metadata is validated against the ToolSchema and stored as a manifest.

Args:
    tool: Tool metadata conforming to ToolSchema (name, description, params, etc.).
    module: Python module file to upload for the tool.

Returns:
    dict: Contains success message, tool name, UUID, and module_name.

Raises:
    HTTPException: 409 if tool already exists, 500 for other errors.

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
    parent = 'parent_example' # str | UUID of the parent object (previous version with same name) (optional)
    created_at = 'created_at_example' # str | ISO 8601 timestamp when created (optional)
    modified_at = 'modified_at_example' # str | ISO 8601 timestamp when last modified (optional)
    module_name = 'module_name_example' # str | Name of the module containing the tool (optional)
    programming_language = 'python' # str | Programming language of the tool (optional) (default to 'python')
    packaging_format = 'code' # str | Packaging format of the tool (e.g., 'code', 'mcp') (optional) (default to 'code')
    packaging_params = None # Dict[str, object] | Parameters specific to the packaging format. For 'mcp' format, should contain 'mcp_url' and 'mcp_tool_name'. Can be provided as a JSON string or dict. (optional)
    params = skillberry_store_sdk.ToolParamsSchema() # ToolParamsSchema | Parameters schema for the tool (optional)
    returns = skillberry_store_sdk.ToolReturnsSchema() # ToolReturnsSchema | Return value schema for the tool (optional)
    dependencies = ['dependencies_example'] # List[str] | List of tool names that this tool depends on (optional)

    try:
        # Create Tool
        api_response = api_instance.create_tool(module, name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, module_name=module_name, programming_language=programming_language, packaging_format=packaging_format, packaging_params=packaging_params, params=params, returns=returns, dependencies=dependencies)
        print("The response of ToolsApi->create_tool:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->create_tool: %s\n" % e)
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
 **parent** | **str**| UUID of the parent object (previous version with same name) | [optional] 
 **created_at** | **str**| ISO 8601 timestamp when created | [optional] 
 **modified_at** | **str**| ISO 8601 timestamp when last modified | [optional] 
 **module_name** | **str**| Name of the module containing the tool | [optional] 
 **programming_language** | **str**| Programming language of the tool | [optional] [default to &#39;python&#39;]
 **packaging_format** | **str**| Packaging format of the tool (e.g., &#39;code&#39;, &#39;mcp&#39;) | [optional] [default to &#39;code&#39;]
 **packaging_params** | [**Dict[str, object]**](object.md)| Parameters specific to the packaging format. For &#39;mcp&#39; format, should contain &#39;mcp_url&#39; and &#39;mcp_tool_name&#39;. Can be provided as a JSON string or dict. | [optional] 
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

# **delete_tool**
> Dict[str, object] delete_tool(uuid_or_name)

Delete Tool

Delete a tool from the store.

Removes a tool and its associated files from the store. This operation
also triggers a content deletion event for plugin processing.

Args:
    uuid_or_name: The UUID or name of the tool to delete.

Returns:
    dict: Success message confirming deletion.

Raises:
    HTTPException: 404 if tool not found, 500 for other errors.

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
    uuid_or_name = 'uuid_or_name_example' # str | 

    try:
        # Delete Tool
        api_response = api_instance.delete_tool(uuid_or_name)
        print("The response of ToolsApi->delete_tool:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->delete_tool: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uuid_or_name** | **str**|  | 

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

# **execute_tool**
> Dict[str, object] execute_tool(uuid_or_name, request_body=request_body)

Execute Tool

Execute a tool by UUID or name with the provided parameters.

This endpoint mirrors the functionality of /manifests/execute/{uid} but works
with tool UUIDs or names instead of manifest UIDs.

Args:
    uuid_or_name: The UUID or name of the tool to execute.
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
    uuid_or_name = 'uuid_or_name_example' # str | 
    request_body = None # Dict[str, object] |  (optional)

    try:
        # Execute Tool
        api_response = api_instance.execute_tool(uuid_or_name, request_body=request_body)
        print("The response of ToolsApi->execute_tool:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->execute_tool: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uuid_or_name** | **str**|  | 
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

# **get_tool**
> Dict[str, object] get_tool(uuid_or_name, fields=fields)

Get Tool

Get metadata for a specific tool by UUID or name.

Retrieves the manifest/metadata for a tool identified by either
its UUID or its unique name.

Args:
    uuid_or_name: The UUID or name of the tool to retrieve.
    fields: Optional field-selection spec (see query-param description).

Returns:
    dict: Tool metadata (subset when ``fields`` narrows the
        field selection).

Raises:
    HTTPException: 400 if ``fields`` is invalid, 404 if tool
        not found, 500 for other errors.

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
    uuid_or_name = 'uuid_or_name_example' # str | 
    fields = 'fields_example' # str | Field selection. 'minimal' returns uuid only. Omit or 'narrow' for the UI listing set (default). 'wide' returns every persisted manifest field. 'full' returns the complete object, including flag fields that trigger bundling mechanisms. Or supply a comma-separated allowlist of field names. (optional)

    try:
        # Get Tool
        api_response = api_instance.get_tool(uuid_or_name, fields=fields)
        print("The response of ToolsApi->get_tool:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->get_tool: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uuid_or_name** | **str**|  | 
 **fields** | **str**| Field selection. &#39;minimal&#39; returns uuid only. Omit or &#39;narrow&#39; for the UI listing set (default). &#39;wide&#39; returns every persisted manifest field. &#39;full&#39; returns the complete object, including flag fields that trigger bundling mechanisms. Or supply a comma-separated allowlist of field names. | [optional] 

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

# **get_tool_module**
> str get_tool_module(uuid_or_name)

Get Tool Module

Get the module file content for a specific tool.

Retrieves the Python source code or MCP content for a tool. For MCP-packaged
tools, returns the MCP manifest stub. For code-packaged tools, returns
the Python module source.

Args:
    uuid_or_name: The UUID or name of the tool whose module to retrieve.

Returns:
    PlainTextResponse: The module file content as plain text.

Raises:
    HTTPException: 404 if tool not found, 500 for other errors.

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
    uuid_or_name = 'uuid_or_name_example' # str | 

    try:
        # Get Tool Module
        api_response = api_instance.get_tool_module(uuid_or_name)
        print("The response of ToolsApi->get_tool_module:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->get_tool_module: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uuid_or_name** | **str**|  | 

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

# **list_tools**
> object list_tools(fields=fields, search=search, tags=tags, state=state, sort=sort, limit=limit, offset=offset)

List Tools

List tools with optional filter / sort / paginate / project.

See query-param descriptions for behavior. When neither ``limit``
nor ``offset`` is set, returns a bare list. Otherwise returns
``{items, total, offset, limit}``.

Raises:
    HTTPException: 400 if ``fields`` is invalid, 500 if listing fails.

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
    fields = 'fields_example' # str | Field selection. 'minimal' returns uuid only. Omit or 'narrow' for the UI listing set (default). 'wide' returns every persisted manifest field. 'full' returns the complete object, including flag fields that trigger bundling mechanisms. Or supply a comma-separated allowlist of field names. (optional)
    search = 'search_example' # str | Case-insensitive substring over name + description. (optional)
    tags = ['tags_example'] # List[str] | Repeat to filter by multiple tags (AND semantics). Namespace tags are ordinary tags — pass ``namespace:xyz`` to filter by namespace. (optional)
    state = 'state_example' # str | Exact-match lifecycle state filter. (optional)
    sort = 'sort_example' # str | ``field:direction`` (e.g. ``name:asc``). Defaults to ``modified_at:desc``. (optional)
    limit = 56 # int | Max items to return. Setting ``limit`` (or ``offset``) switches the response to a ``{items, total, offset, limit}`` envelope. Omit both for the legacy bare array. (optional)
    offset = 56 # int | Page offset. (optional)

    try:
        # List Tools
        api_response = api_instance.list_tools(fields=fields, search=search, tags=tags, state=state, sort=sort, limit=limit, offset=offset)
        print("The response of ToolsApi->list_tools:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->list_tools: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **fields** | **str**| Field selection. &#39;minimal&#39; returns uuid only. Omit or &#39;narrow&#39; for the UI listing set (default). &#39;wide&#39; returns every persisted manifest field. &#39;full&#39; returns the complete object, including flag fields that trigger bundling mechanisms. Or supply a comma-separated allowlist of field names. | [optional] 
 **search** | **str**| Case-insensitive substring over name + description. | [optional] 
 **tags** | [**List[str]**](str.md)| Repeat to filter by multiple tags (AND semantics). Namespace tags are ordinary tags — pass &#x60;&#x60;namespace:xyz&#x60;&#x60; to filter by namespace. | [optional] 
 **state** | **str**| Exact-match lifecycle state filter. | [optional] 
 **sort** | **str**| &#x60;&#x60;field:direction&#x60;&#x60; (e.g. &#x60;&#x60;name:asc&#x60;&#x60;). Defaults to &#x60;&#x60;modified_at:desc&#x60;&#x60;. | [optional] 
 **limit** | **int**| Max items to return. Setting &#x60;&#x60;limit&#x60;&#x60; (or &#x60;&#x60;offset&#x60;&#x60;) switches the response to a &#x60;&#x60;{items, total, offset, limit}&#x60;&#x60; envelope. Omit both for the legacy bare array. | [optional] 
 **offset** | **int**| Page offset. | [optional] 

### Return type

**object**

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

# **search_tools**
> List[object] search_tools(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state, fields=fields)

Search Tools

Return a list of tools that are similar to the given search term.

Returns tools that are below the similarity threshold and match the filters.

Args:
    search_term: Search term.
    max_number_of_results: Number of results to return.
    similarity_threshold: Threshold to be used.
    manifest_filter: Manifest properties to filter (e.g., "tags:python", "state:approved").
    lifecycle_state: State to filter by (e.g., LifecycleState.APPROVED).
    fields: Optional field-selection spec (see query-param description).

Returns:
    list: Field-selected tool dicts with ``similarity_score``
        merged in.

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
    fields = 'fields_example' # str | Field selection over each match. Same grammar as the list endpoint ('minimal' for uuid-only search results that cross-reference a loaded listing; omit or 'narrow' for the UI listing set — default; 'wide' for every persisted manifest field; 'full' for the complete object; CSV allowlist). Each match is a field-selected tool dict with 'similarity_score' merged in. (optional)

    try:
        # Search Tools
        api_response = api_instance.search_tools(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state, fields=fields)
        print("The response of ToolsApi->search_tools:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->search_tools: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **search_term** | **str**|  | 
 **max_number_of_results** | **int**|  | [optional] [default to 5]
 **similarity_threshold** | **float**|  | [optional] [default to 1]
 **manifest_filter** | **str**|  | [optional] [default to &#39;.&#39;]
 **lifecycle_state** | [**LifecycleState**](.md)|  | [optional] 
 **fields** | **str**| Field selection over each match. Same grammar as the list endpoint (&#39;minimal&#39; for uuid-only search results that cross-reference a loaded listing; omit or &#39;narrow&#39; for the UI listing set — default; &#39;wide&#39; for every persisted manifest field; &#39;full&#39; for the complete object; CSV allowlist). Each match is a field-selected tool dict with &#39;similarity_score&#39; merged in. | [optional] 

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

# **tool_facets**
> object tool_facets()

Tool Facets

Return the unique tags / namespaces / states over all tools.

Powers filter-picker widgets so callers can enumerate every
available value without fetching every tool.

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
        # Tool Facets
        api_response = api_instance.tool_facets()
        print("The response of ToolsApi->tool_facets:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->tool_facets: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**object**

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

# **update_tool**
> Dict[str, object] update_tool(uuid_or_name, tool_schema)

Update Tool

Update an existing tool's metadata.

Updates the manifest/metadata for an existing tool. The module file is not
updated by this endpoint. This operation triggers a content update event
for plugin processing.

Args:
    uuid_or_name: The UUID or name of the tool to update.
    tool: Updated tool metadata conforming to ToolSchema.

Returns:
    dict: Success message confirming update.

Raises:
    HTTPException: 404 if tool not found, 500 for other errors.

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
    uuid_or_name = 'uuid_or_name_example' # str | 
    tool_schema = skillberry_store_sdk.ToolSchema() # ToolSchema | 

    try:
        # Update Tool
        api_response = api_instance.update_tool(uuid_or_name, tool_schema)
        print("The response of ToolsApi->update_tool:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ToolsApi->update_tool: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uuid_or_name** | **str**|  | 
 **tool_schema** | [**ToolSchema**](ToolSchema.md)|  | 

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

