# skillberry_store_sdk.AdminApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**backup_all_data**](AdminApi.md#backup_all_data) | **GET** /admin/backup | Backup All Data
[**get_changes_count**](AdminApi.md#get_changes_count) | **GET** /changes | Get Changes Count
[**get_metrics**](AdminApi.md#get_metrics) | **GET** /admin/metrics | Get Metrics
[**health_check**](AdminApi.md#health_check) | **GET** /health | Health Check
[**purge_all_data**](AdminApi.md#purge_all_data) | **DELETE** /admin/purge-all | Purge All Data
[**readiness_check**](AdminApi.md#readiness_check) | **GET** /health/ready | Readiness Check
[**restore_all_data**](AdminApi.md#restore_all_data) | **POST** /admin/restore | Restore All Data


# **backup_all_data**
> backup_all_data()

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
        api_instance.backup_all_data()
    except Exception as e:
        print("Exception when calling AdminApi->backup_all_data: %s\n" % e)
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

# **get_changes_count**
> object get_changes_count()

Get Changes Count

Get the global mutation counter for detecting data changes.

Returns a counter that increments whenever data is modified (create, update, delete).
The UI uses this to detect when to refresh data without polling individual endpoints.

Args:
    None.

Returns:
    dict: Contains 'count' key with the current mutation counter value.

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
        api_response = api_instance.get_changes_count()
        print("The response of AdminApi->get_changes_count:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AdminApi->get_changes_count: %s\n" % e)
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

# **get_metrics**
> str get_metrics()

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
        api_response = api_instance.get_metrics()
        print("The response of AdminApi->get_metrics:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AdminApi->get_metrics: %s\n" % e)
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

# **health_check**
> object health_check()

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
        api_response = api_instance.health_check()
        print("The response of AdminApi->health_check:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AdminApi->health_check: %s\n" % e)
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

# **purge_all_data**
> object purge_all_data()

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
        api_response = api_instance.purge_all_data()
        print("The response of AdminApi->purge_all_data:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AdminApi->purge_all_data: %s\n" % e)
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

# **readiness_check**
> object readiness_check()

Readiness Check

Readiness check endpoint - verifies all description stores are initialized.

Returns:
    dict: Readiness status with details about each object type (HTTP 200 when ready).

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
        api_response = api_instance.readiness_check()
        print("The response of AdminApi->readiness_check:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AdminApi->readiness_check: %s\n" % e)
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

# **restore_all_data**
> object restore_all_data(backup_file)

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
    backup_file = None # bytearray | 

    try:
        # Restore All Data
        api_response = api_instance.restore_all_data(backup_file)
        print("The response of AdminApi->restore_all_data:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AdminApi->restore_all_data: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **backup_file** | **bytearray**|  | 

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

