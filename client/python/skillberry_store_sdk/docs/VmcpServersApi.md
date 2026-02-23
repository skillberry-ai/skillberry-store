# skillberry_store_sdk.VmcpServersApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_vmcp_server_vmcp_servers_post**](VmcpServersApi.md#create_vmcp_server_vmcp_servers_post) | **POST** /vmcp_servers/ | Create Vmcp Server
[**delete_vmcp_server_vmcp_servers_name_delete**](VmcpServersApi.md#delete_vmcp_server_vmcp_servers_name_delete) | **DELETE** /vmcp_servers/{name} | Delete Vmcp Server
[**get_vmcp_server_vmcp_servers_name_get**](VmcpServersApi.md#get_vmcp_server_vmcp_servers_name_get) | **GET** /vmcp_servers/{name} | Get Vmcp Server
[**list_vmcp_servers_vmcp_servers_get**](VmcpServersApi.md#list_vmcp_servers_vmcp_servers_get) | **GET** /vmcp_servers/ | List Vmcp Servers
[**search_vmcp_servers_search_vmcp_servers_get**](VmcpServersApi.md#search_vmcp_servers_search_vmcp_servers_get) | **GET** /search/vmcp_servers | Search Vmcp Servers
[**start_vmcp_server_vmcp_servers_name_start_post**](VmcpServersApi.md#start_vmcp_server_vmcp_servers_name_start_post) | **POST** /vmcp_servers/{name}/start | Start Vmcp Server
[**update_vmcp_server_vmcp_servers_name_put**](VmcpServersApi.md#update_vmcp_server_vmcp_servers_name_put) | **PUT** /vmcp_servers/{name} | Update Vmcp Server


# **create_vmcp_server_vmcp_servers_post**
> object create_vmcp_server_vmcp_servers_post(name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, port=port, skill_uuid=skill_uuid)

Create Vmcp Server

Create a new virtual MCP server.  Creates both the persistent JSON representation and starts the runtime server.  Args:     vmcp: The vmcp schema (auto-generated from VmcpSchema).     request: The incoming request object for context extraction.  Returns:     dict: Success message with the vmcp server name, uuid, and port.  Raises:     HTTPException: If vmcp server already exists (409) or creation fails (500).

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.manifest_state import ManifestState
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
    tags = ['tags_example'] # List[Optional[str]] | List of tags for categorizing (optional)
    extra = None # Dict[str, object] | Optional key-value pairs for additional flexible information (optional)
    port = 56 # int | Port on which the virtual MCP server is running. If None, an available port will be auto-assigned. (optional)
    skill_uuid = 'skill_uuid_example' # str | UUID of the skill registered with the virtual MCP server (optional)

    try:
        # Create Vmcp Server
        api_response = api_instance.create_vmcp_server_vmcp_servers_post(name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, port=port, skill_uuid=skill_uuid)
        print("The response of VmcpServersApi->create_vmcp_server_vmcp_servers_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VmcpServersApi->create_vmcp_server_vmcp_servers_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**| Name | [optional] 
 **uuid** | **str**| A UUID. If not provided, a UUID will be automatically generated. | [optional] 
 **version** | **str**| Version | [optional] 
 **description** | **str**| Short description | [optional] 
 **state** | [**ManifestState**](.md)| Lifecycle state | [optional] 
 **tags** | [**List[Optional[str]]**](str.md)| List of tags for categorizing | [optional] 
 **extra** | [**Dict[str, object]**](object.md)| Optional key-value pairs for additional flexible information | [optional] 
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

# **delete_vmcp_server_vmcp_servers_name_delete**
> object delete_vmcp_server_vmcp_servers_name_delete(name)

Delete Vmcp Server

Delete a virtual MCP server by name.  Stops the runtime server and removes persistent data.  Args:     name: The name of the vmcp server to delete.  Returns:     dict: Success message.  Raises:     HTTPException: If vmcp server not found (404) or deletion fails (500).

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
    name = 'name_example' # str | 

    try:
        # Delete Vmcp Server
        api_response = api_instance.delete_vmcp_server_vmcp_servers_name_delete(name)
        print("The response of VmcpServersApi->delete_vmcp_server_vmcp_servers_name_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VmcpServersApi->delete_vmcp_server_vmcp_servers_name_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**|  | 

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

# **get_vmcp_server_vmcp_servers_name_get**
> object get_vmcp_server_vmcp_servers_name_get(name)

Get Vmcp Server

Get a specific virtual MCP server by name.  Returns both persistent and runtime information.  Args:     name: The name of the vmcp server.  Returns:     dict: The vmcp server object with runtime details.  Raises:     HTTPException: If vmcp server not found (404) or retrieval fails (500).

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
    name = 'name_example' # str | 

    try:
        # Get Vmcp Server
        api_response = api_instance.get_vmcp_server_vmcp_servers_name_get(name)
        print("The response of VmcpServersApi->get_vmcp_server_vmcp_servers_name_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VmcpServersApi->get_vmcp_server_vmcp_servers_name_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**|  | 

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

# **list_vmcp_servers_vmcp_servers_get**
> object list_vmcp_servers_vmcp_servers_get()

List Vmcp Servers

List all virtual MCP servers.  Returns both persistent and runtime information.  Returns:     dict: Dictionary containing a dict of virtual MCP servers with full details.  Raises:     HTTPException: If listing fails (500).

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
        # List Vmcp Servers
        api_response = api_instance.list_vmcp_servers_vmcp_servers_get()
        print("The response of VmcpServersApi->list_vmcp_servers_vmcp_servers_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VmcpServersApi->list_vmcp_servers_vmcp_servers_get: %s\n" % e)
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

# **search_vmcp_servers_search_vmcp_servers_get**
> object search_vmcp_servers_search_vmcp_servers_get(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)

Search Vmcp Servers

Search for vmcp servers by description.  Returns vmcp servers that are below the similarity threshold and match the filters.  Args:     search_term: Search term.     max_number_of_results: Number of results to return.     similarity_threshold: Threshold to be used.     manifest_filter: Manifest properties to filter (e.g., \"tags:python\", \"state:approved\").     lifecycle_state: State to filter by (e.g., LifecycleState.APPROVED).  Returns:     list: A list of matched vmcp server names and similarity scores.

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.lifecycle_state import LifecycleState
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

    try:
        # Search Vmcp Servers
        api_response = api_instance.search_vmcp_servers_search_vmcp_servers_get(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)
        print("The response of VmcpServersApi->search_vmcp_servers_search_vmcp_servers_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VmcpServersApi->search_vmcp_servers_search_vmcp_servers_get: %s\n" % e)
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

# **start_vmcp_server_vmcp_servers_name_start_post**
> object start_vmcp_server_vmcp_servers_name_start_post(name)

Start Vmcp Server

Start or restart a virtual MCP server.  This endpoint allows starting a server that exists in persistent storage but is not currently running in the runtime manager.  Args:     name: The name of the vmcp server to start.     request: The incoming request object for context extraction.  Returns:     dict: Success message with the server port.  Raises:     HTTPException: If vmcp server not found (404) or start fails (500).

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
    name = 'name_example' # str | 

    try:
        # Start Vmcp Server
        api_response = api_instance.start_vmcp_server_vmcp_servers_name_start_post(name)
        print("The response of VmcpServersApi->start_vmcp_server_vmcp_servers_name_start_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VmcpServersApi->start_vmcp_server_vmcp_servers_name_start_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**|  | 

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

# **update_vmcp_server_vmcp_servers_name_put**
> object update_vmcp_server_vmcp_servers_name_put(name, name2=name2, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, port=port, skill_uuid=skill_uuid)

Update Vmcp Server

Update an existing virtual MCP server.  Updates both persistent data and restarts the runtime server.  Args:     name: The name of the vmcp server to update.     vmcp: The updated vmcp schema.     request: The incoming request object for context extraction.  Returns:     dict: Success message with new port.  Raises:     HTTPException: If vmcp server not found (404) or update fails (500).

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.manifest_state import ManifestState
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
    name = 'name_example' # str | 
    name2 = 'name_example' # str | Name (optional)
    uuid = 'uuid_example' # str | A UUID. If not provided, a UUID will be automatically generated. (optional)
    version = 'version_example' # str | Version (optional)
    description = 'description_example' # str | Short description (optional)
    state = skillberry_store_sdk.ManifestState() # ManifestState | Lifecycle state (optional)
    tags = ['tags_example'] # List[str] | List of tags for categorizing (optional)
    extra = None # Dict[str, object] | Optional key-value pairs for additional flexible information (optional)
    port = 56 # int | Port on which the virtual MCP server is running. If None, an available port will be auto-assigned. (optional)
    skill_uuid = 'skill_uuid_example' # str | UUID of the skill registered with the virtual MCP server (optional)

    try:
        # Update Vmcp Server
        api_response = api_instance.update_vmcp_server_vmcp_servers_name_put(name, name2=name2, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, port=port, skill_uuid=skill_uuid)
        print("The response of VmcpServersApi->update_vmcp_server_vmcp_servers_name_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VmcpServersApi->update_vmcp_server_vmcp_servers_name_put: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**|  | 
 **name2** | **str**| Name | [optional] 
 **uuid** | **str**| A UUID. If not provided, a UUID will be automatically generated. | [optional] 
 **version** | **str**| Version | [optional] 
 **description** | **str**| Short description | [optional] 
 **state** | [**ManifestState**](.md)| Lifecycle state | [optional] 
 **tags** | [**List[str]**](str.md)| List of tags for categorizing | [optional] 
 **extra** | [**Dict[str, object]**](object.md)| Optional key-value pairs for additional flexible information | [optional] 
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

