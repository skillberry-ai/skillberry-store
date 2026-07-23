# EvaluateRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**uuid** | **str** |  | 
**content_type** | **str** |  | 

## Example

```python
from skillberry_store_sdk.models.evaluate_request import EvaluateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluateRequest from a JSON string
evaluate_request_instance = EvaluateRequest.from_json(json)
# print the JSON string representation of the object
print(EvaluateRequest.to_json())

# convert the object into a dict
evaluate_request_dict = evaluate_request_instance.to_dict()
# create an instance of EvaluateRequest from a dict
evaluate_request_from_dict = EvaluateRequest.from_dict(evaluate_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


