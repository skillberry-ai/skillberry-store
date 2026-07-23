# skillberry_store_sdk.SimulateApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**simulate_active**](SimulateApi.md#simulate_active) | **GET** /plugins/simulate/active/{skill_uuid} | Active
[**simulate_simulate**](SimulateApi.md#simulate_simulate) | **POST** /plugins/simulate/simulate | Simulate
[**simulate_simulate_status**](SimulateApi.md#simulate_simulate_status) | **GET** /plugins/simulate/status/{job_id} | Simulate Status
[**simulate_teardown**](SimulateApi.md#simulate_teardown) | **POST** /plugins/simulate/teardown | Teardown
[**simulate_toggle**](SimulateApi.md#simulate_toggle) | **POST** /plugins/simulate/toggle | Toggle


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
    api_instance = skillberry_store_sdk.SimulateApi(api_client)
    skill_uuid = 'skill_uuid_example' # str | 

    try:
        # Active
        api_response = api_instance.simulate_active(skill_uuid)
        print("The response of SimulateApi->simulate_active:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulateApi->simulate_active: %s\n" % e)
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
    api_instance = skillberry_store_sdk.SimulateApi(api_client)
    simulate_request = skillberry_store_sdk.SimulateRequest() # SimulateRequest | 

    try:
        # Simulate
        api_response = api_instance.simulate_simulate(simulate_request)
        print("The response of SimulateApi->simulate_simulate:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulateApi->simulate_simulate: %s\n" % e)
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
    api_instance = skillberry_store_sdk.SimulateApi(api_client)
    job_id = 'job_id_example' # str | 

    try:
        # Simulate Status
        api_response = api_instance.simulate_simulate_status(job_id)
        print("The response of SimulateApi->simulate_simulate_status:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulateApi->simulate_simulate_status: %s\n" % e)
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
    api_instance = skillberry_store_sdk.SimulateApi(api_client)
    skill_request = skillberry_store_sdk.SkillRequest() # SkillRequest | 

    try:
        # Teardown
        api_response = api_instance.simulate_teardown(skill_request)
        print("The response of SimulateApi->simulate_teardown:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulateApi->simulate_teardown: %s\n" % e)
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
    api_instance = skillberry_store_sdk.SimulateApi(api_client)
    skill_request = skillberry_store_sdk.SkillRequest() # SkillRequest | 

    try:
        # Toggle
        api_response = api_instance.simulate_toggle(skill_request)
        print("The response of SimulateApi->simulate_toggle:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulateApi->simulate_toggle: %s\n" % e)
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

