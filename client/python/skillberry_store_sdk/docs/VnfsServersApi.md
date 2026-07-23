# skillberry_store_sdk.VnfsServersApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_vnfs_server**](VnfsServersApi.md#create_vnfs_server) | **POST** /vnfs_servers/ | Create Vnfs Server
[**delete_vnfs_server**](VnfsServersApi.md#delete_vnfs_server) | **DELETE** /vnfs_servers/{uuid_or_name} | Delete Vnfs Server
[**get_vnfs_server**](VnfsServersApi.md#get_vnfs_server) | **GET** /vnfs_servers/{uuid_or_name} | Get Vnfs Server
[**list_vnfs_servers**](VnfsServersApi.md#list_vnfs_servers) | **GET** /vnfs_servers/ | List Vnfs Servers
[**search_vnfs_servers**](VnfsServersApi.md#search_vnfs_servers) | **GET** /search/vnfs_servers | Search Vnfs Servers
[**start_vnfs_server**](VnfsServersApi.md#start_vnfs_server) | **POST** /vnfs_servers/{uuid_or_name}/start | Start Vnfs Server
[**update_vnfs_server**](VnfsServersApi.md#update_vnfs_server) | **PUT** /vnfs_servers/{uuid_or_name} | Update Vnfs Server
[**vnfs_server_facets**](VnfsServersApi.md#vnfs_server_facets) | **GET** /facets/vnfs_servers | Vnfs Server Facets


# **create_vnfs_server**
> object create_vnfs_server(name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, port=port, skill_uuid=skill_uuid, protocol=protocol)

Create Vnfs Server

Create a new virtual NFS server.

Creates a virtual NFS server that exposes snippets through a network
file system interface on a specified port.

Args:
    vnfs: Virtual NFS server metadata conforming to VnfsSchema (name, skill_uuid, port, etc.).
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
    api_instance = skillberry_store_sdk.VnfsServersApi(api_client)
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
    port = 56 # int | Port for the vNFS server. Auto-assigned if None. (optional)
    skill_uuid = 'skill_uuid_example' # str | UUID of the skill to expose as a filesystem (optional)
    protocol = 'webdav' # str | Network filesystem protocol: 'webdav' or 'nfs' (optional) (default to 'webdav')

    try:
        # Create Vnfs Server
        api_response = api_instance.create_vnfs_server(name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, port=port, skill_uuid=skill_uuid, protocol=protocol)
        print("The response of VnfsServersApi->create_vnfs_server:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VnfsServersApi->create_vnfs_server: %s\n" % e)
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
 **port** | **int**| Port for the vNFS server. Auto-assigned if None. | [optional] 
 **skill_uuid** | **str**| UUID of the skill to expose as a filesystem | [optional] 
 **protocol** | **str**| Network filesystem protocol: &#39;webdav&#39; or &#39;nfs&#39; | [optional] [default to &#39;webdav&#39;]

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

# **delete_vnfs_server**
> object delete_vnfs_server(uuid_or_name)

Delete Vnfs Server

Delete a virtual NFS server from the store.

Removes a virtual NFS server and stops it if running.

Args:
    uuid_or_name: The UUID or name of the virtual NFS server to delete.

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
    api_instance = skillberry_store_sdk.VnfsServersApi(api_client)
    uuid_or_name = 'uuid_or_name_example' # str | 

    try:
        # Delete Vnfs Server
        api_response = api_instance.delete_vnfs_server(uuid_or_name)
        print("The response of VnfsServersApi->delete_vnfs_server:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VnfsServersApi->delete_vnfs_server: %s\n" % e)
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

# **get_vnfs_server**
> object get_vnfs_server(uuid_or_name)

Get Vnfs Server

Get metadata for a specific virtual NFS server by UUID or name.

Retrieves the complete manifest/metadata for a virtual NFS server identified
by either its UUID or its unique name.

Args:
    uuid_or_name: The UUID or name of the virtual NFS server to retrieve.

Returns:
    dict: Virtual NFS server metadata including name, uuid, skill_uuid, port, etc.

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
    api_instance = skillberry_store_sdk.VnfsServersApi(api_client)
    uuid_or_name = 'uuid_or_name_example' # str | 

    try:
        # Get Vnfs Server
        api_response = api_instance.get_vnfs_server(uuid_or_name)
        print("The response of VnfsServersApi->get_vnfs_server:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VnfsServersApi->get_vnfs_server: %s\n" % e)
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

# **list_vnfs_servers**
> object list_vnfs_servers(skill_uuid=skill_uuid, fields=fields, search=search, tags=tags, state=state, sort=sort, limit=limit, offset=offset)

List Vnfs Servers

List vNFS servers with optional filter / sort / paginate / project.

Response shape: bare array when neither ``limit`` nor ``offset`` is
set (a breaking change vs. the pre-Phase-2 ``{virtual_nfs_servers:
{...}}`` wrapper); envelope ``{items, total, offset, limit}``
otherwise. Runtime enrichment runs only on the current page.

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
    api_instance = skillberry_store_sdk.VnfsServersApi(api_client)
    skill_uuid = 'skill_uuid_example' # str |  (optional)
    fields = 'fields_example' # str | Field projection. Omit for the full enriched shape. Use 'list' for the slim list-view preset (persistent metadata + runtime status), 'full' for every field, or a comma-separated allowlist. (optional)
    search = 'search_example' # str | Case-insensitive substring over name + description. (optional)
    tags = ['tags_example'] # List[str] | Repeat to filter by multiple tags (AND semantics). Namespace tags are ordinary tags — pass ``namespace:xyz`` to filter by namespace. (optional)
    state = 'state_example' # str | Exact-match lifecycle state filter. (optional)
    sort = 'sort_example' # str | ``field:direction`` (e.g. ``name:asc``). Defaults to ``modified_at:desc``. (optional)
    limit = 56 # int | Max items to return. Setting ``limit`` (or ``offset``) switches the response to a ``{items, total, offset, limit}`` envelope. Omit both for a bare array. (optional)
    offset = 56 # int | Page offset. (optional)

    try:
        # List Vnfs Servers
        api_response = api_instance.list_vnfs_servers(skill_uuid=skill_uuid, fields=fields, search=search, tags=tags, state=state, sort=sort, limit=limit, offset=offset)
        print("The response of VnfsServersApi->list_vnfs_servers:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VnfsServersApi->list_vnfs_servers: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **skill_uuid** | **str**|  | [optional] 
 **fields** | **str**| Field projection. Omit for the full enriched shape. Use &#39;list&#39; for the slim list-view preset (persistent metadata + runtime status), &#39;full&#39; for every field, or a comma-separated allowlist. | [optional] 
 **search** | **str**| Case-insensitive substring over name + description. | [optional] 
 **tags** | [**List[str]**](str.md)| Repeat to filter by multiple tags (AND semantics). Namespace tags are ordinary tags — pass &#x60;&#x60;namespace:xyz&#x60;&#x60; to filter by namespace. | [optional] 
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

# **search_vnfs_servers**
> object search_vnfs_servers(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state, fields=fields)

Search Vnfs Servers

Search for virtual NFS servers using semantic similarity.

Args:
    search_term: Search term to find similar virtual NFS servers.
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
    api_instance = skillberry_store_sdk.VnfsServersApi(api_client)
    search_term = 'search_term_example' # str | 
    max_number_of_results = 5 # int |  (optional) (default to 5)
    similarity_threshold = 1 # float |  (optional) (default to 1)
    manifest_filter = '.' # str |  (optional) (default to '.')
    lifecycle_state = skillberry_store_sdk.LifecycleState() # LifecycleState |  (optional)
    fields = 'fields_example' # str | Optional projection over each matched server. Omit for the legacy '{filename, similarity_score}' shape. Otherwise the same grammar as list projection applies. (optional)

    try:
        # Search Vnfs Servers
        api_response = api_instance.search_vnfs_servers(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state, fields=fields)
        print("The response of VnfsServersApi->search_vnfs_servers:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VnfsServersApi->search_vnfs_servers: %s\n" % e)
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

# **start_vnfs_server**
> object start_vnfs_server(uuid_or_name)

Start Vnfs Server

Start or restart a virtual NFS server.

Starts a virtual NFS server process that exposes the associated skill's
snippets via a network file system interface. If already running, returns
the existing server information.

Args:
    uuid_or_name: The UUID or name of the virtual NFS server to start.
    request: FastAPI request object (kept for OpenAPI shape compatibility;
        ``VnfsService.start`` does not need request context).

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
    api_instance = skillberry_store_sdk.VnfsServersApi(api_client)
    uuid_or_name = 'uuid_or_name_example' # str | 

    try:
        # Start Vnfs Server
        api_response = api_instance.start_vnfs_server(uuid_or_name)
        print("The response of VnfsServersApi->start_vnfs_server:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VnfsServersApi->start_vnfs_server: %s\n" % e)
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

# **update_vnfs_server**
> object update_vnfs_server(uuid_or_name, name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, port=port, skill_uuid=skill_uuid, protocol=protocol)

Update Vnfs Server

Update an existing virtual NFS server's metadata.

Updates the manifest/metadata for an existing virtual NFS server. If the
server is running, it will be restarted with the new configuration.

Args:
    uuid_or_name: The UUID or name of the virtual NFS server to update.
    vnfs: Updated virtual NFS server metadata conforming to VnfsSchema.
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
    api_instance = skillberry_store_sdk.VnfsServersApi(api_client)
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
    port = 56 # int | Port for the vNFS server. Auto-assigned if None. (optional)
    skill_uuid = 'skill_uuid_example' # str | UUID of the skill to expose as a filesystem (optional)
    protocol = 'webdav' # str | Network filesystem protocol: 'webdav' or 'nfs' (optional) (default to 'webdav')

    try:
        # Update Vnfs Server
        api_response = api_instance.update_vnfs_server(uuid_or_name, name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, port=port, skill_uuid=skill_uuid, protocol=protocol)
        print("The response of VnfsServersApi->update_vnfs_server:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VnfsServersApi->update_vnfs_server: %s\n" % e)
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
 **port** | **int**| Port for the vNFS server. Auto-assigned if None. | [optional] 
 **skill_uuid** | **str**| UUID of the skill to expose as a filesystem | [optional] 
 **protocol** | **str**| Network filesystem protocol: &#39;webdav&#39; or &#39;nfs&#39; | [optional] [default to &#39;webdav&#39;]

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

# **vnfs_server_facets**
> object vnfs_server_facets()

Vnfs Server Facets

Return the unique tags / namespaces / states over all vNFS servers.

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
    api_instance = skillberry_store_sdk.VnfsServersApi(api_client)

    try:
        # Vnfs Server Facets
        api_response = api_instance.vnfs_server_facets()
        print("The response of VnfsServersApi->vnfs_server_facets:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VnfsServersApi->vnfs_server_facets: %s\n" % e)
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

