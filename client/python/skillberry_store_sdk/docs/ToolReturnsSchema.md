# ToolReturnsSchema

Schema for tool return values.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** |  | [optional] 
**description** | **str** |  | [optional] 

## Example

```python
from skillberry_store_sdk.models.tool_returns_schema import ToolReturnsSchema

# TODO update the JSON string below
json = "{}"
# create an instance of ToolReturnsSchema from a JSON string
tool_returns_schema_instance = ToolReturnsSchema.from_json(json)
# print the JSON string representation of the object
print(ToolReturnsSchema.to_json())

# convert the object into a dict
tool_returns_schema_dict = tool_returns_schema_instance.to_dict()
# create an instance of ToolReturnsSchema from a dict
tool_returns_schema_from_dict = ToolReturnsSchema.from_dict(tool_returns_schema_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


