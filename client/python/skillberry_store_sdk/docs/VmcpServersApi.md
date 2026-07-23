# skillberry_store_sdk.VmcpServersApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_vmcp_server**](VmcpServersApi.md#create_vmcp_server) | **POST** /vmcp_servers/ | Create Vmcp Server
[**delete_vmcp_server**](VmcpServersApi.md#delete_vmcp_server) | **DELETE** /vmcp_servers/{uuid_or_name} | Delete Vmcp Server
[**get_vmcp_server**](VmcpServersApi.md#get_vmcp_server) | **GET** /vmcp_servers/{uuid_or_name} | Get Vmcp Server
[**list_vmcp_servers**](VmcpServersApi.md#list_vmcp_servers) | **GET** /vmcp_servers/ | List Vmcp Servers
[**search_vmcp_servers**](VmcpServersApi.md#search_vmcp_servers) | **GET** /search/vmcp_servers | Search Vmcp Servers
[**start_vmcp_server**](VmcpServersApi.md#start_vmcp_server) | **POST** /vmcp_servers/{uuid_or_name}/start | Start Vmcp Server
[**update_vmcp_server**](VmcpServersApi.md#update_vmcp_server) | **PUT** /vmcp_servers/{uuid_or_name} | Update Vmcp Server
[**vmcp_server_facets**](VmcpServersApi.md#vmcp_server_facets) | **GET** /facets/vmcp_servers | Vmcp Server Facets


# **create_vmcp_server**
> object create_vmcp_server(name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, port=port, skill_uuid=skill_uuid)

Create Vmcp Server

Create a new virtual MCP server.

Creates a virtual MCP server that exposes a skill's tools and snippets
through the MCP protocol on a specified port.

Args:
    vmcp: Virtual MCP server metadata conforming to VmcpSchema (name, skill_uuid, port, etc.).
    request: FastAPI request object for extracting environment context.

Returns:
    dict: Success message with server name, UUID, and assigned port.

Raises:
    HTTPException: 409 if server already exists or port conflict, 500 for other errors.

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
    api_instance = skillberry_store_sdk.VmcpServersApi(api_client)
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
    port = 56 # int | Port on which the virtual MCP server is running. If None, an available port will be auto-assigned. (optional)
    skill_uuid = 'skill_uuid_example' # str | UUID of the skill registered with the virtual MCP server (optional)

    try:
        # Create Vmcp Server
        api_response = api_instance.create_vmcp_server(name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, port=port, skill_uuid=skill_uuid)
        print("The response of VmcpServersApi->create_vmcp_server:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VmcpServersApi->create_vmcp_server: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
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
 **port** | **int**| Port on which the virtual MCP server is running. If None, an available port will be auto-assigned. | [optional] 
 **skill_uuid** | **str**| UUID of the skill registered with the virtual MCP server | [optional] 

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

# **delete_vmcp_server**
> object delete_vmcp_server(uuid_or_name)

Delete Vmcp Server

Delete a virtual MCP server from the store.

Removes a virtual MCP server and stops it if running.

Args:
    uuid_or_name: The UUID or name of the virtual MCP server to delete.

Returns:
    dict: Success message confirming deletion.

Raises:
    HTTPException: 404 if server not found, 500 for other errors.

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
    api_instance = skillberry_store_sdk.VmcpServersApi(api_client)
    uuid_or_name = 'uuid_or_name_example' # str | 

    try:
        # Delete Vmcp Server
        api_response = api_instance.delete_vmcp_server(uuid_or_name)
        print("The response of VmcpServersApi->delete_vmcp_server:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VmcpServersApi->delete_vmcp_server: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uuid_or_name** | **str**|  | 

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

# **get_vmcp_server**
> object get_vmcp_server(uuid_or_name)

Get Vmcp Server

Get metadata for a specific virtual MCP server by UUID or name.

Retrieves the complete manifest/metadata for a virtual MCP server identified
by either its UUID or its unique name.

Args:
    uuid_or_name: The UUID or name of the virtual MCP server to retrieve.

Returns:
    dict: Virtual MCP server metadata including name, uuid, skill_uuid, port, etc.

Raises:
    HTTPException: 404 if server not found, 500 for other errors.

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
    api_instance = skillberry_store_sdk.VmcpServersApi(api_client)
    uuid_or_name = 'uuid_or_name_example' # str | 

    try:
        # Get Vmcp Server
        api_response = api_instance.get_vmcp_server(uuid_or_name)
        print("The response of VmcpServersApi->get_vmcp_server:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VmcpServersApi->get_vmcp_server: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uuid_or_name** | **str**|  | 

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

# **list_vmcp_servers**
> object list_vmcp_servers(skill_uuid=skill_uuid, fields=fields, search=search, tags=tags, state=state, sort=sort, limit=limit, offset=offset)

List Vmcp Servers

List VMCP servers with optional filter / sort / paginate / project.

Response shape: bare array when neither ``limit`` nor ``offset`` is
set (a breaking change vs. the pre-Phase-2 ``{virtual_mcp_servers:
{...}}`` wrapper); envelope ``{items, total, offset, limit}``
otherwise. Runtime enrichment runs only on the current page.

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
    api_instance = skillberry_store_sdk.VmcpServersApi(api_client)
    skill_uuid = 'skill_uuid_example' # str |  (optional)
    fields = 'fields_example' # str | Field projection. Omit for the full enriched shape. Use 'list' for the slim list-view preset (persistent metadata + runtime status), 'full' for every field, or a comma-separated allowlist. (optional)
    search = 'search_example' # str | Case-insensitive substring over name + description. (optional)
    tags = ['tags_example'] # List[Optional[str]] | Repeat to filter by multiple tags (AND semantics). Namespace tags are ordinary tags — pass ``namespace:xyz`` to filter by namespace. (optional)
    state = 'state_example' # str | Exact-match lifecycle state filter. (optional)
    sort = 'sort_example' # str | ``field:direction`` (e.g. ``name:asc``). Defaults to ``modified_at:desc``. (optional)
    limit = 56 # int | Max items to return. Setting ``limit`` (or ``offset``) switches the response to a ``{items, total, offset, limit}`` envelope. Omit both for a bare array. (optional)
    offset = 56 # int | Page offset. (optional)

    try:
        # List Vmcp Servers
        api_response = api_instance.list_vmcp_servers(skill_uuid=skill_uuid, fields=fields, search=search, tags=tags, state=state, sort=sort, limit=limit, offset=offset)
        print("The response of VmcpServersApi->list_vmcp_servers:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VmcpServersApi->list_vmcp_servers: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **skill_uuid** | **str**|  | [optional] 
 **fields** | **str**| Field projection. Omit for the full enriched shape. Use &#39;list&#39; for the slim list-view preset (persistent metadata + runtime status), &#39;full&#39; for every field, or a comma-separated allowlist. | [optional] 
 **search** | **str**| Case-insensitive substring over name + description. | [optional] 
 **tags** | [**List[Optional[str]]**](str.md)| Repeat to filter by multiple tags (AND semantics). Namespace tags are ordinary tags — pass &#x60;&#x60;namespace:xyz&#x60;&#x60; to filter by namespace. | [optional] 
 **state** | **str**| Exact-match lifecycle state filter. | [optional] 
 **sort** | **str**| &#x60;&#x60;field:direction&#x60;&#x60; (e.g. &#x60;&#x60;name:asc&#x60;&#x60;). Defaults to &#x60;&#x60;modified_at:desc&#x60;&#x60;. | [optional] 
 **limit** | **int**| Max items to return. Setting &#x60;&#x60;limit&#x60;&#x60; (or &#x60;&#x60;offset&#x60;&#x60;) switches the response to a &#x60;&#x60;{items, total, offset, limit}&#x60;&#x60; envelope. Omit both for a bare array. | [optional] 
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

# **search_vmcp_servers**
> object search_vmcp_servers(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state, fields=fields)

Search Vmcp Servers

Search for virtual MCP servers using semantic similarity.

Args:
    search_term: Search term to find similar virtual MCP servers.
    max_number_of_results: Maximum number of results to return.
    similarity_threshold: Maximum similarity score threshold.
    manifest_filter: Manifest properties to filter.
    lifecycle_state: State to filter by.
    fields: Optional projection spec (see query-param description).

Raises:
    HTTPException: 400 if ``fields`` is invalid, 503 if search is not
        available, 500 for other errors.

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
    api_instance = skillberry_store_sdk.VmcpServersApi(api_client)
    search_term = 'search_term_example' # str | 
    max_number_of_results = 5 # int |  (optional) (default to 5)
    similarity_threshold = 1 # float |  (optional) (default to 1)
    manifest_filter = '.' # str |  (optional) (default to '.')
    lifecycle_state = skillberry_store_sdk.LifecycleState() # LifecycleState |  (optional)
    fields = 'fields_example' # str | Optional projection over each matched server. Omit for the legacy '{filename, similarity_score}' shape. Otherwise the same grammar as list projection applies. (optional)

    try:
        # Search Vmcp Servers
        api_response = api_instance.search_vmcp_servers(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state, fields=fields)
        print("The response of VmcpServersApi->search_vmcp_servers:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VmcpServersApi->search_vmcp_servers: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **search_term** | **str**|  | 
 **max_number_of_results** | **int**|  | [optional] [default to 5]
 **similarity_threshold** | **float**|  | [optional] [default to 1]
 **manifest_filter** | **str**|  | [optional] [default to &#39;.&#39;]
 **lifecycle_state** | [**LifecycleState**](.md)|  | [optional] 
 **fields** | **str**| Optional projection over each matched server. Omit for the legacy &#39;{filename, similarity_score}&#39; shape. Otherwise the same grammar as list projection applies. | [optional] 

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

# **start_vmcp_server**
> object start_vmcp_server(uuid_or_name)

Start Vmcp Server

Start or restart a virtual MCP server.

Starts a virtual MCP server process that exposes the associated skill's
tools and snippets via the MCP protocol. If already running, returns
the existing server information.

Args:
    uuid_or_name: The UUID or name of the virtual MCP server to start.
    request: FastAPI request object for extracting environment context.

Returns:
    dict: Success message with server name and port.

Raises:
    HTTPException: 404 if server or skill not found, 500 for other errors.

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
    api_instance = skillberry_store_sdk.VmcpServersApi(api_client)
    uuid_or_name = 'uuid_or_name_example' # str | 

    try:
        # Start Vmcp Server
        api_response = api_instance.start_vmcp_server(uuid_or_name)
        print("The response of VmcpServersApi->start_vmcp_server:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VmcpServersApi->start_vmcp_server: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uuid_or_name** | **str**|  | 

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

# **update_vmcp_server**
> object update_vmcp_server(uuid_or_name, name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, port=port, skill_uuid=skill_uuid)

Update Vmcp Server

Update an existing virtual MCP server's metadata.

Updates the manifest/metadata for an existing virtual MCP server. If the
server is running, it will be restarted with the new configuration.

Args:
    uuid_or_name: The UUID or name of the virtual MCP server to update.
    vmcp: Updated virtual MCP server metadata conforming to VmcpSchema.
    request: FastAPI request object for extracting environment context.

Returns:
    dict: Success message with server name and port.

Raises:
    HTTPException: 404 if server not found, 500 for other errors.

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
    api_instance = skillberry_store_sdk.VmcpServersApi(api_client)
    uuid_or_name = 'uuid_or_name_example' # str | 
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
    port = 56 # int | Port on which the virtual MCP server is running. If None, an available port will be auto-assigned. (optional)
    skill_uuid = 'skill_uuid_example' # str | UUID of the skill registered with the virtual MCP server (optional)

    try:
        # Update Vmcp Server
        api_response = api_instance.update_vmcp_server(uuid_or_name, name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, port=port, skill_uuid=skill_uuid)
        print("The response of VmcpServersApi->update_vmcp_server:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VmcpServersApi->update_vmcp_server: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uuid_or_name** | **str**|  | 
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
 **port** | **int**| Port on which the virtual MCP server is running. If None, an available port will be auto-assigned. | [optional] 
 **skill_uuid** | **str**| UUID of the skill registered with the virtual MCP server | [optional] 

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

# **vmcp_server_facets**
> object vmcp_server_facets()

Vmcp Server Facets

Return the unique tags / namespaces / states over all VMCP servers.

Powers filter-picker widgets so callers can enumerate every
available value without fetching every server.

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
    api_instance = skillberry_store_sdk.VmcpServersApi(api_client)

    try:
        # Vmcp Server Facets
        api_response = api_instance.vmcp_server_facets()
        print("The response of VmcpServersApi->vmcp_server_facets:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VmcpServersApi->vmcp_server_facets: %s\n" % e)
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

