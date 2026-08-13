# WhoAmIResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**tenant_id** | **str** |  | [optional] 
**groups** | **List[str]** |  | [optional] 
**roles** | **List[str]** |  | [optional] 

## Example

```python
from skillberry_store_sdk.models.who_am_i_response import WhoAmIResponse

# TODO update the JSON string below
json = "{}"
# create an instance of WhoAmIResponse from a JSON string
who_am_i_response_instance = WhoAmIResponse.from_json(json)
# print the JSON string representation of the object
print(WhoAmIResponse.to_json())

# convert the object into a dict
who_am_i_response_dict = who_am_i_response_instance.to_dict()
# create an instance of WhoAmIResponse from a dict
who_am_i_response_from_dict = WhoAmIResponse.from_dict(who_am_i_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


