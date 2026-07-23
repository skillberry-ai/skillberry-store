# FixRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**object_uuids** | **List[str]** |  | 
**severities** | **List[str]** |  | [optional] 

## Example

```python
from skillberry_store_sdk.models.fix_request import FixRequest

# TODO update the JSON string below
json = "{}"
# create an instance of FixRequest from a JSON string
fix_request_instance = FixRequest.from_json(json)
# print the JSON string representation of the object
print(FixRequest.to_json())

# convert the object into a dict
fix_request_dict = fix_request_instance.to_dict()
# create an instance of FixRequest from a dict
fix_request_from_dict = FixRequest.from_dict(fix_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


