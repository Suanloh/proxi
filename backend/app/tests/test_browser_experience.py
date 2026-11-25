import json
import socket
from contextlib import contextmanager
from pathlib import Path
from threading import Thread
from time import monotonic, sleep
from uuid import UUID, uuid4

import httpx2
import pytest
import uvicorn
from fastapi import FastAPI
from playwright.sync_api import expect, sync_playwright
from pydantic import SecretStr

from app.api.browser_experience import create_browser_experience_router
from app.api.owner_auth import create_owner_auth
from app.integrations.browser.launcher import BrowserWorkspace, open_console
from app.integrations.browser.playwright import SUPPORTED_ACTIONS


def test_console_uses_bound_actions_and_shuts_down() -> None:
    agent, session, task, cap, approval = [str(uuid4()) for _ in range(5)]
    requests = []
    online = True
    workspace_status = dict(agent_name="Demo agent", agent_status="active", session_status="active",
                            session_expires_at="2099-01-01T00:00:00Z", task_name="Compare flights",
                            task_status="pending", configured=True, capabilities=[dict(id=cap, action="browser.read",
                            resource="https://example.org/")], pending_approvals=[], events=[])

    def backend(request):
        assert request.headers["Authorization"] == "Bearer test-agent"
        if not online:
            raise httpx2.ConnectError("offline", request=request)
        if request.method == "GET":
            assert request.url.path == f"/browser/workspace/{agent}/{session}/{task}"
            return httpx2.Response(200, json=workspace_status)
        assert request.method == "POST" and request.url.path == "/browser/actions"
        body = json.loads(request.content)
        assert (body["agent_id"], body["session_id"], body["task_id"], body["capability_id"]) == (agent, session, task, cap)
        requests.append(body)
        if len(requests) == 1:
            outcome, reason, result = "HOLD", "approval_required", None
            workspace_status["pending_approvals"] = [dict(id=approval, action="browser.read", expires_at="2099-01-01T00:00:00Z")]
        elif len(requests) == 2:
            outcome, reason = "ALLOW", "checks_passed"
            result = dict(title="Flight fares", text="<img src=x onerror=alert(1)>", url="https://example.org/")
            workspace_status["pending_approvals"] = []
        else:
            outcome, reason, result = "BLOCK", "adapter_unavailable", None
        return httpx2.Response(200, json=dict(decision=dict(request_id=body["request_id"], outcome=outcome, reason=reason),
                                             executed=result is not None, result=result,
                                             approval_id=approval if outcome == "HOLD" else None))

    with httpx2.Client(base_url="http://127.0.0.1:8000/browser", headers={"Authorization": "Bearer test-agent"},
                      transport=httpx2.MockTransport(backend)) as client:
        workspace = BrowserWorkspace(client, UUID(agent), UUID(session), UUID(task))
        with open_console(workspace, headless=True) as page:
            expect(page.locator("#task")).to_contain_text("Compare flights")
            page.locator("#execute").click()
            expect(page.locator("#notice")).to_contain_text("Approval required")
            expect(page.locator("#approvals")).to_contain_text(approval)
            page.locator("#retry").click()
            expect(page.locator("#website")).to_contain_text("Flight fares")
            expect(page.locator("#pageText")).to_have_text("<img src=x onerror=alert(1)>")
            expect(page.locator("img")).to_have_count(0)
            assert requests[0] == requests[1]
            workspace_status["capabilities"][0]["action"] = "browser.click"
            expect(page.locator("#capability")).to_contain_text("browser.click")
            page.locator("#execute").click()
            expect(page.locator("#notice")).to_contain_text("Blocked")
            expect(page.locator("#website")).to_contain_text("Flight fares")
            workspace_status["capabilities"] = []
            workspace_status["events"] = [dict(event_type="CapabilityRevoked", action="browser.read",
                                                outcome=None, reason=None, created_at="2026-11-25T00:00:00Z")]
            expect(page.locator("#events")).to_contain_text("Capability revoked")
            expect(page.locator("#execute")).to_be_disabled()
            workspace_status["session_status"] = "expired"
            expect(page.locator("#session")).to_have_text("Agent session expired")
            online = False
            expect(page.locator("#connection")).to_contain_text("Backend disconnected")
            expect(page.locator("#execute")).to_be_disabled()
            assert page.evaluate("proxi('unexpected')") == {"error": "Unsupported workspace operation."}
            with page.expect_event("close"):
                page.locator("#stop").click(no_wait_after=True)
        assert page.is_closed()


