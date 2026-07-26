# SkillRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**skill_uuid** | **str** |  | 

## Example

```python
from skillberry_store_sdk.models.skill_request import SkillRequest

# TODO update the JSON string below
json = "{}"
# create an instance of SkillRequest from a JSON string
skill_request_instance = SkillRequest.from_json(json)
# print the JSON string representation of the object
print(SkillRequest.to_json())

# convert the object into a dict
skill_request_dict = skill_request_instance.to_dict()
# create an instance of SkillRequest from a dict
skill_request_from_dict = SkillRequest.from_dict(skill_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


