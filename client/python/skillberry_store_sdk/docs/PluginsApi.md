# skillberry_store_sdk.PluginsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**anthropic_skill_generator_generate_skill_endpoint**](PluginsApi.md#anthropic_skill_generator_generate_skill_endpoint) | **POST** /plugins/anthropic-skill-generator/generate-skill | Generate Skill Endpoint
[**ask_runspace_cleanup_workspace**](PluginsApi.md#ask_runspace_cleanup_workspace) | **POST** /plugins/ask-runspace/cleanup/{job_id} | Cleanup Workspace
[**ask_runspace_presets**](PluginsApi.md#ask_runspace_presets) | **GET** /plugins/ask-runspace/presets | Presets
[**ask_runspace_run**](PluginsApi.md#ask_runspace_run) | **POST** /plugins/ask-runspace/run | Run
[**ask_runspace_status**](PluginsApi.md#ask_runspace_status) | **GET** /plugins/ask-runspace/status/{job_id} | Status
[**ask_runspace_upload_skills**](PluginsApi.md#ask_runspace_upload_skills) | **POST** /plugins/ask-runspace/upload-skills | Upload Skills
[**creator_create_snippet_endpoint**](PluginsApi.md#creator_create_snippet_endpoint) | **POST** /plugins/creator/create-snippet | Create Snippet Endpoint
[**dast_scan_endpoint**](PluginsApi.md#dast_scan_endpoint) | **POST** /plugins/dast/scan | Scan Endpoint
[**dast_scan_status**](PluginsApi.md#dast_scan_status) | **GET** /plugins/dast/scan-status | Scan Status
[**dedupe_delete_decision**](PluginsApi.md#dedupe_delete_decision) | **POST** /plugins/dedupe/decisions/{uuid}/delete | Delete Decision
[**dedupe_keep_decision**](PluginsApi.md#dedupe_keep_decision) | **POST** /plugins/dedupe/decisions/{uuid}/keep | Keep Decision
[**dedupe_list_decisions**](PluginsApi.md#dedupe_list_decisions) | **GET** /plugins/dedupe/decisions | List Decisions
[**dependency_tracker_scan_endpoint**](PluginsApi.md#dependency_tracker_scan_endpoint) | **POST** /plugins/dependency_tracker/resolve-dependencies | Scan Endpoint
[**doc_generator_generate_endpoint**](PluginsApi.md#doc_generator_generate_endpoint) | **POST** /plugins/doc_generator/generate | Generate Endpoint
[**doc_generator_refresh_endpoint**](PluginsApi.md#doc_generator_refresh_endpoint) | **POST** /plugins/doc_generator/refresh | Refresh Endpoint
[**evaluator_evaluate_endpoint**](PluginsApi.md#evaluator_evaluate_endpoint) | **POST** /plugins/evaluator/evaluate | Evaluate Endpoint
[**get_plugin_info**](PluginsApi.md#get_plugin_info) | **GET** /plugins/{plugin_name} | Get plugin information
[**list_plugins**](PluginsApi.md#list_plugins) | **GET** /plugins/ | List all plugins
[**mcp_importer_import_tools**](PluginsApi.md#mcp_importer_import_tools) | **POST** /plugins/mcp-importer/import-tools | Import Tools
[**provenance_check_endpoint**](PluginsApi.md#provenance_check_endpoint) | **POST** /plugins/provenance/check | Check Endpoint
[**provenance_recheck_endpoint**](PluginsApi.md#provenance_recheck_endpoint) | **POST** /plugins/provenance/recheck | Recheck Endpoint
[**sast_fix_endpoint**](PluginsApi.md#sast_fix_endpoint) | **POST** /plugins/sast/fix | Fix Endpoint
[**sast_scan_endpoint**](PluginsApi.md#sast_scan_endpoint) | **POST** /plugins/sast/scan | Scan Endpoint
[**security_evaluate_endpoint**](PluginsApi.md#security_evaluate_endpoint) | **POST** /plugins/security/evaluate | Evaluate Endpoint
[**simulate_active**](PluginsApi.md#simulate_active) | **GET** /plugins/simulate/active/{skill_uuid} | Active
[**simulate_simulate**](PluginsApi.md#simulate_simulate) | **POST** /plugins/simulate/simulate | Simulate
[**simulate_simulate_status**](PluginsApi.md#simulate_simulate_status) | **GET** /plugins/simulate/status/{job_id} | Simulate Status
[**simulate_teardown**](PluginsApi.md#simulate_teardown) | **POST** /plugins/simulate/teardown | Teardown
[**simulate_toggle**](PluginsApi.md#simulate_toggle) | **POST** /plugins/simulate/toggle | Toggle
[**skill_optimizer_optimize_skill_endpoint**](PluginsApi.md#skill_optimizer_optimize_skill_endpoint) | **POST** /plugins/skill-optimizer/optimize-skill | Optimize Skill Endpoint
[**skillssh_importer_import_skills**](PluginsApi.md#skillssh_importer_import_skills) | **POST** /plugins/skillssh-importer/import | Import Skills
[**skillssh_importer_search**](PluginsApi.md#skillssh_importer_search) | **POST** /plugins/skillssh-importer/search | Search
[**skillssh_importer_skill_description**](PluginsApi.md#skillssh_importer_skill_description) | **GET** /plugins/skillssh-importer/skill-description/{skill_id} | Skill Description
[**update_plugin**](PluginsApi.md#update_plugin) | **PATCH** /plugins/{plugin_name} | Enable or disable a plugin


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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    generate_skill_request = skillberry_store_sdk.GenerateSkillRequest() # GenerateSkillRequest | 

    try:
        # Generate Skill Endpoint
        api_response = api_instance.anthropic_skill_generator_generate_skill_endpoint(generate_skill_request)
        print("The response of PluginsApi->anthropic_skill_generator_generate_skill_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->anthropic_skill_generator_generate_skill_endpoint: %s\n" % e)
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

# **ask_runspace_cleanup_workspace**
> object ask_runspace_cleanup_workspace(job_id)

Cleanup Workspace

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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    job_id = 'job_id_example' # str | 

    try:
        # Cleanup Workspace
        api_response = api_instance.ask_runspace_cleanup_workspace(job_id)
        print("The response of PluginsApi->ask_runspace_cleanup_workspace:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->ask_runspace_cleanup_workspace: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **job_id** | **str**|  | 

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

# **ask_runspace_presets**
> object ask_runspace_presets()

Presets

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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)

    try:
        # Presets
        api_response = api_instance.ask_runspace_presets()
        print("The response of PluginsApi->ask_runspace_presets:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->ask_runspace_presets: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

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

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **ask_runspace_run**
> object ask_runspace_run(run_request)

Run

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.run_request import RunRequest
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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    run_request = skillberry_store_sdk.RunRequest() # RunRequest | 

    try:
        # Run
        api_response = api_instance.ask_runspace_run(run_request)
        print("The response of PluginsApi->ask_runspace_run:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->ask_runspace_run: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **run_request** | [**RunRequest**](RunRequest.md)|  | 

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

# **ask_runspace_status**
> object ask_runspace_status(job_id)

Status

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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    job_id = 'job_id_example' # str | 

    try:
        # Status
        api_response = api_instance.ask_runspace_status(job_id)
        print("The response of PluginsApi->ask_runspace_status:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->ask_runspace_status: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **job_id** | **str**|  | 

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

# **ask_runspace_upload_skills**
> object ask_runspace_upload_skills(files)

Upload Skills

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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    files = ['files_example'] # List[str] | 

    try:
        # Upload Skills
        api_response = api_instance.ask_runspace_upload_skills(files)
        print("The response of PluginsApi->ask_runspace_upload_skills:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->ask_runspace_upload_skills: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **files** | [**List[str]**](str.md)|  | 

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    create_snippet_request = skillberry_store_sdk.CreateSnippetRequest() # CreateSnippetRequest | 

    try:
        # Create Snippet Endpoint
        api_response = api_instance.creator_create_snippet_endpoint(create_snippet_request)
        print("The response of PluginsApi->creator_create_snippet_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->creator_create_snippet_endpoint: %s\n" % e)
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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    skillberry_plugin_dast_plugin_skillberry_plugin_dast_get_router_locals_scan_request = skillberry_store_sdk.SkillberryPluginDastPluginSkillberryPluginDastGetRouterLocalsScanRequest() # SkillberryPluginDastPluginSkillberryPluginDastGetRouterLocalsScanRequest | 

    try:
        # Scan Endpoint
        api_response = api_instance.dast_scan_endpoint(skillberry_plugin_dast_plugin_skillberry_plugin_dast_get_router_locals_scan_request)
        print("The response of PluginsApi->dast_scan_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->dast_scan_endpoint: %s\n" % e)
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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    uuid = 'uuid_example' # str | 

    try:
        # Scan Status
        api_response = api_instance.dast_scan_status(uuid)
        print("The response of PluginsApi->dast_scan_status:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->dast_scan_status: %s\n" % e)
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

# **dedupe_delete_decision**
> object dedupe_delete_decision(uuid)

Delete Decision

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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    uuid = 'uuid_example' # str | 

    try:
        # Delete Decision
        api_response = api_instance.dedupe_delete_decision(uuid)
        print("The response of PluginsApi->dedupe_delete_decision:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->dedupe_delete_decision: %s\n" % e)
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

# **dedupe_keep_decision**
> object dedupe_keep_decision(uuid)

Keep Decision

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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    uuid = 'uuid_example' # str | 

    try:
        # Keep Decision
        api_response = api_instance.dedupe_keep_decision(uuid)
        print("The response of PluginsApi->dedupe_keep_decision:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->dedupe_keep_decision: %s\n" % e)
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

# **dedupe_list_decisions**
> object dedupe_list_decisions()

List Decisions

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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)

    try:
        # List Decisions
        api_response = api_instance.dedupe_list_decisions()
        print("The response of PluginsApi->dedupe_list_decisions:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->dedupe_list_decisions: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

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

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    skillberry_plugin_dependency_tracker_plugin_skillberry_plugin_dependency_tracker_get_router_locals_scan_request = skillberry_store_sdk.SkillberryPluginDependencyTrackerPluginSkillberryPluginDependencyTrackerGetRouterLocalsScanRequest() # SkillberryPluginDependencyTrackerPluginSkillberryPluginDependencyTrackerGetRouterLocalsScanRequest | 

    try:
        # Scan Endpoint
        api_response = api_instance.dependency_tracker_scan_endpoint(skillberry_plugin_dependency_tracker_plugin_skillberry_plugin_dependency_tracker_get_router_locals_scan_request)
        print("The response of PluginsApi->dependency_tracker_scan_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->dependency_tracker_scan_endpoint: %s\n" % e)
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

# **doc_generator_generate_endpoint**
> object doc_generator_generate_endpoint(generate_request)

Generate Endpoint

Generate/enrich docs for an object (proposed unless apply=True).

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.generate_request import GenerateRequest
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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    generate_request = skillberry_store_sdk.GenerateRequest() # GenerateRequest | 

    try:
        # Generate Endpoint
        api_response = api_instance.doc_generator_generate_endpoint(generate_request)
        print("The response of PluginsApi->doc_generator_generate_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->doc_generator_generate_endpoint: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **generate_request** | [**GenerateRequest**](GenerateRequest.md)|  | 

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

# **doc_generator_refresh_endpoint**
> object doc_generator_refresh_endpoint(refresh_request)

Refresh Endpoint

Detect drift and propose refreshed docs for an object.

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.refresh_request import RefreshRequest
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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    refresh_request = skillberry_store_sdk.RefreshRequest() # RefreshRequest | 

    try:
        # Refresh Endpoint
        api_response = api_instance.doc_generator_refresh_endpoint(refresh_request)
        print("The response of PluginsApi->doc_generator_refresh_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->doc_generator_refresh_endpoint: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **refresh_request** | [**RefreshRequest**](RefreshRequest.md)|  | 

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

# **evaluator_evaluate_endpoint**
> object evaluator_evaluate_endpoint(evaluate_request)

Evaluate Endpoint

Evaluate a store object and store quality/performance scores.

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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    evaluate_request = skillberry_store_sdk.EvaluateRequest() # EvaluateRequest | 

    try:
        # Evaluate Endpoint
        api_response = api_instance.evaluator_evaluate_endpoint(evaluate_request)
        print("The response of PluginsApi->evaluator_evaluate_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->evaluator_evaluate_endpoint: %s\n" % e)
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

# **get_plugin_info**
> Dict[str, object] get_plugin_info(plugin_name)

Get plugin information

Get detailed information about a specific plugin.

Args:
    plugin_name: Name/slug of the plugin

Returns:
    Plugin info dictionary with metadata and status

Raises:
    HTTPException: 404 if plugin not found

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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    plugin_name = 'plugin_name_example' # str | 

    try:
        # Get plugin information
        api_response = api_instance.get_plugin_info(plugin_name)
        print("The response of PluginsApi->get_plugin_info:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->get_plugin_info: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **plugin_name** | **str**|  | 

### Return type

**Dict[str, object]**

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

# **list_plugins**
> List[Optional[Dict[str, object]]] list_plugins()

List all plugins

List all discovered plugins with their metadata and status.

Returns:
    List of plugin info dictionaries containing:
    - name: Display name
    - description: What the plugin does
    - version: Plugin version
    - plugin_type: Type of plugin (creator, evaluator, optimizer)
    - author: Plugin author (optional)
    - homepage: Plugin homepage URL (optional)
    - enabled: Whether plugin is enabled
    - has_router: Whether plugin provides API routes
    - has_cli: Whether plugin provides CLI commands
    - has_ui: Whether plugin provides UI configuration

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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)

    try:
        # List all plugins
        api_response = api_instance.list_plugins()
        print("The response of PluginsApi->list_plugins:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->list_plugins: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**List[Optional[Dict[str, object]]]**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    skillberry_plugin_mcp_importer_plugin_skillberry_plugin_mcp_importer_get_router_locals_import_request = skillberry_store_sdk.SkillberryPluginMcpImporterPluginSkillberryPluginMcpImporterGetRouterLocalsImportRequest() # SkillberryPluginMcpImporterPluginSkillberryPluginMcpImporterGetRouterLocalsImportRequest | 

    try:
        # Import Tools
        api_response = api_instance.mcp_importer_import_tools(skillberry_plugin_mcp_importer_plugin_skillberry_plugin_mcp_importer_get_router_locals_import_request)
        print("The response of PluginsApi->mcp_importer_import_tools:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->mcp_importer_import_tools: %s\n" % e)
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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    check_request = skillberry_store_sdk.CheckRequest() # CheckRequest | 

    try:
        # Check Endpoint
        api_response = api_instance.provenance_check_endpoint(check_request)
        print("The response of PluginsApi->provenance_check_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->provenance_check_endpoint: %s\n" % e)
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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    recheck_request = skillberry_store_sdk.RecheckRequest() # RecheckRequest | 

    try:
        # Recheck Endpoint
        api_response = api_instance.provenance_recheck_endpoint(recheck_request)
        print("The response of PluginsApi->provenance_recheck_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->provenance_recheck_endpoint: %s\n" % e)
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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    fix_request = skillberry_store_sdk.FixRequest() # FixRequest | 

    try:
        # Fix Endpoint
        api_response = api_instance.sast_fix_endpoint(fix_request)
        print("The response of PluginsApi->sast_fix_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->sast_fix_endpoint: %s\n" % e)
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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    skillberry_plugin_sast_plugin_skillberry_plugin_sast_get_router_locals_scan_request = skillberry_store_sdk.SkillberryPluginSastPluginSkillberryPluginSastGetRouterLocalsScanRequest() # SkillberryPluginSastPluginSkillberryPluginSastGetRouterLocalsScanRequest | 

    try:
        # Scan Endpoint
        api_response = api_instance.sast_scan_endpoint(skillberry_plugin_sast_plugin_skillberry_plugin_sast_get_router_locals_scan_request)
        print("The response of PluginsApi->sast_scan_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->sast_scan_endpoint: %s\n" % e)
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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    evaluate_request = skillberry_store_sdk.EvaluateRequest() # EvaluateRequest | 

    try:
        # Evaluate Endpoint
        api_response = api_instance.security_evaluate_endpoint(evaluate_request)
        print("The response of PluginsApi->security_evaluate_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->security_evaluate_endpoint: %s\n" % e)
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

# **simulate_active**
> object simulate_active(skill_uuid)

Active

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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    skill_uuid = 'skill_uuid_example' # str | 

    try:
        # Active
        api_response = api_instance.simulate_active(skill_uuid)
        print("The response of PluginsApi->simulate_active:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->simulate_active: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **skill_uuid** | **str**|  | 

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

# **simulate_simulate**
> object simulate_simulate(simulate_request)

Simulate

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.simulate_request import SimulateRequest
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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    simulate_request = skillberry_store_sdk.SimulateRequest() # SimulateRequest | 

    try:
        # Simulate
        api_response = api_instance.simulate_simulate(simulate_request)
        print("The response of PluginsApi->simulate_simulate:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->simulate_simulate: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **simulate_request** | [**SimulateRequest**](SimulateRequest.md)|  | 

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

# **simulate_simulate_status**
> object simulate_simulate_status(job_id)

Simulate Status

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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    job_id = 'job_id_example' # str | 

    try:
        # Simulate Status
        api_response = api_instance.simulate_simulate_status(job_id)
        print("The response of PluginsApi->simulate_simulate_status:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->simulate_simulate_status: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **job_id** | **str**|  | 

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

# **simulate_teardown**
> object simulate_teardown(skill_request)

Teardown

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.skill_request import SkillRequest
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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    skill_request = skillberry_store_sdk.SkillRequest() # SkillRequest | 

    try:
        # Teardown
        api_response = api_instance.simulate_teardown(skill_request)
        print("The response of PluginsApi->simulate_teardown:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->simulate_teardown: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **skill_request** | [**SkillRequest**](SkillRequest.md)|  | 

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

# **simulate_toggle**
> object simulate_toggle(skill_request)

Toggle

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.skill_request import SkillRequest
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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    skill_request = skillberry_store_sdk.SkillRequest() # SkillRequest | 

    try:
        # Toggle
        api_response = api_instance.simulate_toggle(skill_request)
        print("The response of PluginsApi->simulate_toggle:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->simulate_toggle: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **skill_request** | [**SkillRequest**](SkillRequest.md)|  | 

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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    optimize_skill_request = skillberry_store_sdk.OptimizeSkillRequest() # OptimizeSkillRequest | 

    try:
        # Optimize Skill Endpoint
        api_response = api_instance.skill_optimizer_optimize_skill_endpoint(optimize_skill_request)
        print("The response of PluginsApi->skill_optimizer_optimize_skill_endpoint:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->skill_optimizer_optimize_skill_endpoint: %s\n" % e)
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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    skillberry_plugin_skillssh_importer_plugin_skillberry_plugin_skills_sh_importer_get_router_locals_import_request = skillberry_store_sdk.SkillberryPluginSkillsshImporterPluginSkillberryPluginSkillsShImporterGetRouterLocalsImportRequest() # SkillberryPluginSkillsshImporterPluginSkillberryPluginSkillsShImporterGetRouterLocalsImportRequest | 

    try:
        # Import Skills
        api_response = api_instance.skillssh_importer_import_skills(skillberry_plugin_skillssh_importer_plugin_skillberry_plugin_skills_sh_importer_get_router_locals_import_request)
        print("The response of PluginsApi->skillssh_importer_import_skills:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->skillssh_importer_import_skills: %s\n" % e)
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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    search_request = skillberry_store_sdk.SearchRequest() # SearchRequest | 

    try:
        # Search
        api_response = api_instance.skillssh_importer_search(search_request)
        print("The response of PluginsApi->skillssh_importer_search:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->skillssh_importer_search: %s\n" % e)
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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    skill_id = 'skill_id_example' # str | 

    try:
        # Skill Description
        api_response = api_instance.skillssh_importer_skill_description(skill_id)
        print("The response of PluginsApi->skillssh_importer_skill_description:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->skillssh_importer_skill_description: %s\n" % e)
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

# **update_plugin**
> Dict[str, object] update_plugin(plugin_name, plugin_enabled_update)

Enable or disable a plugin

Toggle a plugin's admin enablement (global, persisted, live).

Args:
    plugin_name: Name/slug of the plugin
    body: {"enabled": bool}

Returns:
    The updated plugin info dictionary.

Raises:
    HTTPException: 404 if plugin not found

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.plugin_enabled_update import PluginEnabledUpdate
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
    api_instance = skillberry_store_sdk.PluginsApi(api_client)
    plugin_name = 'plugin_name_example' # str | 
    plugin_enabled_update = skillberry_store_sdk.PluginEnabledUpdate() # PluginEnabledUpdate | 

    try:
        # Enable or disable a plugin
        api_response = api_instance.update_plugin(plugin_name, plugin_enabled_update)
        print("The response of PluginsApi->update_plugin:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PluginsApi->update_plugin: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **plugin_name** | **str**|  | 
 **plugin_enabled_update** | [**PluginEnabledUpdate**](PluginEnabledUpdate.md)|  | 

### Return type

**Dict[str, object]**

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

