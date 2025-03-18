# openapi_client.ExecutionApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**execute_file_execute_filename_post**](ExecutionApi.md#execute_file_execute_filename_post) | **POST** /execute/{filename} | Execute File


# **execute_file_execute_filename_post**
> execute_file_execute_filename_post(filename, body=body)

Execute File

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
    api_instance = openapi_client.ExecutionApi(api_client)
    filename = 'filename_example' # str | 
    body = None # object |  (optional)

    try:
        # Execute File
        api_instance.execute_file_execute_filename_post(filename, body=body)
    except Exception as e:
        print("Exception when calling ExecutionApi->execute_file_execute_filename_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **filename** | **str**|  | 
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

