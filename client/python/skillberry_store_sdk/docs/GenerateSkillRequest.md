# GenerateSkillRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**description** | **str** |  | 
**skill_name** | **str** |  | [optional] 
**tags** | **List[str]** |  | [optional] 
**agent_env** | **Dict[str, str]** |  | [optional] 
**execution_mode** | **str** |  | [optional] 
**max_turns** | **int** |  | [optional] 

## Example

```python
from skillberry_store_sdk.models.generate_skill_request import GenerateSkillRequest

# TODO update the JSON string below
json = "{}"
# create an instance of GenerateSkillRequest from a JSON string
generate_skill_request_instance = GenerateSkillRequest.from_json(json)
# print the JSON string representation of the object
print(GenerateSkillRequest.to_json())

# convert the object into a dict
generate_skill_request_dict = generate_skill_request_instance.to_dict()
# create an instance of GenerateSkillRequest from a dict
generate_skill_request_from_dict = GenerateSkillRequest.from_dict(generate_skill_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


