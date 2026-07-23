# OptimizeSkillRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**skill_uuid** | **str** |  | 
**output_skill_name** | **str** |  | [optional] 
**include_metadata** | **bool** |  | [optional] [default to True]
**trajectories_dir** | **str** |  | [optional] 
**additional_context_dir** | **str** |  | [optional] 
**agent_env** | **Dict[str, str]** |  | [optional] 
**execution_mode** | **str** |  | [optional] 
**max_turns** | **int** |  | [optional] 
**optimization_goal** | **str** |  | [optional] 

## Example

```python
from skillberry_store_sdk.models.optimize_skill_request import OptimizeSkillRequest

# TODO update the JSON string below
json = "{}"
# create an instance of OptimizeSkillRequest from a JSON string
optimize_skill_request_instance = OptimizeSkillRequest.from_json(json)
# print the JSON string representation of the object
print(OptimizeSkillRequest.to_json())

# convert the object into a dict
optimize_skill_request_dict = optimize_skill_request_instance.to_dict()
# create an instance of OptimizeSkillRequest from a dict
optimize_skill_request_from_dict = OptimizeSkillRequest.from_dict(optimize_skill_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


