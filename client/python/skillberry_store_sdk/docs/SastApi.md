# skillberry_store_sdk.SastApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**sast_fix_endpoint**](SastApi.md#sast_fix_endpoint) | **POST** /plugins/sast/fix | Fix Endpoint
[**sast_scan_endpoint**](SastApi.md#sast_scan_endpoint) | **POST** /plugins/sast/scan | Scan Endpoint


# **sast_fix_endpoint**
> object sast_fix_endpoint(fix_request)

Fix Endpoint

Fix selected objects' findings (at given severities) with the LLM.

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.fix_request import FixRequest
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
    api_instance = skillberry_store_sdk.SastApi(api_client)
    fix_request = skillberry_store_sdk.FixRequest() # FixRequest | 

    try:
        # Fix Endpoint
        api_response = api_instance.sast_fix_endpoint(fix_request)
        print("The response of SastApi->sast_fix_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SastApi->sast_fix_endpoint: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **fix_request** | [**FixRequest**](FixRequest.md)|  | 

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

# **sast_scan_endpoint**
> object sast_scan_endpoint(skillberry_plugin_sast_plugin_skillberry_plugin_sast_get_router_locals_scan_request)

Scan Endpoint

Scan a store object and persist SAST findings.

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.skillberry_plugin_sast_plugin_skillberry_plugin_sast_get_router_locals_scan_request import SkillberryPluginSastPluginSkillberryPluginSastGetRouterLocalsScanRequest
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
    api_instance = skillberry_store_sdk.SastApi(api_client)
    skillberry_plugin_sast_plugin_skillberry_plugin_sast_get_router_locals_scan_request = skillberry_store_sdk.SkillberryPluginSastPluginSkillberryPluginSastGetRouterLocalsScanRequest() # SkillberryPluginSastPluginSkillberryPluginSastGetRouterLocalsScanRequest | 

    try:
        # Scan Endpoint
        api_response = api_instance.sast_scan_endpoint(skillberry_plugin_sast_plugin_skillberry_plugin_sast_get_router_locals_scan_request)
        print("The response of SastApi->sast_scan_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SastApi->sast_scan_endpoint: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **skillberry_plugin_sast_plugin_skillberry_plugin_sast_get_router_locals_scan_request** | [**SkillberryPluginSastPluginSkillberryPluginSastGetRouterLocalsScanRequest**](SkillberryPluginSastPluginSkillberryPluginSastGetRouterLocalsScanRequest.md)|  | 

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

