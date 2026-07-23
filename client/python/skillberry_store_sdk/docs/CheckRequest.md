# CheckRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**github_url** | **str** |  | [optional] 
**uuid** | **str** |  | [optional] 

## Example

```python
from skillberry_store_sdk.models.check_request import CheckRequest

# TODO update the JSON string below
json = "{}"
# create an instance of CheckRequest from a JSON string
check_request_instance = CheckRequest.from_json(json)
# print the JSON string representation of the object
print(CheckRequest.to_json())

# convert the object into a dict
check_request_dict = check_request_instance.to_dict()
# create an instance of CheckRequest from a dict
check_request_from_dict = CheckRequest.from_dict(check_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


