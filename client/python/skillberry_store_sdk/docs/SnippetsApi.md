# skillberry_store_sdk.SnippetsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_snippet**](SnippetsApi.md#create_snippet) | **POST** /snippets/ | Create Snippet
[**delete_snippet**](SnippetsApi.md#delete_snippet) | **DELETE** /snippets/{uuid_or_name} | Delete Snippet
[**get_snippet**](SnippetsApi.md#get_snippet) | **GET** /snippets/{uuid_or_name} | Get Snippet
[**list_snippets**](SnippetsApi.md#list_snippets) | **GET** /snippets/ | List Snippets
[**search_snippets**](SnippetsApi.md#search_snippets) | **GET** /search/snippets | Search Snippets
[**snippet_facets**](SnippetsApi.md#snippet_facets) | **GET** /facets/snippets | Snippet Facets
[**update_snippet**](SnippetsApi.md#update_snippet) | **PUT** /snippets/{uuid_or_name} | Update Snippet


# **create_snippet**
> object create_snippet(content, name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, content_type=content_type, file=file)

Create Snippet

Create a new snippet in the store.

Creates a snippet with text content. Content can be provided either in the
snippet schema or uploaded as a file. Snippets are reusable text blocks
that can be referenced by skills.

Args:
    snippet: Snippet metadata conforming to SnippetSchema (name, description, content, etc.).
    file: Optional file upload containing snippet content. If provided, overrides snippet.content.

Returns:
    dict: Success message with snippet name and UUID.

Raises:
    HTTPException: 400 if file reading fails, 409 if snippet already exists, 500 for other errors.

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
        api_response = api_instance.create_snippet(content, name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, content_type=content_type, file=file)
        print("The response of SnippetsApi->create_snippet:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SnippetsApi->create_snippet: %s\n" % e)
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

# **delete_snippet**
> object delete_snippet(uuid_or_name)

Delete Snippet

Delete a snippet from the store.

Removes a snippet from the store. This operation triggers a content
deletion event for plugin processing.

Args:
    uuid_or_name: The UUID or name of the snippet to delete.

Returns:
    dict: Success message confirming deletion.

Raises:
    HTTPException: 404 if snippet not found, 500 for other errors.

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
        api_response = api_instance.delete_snippet(uuid_or_name)
        print("The response of SnippetsApi->delete_snippet:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SnippetsApi->delete_snippet: %s\n" % e)
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

# **get_snippet**
> object get_snippet(uuid_or_name, fields=fields)

Get Snippet

Get metadata for a specific snippet by UUID or name.

Retrieves the manifest/metadata for a snippet identified by
either its UUID or its unique name.

Args:
    uuid_or_name: The UUID or name of the snippet to retrieve.
    fields: Optional field-selection spec (see query-param description).

Returns:
    dict: Snippet metadata (subset when ``fields`` narrows the
        field selection).

Raises:
    HTTPException: 400 if ``fields`` is invalid, 404 if snippet
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
    api_instance = skillberry_store_sdk.SnippetsApi(api_client)
    uuid_or_name = 'uuid_or_name_example' # str | 
    fields = 'fields_example' # str | Field selection. 'minimal' returns uuid only. Omit or 'narrow' for the UI listing set (default). 'wide' returns every persisted manifest field (including ``content``). 'full' returns the complete object. Or supply a comma-separated allowlist of field names. (optional)

    try:
        # Get Snippet
        api_response = api_instance.get_snippet(uuid_or_name, fields=fields)
        print("The response of SnippetsApi->get_snippet:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SnippetsApi->get_snippet: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uuid_or_name** | **str**|  | 
 **fields** | **str**| Field selection. &#39;minimal&#39; returns uuid only. Omit or &#39;narrow&#39; for the UI listing set (default). &#39;wide&#39; returns every persisted manifest field (including &#x60;&#x60;content&#x60;&#x60;). &#39;full&#39; returns the complete object. Or supply a comma-separated allowlist of field names. | [optional] 

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

# **list_snippets**
> object list_snippets(fields=fields, search=search, tags=tags, state=state, sort=sort, limit=limit, offset=offset)

List Snippets

List snippets with optional filter / sort / paginate / project.

See query-param descriptions for behavior. When neither ``limit``
nor ``offset`` is set, returns a bare list (100% back-compat).
Otherwise returns ``{items, total, offset, limit}``.

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
    api_instance = skillberry_store_sdk.SnippetsApi(api_client)
    fields = 'fields_example' # str | Field selection. 'minimal' returns uuid only. Omit or 'narrow' for the UI listing set (default). 'wide' returns every persisted manifest field. 'full' returns the complete object, including flag fields that trigger bundling mechanisms. Or supply a comma-separated allowlist of field names. (optional)
    search = 'search_example' # str | Case-insensitive substring over name + description. (optional)
    tags = ['tags_example'] # List[str] | Repeat to filter by multiple tags (AND semantics). Namespace tags are ordinary tags — pass ``namespace:xyz`` to filter by namespace. (optional)
    state = 'state_example' # str | Exact-match lifecycle state filter. (optional)
    sort = 'sort_example' # str | ``field:direction`` (e.g. ``name:asc``). Defaults to ``modified_at:desc``. (optional)
    limit = 56 # int | Max items to return. Setting ``limit`` (or ``offset``) switches the response to a ``{items, total, offset, limit}`` envelope. Omit both for the legacy bare array. (optional)
    offset = 56 # int | Page offset. (optional)

    try:
        # List Snippets
        api_response = api_instance.list_snippets(fields=fields, search=search, tags=tags, state=state, sort=sort, limit=limit, offset=offset)
        print("The response of SnippetsApi->list_snippets:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SnippetsApi->list_snippets: %s\n" % e)
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

# **search_snippets**
> object search_snippets(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state, fields=fields)

Search Snippets

Search for snippets using semantic similarity.

Returns snippets that are semantically similar to the search term and
match the specified filters.

Args:
    search_term: Search term to find similar snippets.
    max_number_of_results: Maximum number of results to return (default: 5).
    similarity_threshold: Maximum similarity score threshold (default: 1, lower is more similar).
    manifest_filter: Manifest properties to filter (e.g., "tags:python", "state:approved").
    lifecycle_state: State to filter by (e.g., LifecycleState.APPROVED).
    fields: Optional field-selection spec (see query-param description).

Returns:
    list: Field-selected snippet dicts with ``similarity_score``
        merged in.

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
    api_instance = skillberry_store_sdk.SnippetsApi(api_client)
    search_term = 'search_term_example' # str | 
    max_number_of_results = 5 # int |  (optional) (default to 5)
    similarity_threshold = 1 # float |  (optional) (default to 1)
    manifest_filter = '.' # str |  (optional) (default to '.')
    lifecycle_state = skillberry_store_sdk.LifecycleState() # LifecycleState |  (optional)
    fields = 'fields_example' # str | Field selection over each match. Same grammar as the list endpoint ('minimal' for uuid-only search results that cross-reference a loaded listing; omit or 'narrow' for the UI listing set — default; 'wide' for every persisted manifest field; 'full' for the complete object; CSV allowlist). Each match is a field-selected snippet dict with 'similarity_score' merged in. (optional)

    try:
        # Search Snippets
        api_response = api_instance.search_snippets(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state, fields=fields)
        print("The response of SnippetsApi->search_snippets:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SnippetsApi->search_snippets: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **search_term** | **str**|  | 
 **max_number_of_results** | **int**|  | [optional] [default to 5]
 **similarity_threshold** | **float**|  | [optional] [default to 1]
 **manifest_filter** | **str**|  | [optional] [default to &#39;.&#39;]
 **lifecycle_state** | [**LifecycleState**](.md)|  | [optional] 
 **fields** | **str**| Field selection over each match. Same grammar as the list endpoint (&#39;minimal&#39; for uuid-only search results that cross-reference a loaded listing; omit or &#39;narrow&#39; for the UI listing set — default; &#39;wide&#39; for every persisted manifest field; &#39;full&#39; for the complete object; CSV allowlist). Each match is a field-selected snippet dict with &#39;similarity_score&#39; merged in. | [optional] 

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

# **snippet_facets**
> object snippet_facets()

Snippet Facets

Return the unique tags / namespaces / states over all snippets.

Powers filter-picker widgets so callers can enumerate every
available value without fetching every snippet.

Returns:
    dict: ``{"tags": [...], "namespaces": [...], "states": [...]}``.

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
        # Snippet Facets
        api_response = api_instance.snippet_facets()
        print("The response of SnippetsApi->snippet_facets:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SnippetsApi->snippet_facets: %s\n" % e)
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

# **update_snippet**
> object update_snippet(uuid_or_name, snippet_schema)

Update Snippet

Update an existing snippet's metadata and content.

Updates the manifest/metadata and content for an existing snippet.
This operation triggers a content update event for plugin processing.

Args:
    uuid_or_name: The UUID or name of the snippet to update.
    snippet: Updated snippet metadata conforming to SnippetSchema.

Returns:
    dict: Success message confirming update.

Raises:
    HTTPException: 404 if snippet not found, 500 for other errors.

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
        api_response = api_instance.update_snippet(uuid_or_name, snippet_schema)
        print("The response of SnippetsApi->update_snippet:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SnippetsApi->update_snippet: %s\n" % e)
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

