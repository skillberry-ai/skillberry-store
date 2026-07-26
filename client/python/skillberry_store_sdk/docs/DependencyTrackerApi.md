# skillberry_store_sdk.DependencyTrackerApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**dependency_tracker_scan_endpoint**](DependencyTrackerApi.md#dependency_tracker_scan_endpoint) | **POST** /plugins/dependency_tracker/resolve-dependencies | Scan Endpoint


# **dependency_tracker_scan_endpoint**
> object dependency_tracker_scan_endpoint(skillberry_plugin_dependency_tracker_plugin_skillberry_plugin_dependency_tracker_get_router_locals_scan_request)

Scan Endpoint

Resolve & record external Python dependencies for an object.

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.skillberry_plugin_dependency_tracker_plugin_skillberry_plugin_dependency_tracker_get_router_locals_scan_request import SkillberryPluginDependencyTrackerPluginSkillberryPluginDependencyTrackerGetRouterLocalsScanRequest
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
    api_instance = skillberry_store_sdk.DependencyTrackerApi(api_client)
    skillberry_plugin_dependency_tracker_plugin_skillberry_plugin_dependency_tracker_get_router_locals_scan_request = skillberry_store_sdk.SkillberryPluginDependencyTrackerPluginSkillberryPluginDependencyTrackerGetRouterLocalsScanRequest() # SkillberryPluginDependencyTrackerPluginSkillberryPluginDependencyTrackerGetRouterLocalsScanRequest | 

    try:
        # Scan Endpoint
        api_response = api_instance.dependency_tracker_scan_endpoint(skillberry_plugin_dependency_tracker_plugin_skillberry_plugin_dependency_tracker_get_router_locals_scan_request)
        print("The response of DependencyTrackerApi->dependency_tracker_scan_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DependencyTrackerApi->dependency_tracker_scan_endpoint: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **skillberry_plugin_dependency_tracker_plugin_skillberry_plugin_dependency_tracker_get_router_locals_scan_request** | [**SkillberryPluginDependencyTrackerPluginSkillberryPluginDependencyTrackerGetRouterLocalsScanRequest**](SkillberryPluginDependencyTrackerPluginSkillberryPluginDependencyTrackerGetRouterLocalsScanRequest.md)|  | 

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

