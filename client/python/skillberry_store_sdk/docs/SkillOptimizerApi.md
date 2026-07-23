# skillberry_store_sdk.SkillOptimizerApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**skill_optimizer_optimize_skill_endpoint**](SkillOptimizerApi.md#skill_optimizer_optimize_skill_endpoint) | **POST** /plugins/skill-optimizer/optimize-skill | Optimize Skill Endpoint


# **skill_optimizer_optimize_skill_endpoint**
> object skill_optimizer_optimize_skill_endpoint(optimize_skill_request)

Optimize Skill Endpoint

Optimize an existing skill using RunSpace.

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.optimize_skill_request import OptimizeSkillRequest
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
    api_instance = skillberry_store_sdk.SkillOptimizerApi(api_client)
    optimize_skill_request = skillberry_store_sdk.OptimizeSkillRequest() # OptimizeSkillRequest | 

    try:
        # Optimize Skill Endpoint
        api_response = api_instance.skill_optimizer_optimize_skill_endpoint(optimize_skill_request)
        print("The response of SkillOptimizerApi->skill_optimizer_optimize_skill_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillOptimizerApi->skill_optimizer_optimize_skill_endpoint: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **optimize_skill_request** | [**OptimizeSkillRequest**](OptimizeSkillRequest.md)|  | 

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

