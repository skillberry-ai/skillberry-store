# skillberry_store_sdk.SkillsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_skill_skills_post**](SkillsApi.md#create_skill_skills_post) | **POST** /skills/ | Create Skill
[**delete_skill_skills_name_delete**](SkillsApi.md#delete_skill_skills_name_delete) | **DELETE** /skills/{name} | Delete Skill
[**export_anthropic_skill_skills_name_export_anthropic_get**](SkillsApi.md#export_anthropic_skill_skills_name_export_anthropic_get) | **GET** /skills/{name}/export-anthropic | Export Anthropic Skill
[**get_skill_skills_name_get**](SkillsApi.md#get_skill_skills_name_get) | **GET** /skills/{name} | Get Skill
[**import_anthropic_skill_skills_import_anthropic_post**](SkillsApi.md#import_anthropic_skill_skills_import_anthropic_post) | **POST** /skills/import-anthropic | Import Anthropic Skill
[**list_skills_skills_get**](SkillsApi.md#list_skills_skills_get) | **GET** /skills/ | List Skills
[**search_skills_search_skills_get**](SkillsApi.md#search_skills_search_skills_get) | **GET** /search/skills | Search Skills
[**update_skill_skills_name_put**](SkillsApi.md#update_skill_skills_name_put) | **PUT** /skills/{name} | Update Skill


# **create_skill_skills_post**
> object create_skill_skills_post(name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, tool_uuids=tool_uuids, snippet_uuids=snippet_uuids)

Create Skill

Create a new skill.  The form fields are dynamically generated from SkillSchema. Any changes to SkillSchema will automatically reflect in this API.  Args:     skill: The skill schema with tool_uuids and snippet_uuids (auto-generated from SkillSchema).            If uuid is not provided, it will be automatically generated.  Returns:     dict: Success message with the skill name and uuid.  Raises:     HTTPException: If skill already exists (409) or creation fails (500).

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.manifest_state import ManifestState
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
    api_instance = skillberry_store_sdk.SkillsApi(api_client)
    name = 'name_example' # str | Name (optional)
    uuid = 'uuid_example' # str | A UUID. If not provided, a UUID will be automatically generated. (optional)
    version = 'version_example' # str | Version (optional)
    description = 'description_example' # str | Short description (optional)
    state = skillberry_store_sdk.ManifestState() # ManifestState | Lifecycle state (optional)
    tags = ['tags_example'] # List[str] | List of tags for categorizing (optional)
    tool_uuids = ['tool_uuids_example'] # List[Optional[str]] | Ordered list of tool UUIDs that comprise this skill (optional)
    snippet_uuids = ['snippet_uuids_example'] # List[Optional[str]] | Ordered list of snippet UUIDs that comprise this skill (optional)

    try:
        # Create Skill
        api_response = api_instance.create_skill_skills_post(name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, tool_uuids=tool_uuids, snippet_uuids=snippet_uuids)
        print("The response of SkillsApi->create_skill_skills_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsApi->create_skill_skills_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**| Name | [optional] 
 **uuid** | **str**| A UUID. If not provided, a UUID will be automatically generated. | [optional] 
 **version** | **str**| Version | [optional] 
 **description** | **str**| Short description | [optional] 
 **state** | [**ManifestState**](.md)| Lifecycle state | [optional] 
 **tags** | [**List[str]**](str.md)| List of tags for categorizing | [optional] 
 **tool_uuids** | [**List[Optional[str]]**](str.md)| Ordered list of tool UUIDs that comprise this skill | [optional] 
 **snippet_uuids** | [**List[Optional[str]]**](str.md)| Ordered list of snippet UUIDs that comprise this skill | [optional] 

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

# **delete_skill_skills_name_delete**
> object delete_skill_skills_name_delete(name)

Delete Skill

Delete a skill by name.  Args:     name: The name of the skill to delete.  Returns:     dict: Success message.  Raises:     HTTPException: If skill not found (404) or deletion fails (500).

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
    api_instance = skillberry_store_sdk.SkillsApi(api_client)
    name = 'name_example' # str | 

    try:
        # Delete Skill
        api_response = api_instance.delete_skill_skills_name_delete(name)
        print("The response of SkillsApi->delete_skill_skills_name_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsApi->delete_skill_skills_name_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**|  | 

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

# **export_anthropic_skill_skills_name_export_anthropic_get**
> object export_anthropic_skill_skills_name_export_anthropic_get(name)

Export Anthropic Skill

Export a skill to Anthropic format as a ZIP file.  Args:     name: The name of the skill to export      Returns:     ZIP file with the skill in Anthropic format      Raises:     HTTPException: If skill not found or export fails

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
    api_instance = skillberry_store_sdk.SkillsApi(api_client)
    name = 'name_example' # str | 

    try:
        # Export Anthropic Skill
        api_response = api_instance.export_anthropic_skill_skills_name_export_anthropic_get(name)
        print("The response of SkillsApi->export_anthropic_skill_skills_name_export_anthropic_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsApi->export_anthropic_skill_skills_name_export_anthropic_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**|  | 

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

# **get_skill_skills_name_get**
> object get_skill_skills_name_get(name)

Get Skill

Get a specific skill by name with populated tool and snippet objects.  Args:     name: The name of the skill.  Returns:     dict: The skill object with full tool and snippet details.  Raises:     HTTPException: If skill not found (404) or retrieval fails (500).

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
    api_instance = skillberry_store_sdk.SkillsApi(api_client)
    name = 'name_example' # str | 

    try:
        # Get Skill
        api_response = api_instance.get_skill_skills_name_get(name)
        print("The response of SkillsApi->get_skill_skills_name_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsApi->get_skill_skills_name_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**|  | 

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

# **import_anthropic_skill_skills_import_anthropic_post**
> object import_anthropic_skill_skills_import_anthropic_post(source_type, github_url=github_url, zip_file=zip_file, folder_path=folder_path, snippet_mode=snippet_mode)

Import Anthropic Skill

Import an Anthropic skill from GitHub URL, ZIP file, or local folder.  Args:     source_type: 'url', 'zip', or 'folder'     github_url: GitHub repository URL (required if source_type='url')     zip_file: ZIP file upload (required if source_type='zip')     folder_path: Local folder path (required if source_type='folder')     snippet_mode: 'file' or 'paragraph' - how to import text files      Returns:     dict: Import result with created tools, snippets, and skill info      Raises:     HTTPException: If import fails

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
    api_instance = skillberry_store_sdk.SkillsApi(api_client)
    source_type = 'source_type_example' # str | 
    github_url = 'github_url_example' # str |  (optional)
    zip_file = None # bytearray |  (optional)
    folder_path = 'folder_path_example' # str |  (optional)
    snippet_mode = 'file' # str |  (optional) (default to 'file')

    try:
        # Import Anthropic Skill
        api_response = api_instance.import_anthropic_skill_skills_import_anthropic_post(source_type, github_url=github_url, zip_file=zip_file, folder_path=folder_path, snippet_mode=snippet_mode)
        print("The response of SkillsApi->import_anthropic_skill_skills_import_anthropic_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsApi->import_anthropic_skill_skills_import_anthropic_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **source_type** | **str**|  | 
 **github_url** | **str**|  | [optional] 
 **zip_file** | **bytearray**|  | [optional] 
 **folder_path** | **str**|  | [optional] 
 **snippet_mode** | **str**|  | [optional] [default to &#39;file&#39;]

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

# **list_skills_skills_get**
> object list_skills_skills_get()

List Skills

List all skills with populated tool and snippet objects.  Returns:     list: A list of all skill objects with full tool and snippet details.  Raises:     HTTPException: If listing fails (500).

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
    api_instance = skillberry_store_sdk.SkillsApi(api_client)

    try:
        # List Skills
        api_response = api_instance.list_skills_skills_get()
        print("The response of SkillsApi->list_skills_skills_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsApi->list_skills_skills_get: %s\n" % e)
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

# **search_skills_search_skills_get**
> object search_skills_search_skills_get(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)

Search Skills

Return a list of skills that are similar to the given search term.  Returns skills that are below the similarity threshold and match the filters.  Args:     search_term: Search term.     max_number_of_results: Number of results to return.     similarity_threshold: Threshold to be used.     manifest_filter: Manifest properties to filter (e.g., \"tags:python\", \"state:approved\").     lifecycle_state: State to filter by (e.g., LifecycleState.APPROVED).  Returns:     list: A list of matched skill names and similarity scores.

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.lifecycle_state import LifecycleState
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
    api_instance = skillberry_store_sdk.SkillsApi(api_client)
    search_term = 'search_term_example' # str | 
    max_number_of_results = 5 # int |  (optional) (default to 5)
    similarity_threshold = 1 # float |  (optional) (default to 1)
    manifest_filter = '.' # str |  (optional) (default to '.')
    lifecycle_state = skillberry_store_sdk.LifecycleState() # LifecycleState |  (optional)

    try:
        # Search Skills
        api_response = api_instance.search_skills_search_skills_get(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)
        print("The response of SkillsApi->search_skills_search_skills_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsApi->search_skills_search_skills_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **search_term** | **str**|  | 
 **max_number_of_results** | **int**|  | [optional] [default to 5]
 **similarity_threshold** | **float**|  | [optional] [default to 1]
 **manifest_filter** | **str**|  | [optional] [default to &#39;.&#39;]
 **lifecycle_state** | [**LifecycleState**](.md)|  | [optional] 

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

# **update_skill_skills_name_put**
> object update_skill_skills_name_put(name, skill_schema)

Update Skill

Update an existing skill.  Args:     name: The name of the skill to update.     skill: The updated skill schema.  Returns:     dict: Success message.  Raises:     HTTPException: If skill not found (404) or update fails (500).

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.skill_schema import SkillSchema
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
    api_instance = skillberry_store_sdk.SkillsApi(api_client)
    name = 'name_example' # str | 
    skill_schema = skillberry_store_sdk.SkillSchema() # SkillSchema | 

    try:
        # Update Skill
        api_response = api_instance.update_skill_skills_name_put(name, skill_schema)
        print("The response of SkillsApi->update_skill_skills_name_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsApi->update_skill_skills_name_put: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**|  | 
 **skill_schema** | [**SkillSchema**](SkillSchema.md)|  | 

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

