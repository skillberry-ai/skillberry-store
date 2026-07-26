# skillberry_store_sdk.SecurityApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**security_evaluate_endpoint**](SecurityApi.md#security_evaluate_endpoint) | **POST** /plugins/security/evaluate | Evaluate Endpoint


# **security_evaluate_endpoint**
> object security_evaluate_endpoint(evaluate_request)

Evaluate Endpoint

Evaluate a store object and store the security score.

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.evaluate_request import EvaluateRequest
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
    api_instance = skillberry_store_sdk.SecurityApi(api_client)
    evaluate_request = skillberry_store_sdk.EvaluateRequest() # EvaluateRequest | 

    try:
        # Evaluate Endpoint
        api_response = api_instance.security_evaluate_endpoint(evaluate_request)
        print("The response of SecurityApi->security_evaluate_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SecurityApi->security_evaluate_endpoint: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **evaluate_request** | [**EvaluateRequest**](EvaluateRequest.md)|  | 

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

