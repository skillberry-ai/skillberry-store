# skillberry_store_sdk.SnippetsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_snippet_snippets_post**](SnippetsApi.md#create_snippet_snippets_post) | **POST** /snippets/ | Create Snippet
[**delete_snippet_snippets_uuid_or_name_delete**](SnippetsApi.md#delete_snippet_snippets_uuid_or_name_delete) | **DELETE** /snippets/{uuid_or_name} | Delete Snippet
[**get_snippet_snippets_uuid_or_name_get**](SnippetsApi.md#get_snippet_snippets_uuid_or_name_get) | **GET** /snippets/{uuid_or_name} | Get Snippet
[**list_snippets_snippets_get**](SnippetsApi.md#list_snippets_snippets_get) | **GET** /snippets/ | List Snippets
[**search_snippets_search_snippets_get**](SnippetsApi.md#search_snippets_search_snippets_get) | **GET** /search/snippets | Search Snippets
[**update_snippet_snippets_uuid_or_name_put**](SnippetsApi.md#update_snippet_snippets_uuid_or_name_put) | **PUT** /snippets/{uuid_or_name} | Update Snippet


# **create_snippet_snippets_post**
> object create_snippet_snippets_post(content, name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, content_type=content_type, file=file)

Create Snippet

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
    api_instance = skillberry_store_sdk.SnippetsApi(api_client)
    content = 'content_example' # str | The text content of the snippet
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
    content_type = skillberry_store_sdk.ContentType() # ContentType | MIME type of the snippet content (optional)
    file = 'file_example' # str |  (optional)

    try:
        # Create Snippet
        api_response = api_instance.create_snippet_snippets_post(content, name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, content_type=content_type, file=file)
        print("The response of SnippetsApi->create_snippet_snippets_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SnippetsApi->create_snippet_snippets_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **content** | **str**| The text content of the snippet | 
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
 **content_type** | [**ContentType**](.md)| MIME type of the snippet content | [optional] 
 **file** | **str**|  | [optional] 

### Return type

**object**

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

# **delete_snippet_snippets_uuid_or_name_delete**
> object delete_snippet_snippets_uuid_or_name_delete(uuid_or_name)

Delete Snippet

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
    api_instance = skillberry_store_sdk.SnippetsApi(api_client)
    uuid_or_name = 'uuid_or_name_example' # str | 

    try:
        # Delete Snippet
        api_response = api_instance.delete_snippet_snippets_uuid_or_name_delete(uuid_or_name)
        print("The response of SnippetsApi->delete_snippet_snippets_uuid_or_name_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SnippetsApi->delete_snippet_snippets_uuid_or_name_delete: %s\n" % e)
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

# **get_snippet_snippets_uuid_or_name_get**
> object get_snippet_snippets_uuid_or_name_get(uuid_or_name)

Get Snippet

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
    api_instance = skillberry_store_sdk.SnippetsApi(api_client)
    uuid_or_name = 'uuid_or_name_example' # str | 

    try:
        # Get Snippet
        api_response = api_instance.get_snippet_snippets_uuid_or_name_get(uuid_or_name)
        print("The response of SnippetsApi->get_snippet_snippets_uuid_or_name_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SnippetsApi->get_snippet_snippets_uuid_or_name_get: %s\n" % e)
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

# **list_snippets_snippets_get**
> object list_snippets_snippets_get()

List Snippets

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
    api_instance = skillberry_store_sdk.SnippetsApi(api_client)

    try:
        # List Snippets
        api_response = api_instance.list_snippets_snippets_get()
        print("The response of SnippetsApi->list_snippets_snippets_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SnippetsApi->list_snippets_snippets_get: %s\n" % e)
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

# **search_snippets_search_snippets_get**
> object search_snippets_search_snippets_get(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)

Search Snippets

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
    api_instance = skillberry_store_sdk.SnippetsApi(api_client)
    search_term = 'search_term_example' # str | 
    max_number_of_results = 5 # int |  (optional) (default to 5)
    similarity_threshold = 1 # float |  (optional) (default to 1)
    manifest_filter = '.' # str |  (optional) (default to '.')
    lifecycle_state = skillberry_store_sdk.LifecycleState() # LifecycleState |  (optional)

    try:
        # Search Snippets
        api_response = api_instance.search_snippets_search_snippets_get(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)
        print("The response of SnippetsApi->search_snippets_search_snippets_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SnippetsApi->search_snippets_search_snippets_get: %s\n" % e)
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

# **update_snippet_snippets_uuid_or_name_put**
> object update_snippet_snippets_uuid_or_name_put(uuid_or_name, snippet_schema)

Update Snippet

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.snippet_schema import SnippetSchema
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
    api_instance = skillberry_store_sdk.SnippetsApi(api_client)
    uuid_or_name = 'uuid_or_name_example' # str | 
    snippet_schema = skillberry_store_sdk.SnippetSchema() # SnippetSchema | 

    try:
        # Update Snippet
        api_response = api_instance.update_snippet_snippets_uuid_or_name_put(uuid_or_name, snippet_schema)
        print("The response of SnippetsApi->update_snippet_snippets_uuid_or_name_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SnippetsApi->update_snippet_snippets_uuid_or_name_put: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uuid_or_name** | **str**|  | 
 **snippet_schema** | [**SnippetSchema**](SnippetSchema.md)|  | 

### Return type

**object**

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

