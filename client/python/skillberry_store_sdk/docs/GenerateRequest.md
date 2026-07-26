# GenerateRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**object_type** | **str** |  | [optional] [default to 'tool']
**uuid** | **str** |  | [optional] 
**apply** | **bool** |  | [optional] [default to False]
**only_if_missing** | **bool** |  | [optional] [default to False]

## Example

```python
from skillberry_store_sdk.models.generate_request import GenerateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of GenerateRequest from a JSON string
generate_request_instance = GenerateRequest.from_json(json)
# print the JSON string representation of the object
print(GenerateRequest.to_json())

# convert the object into a dict
generate_request_dict = generate_request_instance.to_dict()
# create an instance of GenerateRequest from a dict
generate_request_from_dict = GenerateRequest.from_dict(generate_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


