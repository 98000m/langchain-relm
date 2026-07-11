# langchain-relm

LangChain tools for [**Relm**](https://relmcrm.com) - the CRM for LLMs and AI agents.

Give a LangChain / LangGraph agent a real CRM: create and find contacts, companies and
deals, log activities, and move deals through a pipeline - in a few typed tools. Relm's
errors are RFC-9457 problem+json with `valid_options` and a `suggestion`, and this
adapter passes them straight back to the model, so your agent **self-corrects in one
turn** instead of crashing on a bad field or stage.

## Install

```bash
pip install langchain-relm
```

## Quickstart

Mint a free key (and a free test-mode key) at [app.relmcrm.com](https://app.relmcrm.com/), then:

```python
from langchain_relm import get_relm_tools
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

tools = get_relm_tools(api_key="relm_live_...")   # or set RELM_API_KEY
agent = create_react_agent(ChatOpenAI(model="gpt-4o"), tools)

agent.invoke({"messages": [(
    "user",
    "Add Maria Diaz (maria@acmelogistics.com) as a lead, create Acme Logistics "
    "as her company, and open a $18,500 deal for the annual plan.",
)]})
```

The agent calls `relm_describe_schema` to learn what exists, then creates the company,
the contact and the deal - and if it sends a stage or type that doesn't exist, Relm
hands back the valid options and it retries.

## The tools

| Tool | What it does |
|---|---|
| `relm_describe_schema` | The live contract: objects, fields, id prefixes, filters, enum values. Call it first. |
| `relm_search` | Find a contact/company/deal by name, email or title. |
| `relm_list` | List records of an object with an optional `q` filter. |
| `relm_create_contact` | Create a person (email/phone/linkedin/name/company - at least one). |
| `relm_create_company` | Create an account. |
| `relm_create_deal` | Open a deal (`value_cents` is integer cents). |
| `relm_log_activity` | Log a note/call/email/meeting/task on a contact and/or deal. |
| `relm_move_deal` | Move a deal to another stage. |

## Direct client

Skip the tools and call the API yourself:

```python
from langchain_relm import RelmClient

relm = RelmClient(api_key="relm_live_...")
relm.get("/schema")
relm.post("/contacts", {"email": "ada@example.com", "type": "lead"})
```

## Notes

- **Test mode is free.** A `relm_test_` key writes to an isolated, unmetered dataset -
  rehearse there, then swap one string.
- **Native MCP + A2A too.** Prefer MCP? Relm ships a native MCP server at
  `https://api.relmcrm.com/mcp` and an A2A endpoint - see the
  [agent hub](https://relmcrm.com/agents).
- Docs: [relmcrm.com/docs](https://relmcrm.com/docs) · OpenAPI:
  [relmcrm.com/openapi.json](https://relmcrm.com/openapi.json)

## License

MIT
