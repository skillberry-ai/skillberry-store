from skillberry_plugin_sdk.decorators import get_event_handlers, on_event


class Sample:
    @on_event("content.skill.added")
    @on_event("content.skill.updated")
    async def on_change(self, event):
        return event

    @on_event("content.tool.deleted")
    async def on_tool_del(self, event):
        return event


def test_get_event_handlers_bundles_topics() -> None:
    handlers = get_event_handlers(Sample())
    assert set(handlers.keys()) == {
        "content.skill.added",
        "content.skill.updated",
        "content.tool.deleted",
    }
    assert len(handlers["content.skill.added"]) == 1
    assert len(handlers["content.tool.deleted"]) == 1
