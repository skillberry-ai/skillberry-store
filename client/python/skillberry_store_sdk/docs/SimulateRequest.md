# SimulateRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**skill_uuid** | **str** |  | 
**vmcp_uuid** | **str** |  | [optional] 

## Example

```python
from skillberry_store_sdk.models.simulate_request import SimulateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of SimulateRequest from a JSON string
simulate_request_instance = SimulateRequest.from_json(json)
# print the JSON string representation of the object
print(SimulateRequest.to_json())

# convert the object into a dict
simulate_request_dict = simulate_request_instance.to_dict()
# create an instance of SimulateRequest from a dict
simulate_request_from_dict = SimulateRequest.from_dict(simulate_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