def test_unpacked_extension_connects_only_with_pairing(tmp_path, monkeypatch) -> None:
    extension = Path(__file__).resolve().parents[3] / "chrome-extension"
    owner = uuid4()
    owner_token = "test-owner-token-" * 3

    class Identity:
        def require_active_owner(self, requested):
            assert requested == owner

    @contextmanager
    def transaction(_request):
        yield None, Identity()

    monkeypatch.setattr("app.api.browser_experience.browser_events", lambda _db, _owner: [dict(
        event_type="ActionBlocked", action="browser.click", reason="adapter_unavailable", outcome="BLOCK",
        created_at="2026-11-25T00:00:00Z",
    )])
    monkeypatch.setattr(uvicorn.Server, "install_signal_handlers", lambda self: None, raising=False)
    with socket.socket() as listener:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            listener.bind(("127.0.0.1", 8000))
        except OSError:
            pytest.skip("Local PROXI port 8000 is already in use")
        listener.listen()
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                str(tmp_path / "profile"), channel="chromium", headless=True, chromium_sandbox=True,
                args=[f"--disable-extensions-except={extension}", f"--load-extension={extension}"],
            )
            try:
                worker = context.service_workers[0] if context.service_workers else context.wait_for_event("serviceworker")
                origin = worker.url.rsplit("/", 1)[0]
                extension_id = origin.split("://")[1]
                app = FastAPI()
                app.include_router(create_browser_experience_router(
                    create_owner_auth(owner, SecretStr(owner_token)), transaction, None,
                    None, lambda: True, extension_id,
                ), prefix="/api/v1")
                server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
                thread = Thread(target=server.run, kwargs={"sockets": [listener]})
                thread.start()
                try:
                    timeout = monotonic() + 5
                    while not server.started and monotonic() < timeout:
                        sleep(.01)
                    assert server.started
                    with httpx2.Client(base_url="http://127.0.0.1:8000/api/v1/browser/companion", trust_env=False) as client:
                        owner_headers = {"Authorization": f"Bearer {owner_token}"}
                        assert client.post("/pairing", headers={**owner_headers, "Origin": origin}, json={}).status_code == 403
                        minted = client.post("/pairing", headers=owner_headers, json={})
                        assert minted.status_code == 200
                        token = minted.json()["token"]
                        headers = {"Authorization": f"Bearer {token}", "Origin": origin}
                        assert client.post("/status", headers={**headers, "Origin": "http://example.org"}, json={}).status_code == 403
                        assert client.post("/status", headers=headers, json={"operation": "approve"}).status_code == 422
                        assert client.post("/status", headers={**owner_headers, "Origin": origin}, json={}).status_code == 401
                        page = context.pages[0]
                        page.goto(f"{origin}/popup.html")
                        page.locator("#token").fill(token)
                        page.get_by_role("button", name="Connect / Refresh").click()
                        expect(page.locator("#connection")).to_have_text("Connected to local PROXI.")
                        expect(page.locator("#operations")).to_have_text(", ".join(SUPPORTED_ACTIONS))
                        expect(page.locator("#events")).to_contain_text("Blocked")
                        assert client.post("/pairing", headers=owner_headers, json={}).status_code == 200
                        page.get_by_role("button", name="Connect / Refresh").click()
                        expect(page.locator("#connection")).to_contain_text("Pairing expired or invalid")
                finally:
                    server.should_exit = True
                    thread.join(10)
                    assert not thread.is_alive()
                page.locator("#token").fill(token)
                page.get_by_role("button", name="Connect / Refresh").click()
                expect(page.locator("#connection")).to_contain_text("Local backend disconnected")
            finally:
                context.close()
