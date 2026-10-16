# Skeleton framework comparison: 4-hour agent workshop (as of 2026-10-16 KST)

Audience: 16 3rd/4th-year students who use Cursor and Claude and have API keys. Each student builds a different agent from a shared skeleton.

## Versions (PyPI JSON API, checked 2026-10-16; upload times in UTC)
| Package | Latest | Released |
|---|---|---|
| aisuite | 0.2.0 | 2026-09-18 |
| langchain | 1.4.6 | 2026-10-14 |
| langgraph | 1.2.15 | 2026-10-12 |
| openai-agents | 0.24.0 | 2026-10-15 |
| claude-agent-sdk | 0.2.168 | 2026-10-15 |
| pydantic-ai | 2.57.0 | 2026-10-16 |
| google-adk | 2.12.0 | 2026-10-13 |

aisuite ships much less often: there was a month between releases. Every other package released within the last few days.

## (a) aisuite 0.2.0 (https://github.com/andrewyng/aisuite, docs/agents-quickstart.md)
What the quickstart documents:
- `client.chat.completions.create(..., tools=[py_funcs], max_turns=N)`. The tool schema is built from the function's docstring, and the tool loop runs automatically. `intermediate_messages` holds the history.
- Manual mode: leave out `max_turns` and you get back the raw tool calls, so you write the loop yourself. This is good for teaching.
- `Agent(name, model, instructions, tools)` with `Runner.run(agent, input)` returns `final_output`.
- Toolkits: `ai.toolkits.files/git/shell(root=...)`.
- MCP: an inline `{"type":"mcp", command, args}` entry, or `aisuite.mcp.MCPClient(...).get_callable_tools()`, with security filters and tool prefixes.
- Policies: `RequireApprovalPolicy`, `AllowToolsPolicy`, `DenyAllToolPolicy`, or any callable that takes a `ToolPolicyContext`. This is a human-in-the-loop hook.
- State stores: InMemory, File, or Postgres, keyed by `thread_id` so a run can resume.
- Artifacts (File/InMemory). Tracing: `RunResult` steps, `trace_id`, trace sinks.

Gaps I found (from the quickstart; the source code would need checking to confirm):
- The quickstart shows no graph, branching, or orchestration primitive. Multi-agent work would be plain Python calling `Runner.run` more than once.
- It does not document lifecycle hooks or middleware (before/after model, before/after tool) apart from tool policies. It also does not document context management such as summarization or trimming.
- It does not show structured output, streaming in the Runner, guardrails, handoffs, an evals helper, a skills concept, or long-term memory.
- MCP examples cover stdio only. They don't show remote HTTP/SSE servers, OAuth, or what happens to the MCPClient's lifetime inside a Runner.
- The quickstart examples still use `openai:gpt-4o`. Swapping in a newer model string is trivial.
- The community and ecosystem are small, so students will find fewer answers on Stack Overflow or Discord, and LLMs know the API less well.

Assessment:
- Difficulty: lowest. The code is close to the raw API, so students can see exactly what the loop does.
- Connectivity: many providers, MCP, three toolkits.
- Trends: covers tool calling and MCP; HITL is basic; it lacks hooks, skills, and graphs.
- Flexibility: good for single-agent tool apps.
- Loop engineering: excellent. `max_turns` vs. the manual loop compares directly to Andrew Ng's course.
- Graph engineering: weak; you write it by hand.

