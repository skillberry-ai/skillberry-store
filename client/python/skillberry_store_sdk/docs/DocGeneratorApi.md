# skillberry_store_sdk.DocGeneratorApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**doc_generator_generate_endpoint**](DocGeneratorApi.md#doc_generator_generate_endpoint) | **POST** /plugins/doc_generator/generate | Generate Endpoint
[**doc_generator_refresh_endpoint**](DocGeneratorApi.md#doc_generator_refresh_endpoint) | **POST** /plugins/doc_generator/refresh | Refresh Endpoint


# **doc_generator_generate_endpoint**
> object doc_generator_generate_endpoint(generate_request)

Generate Endpoint

Generate/enrich docs for an object (proposed unless apply=True).

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.generate_request import GenerateRequest
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
    api_instance = skillberry_store_sdk.DocGeneratorApi(api_client)
    generate_request = skillberry_store_sdk.GenerateRequest() # GenerateRequest | 

    try:
        # Generate Endpoint
        api_response = api_instance.doc_generator_generate_endpoint(generate_request)
        print("The response of DocGeneratorApi->doc_generator_generate_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DocGeneratorApi->doc_generator_generate_endpoint: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **generate_request** | [**GenerateRequest**](GenerateRequest.md)|  | 

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

# **doc_generator_refresh_endpoint**
> object doc_generator_refresh_endpoint(refresh_request)

Refresh Endpoint

Detect drift and propose refreshed docs for an object.

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.refresh_request import RefreshRequest
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
    api_instance = skillberry_store_sdk.DocGeneratorApi(api_client)
    refresh_request = skillberry_store_sdk.RefreshRequest() # RefreshRequest | 

    try:
        # Refresh Endpoint
        api_response = api_instance.doc_generator_refresh_endpoint(refresh_request)
        print("The response of DocGeneratorApi->doc_generator_refresh_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DocGeneratorApi->doc_generator_refresh_endpoint: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **refresh_request** | [**RefreshRequest**](RefreshRequest.md)|  | 

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

