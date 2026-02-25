# SkillSchema

Pydantic schema for a skill.  This schema extends ManifestSchema and represents the structure of a skill in the skillberry-store system. A skill is an ordered collection of tools and snippets referenced by their UUIDs.

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
**tool_uuids** | **List[str]** | Ordered list of tool UUIDs that comprise this skill | [optional] 
**snippet_uuids** | **List[str]** | Ordered list of snippet UUIDs that comprise this skill | [optional] 

## Example

```python
from skillberry_store_sdk.models.skill_schema import SkillSchema

# TODO update the JSON string below
json = "{}"
# create an instance of SkillSchema from a JSON string
skill_schema_instance = SkillSchema.from_json(json)
# print the JSON string representation of the object
print(SkillSchema.to_json())

# convert the object into a dict
skill_schema_dict = skill_schema_instance.to_dict()
# create an instance of SkillSchema from a dict
skill_schema_from_dict = SkillSchema.from_dict(skill_schema_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


