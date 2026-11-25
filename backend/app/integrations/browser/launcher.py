import argparse
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from getpass import getpass
from pathlib import Path
from uuid import UUID, uuid4

import httpx2
from playwright.sync_api import Error as PlaywrightError, Page, sync_playwright

from ...schs.browser import BrowserAction, BrowserResponse
from ...schs.browser_experience import CompanionPairing, WorkspaceStatus

_API = "http://127.0.0.1:8000/api/v1/browser"


class BrowserWorkspace:
    def __init__(self, client: httpx2.Client, agent: UUID, session: UUID, task: UUID) -> None:
        self._client = client
        self._binding = {"agent_id": agent, "session_id": session, "task_id": task}
        self._path = f"/workspace/{agent}/{session}/{task}"
        self._held: BrowserAction | None = None
        self._status: WorkspaceStatus | None = None

    def refresh(self) -> WorkspaceStatus:
        response = self._client.get(self._path)
        response.raise_for_status()
        self._status = WorkspaceStatus.model_validate(response.json())
        return self._status

    def submit(self, capability: str) -> BrowserResponse:
        status = self.refresh()
        if (not status.configured or status.session_status != "active" or status.agent_status != "active"
                or status.task_status != "pending"):
            raise ValueError("Workspace is not active")
        if capability == "retry":
            if self._held is None:
                raise ValueError("No held action")
            body = self._held
            if not any(cap.id == body.capability_id for cap in status.capabilities):
                raise ValueError("Capability is no longer available")
        else:
            scope = next((cap for cap in status.capabilities if str(cap.id) == capability), None)
            if scope is None:
                raise ValueError("Capability is not available")
            body = BrowserAction(request_id=uuid4(), **self._binding, capability_id=scope.id,
                                 action=scope.action, url=scope.resource, timestamp=datetime.now(UTC))
        response = self._client.post("/actions", json=body.model_dump(mode="json"))
        response.raise_for_status()
        result = BrowserResponse.model_validate(response.json())
        self._held = body if result.decision.outcome == "HOLD" and result.approval_id else None
        return result

    def handle(self, operation: str, argument: str = "") -> dict:
        try:
            if operation == "status":
                return {"status": self.refresh().model_dump(mode="json"), "retry": self._held is not None}
            if operation == "execute" and isinstance(argument, str) and len(argument) <= 36:
                return {"result": self.submit(argument).model_dump(mode="json")}
            return {"error": "Unsupported workspace operation."}
        except httpx2.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                expired = self._status and self._status.session_expires_at <= datetime.now(UTC)
                return {"error": "Agent session expired." if expired else "Agent credential expired, was revoked, or does not match this session."}
            if exc.response.status_code == 404:
                return {"error": "Browser agent, session, and task are not bound."}
            if exc.response.status_code == 502:
                return {"error": "Backend reported a browser execution failure. The page was not updated."}
            return {"error": "Backend could not complete this request."}
        except httpx2.RequestError:
            return {"error": "Backend disconnected. Action completion is unknown if a request was in flight."}
        except ValueError:
            return {"error": "Operation unavailable for this workspace or capability."}


@contextmanager
def open_console(workspace: BrowserWorkspace, *, headless: bool = False) -> Iterator[Page]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless, chromium_sandbox=True)
        try:
            context = browser.new_context(offline=True, accept_downloads=False, service_workers="block")
            try:
                context.route("**/*", lambda route: route.abort())
                page = context.new_page()

                def bridge(source, operation: str, argument: str = "") -> dict:
                    if source["frame"] != page.main_frame or page.url != "about:blank":
                        return {"error": "Untrusted workspace frame."}
                    if operation == "stop":
                        page.close()
                        return {}
                    return workspace.handle(operation, argument)

                page.expose_binding("proxi", bridge)
                page.set_content(Path(__file__).with_name("workspace.html").read_text(encoding="utf-8"))
                yield page
            finally:
                context.close()
        finally:
            browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Local PROXI Browser and Chrome companion pairing")
    commands = parser.add_subparsers(dest="command", required=True)
    launch = commands.add_parser("launch", help="Open the isolated browser console")
    for name in ("agent", "session", "task"):
        launch.add_argument(name, type=UUID)
    commands.add_parser("pair", help="Mint a five-minute Chrome companion token")
    args = parser.parse_args()
    token = getpass("Owner token: " if args.command == "pair" else "Agent credential: ").strip()
    with httpx2.Client(base_url=_API, headers={"Authorization": f"Bearer {token}"}, trust_env=False,
                      follow_redirects=False, timeout=20) as client:
        if args.command == "pair":
            try:
                response = client.post("/companion/pairing", json={})
                response.raise_for_status()
                pairing = CompanionPairing.model_validate(response.json())
            except (httpx2.HTTPError, ValueError):
                parser.exit(1, "Pairing failed. Check the local backend, owner token and extension ID.\n")
            print(f"Paste into PROXI Companion within {pairing.expires_in} seconds: {pairing.token}")
        else:
            workspace = BrowserWorkspace(client, args.agent, args.session, args.task)
            try:
                with open_console(workspace) as page:
                    page.wait_for_event("close", timeout=0)
            except KeyboardInterrupt:
                pass
            except PlaywrightError:
                if "page" not in locals() or not page.is_closed():
                    parser.exit(1, "Could not run Chromium. Check the Playwright browser installation.\n")


if __name__ == "__main__":
    main()
