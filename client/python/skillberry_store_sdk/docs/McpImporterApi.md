# skillberry_store_sdk.McpImporterApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**mcp_importer_import_tools**](McpImporterApi.md#mcp_importer_import_tools) | **POST** /plugins/mcp-importer/import-tools | Import Tools


# **mcp_importer_import_tools**
> object mcp_importer_import_tools(skillberry_plugin_mcp_importer_plugin_skillberry_plugin_mcp_importer_get_router_locals_import_request)

Import Tools

Import all tools from the given MCP SSE server into the store.

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.skillberry_plugin_mcp_importer_plugin_skillberry_plugin_mcp_importer_get_router_locals_import_request import SkillberryPluginMcpImporterPluginSkillberryPluginMcpImporterGetRouterLocalsImportRequest
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
    api_instance = skillberry_store_sdk.McpImporterApi(api_client)
    skillberry_plugin_mcp_importer_plugin_skillberry_plugin_mcp_importer_get_router_locals_import_request = skillberry_store_sdk.SkillberryPluginMcpImporterPluginSkillberryPluginMcpImporterGetRouterLocalsImportRequest() # SkillberryPluginMcpImporterPluginSkillberryPluginMcpImporterGetRouterLocalsImportRequest | 

    try:
        # Import Tools
        api_response = api_instance.mcp_importer_import_tools(skillberry_plugin_mcp_importer_plugin_skillberry_plugin_mcp_importer_get_router_locals_import_request)
        print("The response of McpImporterApi->mcp_importer_import_tools:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling McpImporterApi->mcp_importer_import_tools: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **skillberry_plugin_mcp_importer_plugin_skillberry_plugin_mcp_importer_get_router_locals_import_request** | [**SkillberryPluginMcpImporterPluginSkillberryPluginMcpImporterGetRouterLocalsImportRequest**](SkillberryPluginMcpImporterPluginSkillberryPluginMcpImporterGetRouterLocalsImportRequest.md)|  | 

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

