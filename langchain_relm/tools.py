"""LangChain tools for Relm - the CRM for LLMs.

    from langchain_relm import get_relm_tools
    tools = get_relm_tools(api_key="relm_live_...")   # or set RELM_API_KEY
    # then hand `tools` to any LangChain / LangGraph agent

Every tool returns a JSON string. On a bad value the string is Relm's problem+json
(with ``valid_options`` and a ``suggestion``), so the agent fixes itself and retries.
"""
from __future__ import annotations

import json
from typing import List, Optional

from pydantic import BaseModel, Field

try:
    from langchain_core.tools import StructuredTool
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "langchain-relm needs langchain-core. Install it with `pip install langchain-relm` "
        "(or `pip install langchain-core`)."
    ) from exc

from .client import RelmClient, _drop_none


def _dump(x) -> str:
    return json.dumps(x, default=str, ensure_ascii=False)


# ---- argument schemas ----------------------------------------------------
class _NoArgs(BaseModel):
    pass


class _SearchArgs(BaseModel):
    query: str = Field(description="Text to match across contacts, companies and deals (name/email/title).")
    limit: int = Field(10, description="Max results (default 10).")


class _ListArgs(BaseModel):
    object: str = Field(description="One of: contact, company, deal, activity.")
    q: Optional[str] = Field(None, description="Optional substring filter (name/email/title/etc.).")
    limit: int = Field(25, description="Page size (max 100).")


class _CreateContactArgs(BaseModel):
    email: Optional[str] = Field(None, description="Email (unique per workspace).")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    company_id: Optional[str] = Field(None, description="cmp_ id of the contact's company.")
    type: Optional[str] = Field(None, description="A registered contact type, e.g. lead or customer.")


class _CreateCompanyArgs(BaseModel):
    name: str = Field(description="Company name (required).")
    domain: Optional[str] = None


class _CreateDealArgs(BaseModel):
    title: str = Field(description="Deal title (required).")
    value_cents: Optional[int] = Field(None, description="Amount in integer minor units (cents), not dollars.")
    stage: Optional[str] = Field(None, description="Stage key within the pipeline (defaults to the first stage).")
    pipeline: Optional[str] = Field(None, description="Pipeline key or pl_ id (defaults to the default pipeline).")
    company_id: Optional[str] = None
    primary_contact_id: Optional[str] = None


class _LogActivityArgs(BaseModel):
    body: str = Field(description="The note / call summary / message text.")
    type: str = Field("note", description="note, call, email, meeting or task.")
    contact_id: Optional[str] = Field(None, description="con_ id to attach to.")
    deal_id: Optional[str] = Field(None, description="deal_ id to attach to. At least one of contact_id/deal_id is required.")


class _MoveDealArgs(BaseModel):
    deal_id: str = Field(description="The deal_ id to move.")
    stage: str = Field(description="The stage key to move it to.")


def get_relm_tools(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    client: Optional[RelmClient] = None,
) -> List[StructuredTool]:
    """Return the Relm CRM tools bound to a client. Pass an api_key or set RELM_API_KEY."""
    c = client or RelmClient(api_key=api_key, base_url=base_url)

    def describe_schema() -> str:
        return _dump(c.get("/schema"))

    def search(query: str, limit: int = 10) -> str:
        return _dump(c.get("/search", params={"q": query, "limit": limit}))

    def list_records(object: str, q: Optional[str] = None, limit: int = 25) -> str:
        return _dump(c.get(f"/{object}s", params=_drop_none({"q": q, "limit": limit})))

    def create_contact(
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        company_id: Optional[str] = None,
        type: Optional[str] = None,
    ) -> str:
        return _dump(c.post("/contacts", _drop_none({
            "email": email, "first_name": first_name, "last_name": last_name,
            "phone": phone, "linkedin_url": linkedin_url, "company_id": company_id, "type": type,
        })))

    def create_company(name: str, domain: Optional[str] = None) -> str:
        return _dump(c.post("/companies", _drop_none({"name": name, "domain": domain})))

    def create_deal(
        title: str,
        value_cents: Optional[int] = None,
        stage: Optional[str] = None,
        pipeline: Optional[str] = None,
        company_id: Optional[str] = None,
        primary_contact_id: Optional[str] = None,
    ) -> str:
        return _dump(c.post("/deals", _drop_none({
            "title": title, "value_cents": value_cents, "stage": stage, "pipeline": pipeline,
            "company_id": company_id, "primary_contact_id": primary_contact_id,
        })))

    def log_activity(body: str, type: str = "note", contact_id: Optional[str] = None, deal_id: Optional[str] = None) -> str:
        return _dump(c.post("/activities", _drop_none({
            "body": body, "type": type, "contact_id": contact_id, "deal_id": deal_id,
        })))

    def move_deal(deal_id: str, stage: str) -> str:
        return _dump(c.patch(f"/deals/{deal_id}", {"stage": stage}))

    return [
        StructuredTool.from_function(
            describe_schema, name="relm_describe_schema", args_schema=_NoArgs,
            description="Return Relm's live schema: every object, its fields (built-in + custom), id prefixes, list filters and all enum values. ALWAYS call this before guessing a type, stage or field - it is the source of truth for what exists.",
        ),
        StructuredTool.from_function(
            search, name="relm_search", args_schema=_SearchArgs,
            description="Search across contacts, companies and deals by name, email or title. Use it to find a record's id before updating or linking it.",
        ),
        StructuredTool.from_function(
            list_records, name="relm_list", args_schema=_ListArgs,
            description="List records of an object (contact/company/deal/activity), newest first, with an optional `q` substring filter.",
        ),
        StructuredTool.from_function(
            create_contact, name="relm_create_contact", args_schema=_CreateContactArgs,
            description="Create a contact. Needs at least one of: a name, an identifier (email/phone/linkedin_url), or a company. Email is unique per workspace - a duplicate returns the existing contact. Do not invent a placeholder email.",
        ),
        StructuredTool.from_function(
            create_company, name="relm_create_company", args_schema=_CreateCompanyArgs,
            description="Create a company (name required). Returns a cmp_ id you can pass as company_id on contacts and deals.",
        ),
        StructuredTool.from_function(
            create_deal, name="relm_create_deal", args_schema=_CreateDealArgs,
            description="Open a deal. value_cents is integer cents (e.g. $18,500 -> 1850000). Defaults to the default pipeline and its first stage.",
        ),
        StructuredTool.from_function(
            log_activity, name="relm_log_activity", args_schema=_LogActivityArgs,
            description="Log an activity (note/call/email/meeting/task) on a contact and/or deal. At least one of contact_id or deal_id is required.",
        ),
        StructuredTool.from_function(
            move_deal, name="relm_move_deal", args_schema=_MoveDealArgs,
            description="Move a deal to a different stage. If the stage does not exist, the error lists valid_options.",
        ),
    ]
