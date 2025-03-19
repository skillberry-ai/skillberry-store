# openapi_client.ManifestApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**add_manifest_manifests_add_post**](ManifestApi.md#add_manifest_manifests_add_post) | **POST** /manifests/add | Add Manifest
[**delete_manifest_manifests_uid_delete**](ManifestApi.md#delete_manifest_manifests_uid_delete) | **DELETE** /manifests/{uid} | Delete Manifest
[**execute_manifest_manifests_execute_uid_post**](ManifestApi.md#execute_manifest_manifests_execute_uid_post) | **POST** /manifests/execute/{uid} | Execute Manifest
[**get_code_manifest_code_manifests_uid_get**](ManifestApi.md#get_code_manifest_code_manifests_uid_get) | **GET** /code/manifests/{uid} | Get Code Manifest
[**get_manifest_manifests_uid_get**](ManifestApi.md#get_manifest_manifests_uid_get) | **GET** /manifests/{uid} | Get Manifest
[**get_manifests_manifests_get**](ManifestApi.md#get_manifests_manifests_get) | **GET** /manifests | Get Manifests
[**search_manifest_search_manifests_get**](ManifestApi.md#search_manifest_search_manifests_get) | **GET** /search/manifests | Search Manifest


# **add_manifest_manifests_add_post**
> add_manifest_manifests_add_post(file_manifest, file)

Add Manifest

Adds manifest along with its invocation code. As part of the addition, the description of the manifest is embedded and stored in vector db.  The manifest is assigned with a unique identifier.  Parameters:     file_manifest (str): The manifest of the file (json format).     file (UploadFile): The file containing invocation code.  Returns:     dict: The unique identifier of the manifest

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.ManifestApi(api_client)
    file_manifest = 'file_manifest_example' # str | 
    file = None # bytearray | 

    try:
        # Add Manifest
        api_instance.add_manifest_manifests_add_post(file_manifest, file)
    except Exception as e:
        print("Exception when calling ManifestApi->add_manifest_manifests_add_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **file_manifest** | **str**|  | 
 **file** | **bytearray**|  | 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: text/plain, application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_manifest_manifests_uid_delete**
> delete_manifest_manifests_uid_delete(uid)

Delete Manifest

Delete the manifest removing its description from vector db.  Parameters:     dict: manifest deletion message  Raises:     HTTPException (404): If manifest not found

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.ManifestApi(api_client)
    uid = 'uid_example' # str | 

    try:
        # Delete Manifest
        api_instance.delete_manifest_manifests_uid_delete(uid)
    except Exception as e:
        print("Exception when calling ManifestApi->delete_manifest_manifests_uid_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uid** | **str**|  | 

### Return type

void (empty response body)

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

# **execute_manifest_manifests_execute_uid_post**
> execute_manifest_manifests_execute_uid_post(uid, body=body)

Execute Manifest

Invoke manifest function given its uid.  Parameters:     uid (str): The unique identifier of the manifest     parameters (dict): List of key/val pair to be passed to method invocation (Optional)   Returns:     dict: function output  Raises:     HTTPException (404): If manifest not found

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.ManifestApi(api_client)
    uid = 'uid_example' # str | 
    body = None # object |  (optional)

    try:
        # Execute Manifest
        api_instance.execute_manifest_manifests_execute_uid_post(uid, body=body)
    except Exception as e:
        print("Exception when calling ManifestApi->execute_manifest_manifests_execute_uid_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uid** | **str**|  | 
 **body** | **object**|  | [optional] 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: text/plain, application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_code_manifest_code_manifests_uid_get**
> get_code_manifest_code_manifests_uid_get(uid)

Get Code Manifest

Retrieve manifest code for the given uid.  Parameters:     uid (str): The uid of the manifest  Returns:     str: The manifest code  Raises:     HTTPException (404): If manifest or code not found

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.ManifestApi(api_client)
    uid = 'uid_example' # str | 

    try:
        # Get Code Manifest
        api_instance.get_code_manifest_code_manifests_uid_get(uid)
    except Exception as e:
        print("Exception when calling ManifestApi->get_code_manifest_code_manifests_uid_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uid** | **str**|  | 

### Return type

void (empty response body)

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

# **get_manifest_manifests_uid_get**
> get_manifest_manifests_uid_get(uid)

Get Manifest

Retrieve manifest for the given uid.  Parameters:     uid (str): The uid of the manifest  Returns:     dict: The manifest in json format  Raises:     HTTPException (404): If manifest not found

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.ManifestApi(api_client)
    uid = 'uid_example' # str | 

    try:
        # Get Manifest
        api_instance.get_manifest_manifests_uid_get(uid)
    except Exception as e:
        print("Exception when calling ManifestApi->get_manifest_manifests_uid_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uid** | **str**|  | 

### Return type

void (empty response body)

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

# **get_manifests_manifests_get**
> get_manifests_manifests_get(manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)

Get Manifests

Return a list of manifests matching the given lifecycle state and properties filter.  Parameters:     manifest_filter (str): manifest properties to filter (Optional)     lifecycle_state (LifecycleState): state to filter (Optional)  Returns:     list (dict): A list of matched manifests in json format

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.ManifestApi(api_client)
    manifest_filter = '.' # str |  (optional) (default to '.')
    lifecycle_state = openapi_client.LifecycleState() # LifecycleState |  (optional)

    try:
        # Get Manifests
        api_instance.get_manifests_manifests_get(manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)
    except Exception as e:
        print("Exception when calling ManifestApi->get_manifests_manifests_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **manifest_filter** | **str**|  | [optional] [default to &#39;.&#39;]
 **lifecycle_state** | [**LifecycleState**](.md)|  | [optional] 

### Return type

void (empty response body)

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

# **search_manifest_search_manifests_get**
> search_manifest_search_manifests_get(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)

Search Manifest

Return a list of manifests that are similar to the given search term and are below the similarity threshold matching the given lifecycle state.  Parameters:     search_term (str): search term     max_number_of_results (int): number of results to return     similarity_threshold (float): threshold to be used     manifest_filter (str): manifest properties to filter     lifecycle_state (LifecycleState): state to filter  Returns:     list (dict): A list of matched description_vector keys and                  similarity score

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.ManifestApi(api_client)
    search_term = 'search_term_example' # str | 
    max_number_of_results = 5 # int |  (optional) (default to 5)
    similarity_threshold = 1 # float |  (optional) (default to 1)
    manifest_filter = '.' # str |  (optional) (default to '.')
    lifecycle_state = openapi_client.LifecycleState() # LifecycleState |  (optional)

    try:
        # Search Manifest
        api_instance.search_manifest_search_manifests_get(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)
    except Exception as e:
        print("Exception when calling ManifestApi->search_manifest_search_manifests_get: %s\n" % e)
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

void (empty response body)

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

