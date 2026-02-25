# ToolSchema

Pydantic schema for a tool.  This schema extends ManifestSchema and represents the structure of a tool in the skillberry-store system, including programming language, parameters, and execution details.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | [optional] 
**uuid** | **str** |  | [optional] 
**version** | **str** |  | [optional] 
**description** | **str** |  | [optional] 
**state** | [**ManifestState**](ManifestState.md) | Lifecycle state | [optional] 
**tags** | **List[str]** |  | [optional] 
**extra** | **Dict[str, object]** |  | [optional] 
**created_at** | **str** |  | [optional] 
**modified_at** | **str** |  | [optional] 
**module_name** | **str** |  | [optional] 
**programming_language** | **str** | Programming language of the tool | [optional] [default to 'python']
**packaging_format** | **str** | Packaging format of the tool | [optional] [default to 'code']
**params** | [**ToolParamsSchema**](ToolParamsSchema.md) | Parameters schema for the tool | [optional] 
**returns** | [**ToolReturnsSchema**](ToolReturnsSchema.md) |  | [optional] 
**dependencies** | **List[str]** |  | [optional] 

## Example

```python
from skillberry_store_sdk.models.tool_schema import ToolSchema

# TODO update the JSON string below
json = "{}"
# create an instance of ToolSchema from a JSON string
tool_schema_instance = ToolSchema.from_json(json)
# print the JSON string representation of the object
print(ToolSchema.to_json())

# convert the object into a dict
tool_schema_dict = tool_schema_instance.to_dict()
# create an instance of ToolSchema from a dict
tool_schema_from_dict = ToolSchema.from_dict(tool_schema_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


