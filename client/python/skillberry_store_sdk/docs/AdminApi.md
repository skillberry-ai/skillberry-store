# skillberry_store_sdk.AdminApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_metrics_admin_metrics_get**](AdminApi.md#get_metrics_admin_metrics_get) | **GET** /admin/metrics | Get Metrics
[**health_check_health_get**](AdminApi.md#health_check_health_get) | **GET** /health | Health Check
[**purge_all_data_admin_purge_all_delete**](AdminApi.md#purge_all_data_admin_purge_all_delete) | **DELETE** /admin/purge-all | Purge All Data


# **get_metrics_admin_metrics_get**
> str get_metrics_admin_metrics_get()

Get Metrics

Proxy endpoint to fetch Prometheus metrics.  This endpoint proxies requests to the Prometheus metrics server to avoid CORS issues when accessing metrics from the UI.  Returns:     PlainTextResponse: The raw Prometheus metrics in text format.      Raises:     HTTPException: If metrics server is not accessible (503).

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

Health check endpoint.  Returns:     dict: Health status of the service.

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

Delete all backend components including skills, tools, snippets, VMCP servers, and their descriptions.  This endpoint performs a hard delete by: 1. Stopping all running VMCP servers 2. Clearing VMCP servers persistent storage 3. Removing all data directories 4. Recreating empty directories 5. Resetting in-memory vector indexes  Use with caution as this operation is irreversible.  Returns:     dict: Success message with details of deleted directories.  Raises:     HTTPException: If deletion fails (500 status code).

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

