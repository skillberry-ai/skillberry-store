# openapi_client.DescriptionsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**read_description_description_filename_get**](DescriptionsApi.md#read_description_description_filename_get) | **GET** /description/{filename} | Read Description
[**search_description_description_search_get**](DescriptionsApi.md#search_description_description_search_get) | **GET** /description/search | Search Description
[**update_description_description_update_filename_post**](DescriptionsApi.md#update_description_description_update_filename_post) | **POST** /description/update/{filename} | Update Description


# **read_description_description_filename_get**
> read_description_description_filename_get(filename)

Read Description

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
    api_instance = openapi_client.DescriptionsApi(api_client)
    filename = 'filename_example' # str | 

    try:
        # Read Description
        api_instance.read_description_description_filename_get(filename)
    except Exception as e:
        print("Exception when calling DescriptionsApi->read_description_description_filename_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **filename** | **str**|  | 

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

# **search_description_description_search_get**
> search_description_description_search_get(search_term, max_numer_of_results=max_numer_of_results, similarity_threshold=similarity_threshold, metadata_filter=metadata_filter, lifecycle_state=lifecycle_state)

Search Description

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
    api_instance = openapi_client.DescriptionsApi(api_client)
    search_term = 'search_term_example' # str | 
    max_numer_of_results = 5 # int |  (optional) (default to 5)
    similarity_threshold = 1 # float |  (optional) (default to 1)
    metadata_filter = '.' # str |  (optional) (default to '.')
    lifecycle_state = openapi_client.LifecycleState() # LifecycleState |  (optional)

    try:
        # Search Description
        api_instance.search_description_description_search_get(search_term, max_numer_of_results=max_numer_of_results, similarity_threshold=similarity_threshold, metadata_filter=metadata_filter, lifecycle_state=lifecycle_state)
    except Exception as e:
        print("Exception when calling DescriptionsApi->search_description_description_search_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **search_term** | **str**|  | 
 **max_numer_of_results** | **int**|  | [optional] [default to 5]
 **similarity_threshold** | **float**|  | [optional] [default to 1]
 **metadata_filter** | **str**|  | [optional] [default to &#39;.&#39;]
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

# **update_description_description_update_filename_post**
> update_description_description_update_filename_post(filename, new_description)

Update Description

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
    api_instance = openapi_client.DescriptionsApi(api_client)
    filename = 'filename_example' # str | 
    new_description = 'new_description_example' # str | 

    try:
        # Update Description
        api_instance.update_description_description_update_filename_post(filename, new_description)
    except Exception as e:
        print("Exception when calling DescriptionsApi->update_description_description_update_filename_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **filename** | **str**|  | 
 **new_description** | **str**|  | 

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

