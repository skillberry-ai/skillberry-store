# CreateSnippetRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**description** | **str** |  | 
**name** | **str** |  | [optional] 

## Example

```python
from skillberry_store_sdk.models.create_snippet_request import CreateSnippetRequest

# TODO update the JSON string below
json = "{}"
# create an instance of CreateSnippetRequest from a JSON string
create_snippet_request_instance = CreateSnippetRequest.from_json(json)
# print the JSON string representation of the object
print(CreateSnippetRequest.to_json())

# convert the object into a dict
create_snippet_request_dict = create_snippet_request_instance.to_dict()
# create an instance of CreateSnippetRequest from a dict
create_snippet_request_from_dict = CreateSnippetRequest.from_dict(create_snippet_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


