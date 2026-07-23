# skillberry_store_sdk.DastApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**dast_scan_endpoint**](DastApi.md#dast_scan_endpoint) | **POST** /plugins/dast/scan | Scan Endpoint
[**dast_scan_status**](DastApi.md#dast_scan_status) | **GET** /plugins/dast/scan-status | Scan Status


# **dast_scan_endpoint**
> object dast_scan_endpoint(skillberry_plugin_dast_plugin_skillberry_plugin_dast_get_router_locals_scan_request)

Scan Endpoint

Run a DAST scan over a skill's entry points (detect-and-report).

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.skillberry_plugin_dast_plugin_skillberry_plugin_dast_get_router_locals_scan_request import SkillberryPluginDastPluginSkillberryPluginDastGetRouterLocalsScanRequest
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
    api_instance = skillberry_store_sdk.DastApi(api_client)
    skillberry_plugin_dast_plugin_skillberry_plugin_dast_get_router_locals_scan_request = skillberry_store_sdk.SkillberryPluginDastPluginSkillberryPluginDastGetRouterLocalsScanRequest() # SkillberryPluginDastPluginSkillberryPluginDastGetRouterLocalsScanRequest | 

    try:
        # Scan Endpoint
        api_response = api_instance.dast_scan_endpoint(skillberry_plugin_dast_plugin_skillberry_plugin_dast_get_router_locals_scan_request)
        print("The response of DastApi->dast_scan_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DastApi->dast_scan_endpoint: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **skillberry_plugin_dast_plugin_skillberry_plugin_dast_get_router_locals_scan_request** | [**SkillberryPluginDastPluginSkillberryPluginDastGetRouterLocalsScanRequest**](SkillberryPluginDastPluginSkillberryPluginDastGetRouterLocalsScanRequest.md)|  | 

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

# **dast_scan_status**
> object dast_scan_status(uuid)

Scan Status

Live progress of an in-flight scan for ``uuid`` (for the UI label).

Returns ``{state, current, total, entry_point, label}``. ``state`` is
``running`` | ``done`` | ``idle`` (no scan seen for this uuid).

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
    api_instance = skillberry_store_sdk.DastApi(api_client)
    uuid = 'uuid_example' # str | 

    try:
        # Scan Status
        api_response = api_instance.dast_scan_status(uuid)
        print("The response of DastApi->dast_scan_status:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DastApi->dast_scan_status: %s\n" % e)
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

