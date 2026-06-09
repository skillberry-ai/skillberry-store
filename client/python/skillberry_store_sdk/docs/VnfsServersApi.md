# skillberry_store_sdk.VnfsServersApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_vnfs_server_vnfs_servers_post**](VnfsServersApi.md#create_vnfs_server_vnfs_servers_post) | **POST** /vnfs_servers/ | Create Vnfs Server
[**delete_vnfs_server_vnfs_servers_uuid_or_name_delete**](VnfsServersApi.md#delete_vnfs_server_vnfs_servers_uuid_or_name_delete) | **DELETE** /vnfs_servers/{uuid_or_name} | Delete Vnfs Server
[**get_vnfs_server_vnfs_servers_uuid_or_name_get**](VnfsServersApi.md#get_vnfs_server_vnfs_servers_uuid_or_name_get) | **GET** /vnfs_servers/{uuid_or_name} | Get Vnfs Server
[**list_vnfs_servers_vnfs_servers_get**](VnfsServersApi.md#list_vnfs_servers_vnfs_servers_get) | **GET** /vnfs_servers/ | List Vnfs Servers
[**search_vnfs_servers_search_vnfs_servers_get**](VnfsServersApi.md#search_vnfs_servers_search_vnfs_servers_get) | **GET** /search/vnfs_servers | Search Vnfs Servers
[**start_vnfs_server_vnfs_servers_uuid_or_name_start_post**](VnfsServersApi.md#start_vnfs_server_vnfs_servers_uuid_or_name_start_post) | **POST** /vnfs_servers/{uuid_or_name}/start | Start Vnfs Server
[**update_vnfs_server_vnfs_servers_uuid_or_name_put**](VnfsServersApi.md#update_vnfs_server_vnfs_servers_uuid_or_name_put) | **PUT** /vnfs_servers/{uuid_or_name} | Update Vnfs Server


# **create_vnfs_server_vnfs_servers_post**
> object create_vnfs_server_vnfs_servers_post(name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, port=port, skill_uuid=skill_uuid, protocol=protocol)

Create Vnfs Server

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
        api_response = api_instance.create_vnfs_server_vnfs_servers_post(name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, port=port, skill_uuid=skill_uuid, protocol=protocol)
        print("The response of VnfsServersApi->create_vnfs_server_vnfs_servers_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VnfsServersApi->create_vnfs_server_vnfs_servers_post: %s\n" % e)
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

# **delete_vnfs_server_vnfs_servers_uuid_or_name_delete**
> object delete_vnfs_server_vnfs_servers_uuid_or_name_delete(uuid_or_name)

Delete Vnfs Server

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
        api_response = api_instance.delete_vnfs_server_vnfs_servers_uuid_or_name_delete(uuid_or_name)
        print("The response of VnfsServersApi->delete_vnfs_server_vnfs_servers_uuid_or_name_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VnfsServersApi->delete_vnfs_server_vnfs_servers_uuid_or_name_delete: %s\n" % e)
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

# **get_vnfs_server_vnfs_servers_uuid_or_name_get**
> object get_vnfs_server_vnfs_servers_uuid_or_name_get(uuid_or_name)

Get Vnfs Server

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
        api_response = api_instance.get_vnfs_server_vnfs_servers_uuid_or_name_get(uuid_or_name)
        print("The response of VnfsServersApi->get_vnfs_server_vnfs_servers_uuid_or_name_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VnfsServersApi->get_vnfs_server_vnfs_servers_uuid_or_name_get: %s\n" % e)
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

# **list_vnfs_servers_vnfs_servers_get**
> object list_vnfs_servers_vnfs_servers_get()

List Vnfs Servers

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
        # List Vnfs Servers
        api_response = api_instance.list_vnfs_servers_vnfs_servers_get()
        print("The response of VnfsServersApi->list_vnfs_servers_vnfs_servers_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VnfsServersApi->list_vnfs_servers_vnfs_servers_get: %s\n" % e)
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

# **search_vnfs_servers_search_vnfs_servers_get**
> object search_vnfs_servers_search_vnfs_servers_get(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)

Search Vnfs Servers

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

    try:
        # Search Vnfs Servers
        api_response = api_instance.search_vnfs_servers_search_vnfs_servers_get(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)
        print("The response of VnfsServersApi->search_vnfs_servers_search_vnfs_servers_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VnfsServersApi->search_vnfs_servers_search_vnfs_servers_get: %s\n" % e)
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

# **start_vnfs_server_vnfs_servers_uuid_or_name_start_post**
> object start_vnfs_server_vnfs_servers_uuid_or_name_start_post(uuid_or_name)

Start Vnfs Server

Start or restart a vNFS endpoint.

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
        api_response = api_instance.start_vnfs_server_vnfs_servers_uuid_or_name_start_post(uuid_or_name)
        print("The response of VnfsServersApi->start_vnfs_server_vnfs_servers_uuid_or_name_start_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VnfsServersApi->start_vnfs_server_vnfs_servers_uuid_or_name_start_post: %s\n" % e)
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

# **update_vnfs_server_vnfs_servers_uuid_or_name_put**
> object update_vnfs_server_vnfs_servers_uuid_or_name_put(uuid_or_name, name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, port=port, skill_uuid=skill_uuid, protocol=protocol)

Update Vnfs Server

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
        api_response = api_instance.update_vnfs_server_vnfs_servers_uuid_or_name_put(uuid_or_name, name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, port=port, skill_uuid=skill_uuid, protocol=protocol)
        print("The response of VnfsServersApi->update_vnfs_server_vnfs_servers_uuid_or_name_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling VnfsServersApi->update_vnfs_server_vnfs_servers_uuid_or_name_put: %s\n" % e)
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

