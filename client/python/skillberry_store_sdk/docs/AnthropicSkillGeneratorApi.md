# skillberry_store_sdk.AnthropicSkillGeneratorApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**anthropic_skill_generator_generate_skill_endpoint**](AnthropicSkillGeneratorApi.md#anthropic_skill_generator_generate_skill_endpoint) | **POST** /plugins/anthropic-skill-generator/generate-skill | Generate Skill Endpoint


# **anthropic_skill_generator_generate_skill_endpoint**
> object anthropic_skill_generator_generate_skill_endpoint(generate_skill_request)

Generate Skill Endpoint

Generate an Anthropic skill from a description.

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.generate_skill_request import GenerateSkillRequest
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
    api_instance = skillberry_store_sdk.AnthropicSkillGeneratorApi(api_client)
    generate_skill_request = skillberry_store_sdk.GenerateSkillRequest() # GenerateSkillRequest | 

    try:
        # Generate Skill Endpoint
        api_response = api_instance.anthropic_skill_generator_generate_skill_endpoint(generate_skill_request)
        print("The response of AnthropicSkillGeneratorApi->anthropic_skill_generator_generate_skill_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AnthropicSkillGeneratorApi->anthropic_skill_generator_generate_skill_endpoint: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **generate_skill_request** | [**GenerateSkillRequest**](GenerateSkillRequest.md)|  | 

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

