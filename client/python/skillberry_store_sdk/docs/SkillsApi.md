# skillberry_store_sdk.SkillsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_skill**](SkillsApi.md#create_skill) | **POST** /skills/ | Create Skill
[**delete_skill**](SkillsApi.md#delete_skill) | **DELETE** /skills/{uuid_or_name} | Delete Skill
[**detect_anthropic_skills**](SkillsApi.md#detect_anthropic_skills) | **POST** /skills/detect-anthropic-skills | Detect Anthropic Skills
[**export_anthropic_skill**](SkillsApi.md#export_anthropic_skill) | **GET** /skills/{uuid_or_name}/export-anthropic | Export Anthropic Skill
[**get_skill**](SkillsApi.md#get_skill) | **GET** /skills/{uuid_or_name} | Get Skill
[**import_anthropic_skill**](SkillsApi.md#import_anthropic_skill) | **POST** /skills/import-anthropic | Import Anthropic Skill
[**list_skills**](SkillsApi.md#list_skills) | **GET** /skills/ | List Skills
[**search_skills**](SkillsApi.md#search_skills) | **GET** /search/skills | Search Skills
[**skill_facets**](SkillsApi.md#skill_facets) | **GET** /facets/skills | Skill Facets
[**update_skill**](SkillsApi.md#update_skill) | **PUT** /skills/{uuid_or_name} | Update Skill


# **create_skill**
> object create_skill(name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, tool_uuids=tool_uuids, snippet_uuids=snippet_uuids)

Create Skill

Create a new skill in the store.

Creates a skill manifest that references tools and snippets by their UUIDs.
Skills are high-level compositions that group related tools and snippets.

Args:
    skill: Skill metadata conforming to SkillSchema (name, description, tool_uuids, snippet_uuids, etc.).

Returns:
    dict: Success message with skill name and UUID.

Raises:
    HTTPException: 409 if skill already exists, 500 for other errors.

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
    name = 'name_example' # str | Name (optional)
    uuid = 'uuid_example' # str | A UUID. If not provided, a UUID will be automatically generated. (optional)
    version = 'version_example' # str | Version (optional)
    description = 'description_example' # str | Short description (optional)
    state = skillberry_store_sdk.ManifestState() # ManifestState | Lifecycle state (optional)
    tags = ['tags_example'] # List[str] | List of tags for categorizing (optional)
    extra = None # Dict[str, object] | Optional dictionary for additional flexible information (optional)
    parent = 'parent_example' # str | UUID of the parent object (previous version with same name) (optional)
    created_at = 'created_at_example' # str | ISO 8601 timestamp when created (optional)
    modified_at = 'modified_at_example' # str | ISO 8601 timestamp when last modified (optional)
    tool_uuids = ['tool_uuids_example'] # List[Optional[str]] | Ordered list of tool UUIDs that comprise this skill (optional)
    snippet_uuids = ['snippet_uuids_example'] # List[Optional[str]] | Ordered list of snippet UUIDs that comprise this skill (optional)

    try:
        # Create Skill
        api_response = api_instance.create_skill(name=name, uuid=uuid, version=version, description=description, state=state, tags=tags, extra=extra, parent=parent, created_at=created_at, modified_at=modified_at, tool_uuids=tool_uuids, snippet_uuids=snippet_uuids)
        print("The response of SkillsApi->create_skill:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsApi->create_skill: %s\n" % e)
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
 **extra** | [**Dict[str, object]**](object.md)| Optional dictionary for additional flexible information | [optional] 
 **parent** | **str**| UUID of the parent object (previous version with same name) | [optional] 
 **created_at** | **str**| ISO 8601 timestamp when created | [optional] 
 **modified_at** | **str**| ISO 8601 timestamp when last modified | [optional] 
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

# **delete_skill**
> object delete_skill(uuid_or_name, delete_tools=delete_tools, delete_snippets=delete_snippets)

Delete Skill

Delete a skill from the store with optional cascade deletion.

Removes a skill and optionally its associated tools and snippets if they
are not referenced by other skills. This operation triggers a content
deletion event for plugin processing.

Args:
    uuid_or_name: The UUID or name of the skill to delete.
    delete_tools: If True, delete tools that are not shared with other skills (default: False).
    delete_snippets: If True, delete snippets that are not shared with other skills (default: False).

Returns:
    dict: Success message with lists of deleted tools and snippets.

Raises:
    HTTPException: 404 if skill not found, 500 for other errors.

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
    uuid_or_name = 'uuid_or_name_example' # str | 
    delete_tools = False # bool | Delete tools not shared with other skills (optional) (default to False)
    delete_snippets = False # bool | Delete snippets not shared with other skills (optional) (default to False)

    try:
        # Delete Skill
        api_response = api_instance.delete_skill(uuid_or_name, delete_tools=delete_tools, delete_snippets=delete_snippets)
        print("The response of SkillsApi->delete_skill:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsApi->delete_skill: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uuid_or_name** | **str**|  | 
 **delete_tools** | **bool**| Delete tools not shared with other skills | [optional] [default to False]
 **delete_snippets** | **bool**| Delete snippets not shared with other skills | [optional] [default to False]

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

# **detect_anthropic_skills**
> object detect_anthropic_skills(source_type, x_endpoint_token=x_endpoint_token, github_url=github_url, folder_path=folder_path, anonymous=anonymous, prewarm=prewarm)

Detect Anthropic Skills

Detect child skill directories in a parent directory.

This endpoint scans a parent directory (from GitHub URL or local folder)
and returns a list of subdirectories that contain SKILL.md files.

Args:
    source_type: 'url' or 'folder'
    github_url: GitHub repository URL (required if source_type='url')
    folder_path: Local folder path (required if source_type='folder')
    prewarm: When true and ``source_type='url'``, spawn a best-effort
        background clone of the source repo into the local import
        cache while this handler is doing its GitHub API work. Any
        subsequent ``/skills/import-anthropic`` calls for skills
        under the same repo then hit a warm cache. Non-blocking:
        does not affect this response's latency or error behavior.

Returns:
    dict: List of skill paths relative to the parent directory

Raises:
    HTTPException: If detection fails

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
    x_endpoint_token = 'x_endpoint_token_example' # str |  (optional)
    github_url = 'github_url_example' # str |  (optional)
    folder_path = 'folder_path_example' # str |  (optional)
    anonymous = True # bool |  (optional) (default to True)
    prewarm = False # bool |  (optional) (default to False)

    try:
        # Detect Anthropic Skills
        api_response = api_instance.detect_anthropic_skills(source_type, x_endpoint_token=x_endpoint_token, github_url=github_url, folder_path=folder_path, anonymous=anonymous, prewarm=prewarm)
        print("The response of SkillsApi->detect_anthropic_skills:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsApi->detect_anthropic_skills: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **source_type** | **str**|  | 
 **x_endpoint_token** | **str**|  | [optional] 
 **github_url** | **str**|  | [optional] 
 **folder_path** | **str**|  | [optional] 
 **anonymous** | **bool**|  | [optional] [default to True]
 **prewarm** | **bool**|  | [optional] [default to False]

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/x-www-form-urlencoded
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **export_anthropic_skill**
> object export_anthropic_skill(uuid_or_name)

Export Anthropic Skill

Export a skill to Anthropic format as a ZIP file.

Args:
    uuid_or_name: The UUID or name of the skill to export

Returns:
    ZIP file with the skill in Anthropic format

Raises:
    HTTPException: If skill not found or export fails

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
    uuid_or_name = 'uuid_or_name_example' # str | 

    try:
        # Export Anthropic Skill
        api_response = api_instance.export_anthropic_skill(uuid_or_name)
        print("The response of SkillsApi->export_anthropic_skill:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsApi->export_anthropic_skill: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uuid_or_name** | **str**|  | 

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

# **get_skill**
> object get_skill(uuid_or_name, fields=fields)

Get Skill

Get metadata for a specific skill by UUID or name.

Retrieves the manifest/metadata for a skill identified by either
its UUID or its unique name.

Args:
    uuid_or_name: The UUID or name of the skill to retrieve.
    fields: Optional field-selection spec (see query-param description).

Returns:
    dict: Skill metadata (subset when ``fields`` narrows the
        field selection). When ``fields`` resolves to a preset
        that tags ``_populate``, ``tools`` / ``snippets`` are
        inlined.

Raises:
    HTTPException: 400 if ``fields`` is invalid, 404 if skill
        not found, 505 if referenced resources are invalid,
        500 for other errors.

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
    uuid_or_name = 'uuid_or_name_example' # str | 
    fields = 'fields_example' # str | Field selection. 'minimal' returns uuid only. Omit or 'narrow' for the UI listing set (default; tool_uuids and snippet_uuids only, no inlining). 'wide' returns every persisted manifest field. 'full' returns the complete object with inlined ``tools`` / ``snippets`` populated. Or supply a comma-separated allowlist. (optional)

    try:
        # Get Skill
        api_response = api_instance.get_skill(uuid_or_name, fields=fields)
        print("The response of SkillsApi->get_skill:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsApi->get_skill: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uuid_or_name** | **str**|  | 
 **fields** | **str**| Field selection. &#39;minimal&#39; returns uuid only. Omit or &#39;narrow&#39; for the UI listing set (default; tool_uuids and snippet_uuids only, no inlining). &#39;wide&#39; returns every persisted manifest field. &#39;full&#39; returns the complete object with inlined &#x60;&#x60;tools&#x60;&#x60; / &#x60;&#x60;snippets&#x60;&#x60; populated. Or supply a comma-separated allowlist. | [optional] 

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

# **import_anthropic_skill**
> object import_anthropic_skill(source_type, x_endpoint_token=x_endpoint_token, github_url=github_url, zip_file=zip_file, folder_path=folder_path, snippet_mode=snippet_mode, treat_all_as_documents=treat_all_as_documents, tags=tags, anonymous=anonymous)

Import Anthropic Skill

Import an Anthropic skill from GitHub URL, ZIP file, or local folder.

Args:
    source_type: 'url', 'zip', or 'folder'
    github_url: GitHub repository URL (required if source_type='url')
    zip_file: ZIP file upload (required if source_type='zip')
    folder_path: Local folder path (required if source_type='folder')
    snippet_mode: 'file' or 'paragraph' - how to import text files
    tags: List of additional tags to add to all imported objects (skills, tools, snippets)

Returns:
    dict: Import result with created tools, snippets, and skill info

Raises:
    HTTPException: If import fails

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
    x_endpoint_token = 'x_endpoint_token_example' # str |  (optional)
    github_url = 'github_url_example' # str |  (optional)
    zip_file = 'zip_file_example' # str |  (optional)
    folder_path = 'folder_path_example' # str |  (optional)
    snippet_mode = 'file' # str |  (optional) (default to 'file')
    treat_all_as_documents = False # bool |  (optional) (default to False)
    tags = ['tags_example'] # List[str] |  (optional)
    anonymous = True # bool |  (optional) (default to True)

    try:
        # Import Anthropic Skill
        api_response = api_instance.import_anthropic_skill(source_type, x_endpoint_token=x_endpoint_token, github_url=github_url, zip_file=zip_file, folder_path=folder_path, snippet_mode=snippet_mode, treat_all_as_documents=treat_all_as_documents, tags=tags, anonymous=anonymous)
        print("The response of SkillsApi->import_anthropic_skill:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsApi->import_anthropic_skill: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **source_type** | **str**|  | 
 **x_endpoint_token** | **str**|  | [optional] 
 **github_url** | **str**|  | [optional] 
 **zip_file** | **str**|  | [optional] 
 **folder_path** | **str**|  | [optional] 
 **snippet_mode** | **str**|  | [optional] [default to &#39;file&#39;]
 **treat_all_as_documents** | **bool**|  | [optional] [default to False]
 **tags** | [**List[str]**](str.md)|  | [optional] 
 **anonymous** | **bool**|  | [optional] [default to True]

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

# **list_skills**
> object list_skills(fields=fields, search=search, tags=tags, state=state, sort=sort, limit=limit, offset=offset)

List Skills

List skills with optional filter / sort / paginate / project.

See query-param descriptions for behavior. When neither ``limit``
nor ``offset`` is set, returns a bare list. Otherwise returns
``{items, total, offset, limit}``.

Raises:
    HTTPException: 400 if ``fields`` is invalid, 500 if listing fails.

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
    fields = 'fields_example' # str | Field selection. 'minimal' returns uuid only. Omit or 'narrow' for the UI listing set — no inlining; use tool_uuids/snippet_uuids (default). 'wide' returns every persisted manifest field (no inlining). 'full' returns the complete object with the '_populate' mechanism running — 'tools' and 'snippets' are inlined from tool_uuids/snippet_uuids. Or supply a comma-separated allowlist of field names (include '_populate' to trigger inlining). (optional)
    search = 'search_example' # str | Case-insensitive substring over name + description. (optional)
    tags = ['tags_example'] # List[str] | Repeat to filter by multiple tags (AND semantics). Namespace tags are ordinary tags — pass ``namespace:xyz`` to filter by namespace. (optional)
    state = 'state_example' # str | Exact-match lifecycle state filter. (optional)
    sort = 'sort_example' # str | ``field:direction`` (e.g. ``name:asc``). Defaults to ``modified_at:desc``. (optional)
    limit = 56 # int | Max items to return. Setting ``limit`` (or ``offset``) switches the response to a ``{items, total, offset, limit}`` envelope. Omit both for the legacy bare array. (optional)
    offset = 56 # int | Page offset. (optional)

    try:
        # List Skills
        api_response = api_instance.list_skills(fields=fields, search=search, tags=tags, state=state, sort=sort, limit=limit, offset=offset)
        print("The response of SkillsApi->list_skills:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsApi->list_skills: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **fields** | **str**| Field selection. &#39;minimal&#39; returns uuid only. Omit or &#39;narrow&#39; for the UI listing set — no inlining; use tool_uuids/snippet_uuids (default). &#39;wide&#39; returns every persisted manifest field (no inlining). &#39;full&#39; returns the complete object with the &#39;_populate&#39; mechanism running — &#39;tools&#39; and &#39;snippets&#39; are inlined from tool_uuids/snippet_uuids. Or supply a comma-separated allowlist of field names (include &#39;_populate&#39; to trigger inlining). | [optional] 
 **search** | **str**| Case-insensitive substring over name + description. | [optional] 
 **tags** | [**List[str]**](str.md)| Repeat to filter by multiple tags (AND semantics). Namespace tags are ordinary tags — pass &#x60;&#x60;namespace:xyz&#x60;&#x60; to filter by namespace. | [optional] 
 **state** | **str**| Exact-match lifecycle state filter. | [optional] 
 **sort** | **str**| &#x60;&#x60;field:direction&#x60;&#x60; (e.g. &#x60;&#x60;name:asc&#x60;&#x60;). Defaults to &#x60;&#x60;modified_at:desc&#x60;&#x60;. | [optional] 
 **limit** | **int**| Max items to return. Setting &#x60;&#x60;limit&#x60;&#x60; (or &#x60;&#x60;offset&#x60;&#x60;) switches the response to a &#x60;&#x60;{items, total, offset, limit}&#x60;&#x60; envelope. Omit both for the legacy bare array. | [optional] 
 **offset** | **int**| Page offset. | [optional] 

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

# **search_skills**
> object search_skills(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state, fields=fields)

Search Skills

Return a list of skills that are similar to the given search term.

Returns skills that are below the similarity threshold and match the filters.

Args:
    search_term: Search term.
    max_number_of_results: Number of results to return.
    similarity_threshold: Threshold to be used.
    manifest_filter: Manifest properties to filter (e.g., "tags:python", "state:approved").
    lifecycle_state: State to filter by (e.g., LifecycleState.APPROVED).
    fields: Optional field-selection spec (see query-param description).

Returns:
    list: Field-selected skill dicts with ``similarity_score``
        merged in.

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
    search_term = 'search_term_example' # str | 
    max_number_of_results = 5 # int |  (optional) (default to 5)
    similarity_threshold = 1 # float |  (optional) (default to 1)
    manifest_filter = '.' # str |  (optional) (default to '.')
    lifecycle_state = skillberry_store_sdk.LifecycleState() # LifecycleState |  (optional)
    fields = 'fields_example' # str | Field selection over each match. Same grammar as the list endpoint. 'minimal' for uuid-only results (cross-reference a loaded listing). Default (omit / 'narrow') returns the UI listing set (no inlining). 'wide' returns every persisted manifest field (no inlining). 'full' triggers '_populate' — 'tools' and 'snippets' are inlined. CSV allowlist also supported. Each match is a field-selected skill dict with 'similarity_score' merged in. (optional)

    try:
        # Search Skills
        api_response = api_instance.search_skills(search_term, max_number_of_results=max_number_of_results, similarity_threshold=similarity_threshold, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state, fields=fields)
        print("The response of SkillsApi->search_skills:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsApi->search_skills: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **search_term** | **str**|  | 
 **max_number_of_results** | **int**|  | [optional] [default to 5]
 **similarity_threshold** | **float**|  | [optional] [default to 1]
 **manifest_filter** | **str**|  | [optional] [default to &#39;.&#39;]
 **lifecycle_state** | [**LifecycleState**](.md)|  | [optional] 
 **fields** | **str**| Field selection over each match. Same grammar as the list endpoint. &#39;minimal&#39; for uuid-only results (cross-reference a loaded listing). Default (omit / &#39;narrow&#39;) returns the UI listing set (no inlining). &#39;wide&#39; returns every persisted manifest field (no inlining). &#39;full&#39; triggers &#39;_populate&#39; — &#39;tools&#39; and &#39;snippets&#39; are inlined. CSV allowlist also supported. Each match is a field-selected skill dict with &#39;similarity_score&#39; merged in. | [optional] 

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

# **skill_facets**
> object skill_facets()

Skill Facets

Return the unique tags / namespaces / states over all skills.

Powers filter-picker widgets so callers can enumerate every
available value without fetching every skill.

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
        # Skill Facets
        api_response = api_instance.skill_facets()
        print("The response of SkillsApi->skill_facets:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsApi->skill_facets: %s\n" % e)
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

# **update_skill**
> object update_skill(uuid_or_name, skill_schema)

Update Skill

Update an existing skill's metadata.

Updates the manifest/metadata for an existing skill. This operation
triggers a content update event for plugin processing.

Args:
    uuid_or_name: The UUID or name of the skill to update.
    skill: Updated skill metadata conforming to SkillSchema.

Returns:
    dict: Success message confirming update.

Raises:
    HTTPException: 404 if skill not found, 500 for other errors.

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
    uuid_or_name = 'uuid_or_name_example' # str | 
    skill_schema = skillberry_store_sdk.SkillSchema() # SkillSchema | 

    try:
        # Update Skill
        api_response = api_instance.update_skill(uuid_or_name, skill_schema)
        print("The response of SkillsApi->update_skill:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SkillsApi->update_skill: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uuid_or_name** | **str**|  | 
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

