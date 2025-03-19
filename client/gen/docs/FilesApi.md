# openapi_client.FilesApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**delete_file_file_filename_delete**](FilesApi.md#delete_file_file_filename_delete) | **DELETE** /file/{filename} | Delete File
[**delete_files_files_delete**](FilesApi.md#delete_files_files_delete) | **DELETE** /files | Delete Files
[**export_files_export_files_post**](FilesApi.md#export_files_export_files_post) | **POST** /export/files | Export Files
[**import_files_import_files_post**](FilesApi.md#import_files_import_files_post) | **POST** /import/files | Import Files
[**list_files_files_get**](FilesApi.md#list_files_files_get) | **GET** /files | List Files
[**read_file_file_filename_get**](FilesApi.md#read_file_file_filename_get) | **GET** /file/{filename} | Read File
[**read_file_json_file_json_filename_get**](FilesApi.md#read_file_json_file_json_filename_get) | **GET** /file/json/{filename} | Read File Json
[**rename_file_rename_file_filename_post**](FilesApi.md#rename_file_rename_file_filename_post) | **POST** /rename/file/{filename} | Rename File
[**write_file_file_post**](FilesApi.md#write_file_file_post) | **POST** /file | Write File
[**write_file_json_file_json_filename_post**](FilesApi.md#write_file_json_file_json_filename_post) | **POST** /file/json/{filename} | Write File Json


# **delete_file_file_filename_delete**
> delete_file_file_filename_delete(filename)

Delete File

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.FilesApi(api_client)
    filename = 'filename_example' # str | 

    try:
        # Delete File
        api_instance.delete_file_file_filename_delete(filename)
    except Exception as e:
        print("Exception when calling FilesApi->delete_file_file_filename_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **filename** | **str**|  | 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: text/plain, application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_files_files_delete**
> delete_files_files_delete(regex=regex, lifecycle_state=lifecycle_state)

Delete Files

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.FilesApi(api_client)
    regex = '.' # str |  (optional) (default to '.')
    lifecycle_state = openapi_client.LifecycleState() # LifecycleState |  (optional)

    try:
        # Delete Files
        api_instance.delete_files_files_delete(regex=regex, lifecycle_state=lifecycle_state)
    except Exception as e:
        print("Exception when calling FilesApi->delete_files_files_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **regex** | **str**|  | [optional] [default to &#39;.&#39;]
 **lifecycle_state** | [**LifecycleState**](.md)|  | [optional] 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: text/plain, application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **export_files_export_files_post**
> export_files_export_files_post(path, regex=regex, lifecycle_state=lifecycle_state)

Export Files

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.FilesApi(api_client)
    path = 'path_example' # str | 
    regex = '.' # str |  (optional) (default to '.')
    lifecycle_state = openapi_client.LifecycleState() # LifecycleState |  (optional)

    try:
        # Export Files
        api_instance.export_files_export_files_post(path, regex=regex, lifecycle_state=lifecycle_state)
    except Exception as e:
        print("Exception when calling FilesApi->export_files_export_files_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **path** | **str**|  | 
 **regex** | **str**|  | [optional] [default to &#39;.&#39;]
 **lifecycle_state** | [**LifecycleState**](.md)|  | [optional] 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: text/plain, application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **import_files_import_files_post**
> import_files_import_files_post(path)

Import Files

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.FilesApi(api_client)
    path = 'path_example' # str | 

    try:
        # Import Files
        api_instance.import_files_import_files_post(path)
    except Exception as e:
        print("Exception when calling FilesApi->import_files_import_files_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **path** | **str**|  | 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: text/plain, application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_files_files_get**
> list_files_files_get(lifecycle_state=lifecycle_state)

List Files

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.FilesApi(api_client)
    lifecycle_state = openapi_client.LifecycleState() # LifecycleState |  (optional)

    try:
        # List Files
        api_instance.list_files_files_get(lifecycle_state=lifecycle_state)
    except Exception as e:
        print("Exception when calling FilesApi->list_files_files_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **lifecycle_state** | [**LifecycleState**](.md)|  | [optional] 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: text/plain, application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **read_file_file_filename_get**
> read_file_file_filename_get(filename)

Read File

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.FilesApi(api_client)
    filename = 'filename_example' # str | 

    try:
        # Read File
        api_instance.read_file_file_filename_get(filename)
    except Exception as e:
        print("Exception when calling FilesApi->read_file_file_filename_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **filename** | **str**|  | 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: text/plain, application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **read_file_json_file_json_filename_get**
> read_file_json_file_json_filename_get(filename)

Read File Json

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.FilesApi(api_client)
    filename = 'filename_example' # str | 

    try:
        # Read File Json
        api_instance.read_file_json_file_json_filename_get(filename)
    except Exception as e:
        print("Exception when calling FilesApi->read_file_json_file_json_filename_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **filename** | **str**|  | 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: text/plain, application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **rename_file_rename_file_filename_post**
> rename_file_rename_file_filename_post(src_filename, dest_filename)

Rename File

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.FilesApi(api_client)
    src_filename = 'src_filename_example' # str | 
    dest_filename = 'dest_filename_example' # str | 

    try:
        # Rename File
        api_instance.rename_file_rename_file_filename_post(src_filename, dest_filename)
    except Exception as e:
        print("Exception when calling FilesApi->rename_file_rename_file_filename_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **src_filename** | **str**|  | 
 **dest_filename** | **str**|  | 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: text/plain, application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **write_file_file_post**
> write_file_file_post(file, file_description=file_description, file_metadata=file_metadata)

Write File

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.FilesApi(api_client)
    file = None # bytearray | 
    file_description = 'file_description_example' # str |  (optional)
    file_metadata = 'file_metadata_example' # str |  (optional)

    try:
        # Write File
        api_instance.write_file_file_post(file, file_description=file_description, file_metadata=file_metadata)
    except Exception as e:
        print("Exception when calling FilesApi->write_file_file_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **file** | **bytearray**|  | 
 **file_description** | **str**|  | [optional] 
 **file_metadata** | **str**|  | [optional] 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: text/plain, application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **write_file_json_file_json_filename_post**
> write_file_json_file_json_filename_post(file_name, body)

Write File Json

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.FilesApi(api_client)
    file_name = 'file_name_example' # str | 
    body = None # object | 

    try:
        # Write File Json
        api_instance.write_file_json_file_json_filename_post(file_name, body)
    except Exception as e:
        print("Exception when calling FilesApi->write_file_json_file_json_filename_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **file_name** | **str**|  | 
 **body** | **object**|  | 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: text/plain, application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

