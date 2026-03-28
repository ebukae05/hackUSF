# Google ADK (Agent Development Kit) — Reference

## Installation

```bash
pip install google-adk
```

> **NOTE (2026-03-28):** ADK not installed on this machine. Import paths below are from official docs (google.github.io/adk-docs). After `pip install google-adk`, verify imports work:
> ```python
> from google.adk.agents import Agent, SequentialAgent, LoopAgent
> from google.adk.agents.parallel_agent import ParallelAgent
> from google.adk.tools.tool_context import ToolContext
> ```

## Project Structure

```
parent_folder/
    my_agent/
        __init__.py
        agent.py
        .env
```

**.env:**
```
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=YOUR_API_KEY_HERE
```

**__init__.py:**
```python
from . import agent
```

## Running

```bash
adk web          # Dev UI at http://localhost:8000
adk run my_agent # Terminal mode
```

---

## Agent Types

| Type | Class | Purpose |
|---|---|---|
| LLM Agent | `Agent` / `LlmAgent` | LLM-powered reasoning, tool use, dynamic decisions |
| Sequential Agent | `SequentialAgent` | Runs sub-agents in order |
| Parallel Agent | `ParallelAgent` | Runs sub-agents concurrently |
| Loop Agent | `LoopAgent` | Runs sub-agents iteratively until condition met |
| Custom Agent | extends `BaseAgent` | Custom control flow |

---

## LlmAgent / Agent

The core reasoning agent. Uses an LLM to understand, plan, and act.

### Constructor Parameters

| Parameter | Required | Description |
|---|---|---|
| `name` | Yes | Unique identifier. Avoid `user` as name. |
| `model` | Yes | LLM model string (e.g. `"gemini-2.5-flash"`) |
| `description` | Recommended | What the agent does — used by other agents for routing |
| `instruction` | Recommended | System prompt guiding behavior. Supports `{state_var}` templates. |
| `tools` | Optional | List of functions or `BaseTool` instances |
| `output_key` | Optional | Store final response in session state under this key |
| `include_contents` | Optional | `'default'` or `'none'` — controls conversation history access |
| `generate_content_config` | Optional | LLM params: temperature, max_output_tokens, etc. |
| `input_schema` | Optional | Pydantic BaseModel for expected input |
| `output_schema` | Optional | Pydantic BaseModel for expected output |
| `planner` | Optional | `BuiltInPlanner` or `PlanReActPlanner` for multi-step reasoning |

### Example

```python
from google.adk.agents import Agent

def get_weather(city: str) -> dict:
    """Retrieves current weather for a city."""
    if city.lower() == "new york":
        return {"status": "success", "report": "Sunny, 25C"}
    return {"status": "error", "error_message": f"No data for {city}"}

def get_current_time(city: str) -> dict:
    """Returns current time in specified city."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz_map = {"new york": "America/New_York", "tampa": "America/New_York"}
    tz_id = tz_map.get(city.lower())
    if not tz_id:
        return {"status": "error", "error_message": f"No timezone for {city}"}
    now = datetime.now(ZoneInfo(tz_id))
    return {"status": "success", "report": now.strftime("%Y-%m-%d %H:%M:%S %Z")}

root_agent = Agent(
    name="weather_time_agent",
    model="gemini-2.5-flash",
    description="Answers questions about time and weather.",
    instruction="You are a helpful agent. Use tools to answer questions about time and weather.",
    tools=[get_weather, get_current_time],
)
```

### Tools

Functions are auto-wrapped as `FunctionTool`. Just pass Python functions directly:

```python
def my_tool(param1: str, param2: int) -> dict:
    """Docstring becomes the tool description."""
    return {"result": "value"}

agent = Agent(
    name="my_agent",
    model="gemini-2.5-flash",
    tools=[my_tool]
)
```

### output_key (Inter-Agent Communication)

```python
researcher = LlmAgent(
    name="researcher",
    model="gemini-2.5-flash",
    instruction="Research the topic.",
    output_key="research_result"  # Stored in session state
)

writer = LlmAgent(
    name="writer",
    model="gemini-2.5-flash",
    instruction="Write a report using: {research_result}",  # Access via template
    output_key="final_report"
)
```

---

## SequentialAgent

Runs sub-agents in order. Shares `InvocationContext` across all sub-agents.

```python
from google.adk.agents import SequentialAgent

pipeline = SequentialAgent(
    name="CodePipelineAgent",
    sub_agents=[code_writer, code_reviewer, code_refactorer],
    description="Write, review, then refactor code"
)
```

### Parameters
- `name`: Agent identifier
- `sub_agents`: List of agents to run in order
- `description`: What the pipeline does

### Data flow
Sub-agents pass data via `output_key`. Each agent stores output in session state, next agent reads via `{key_name}` template.

---

## ParallelAgent

Runs sub-agents concurrently. No automatic sharing of state between parallel branches.

```python
from google.adk.agents.parallel_agent import ParallelAgent

parallel_research = ParallelAgent(
    name="ParallelResearchAgent",
    sub_agents=[researcher_1, researcher_2, researcher_3],
    description="Runs multiple researchers in parallel"
)
```

### Parameters
- `name`: Agent identifier
- `sub_agents`: List of agents to run concurrently
- `description`: What the parallel group does

### How it works
1. All sub-agents' `run_async()` start simultaneously
2. Each operates independently — NO automatic state sharing
3. Results collected after all complete (order non-deterministic)

### Collecting results — use output_key

