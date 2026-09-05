"""
Social platform tools.

None of these is implemented against a live API. That was also true before,
but the previous versions said otherwise. With a credential present:

    buffer_post_scheduler   -> "LIVE: Scheduled content to {platform} via Buffer API"
    instagram_analytics_fetcher -> {"status": "Live data fetched", "reach": 12000}

Neither made an HTTP request. The Buffer "implementation" was one return
statement; the Instagram one returned a made-up reach figure. So the system was
*more* misleading with credentials configured than without them: an operator
who set ``BUFFER_ACCESS_TOKEN`` was told their posts were scheduled.

The rule now: a tool returns ``status: "mock"`` with obviously synthetic data
when mock mode is on, and ``status: "not_implemented"`` otherwise. Nothing here
says "live", "scheduled" or "fetched" unless it did that.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app.config import settings

# The set of providers with a working integration. Empty is the honest value.
IMPLEMENTED_PROVIDERS: frozenset[str] = frozenset()


def _not_implemented(tool_name: str, provider: str, credential_present: bool) -> dict[str, Any]:
    return {
        "status": "not_implemented",
        "tool": tool_name,
        "provider": provider,
        "credential_present": credential_present,
        "message": (f"{tool_name} is not connected to {provider}; no request was made."),
    }


@tool("twitter_trend_search")
def twitter_trend_search(query: str) -> dict[str, Any]:
    """Trending topics on X. Mock data in mock mode; otherwise not_implemented."""
    if settings.MOCK_MODE:
        return {
            "status": "mock",
            "query": query,
            "trends": ["#MockTrendOne", "#MockTrendTwo", "#MockTrendThree"],
        }
    return _not_implemented("twitter_trend_search", "X API v2", bool(settings.TWITTER_API_KEY))


@tool("google_trends_analyzer")
def google_trends_analyzer(keyword: str) -> dict[str, Any]:
    """Search interest for a keyword. Mock data in mock mode; otherwise not_implemented."""
    if settings.MOCK_MODE:
        return {
            "status": "mock",
            "keyword": keyword,
            "interest_over_time": "mock",
            "related_topics": ["mock topic A", "mock topic B"],
        }
    return _not_implemented("google_trends_analyzer", "Google Trends", False)


@tool("instagram_analytics_fetcher")
def instagram_analytics_fetcher(client_id: str) -> dict[str, Any]:
    """Instagram reach and engagement. Mock data in mock mode; otherwise not_implemented."""
    if settings.MOCK_MODE:
        return {
            "status": "mock",
            "client_id": client_id,
            "reach": 0,
            "engagement_rate": "0%",
            "note": "mock data; no account was queried",
        }
    return _not_implemented(
        "instagram_analytics_fetcher", "Meta Graph API", bool(settings.META_ACCESS_TOKEN)
    )


@tool("buffer_post_scheduler")
def buffer_post_scheduler(content: str, platform: str, scheduled_time: str) -> dict[str, Any]:
    """Schedule a post via Buffer. Mock receipt in mock mode; otherwise not_implemented."""
    if settings.MOCK_MODE:
        return {
            "status": "mock",
            "platform": platform,
            "scheduled_time": scheduled_time,
            "note": "mock receipt; nothing was scheduled",
        }
    return _not_implemented("buffer_post_scheduler", "Buffer", bool(settings.BUFFER_ACCESS_TOKEN))


def get_all_tools() -> list:
    return [
        twitter_trend_search,
        google_trends_analyzer,
        instagram_analytics_fetcher,
        buffer_post_scheduler,
    ]


def _adapt(lc_tool):
    """
    Wrap one LangChain tool as a crewai tool.

    crewai 1.15's own ``BaseTool.from_langchain`` instantiates the abstract
    ``BaseTool`` and fails with "Can't instantiate abstract class ... without
    an implementation for abstract method '_run'". A subclass per tool is what
    it needs. This is a factory rather than a class in a loop so that ``_run``
    closes over *this* tool and not the last one the loop saw.
    """
    from crewai.tools import BaseTool as CrewBaseTool

    class Adapted(CrewBaseTool):
        name: str = lc_tool.name
        description: str = lc_tool.description
        args_schema: type = lc_tool.args_schema

        def _run(self, **kwargs: Any) -> Any:
            return lc_tool.invoke(kwargs)

    Adapted.__name__ = f"Adapted_{lc_tool.name}"
    return Adapted()


def crewai_tools() -> list:
    """
    The tools in the form a crewai Agent accepts.

    The previous code assigned LangChain tools to ``agent.tools`` after
    construction. crewai validates that field against its own ``BaseTool``,
    so in live mode the assignment would have been rejected -- one more
    failure that mock mode never reached.
    """
    tools = get_all_tools()
    try:
        import crewai.tools  # noqa: F401
    except ImportError:
        return tools
    return [_adapt(tool) for tool in tools]
