"""Unit tests - no network. A fake client records the calls the tools make."""
import json

from langchain_relm import get_relm_tools
from langchain_relm.client import RelmClient


class FakeClient(RelmClient):
    def __init__(self):
        self.calls = []
        self.next_response = {"ok": True}

    def request(self, method, path, params=None, json_body=None):
        self.calls.append({"method": method, "path": path, "params": params, "json": json_body})
        return self.next_response


def tools_by_name(client):
    return {t.name: t for t in get_relm_tools(client=client)}


def test_exposes_expected_tools():
    names = set(tools_by_name(FakeClient()))
    assert {
        "relm_describe_schema", "relm_search", "relm_list", "relm_create_contact",
        "relm_create_company", "relm_create_deal", "relm_log_activity", "relm_move_deal",
    } <= names


def test_create_contact_drops_none_and_posts():
    c = FakeClient()
    c.next_response = {"id": "con_1", "object": "contact"}
    t = tools_by_name(c)["relm_create_contact"]
    out = t.invoke({"email": "ada@x.com", "type": "lead"})
    assert json.loads(out)["id"] == "con_1"
    call = c.calls[-1]
    assert call["method"] == "POST" and call["path"] == "/contacts"
    # None-valued fields (first_name, phone, ...) are omitted, not sent as null
    assert call["json"] == {"email": "ada@x.com", "type": "lead"}


def test_create_deal_sends_value_cents():
    c = FakeClient()
    t = tools_by_name(c)["relm_create_deal"]
    t.invoke({"title": "Acme - annual", "value_cents": 1850000, "company_id": "cmp_1"})
    assert c.calls[-1]["json"] == {"title": "Acme - annual", "value_cents": 1850000, "company_id": "cmp_1"}


def test_search_uses_q_param():
    c = FakeClient()
    tools_by_name(c)["relm_search"].invoke({"query": "diaz", "limit": 5})
    assert c.calls[-1] == {"method": "GET", "path": "/search", "params": {"q": "diaz", "limit": 5}, "json": None}


def test_list_maps_object_to_plural_path():
    c = FakeClient()
    tools_by_name(c)["relm_list"].invoke({"object": "deal", "q": "annual"})
    assert c.calls[-1]["path"] == "/deals" and c.calls[-1]["params"] == {"q": "annual", "limit": 25}


def test_move_deal_patches_stage():
    c = FakeClient()
    tools_by_name(c)["relm_move_deal"].invoke({"deal_id": "deal_1", "stage": "won"})
    assert c.calls[-1] == {"method": "PATCH", "path": "/deals/deal_1", "params": None, "json": {"stage": "won"}}


def test_error_body_is_passed_through(monkeypatch):
    # a real RelmClient returns {"error": <problem+json>} on 4xx so the agent self-corrects
    class Resp:
        status_code = 422
        def json(self):
            return {"code": "unknown_value", "valid_options": ["lead", "customer"], "suggestion": "lead"}
    client = RelmClient(api_key="relm_test_x")
    monkeypatch.setattr(client._session, "request", lambda *a, **k: Resp())
    out = client.get("/contacts", params={"type": "leed"})
    assert out["error"]["valid_options"] == ["lead", "customer"]