```python
researcher_1 = LlmAgent(
    name="DisasterMonitor",
    model="gemini-2.5-flash",
    instruction="Monitor FEMA/NOAA for active disasters.",
    tools=[check_fema_alerts],
    output_key="disaster_data"  # Stored in state
)

researcher_2 = LlmAgent(
    name="ResourceScanner",
    model="gemini-2.5-flash",
    instruction="Inventory available resources from all sources.",
    tools=[scan_resources],
    output_key="resource_data"  # Stored in state
)

researcher_3 = LlmAgent(
    name="NeedMapper",
    model="gemini-2.5-flash",
    instruction="Map community needs using vulnerability data.",
    tools=[get_vulnerability_data],
    output_key="needs_data"  # Stored in state
)

# Run all three in parallel
parallel_agent = ParallelAgent(
    name="DataGathering",
    sub_agents=[researcher_1, researcher_2, researcher_3]
)

# Then synthesize results sequentially
synthesizer = LlmAgent(
    name="MatchOptimizer",
    model="gemini-2.5-flash",
    instruction="""Match resources to needs:
    Disaster data: {disaster_data}
    Resources: {resource_data}
    Needs: {needs_data}
    Produce equity-weighted routing plan.""",
    output_key="routing_plan"
)

# Full pipeline
root_agent = SequentialAgent(
    name="ReliefLink",
    sub_agents=[parallel_agent, synthesizer]
)
```

---

## LoopAgent

Runs sub-agents iteratively until termination condition or max iterations.

```python
from google.adk.agents import LoopAgent

refinement_loop = LoopAgent(
    name="RefinementLoop",
    sub_agents=[critic_agent, refiner_agent],
    max_iterations=5
)
```

### Parameters
- `name`: Agent identifier
- `sub_agents`: List of agents to run sequentially per iteration
- `max_iterations`: Maximum loop cycles before forced stop

### Termination strategies

**1. Max iterations (automatic):**
```python
LoopAgent(sub_agents=[agent1, agent2], max_iterations=5)
```

**2. Sub-agent escalation (programmatic exit):**
```python
from google.adk.tools.tool_context import ToolContext

def exit_loop(tool_context: ToolContext):
    """Call this to exit the optimization loop when results are satisfactory."""
    tool_context.actions.escalate = True
    tool_context.actions.skip_summarization = True
    return {}

optimizer = LlmAgent(
    name="Optimizer",
    model="gemini-2.5-flash",
    instruction="""Review the current routing plan.
    If all high-vulnerability communities are served, call exit_loop.
    Otherwise, re-optimize the allocation.""",
    tools=[exit_loop, reoptimize_matches],
    output_key="optimized_plan"
)

loop = LoopAgent(
    name="OptimizationLoop",
    sub_agents=[evaluator, optimizer],
    max_iterations=5
)
```

### Full LoopAgent example (document refinement pattern):

```python
from google.adk.agents import LoopAgent, LlmAgent, SequentialAgent
from google.adk.tools.tool_context import ToolContext

GEMINI_MODEL = "gemini-2.5-flash"

def exit_loop(tool_context: ToolContext):
    tool_context.actions.escalate = True
    tool_context.actions.skip_summarization = True
    return {}

critic = LlmAgent(
    name="CriticAgent",
    model=GEMINI_MODEL,
    include_contents='none',
    instruction="""Review the routing plan quality.
    If all communities are adequately served, respond: "No major issues found."
    Otherwise provide specific feedback.""",
    output_key="criticism"
)

refiner = LlmAgent(
    name="RefinerAgent",
    model=GEMINI_MODEL,
    include_contents='none',
    instruction="""If critique is "No major issues found.", call exit_loop.
    Otherwise, apply suggestions to improve the plan.""",
    tools=[exit_loop],
    output_key="current_plan"
)

refinement_loop = LoopAgent(
    name="RefinementLoop",
    sub_agents=[critic, refiner],
    max_iterations=5
)
```

---

## A2A (Agent-to-Agent Protocol)

Enables agents to communicate across distributed services.

### Key concepts
- Agents can be **exposed** (made available for others to call) or **consumed** (call remote agents)
- Supports Python, Go, Java
- Full spec at https://a2a-protocol.org/

### Usage patterns
1. **Expose** your agent as an A2A endpoint for other agents to consume
2. **Consume** remote agents from within your agent system

### Setup guides
- Python exposing: https://google.github.io/adk-docs/a2a/python/expose/
- Python consuming: https://google.github.io/adk-docs/a2a/python/consume/

---

## Common Patterns for ReliefLink

### Pattern 1: Parallel data gathering + Sequential synthesis

```python
from google.adk.agents import Agent, SequentialAgent, LoopAgent
from google.adk.agents.parallel_agent import ParallelAgent

# Step 1: Parallel data gathering
parallel_gather = ParallelAgent(
    name="DataGathering",
    sub_agents=[disaster_monitor, resource_scanner, need_mapper]
)

# Step 2: Match optimization loop
match_loop = LoopAgent(
    name="MatchOptimization",
    sub_agents=[match_generator, equity_evaluator],
    max_iterations=3
)

# Step 3: Full pipeline
root_agent = SequentialAgent(
    name="ReliefLinkPipeline",
    sub_agents=[parallel_gather, match_loop],
    description="Disaster response coordination pipeline"
)
```

### Pattern 2: Tool-using agent with ToolContext

```python
from google.adk.tools.tool_context import ToolContext

def check_fema_alerts(tool_context: ToolContext) -> dict:
    """Check FEMA for active disaster declarations."""
    # Access session state
    state = tool_context.state
    # Make API call
    import requests
    resp = requests.get("https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries?$top=5&$orderby=declarationDate desc")
    return resp.json()
```
