# skillberry_store_sdk.ProvenanceApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**provenance_check_endpoint**](ProvenanceApi.md#provenance_check_endpoint) | **POST** /plugins/provenance/check | Check Endpoint
[**provenance_recheck_endpoint**](ProvenanceApi.md#provenance_recheck_endpoint) | **POST** /plugins/provenance/recheck | Recheck Endpoint


# **provenance_check_endpoint**
> object provenance_check_endpoint(check_request)

Check Endpoint

Gather provenance/background for a URL (pre-import) or uuid (post).

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.check_request import CheckRequest
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
    api_instance = skillberry_store_sdk.ProvenanceApi(api_client)
    check_request = skillberry_store_sdk.CheckRequest() # CheckRequest | 

    try:
        # Check Endpoint
        api_response = api_instance.provenance_check_endpoint(check_request)
        print("The response of ProvenanceApi->provenance_check_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ProvenanceApi->provenance_check_endpoint: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **check_request** | [**CheckRequest**](CheckRequest.md)|  | 

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

# **provenance_recheck_endpoint**
> object provenance_recheck_endpoint(recheck_request)

Recheck Endpoint

Re-check a stored skill and report drift vs. its baseline.

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.recheck_request import RecheckRequest
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
    api_instance = skillberry_store_sdk.ProvenanceApi(api_client)
    recheck_request = skillberry_store_sdk.RecheckRequest() # RecheckRequest | 

    try:
        # Recheck Endpoint
        api_response = api_instance.provenance_recheck_endpoint(recheck_request)
        print("The response of ProvenanceApi->provenance_recheck_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ProvenanceApi->provenance_recheck_endpoint: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **recheck_request** | [**RecheckRequest**](RecheckRequest.md)|  | 

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

