# openapi_client.MetadataApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**read_lifecycle_state_lifecycle_state_filename_get**](MetadataApi.md#read_lifecycle_state_lifecycle_state_filename_get) | **GET** /lifecycle_state/{filename} | Read Lifecycle State
[**read_metadata_metadata_filename_get**](MetadataApi.md#read_metadata_metadata_filename_get) | **GET** /metadata/{filename} | Read Metadata
[**update_lifecycle_state_lifecycle_state_update_filename_post**](MetadataApi.md#update_lifecycle_state_lifecycle_state_update_filename_post) | **POST** /lifecycle_state/update/{filename} | Update Lifecycle State
[**update_metadata_metadata_update_filename_post**](MetadataApi.md#update_metadata_metadata_update_filename_post) | **POST** /metadata/update/{filename} | Update Metadata


# **read_lifecycle_state_lifecycle_state_filename_get**
> read_lifecycle_state_lifecycle_state_filename_get(filename)

Read Lifecycle State

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
    api_instance = openapi_client.MetadataApi(api_client)
    filename = 'filename_example' # str | 

    try:
        # Read Lifecycle State
        api_instance.read_lifecycle_state_lifecycle_state_filename_get(filename)
    except Exception as e:
        print("Exception when calling MetadataApi->read_lifecycle_state_lifecycle_state_filename_get: %s\n" % e)
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

# **read_metadata_metadata_filename_get**
> read_metadata_metadata_filename_get(filename)

Read Metadata

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
    api_instance = openapi_client.MetadataApi(api_client)
    filename = 'filename_example' # str | 

    try:
        # Read Metadata
        api_instance.read_metadata_metadata_filename_get(filename)
    except Exception as e:
        print("Exception when calling MetadataApi->read_metadata_metadata_filename_get: %s\n" % e)
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

# **update_lifecycle_state_lifecycle_state_update_filename_post**
> update_lifecycle_state_lifecycle_state_update_filename_post(filename, state)

Update Lifecycle State

### Example


```python
import openapi_client
from openapi_client.models.lifecycle_state import LifecycleState
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
    api_instance = openapi_client.MetadataApi(api_client)
    filename = 'filename_example' # str | 
    state = openapi_client.LifecycleState() # LifecycleState | 

    try:
        # Update Lifecycle State
        api_instance.update_lifecycle_state_lifecycle_state_update_filename_post(filename, state)
    except Exception as e:
        print("Exception when calling MetadataApi->update_lifecycle_state_lifecycle_state_update_filename_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **filename** | **str**|  | 
 **state** | [**LifecycleState**](.md)|  | 

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

# **update_metadata_metadata_update_filename_post**
> update_metadata_metadata_update_filename_post(filename, body)

Update Metadata

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
    api_instance = openapi_client.MetadataApi(api_client)
    filename = 'filename_example' # str | 
    body = None # object | 

    try:
        # Update Metadata
        api_instance.update_metadata_metadata_update_filename_post(filename, body)
    except Exception as e:
        print("Exception when calling MetadataApi->update_metadata_metadata_update_filename_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **filename** | **str**|  | 
 **body** | **object**|  | 

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