## (b) LangChain v1 `create_agent` + middleware + LangGraph
Docs: https://docs.langchain.com/oss/python/langchain/agents , /middleware , https://docs.langchain.com/oss/python/langgraph/overview
- `create_agent(model="anthropic:claude-sonnet-4-6", tools=[...], system_prompt=...)`. It runs on a LangGraph graph underneath.
- Middleware hooks: `before_model`, `after_model`, `wrap_model_call`, `wrap_tool_call`. Built-in middleware includes summarization, human-in-the-loop (interrupts), model/tool call limits, PII redaction, retry, and model fallback.
- MCP via `langchain-mcp-adapters` (`MultiServerMCPClient`, stdio and HTTP).
- The LangGraph layer gives you a StateGraph, conditional edges, checkpointers (memory, SQLite, Postgres), `interrupt()`, persistence and time travel, a long-term memory Store, and multi-agent setups (supervisor/swarm).
- LangSmith adds tracing and evals.
- Assessment:
  - Difficulty: medium. There are many concepts, and the docs history is noisy because older v0.x tutorials still circulate. Community complaints about abstraction overhead are common, though v1 slimmed it down.
  - Connectivity: the largest ecosystem.
  - Trends: covers all of them (middleware, HITL, memory, tracing/evals).
  - Flexibility: highest.
  - Loop engineering: good through middleware (call limits, summarization, retry). The loop itself is hidden inside `create_agent`.
  - Graph engineering: best in class.

## (c) Others (brief)
- **OpenAI Agents SDK** (https://openai.github.io/openai-agents-python/): Agent, Runner, `max_turns`, handoffs, guardrails, sessions, built-in tracing, MCP (stdio, HTTP), and other providers through LiteLLM. Very easy, and the trace UI is strong. It has no graphs, and it works best with OpenAI models.
- **Claude Agent SDK** (https://docs.claude.com/en/api/agent-sdk/overview): the Claude Code harness as a library. It has built-in file/shell/web tools, hooks, skills, subagents, MCP, and permissions. It is the most powerful "out of the box", but it only runs Claude, the loop is opaque, and you have to install the Claude Code CLI. It suits coding or ops agents but is a poor fit for teaching the loop.
- **Pydantic AI** (https://ai.pydantic.dev/): type-safe tools, structured output, many providers, MCP client, Logfire tracing, `pydantic_evals`, and `pydantic-graph`. It is clean and testable, and its eval story is strong. It has moderate difficulty and a smaller ecosystem than LangChain.
- **Google ADK** (https://google.github.io/adk-docs/): LlmAgent plus Sequential/Parallel/Loop workflow agents, callbacks, sessions/memory, MCP, an eval CLI, and a dev web UI. Other providers work through LiteLLM. The `LoopAgent` and workflow agents make good teaching material. It leans toward Gemini/GCP and is heavier to set up.

## Scorecard (5 = best)
| | Difficulty (easy=5) | Connectivity | Trend fit | Flexibility | Loop eng. | Graph eng. |
|---|---|---|---|---|---|---|
| aisuite | 5 | 4 | 3 | 3 | 5 | 2 |
| LangChain v1 + LangGraph | 3 | 5 | 5 | 5 | 4 | 5 |
| OpenAI Agents SDK | 4 | 4 | 4 | 4 | 4 | 2 |
| Claude Agent SDK | 4 | 3 (Claude only) | 5 | 3 | 2 | 2 |
| Pydantic AI | 3 | 4 | 4 | 4 | 4 | 3 |
| Google ADK | 3 | 4 | 4 | 4 | 4 | 4 |
These scores are my judgment, not measured benchmarks.

## Recommendation (hybrid)
1. **Hour 1, loop engineering in aisuite:** students write the manual tool loop themselves, then compare it with `max_turns`. Add a reflection step, retries, and a stop condition. This ties directly to Andrew Ng's lectures.
2. **Hours 2–3, the shared skeleton on LangChain v1 `create_agent`:** use the same model string as aisuite, MCP adapters, and middleware for call limits, summarization, HITL, and retry. Each student swaps in their own tools and MCP servers and writes their own system prompt.
3. **Graph extension for students who need branching or multi-agent:** drop down to a LangGraph StateGraph with a checkpointer. Show this as an optional track, around 30 minutes.
4. **Evals and tracing:** use LangSmith, or a simple CSV of test prompts plus an LLM-as-judge script, following the course's error-analysis method.

If you want only one framework, use LangChain v1 + LangGraph. It is the only option strong on both graph engineering and middleware. Use aisuite only if simplicity matters more than graphs.
Pin the versions in requirements.txt and test them the day before, because LangChain, LangGraph and the other SDKs released several times this week.
