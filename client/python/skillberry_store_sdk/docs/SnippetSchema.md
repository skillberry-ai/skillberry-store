# SnippetSchema

Pydantic schema for a snippet.  This schema extends ManifestSchema and represents the structure of a text snippet in the skillberry-store system.

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
**content** | **str** | The text content of the snippet | 
**content_type** | [**ContentType**](ContentType.md) | MIME type of the snippet content | [optional] 

## Example

```python
from skillberry_store_sdk.models.snippet_schema import SnippetSchema

# TODO update the JSON string below
json = "{}"
# create an instance of SnippetSchema from a JSON string
snippet_schema_instance = SnippetSchema.from_json(json)
# print the JSON string representation of the object
print(SnippetSchema.to_json())

# convert the object into a dict
snippet_schema_dict = snippet_schema_instance.to_dict()
# create an instance of SnippetSchema from a dict
snippet_schema_from_dict = SnippetSchema.from_dict(snippet_schema_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


