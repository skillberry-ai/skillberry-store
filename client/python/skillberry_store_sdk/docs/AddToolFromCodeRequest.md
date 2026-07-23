# AddToolFromCodeRequest

Body for ``POST /tools/add_code`` — Python source as a string, not a file.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**code** | **str** |  | 
**selected_func** | **str** |  | [optional] 
**update** | **bool** |  | [optional] [default to False]
**module_name** | **str** |  | [optional] 

## Example

```python
from skillberry_store_sdk.models.add_tool_from_code_request import AddToolFromCodeRequest

# TODO update the JSON string below
json = "{}"
# create an instance of AddToolFromCodeRequest from a JSON string
add_tool_from_code_request_instance = AddToolFromCodeRequest.from_json(json)
# print the JSON string representation of the object
print(AddToolFromCodeRequest.to_json())

# convert the object into a dict
add_tool_from_code_request_dict = add_tool_from_code_request_instance.to_dict()
# create an instance of AddToolFromCodeRequest from a dict
add_tool_from_code_request_from_dict = AddToolFromCodeRequest.from_dict(add_tool_from_code_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


