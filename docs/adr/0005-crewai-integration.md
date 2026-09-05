# ADR 0005 — crewai gets its own LLM with an explicit key; LangChain tools are adapted, not assigned

**Status:** accepted

## Context

Two integration details that mock mode never reached, found only when the
tests started exercising the live path with fakes and with the real `crewai`:

1. `AgentFactory` built a LangChain `ChatOpenAI` and passed it to
   `crewai.Agent(llm=...)`. crewai unwraps such objects, reads the model name,
   and builds its own client — taking the key from `os.environ`. A key that
   lives only in `.env` (read by pydantic-settings, never exported) is
   invisible to that path. The failure is "Missing credentials" from inside
   `crew.kickoff()`, with the key plainly configured.
2. Nodes did `agent.tools = get_all_tools()` — LangChain tools assigned to a
   crewai agent after construction. crewai validates that field against its
   own `BaseTool`. Its converter, `BaseTool.from_langchain`, instantiates the
   abstract class and fails in 1.15.20 (`Can't instantiate abstract class
   BaseTool without an implementation for abstract method '_run'`).

## Decision

`build_llm()` returns `crewai.LLM(model=settings.OPENAI_MODEL, api_key=...)`
with the key passed explicitly. A test deletes `OPENAI_API_KEY` from the
environment, sets it in settings only, and constructs the real object.

`crewai_tools()` wraps each LangChain tool in a `crewai.tools.BaseTool`
subclass with a `_run` that delegates. The subclass is built by a factory
function, not a class statement inside a loop, so each `_run` closes over its
own tool — a test dispatches through two adapters and checks each reached the
right one. Tools are passed to `Agent(tools=...)` at construction.

`langchain` and `langchain-openai` are no longer imported by anything and are
removed from `requirements.txt`; `langchain-core` stays for the `@tool`
decorator that defines the tools once.

## Consequences

The live path is exercised by tests with fake crewai objects and, for
construction, by the real package. It has **not** been run against the OpenAI
API in this repository; the README says so.
