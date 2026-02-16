# ToolParamsSchema

Schema for tool parameters.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** | Type of the parameters object | [optional] [default to 'object']
**properties** | **Dict[str, Dict[str, object]]** | Dictionary of parameter properties with their types and descriptions | [optional] 
**required** | **List[str]** | List of required parameter names | [optional] 
**optional** | **List[str]** | List of optional parameter names | [optional] 

## Example

```python
from skillberry_store_sdk.models.tool_params_schema import ToolParamsSchema

# TODO update the JSON string below
json = "{}"
# create an instance of ToolParamsSchema from a JSON string
tool_params_schema_instance = ToolParamsSchema.from_json(json)
# print the JSON string representation of the object
print(ToolParamsSchema.to_json())

# convert the object into a dict
tool_params_schema_dict = tool_params_schema_instance.to_dict()
# create an instance of ToolParamsSchema from a dict
tool_params_schema_from_dict = ToolParamsSchema.from_dict(tool_params_schema_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


