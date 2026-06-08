# skillberry_store_sdk.AdminApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**backup_all_data_admin_backup_get**](AdminApi.md#backup_all_data_admin_backup_get) | **GET** /admin/backup | Backup All Data
[**get_changes_count_changes_get**](AdminApi.md#get_changes_count_changes_get) | **GET** /changes | Get Changes Count
[**get_metrics_admin_metrics_get**](AdminApi.md#get_metrics_admin_metrics_get) | **GET** /admin/metrics | Get Metrics
[**health_check_health_get**](AdminApi.md#health_check_health_get) | **GET** /health | Health Check
[**purge_all_data_admin_purge_all_delete**](AdminApi.md#purge_all_data_admin_purge_all_delete) | **DELETE** /admin/purge-all | Purge All Data
[**readiness_check_health_ready_get**](AdminApi.md#readiness_check_health_ready_get) | **GET** /health/ready | Readiness Check
[**restore_all_data_admin_restore_post**](AdminApi.md#restore_all_data_admin_restore_post) | **POST** /admin/restore | Restore All Data


# **backup_all_data_admin_backup_get**
> backup_all_data_admin_backup_get()

Backup All Data

Create a backup of all data (skills, tools, snippets, VMCP servers, vNFS servers).

Returns a compressed JSON file (.json.zip) containing all data.
The UI should download this file directly.

Returns:
    StreamingResponse: A ZIP file containing the backup JSON.

Raises:
    HTTPException: If backup creation fails (500 status code).

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
    api_instance = skillberry_store_sdk.AdminApi(api_client)

    try:
        # Backup All Data
        api_instance.backup_all_data_admin_backup_get()
    except Exception as e:
        print("Exception when calling AdminApi->backup_all_data_admin_backup_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_changes_count_changes_get**
> object get_changes_count_changes_get()

Get Changes Count

Return the global mutation counter. Used by the UI to detect data changes.

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
    api_instance = skillberry_store_sdk.AdminApi(api_client)

    try:
        # Get Changes Count
        api_response = api_instance.get_changes_count_changes_get()
        print("The response of AdminApi->get_changes_count_changes_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AdminApi->get_changes_count_changes_get: %s\n" % e)
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

# **get_metrics_admin_metrics_get**
> str get_metrics_admin_metrics_get()

Get Metrics

Proxy endpoint to fetch Prometheus metrics.

This endpoint proxies requests to the Prometheus metrics server
to avoid CORS issues when accessing metrics from the UI.

Returns:
    PlainTextResponse: The raw Prometheus metrics in text format.

Raises:
    HTTPException: If metrics server is not accessible (503).

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
    api_instance = skillberry_store_sdk.AdminApi(api_client)

    try:
        # Get Metrics
        api_response = api_instance.get_metrics_admin_metrics_get()
        print("The response of AdminApi->get_metrics_admin_metrics_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AdminApi->get_metrics_admin_metrics_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**str**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: text/plain

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **health_check_health_get**
> object health_check_health_get()

Health Check

Health check endpoint.

Returns:
    dict: Health status of the service.

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
    api_instance = skillberry_store_sdk.AdminApi(api_client)

    try:
        # Health Check
        api_response = api_instance.health_check_health_get()
        print("The response of AdminApi->health_check_health_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AdminApi->health_check_health_get: %s\n" % e)
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

# **purge_all_data_admin_purge_all_delete**
> object purge_all_data_admin_purge_all_delete()

Purge All Data

Delete all backend components including skills, tools, snippets, VMCP servers, and their descriptions.

This endpoint performs a hard delete by:
1. Stopping all running VMCP servers
2. Clearing VMCP servers persistent storage
3. Removing all data directories
4. Recreating empty directories
5. Resetting in-memory vector indexes

Use with caution as this operation is irreversible.

Returns:
    dict: Success message with details of deleted directories.

Raises:
    HTTPException: If deletion fails (500 status code).

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
    api_instance = skillberry_store_sdk.AdminApi(api_client)

    try:
        # Purge All Data
        api_response = api_instance.purge_all_data_admin_purge_all_delete()
        print("The response of AdminApi->purge_all_data_admin_purge_all_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AdminApi->purge_all_data_admin_purge_all_delete: %s\n" % e)
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

# **readiness_check_health_ready_get**
> object readiness_check_health_ready_get()

Readiness Check

Readiness check endpoint - verifies all description directories are initialized.

Returns:
    dict: Readiness status with details about each directory (HTTP 200 when ready).

Raises:
    HTTPException: 500 status when still initializing.

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
    api_instance = skillberry_store_sdk.AdminApi(api_client)

    try:
        # Readiness Check
        api_response = api_instance.readiness_check_health_ready_get()
        print("The response of AdminApi->readiness_check_health_ready_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AdminApi->readiness_check_health_ready_get: %s\n" % e)
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

# **restore_all_data_admin_restore_post**
> object restore_all_data_admin_restore_post(backup_file)

Restore All Data

Restore all data from a backup file.

This endpoint:
1. Purges all existing data (calls purge_all_data internally)
2. Restores data from the uploaded backup file
3. Imports in order: tools, snippets, skills, VMCP servers, vNFS servers
4. Starts VMCP/vNFS servers that are in approved state
5. Rebuilds caches and description indexes

Args:
    backup_file: The backup ZIP file to restore from.

Returns:
    dict: Success message with counts of restored items.

Raises:
    HTTPException: If restore fails (400 or 500 status code).

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
    api_instance = skillberry_store_sdk.AdminApi(api_client)
    backup_file = 'backup_file_example' # str | 

    try:
        # Restore All Data
        api_response = api_instance.restore_all_data_admin_restore_post(backup_file)
        print("The response of AdminApi->restore_all_data_admin_restore_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AdminApi->restore_all_data_admin_restore_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **backup_file** | **str**|  | 

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

