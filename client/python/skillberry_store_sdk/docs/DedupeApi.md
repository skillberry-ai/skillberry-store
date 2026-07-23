# skillberry_store_sdk.DedupeApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**dedupe_delete_decision**](DedupeApi.md#dedupe_delete_decision) | **POST** /plugins/dedupe/decisions/{uuid}/delete | Delete Decision
[**dedupe_keep_decision**](DedupeApi.md#dedupe_keep_decision) | **POST** /plugins/dedupe/decisions/{uuid}/keep | Keep Decision
[**dedupe_list_decisions**](DedupeApi.md#dedupe_list_decisions) | **GET** /plugins/dedupe/decisions | List Decisions


# **dedupe_delete_decision**
> object dedupe_delete_decision(uuid)

Delete Decision

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
    api_instance = skillberry_store_sdk.DedupeApi(api_client)
    uuid = 'uuid_example' # str | 

    try:
        # Delete Decision
        api_response = api_instance.dedupe_delete_decision(uuid)
        print("The response of DedupeApi->dedupe_delete_decision:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DedupeApi->dedupe_delete_decision: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uuid** | **str**|  | 

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

# **dedupe_keep_decision**
> object dedupe_keep_decision(uuid)

Keep Decision

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
    api_instance = skillberry_store_sdk.DedupeApi(api_client)
    uuid = 'uuid_example' # str | 

    try:
        # Keep Decision
        api_response = api_instance.dedupe_keep_decision(uuid)
        print("The response of DedupeApi->dedupe_keep_decision:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DedupeApi->dedupe_keep_decision: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uuid** | **str**|  | 

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

# **dedupe_list_decisions**
> object dedupe_list_decisions()

List Decisions

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
    api_instance = skillberry_store_sdk.DedupeApi(api_client)

    try:
        # List Decisions
        api_response = api_instance.dedupe_list_decisions()
        print("The response of DedupeApi->dedupe_list_decisions:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DedupeApi->dedupe_list_decisions: %s\n" % e)
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

