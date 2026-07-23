# skillberry_store_sdk.AskRunspaceApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**ask_runspace_cleanup_workspace**](AskRunspaceApi.md#ask_runspace_cleanup_workspace) | **POST** /plugins/ask-runspace/cleanup/{job_id} | Cleanup Workspace
[**ask_runspace_presets**](AskRunspaceApi.md#ask_runspace_presets) | **GET** /plugins/ask-runspace/presets | Presets
[**ask_runspace_run**](AskRunspaceApi.md#ask_runspace_run) | **POST** /plugins/ask-runspace/run | Run
[**ask_runspace_status**](AskRunspaceApi.md#ask_runspace_status) | **GET** /plugins/ask-runspace/status/{job_id} | Status
[**ask_runspace_upload_skills**](AskRunspaceApi.md#ask_runspace_upload_skills) | **POST** /plugins/ask-runspace/upload-skills | Upload Skills


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
    api_instance = skillberry_store_sdk.AskRunspaceApi(api_client)
    job_id = 'job_id_example' # str | 

    try:
        # Cleanup Workspace
        api_response = api_instance.ask_runspace_cleanup_workspace(job_id)
        print("The response of AskRunspaceApi->ask_runspace_cleanup_workspace:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AskRunspaceApi->ask_runspace_cleanup_workspace: %s\n" % e)
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
    api_instance = skillberry_store_sdk.AskRunspaceApi(api_client)

    try:
        # Presets
        api_response = api_instance.ask_runspace_presets()
        print("The response of AskRunspaceApi->ask_runspace_presets:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AskRunspaceApi->ask_runspace_presets: %s\n" % e)
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
    api_instance = skillberry_store_sdk.AskRunspaceApi(api_client)
    run_request = skillberry_store_sdk.RunRequest() # RunRequest | 

    try:
        # Run
        api_response = api_instance.ask_runspace_run(run_request)
        print("The response of AskRunspaceApi->ask_runspace_run:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AskRunspaceApi->ask_runspace_run: %s\n" % e)
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
    api_instance = skillberry_store_sdk.AskRunspaceApi(api_client)
    job_id = 'job_id_example' # str | 

    try:
        # Status
        api_response = api_instance.ask_runspace_status(job_id)
        print("The response of AskRunspaceApi->ask_runspace_status:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AskRunspaceApi->ask_runspace_status: %s\n" % e)
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
    api_instance = skillberry_store_sdk.AskRunspaceApi(api_client)
    files = ['files_example'] # List[str] | 

    try:
        # Upload Skills
        api_response = api_instance.ask_runspace_upload_skills(files)
        print("The response of AskRunspaceApi->ask_runspace_upload_skills:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AskRunspaceApi->ask_runspace_upload_skills: %s\n" % e)
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

