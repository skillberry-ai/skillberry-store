# skillberry_store_sdk.CreatorApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**creator_create_snippet_endpoint**](CreatorApi.md#creator_create_snippet_endpoint) | **POST** /plugins/creator/create-snippet | Create Snippet Endpoint


# **creator_create_snippet_endpoint**
> object creator_create_snippet_endpoint(create_snippet_request)

Create Snippet Endpoint

Create a code snippet from a description.

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.create_snippet_request import CreateSnippetRequest
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
    api_instance = skillberry_store_sdk.CreatorApi(api_client)
    create_snippet_request = skillberry_store_sdk.CreateSnippetRequest() # CreateSnippetRequest | 

    try:
        # Create Snippet Endpoint
        api_response = api_instance.creator_create_snippet_endpoint(create_snippet_request)
        print("The response of CreatorApi->creator_create_snippet_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling CreatorApi->creator_create_snippet_endpoint: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **create_snippet_request** | [**CreateSnippetRequest**](CreateSnippetRequest.md)|  | 

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

