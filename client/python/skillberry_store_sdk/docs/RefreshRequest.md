# RefreshRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**object_type** | **str** |  | [optional] [default to 'tool']
**uuid** | **str** |  | [optional] 

## Example

```python
from skillberry_store_sdk.models.refresh_request import RefreshRequest

# TODO update the JSON string below
json = "{}"
# create an instance of RefreshRequest from a JSON string
refresh_request_instance = RefreshRequest.from_json(json)
# print the JSON string representation of the object
print(RefreshRequest.to_json())

# convert the object into a dict
refresh_request_dict = refresh_request_instance.to_dict()
# create an instance of RefreshRequest from a dict
refresh_request_from_dict = RefreshRequest.from_dict(refresh_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


