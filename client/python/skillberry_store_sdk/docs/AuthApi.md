# skillberry_store_sdk.AuthApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**login**](AuthApi.md#login) | **POST** /auth/login | Login
[**logout**](AuthApi.md#logout) | **POST** /auth/logout | Logout
[**whoami**](AuthApi.md#whoami) | **GET** /auth/whoami | Whoami


# **login**
> LoginResponse login(login_request)

Login

Authenticate a user and mint a bearer session token.

Validates the supplied username / password against the bcrypt
hashes in ``access_control_config.yaml``. On success, returns an
opaque session token whose lifetime is ``session_ttl_seconds``
(12h default; see §7.2 of docs/design/access-control.md). The
client is expected to send this token on subsequent requests as
``Authorization: Bearer <token>``.

Unknown username and bad password both return the same 401 body
(``invalid_credentials``) — no user enumeration.

Args:
    payload: JSON body with ``username`` and ``password`` fields.

Returns:
    LoginResponse: ``token`` (opaque, URL-safe), ``expires_at``
    (ISO-8601 UTC), and the resolved ``tenant_id``.

Raises:
    HTTPException: 401 ``invalid_credentials`` when the user is
        unknown or the password does not match.

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.login_request import LoginRequest
from skillberry_store_sdk.models.login_response import LoginResponse
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
    api_instance = skillberry_store_sdk.AuthApi(api_client)
    login_request = skillberry_store_sdk.LoginRequest() # LoginRequest | 

    try:
        # Login
        api_response = api_instance.login(login_request)
        print("The response of AuthApi->login:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AuthApi->login: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **login_request** | [**LoginRequest**](LoginRequest.md)|  | 

### Return type

[**LoginResponse**](LoginResponse.md)

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

# **logout**
> Dict[str, object] logout()

Logout

Revoke the bearer token on the request.

Idempotent: a missing / malformed / unknown token still returns
200. Client-side sign-out (clearing the stored token) can always
proceed regardless of the server's view. Listed in the
unauthenticated allow-list so it works even if the token has
already expired — the intent is "make sure this token is gone,"
not "prove you had a live session first."

Args:
    request: The incoming request; the ``Authorization`` header
        (if present) is consulted for the token to revoke.

Returns:
    dict: ``{"status": "ok"}``.

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
    api_instance = skillberry_store_sdk.AuthApi(api_client)

    try:
        # Logout
        api_response = api_instance.logout()
        print("The response of AuthApi->logout:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AuthApi->logout: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

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

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **whoami**
> WhoAmIResponse whoami()

Whoami

Return the caller's identity and the roles bound to it.

Populates the UI's "Signed in as ..." indicator and drives any
future RBAC-aware UI hiding. Also useful as a CLI diagnostic
(``sbs whoami``). Roles are recomputed at request time from the
currently loaded bindings — they are not baked into the session
at login, so a config reload takes effect without invalidating
minted sessions (see the ``Subject`` vs ``whoami`` note in §7 of
docs/design/access-control.md).
In ``disabled`` mode there is no auth layer; the endpoint
returns 503 ``auth_disabled`` and any bearer on the request is
ignored.

Args:
    request: The incoming request; ``Authorization: Bearer`` is
        resolved directly (this endpoint is in the unauth
        allow-list, so the middleware does not populate
        ``request.state.subject`` for it).

Returns:
    WhoAmIResponse: ``tenant_id``, ``groups``, and ``roles``.

Raises:
    HTTPException: 401 in ``standalone`` mode when the header is
        missing / malformed, or the token is expired / unknown.

### Example


```python
import skillberry_store_sdk
from skillberry_store_sdk.models.who_am_i_response import WhoAmIResponse
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
    api_instance = skillberry_store_sdk.AuthApi(api_client)

    try:
        # Whoami
        api_response = api_instance.whoami()
        print("The response of AuthApi->whoami:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AuthApi->whoami: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**WhoAmIResponse**](WhoAmIResponse.md)

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

