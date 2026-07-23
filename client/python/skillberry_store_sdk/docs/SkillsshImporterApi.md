# skillberry_store_sdk.SkillsshImporterApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**skillssh_importer_import_skills**](SkillsshImporterApi.md#skillssh_importer_import_skills) | **POST** /plugins/skillssh-importer/import | Import Skills
[**skillssh_importer_search**](SkillsshImporterApi.md#skillssh_importer_search) | **POST** /plugins/skillssh-importer/search | Search
[**skillssh_importer_skill_description**](SkillsshImporterApi.md#skillssh_importer_skill_description) | **GET** /plugins/skillssh-importer/skill-description/{skill_id} | Skill Description


# **skillssh_importer_import_skills**
> object skillssh_importer_import_skills(skillberry_plugin_skillssh_importer_plugin_skillberry_plugin_skills_sh_importer_get_router_locals_import_request)

Import Skills

Import one or more skills from skills.sh into the store.

For each skill ID the endpoint:
1. Fetches the skill's files (including SKILL.md) from skills.sh.
2. Optionally fetches security audit results.
3. Runs the files through the Anthropic skill importer pipeline.
4. Persists the resulting tools / snippets / skill in the store.
5. Attaches tags: ``skills.sh``, ``installs:<bucket>``,
   ``audit:<provider>:<status>``, ``audit:<overall>``.

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.skillberry_plugin_skillssh_importer_plugin_skillberry_plugin_skills_sh_importer_get_router_locals_import_request import SkillberryPluginSkillsshImporterPluginSkillberryPluginSkillsShImporterGetRouterLocalsImportRequest
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
    api_instance = skillberry_store_sdk.SkillsshImporterApi(api_client)
    skillberry_plugin_skillssh_importer_plugin_skillberry_plugin_skills_sh_importer_get_router_locals_import_request = skillberry_store_sdk.SkillberryPluginSkillsshImporterPluginSkillberryPluginSkillsShImporterGetRouterLocalsImportRequest() # SkillberryPluginSkillsshImporterPluginSkillberryPluginSkillsShImporterGetRouterLocalsImportRequest | 

    try:
        # Import Skills
        api_response = api_instance.skillssh_importer_import_skills(skillberry_plugin_skillssh_importer_plugin_skillberry_plugin_skills_sh_importer_get_router_locals_import_request)
        print("The response of SkillsshImporterApi->skillssh_importer_import_skills:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsshImporterApi->skillssh_importer_import_skills: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **skillberry_plugin_skillssh_importer_plugin_skillberry_plugin_skills_sh_importer_get_router_locals_import_request** | [**SkillberryPluginSkillsshImporterPluginSkillberryPluginSkillsShImporterGetRouterLocalsImportRequest**](SkillberryPluginSkillsshImporterPluginSkillberryPluginSkillsShImporterGetRouterLocalsImportRequest.md)|  | 

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

# **skillssh_importer_search**
> object skillssh_importer_search(search_request)

Search

Search the skills.sh directory. Returns up to ``limit`` skill entries.

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.search_request import SearchRequest
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
    api_instance = skillberry_store_sdk.SkillsshImporterApi(api_client)
    search_request = skillberry_store_sdk.SearchRequest() # SearchRequest | 

    try:
        # Search
        api_response = api_instance.skillssh_importer_search(search_request)
        print("The response of SkillsshImporterApi->skillssh_importer_search:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsshImporterApi->skillssh_importer_search: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **search_request** | [**SearchRequest**](SearchRequest.md)|  | 

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

# **skillssh_importer_skill_description**
> object skillssh_importer_skill_description(skill_id)

Skill Description

Return the description extracted from a skill's SKILL.md.

Called lazily by the UI table as rows scroll into view — one
request per skill so the search response stays fast.

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
    api_instance = skillberry_store_sdk.SkillsshImporterApi(api_client)
    skill_id = 'skill_id_example' # str | 

    try:
        # Skill Description
        api_response = api_instance.skillssh_importer_skill_description(skill_id)
        print("The response of SkillsshImporterApi->skillssh_importer_skill_description:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsshImporterApi->skillssh_importer_skill_description: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **skill_id** | **str**|  | 

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

