# RunRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**request** | **str** |  | 
**skills** | **List[str]** |  | [optional] [default to []]
**skills_dir** | **str** |  | [optional] 
**skills_upload_id** | **str** |  | [optional] 
**mcp_servers** | [**AnyOf**](AnyOf.md) |  | [optional] 
**execution_mode** | **str** |  | [optional] 
**agent_env** | **Dict[str, str]** |  | [optional] 
**keep_workspace** | **bool** |  | [optional] [default to False]
**use_runspace_server** | **bool** |  | [optional] [default to False]
**runspace_server_url** | **str** |  | [optional] 

## Example

```python
from skillberry_store_sdk.models.run_request import RunRequest

# TODO update the JSON string below
json = "{}"
# create an instance of RunRequest from a JSON string
run_request_instance = RunRequest.from_json(json)
# print the JSON string representation of the object
print(RunRequest.to_json())

# convert the object into a dict
run_request_dict = run_request_instance.to_dict()
# create an instance of RunRequest from a dict
run_request_from_dict = RunRequest.from_dict(run_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


