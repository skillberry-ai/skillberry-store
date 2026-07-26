# PluginEnabledUpdate

Body for toggling a plugin's admin enablement.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**enabled** | **bool** |  | 

## Example

```python
from skillberry_store_sdk.models.plugin_enabled_update import PluginEnabledUpdate

# TODO update the JSON string below
json = "{}"
# create an instance of PluginEnabledUpdate from a JSON string
plugin_enabled_update_instance = PluginEnabledUpdate.from_json(json)
# print the JSON string representation of the object
print(PluginEnabledUpdate.to_json())

# convert the object into a dict
plugin_enabled_update_dict = plugin_enabled_update_instance.to_dict()
# create an instance of PluginEnabledUpdate from a dict
plugin_enabled_update_from_dict = PluginEnabledUpdate.from_dict(plugin_enabled_update_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


