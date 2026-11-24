from time import monotonic

import httpx2
from playwright.sync_api import Error as PlaywrightError, Route, sync_playwright

from ...schs.authz import ActionRequest, Reason
from ...schs.browser import PageResult

SUPPORTED_ACTIONS = ("browser.navigate", "browser.read")
_TIMEOUT = 5
_MAX_BODY = 1024 * 1024
_MAX_TEXT = 16000
_CSP = "sandbox; default-src 'none'; base-uri 'none'; form-action 'none'"


class BrowserExecutionError(RuntimeError):
    pass


def _fetch_html(url: str) -> tuple[bytes, str]:
    deadline = monotonic() + _TIMEOUT
    with httpx2.Client(trust_env=False, follow_redirects=False, timeout=_TIMEOUT) as client:
        with client.stream("GET", url, headers={"Accept-Encoding": "identity", "Accept": "text/html"}) as response:
            content_type = response.headers.get("content-type", "")
            if (response.status_code != 200 or content_type.partition(";")[0].strip().lower() != "text/html"
                    or response.headers.get("content-encoding", "identity").lower() != "identity"
                    or "attachment" in response.headers.get("content-disposition", "").lower()):
                raise BrowserExecutionError("Page did not return a supported HTML response")
            body = bytearray()
            for chunk in response.iter_raw():
                if monotonic() >= deadline or len(body) + len(chunk) > _MAX_BODY:
                    raise BrowserExecutionError("Page exceeded the browser response limits")
                body.extend(chunk)
            return bytes(body), content_type


class PlaywrightBrowser:
    def __init__(self, allowed_pages: tuple[str, ...], denied_pages: tuple[str, ...]) -> None:
        self._allowed = frozenset(allowed_pages)
        self._denied = frozenset(denied_pages)

    def restriction(self, request: ActionRequest) -> Reason | None:
        if request.action not in SUPPORTED_ACTIONS:
            return Reason.ADAPTER_UNAVAILABLE
        if request.resource in self._denied or request.resource not in self._allowed:
            return Reason.RESOURCE_OUT_OF_SCOPE
        return None

    def render(self, request: ActionRequest) -> PageResult:
        if self.restriction(request) is not None:
            raise BrowserExecutionError("Browser action is outside the adapter scope")
        url = request.resource
        try:
            # Never expose an online browser or reusable context to an agent. Only this exact GET leaves PROXI.
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(chromium_sandbox=True, timeout=_TIMEOUT * 1000)
                try:
                    context = browser.new_context(offline=True, java_script_enabled=False, accept_downloads=False,
                                                  service_workers="block")
                    context.set_default_timeout(_TIMEOUT * 1000)
                    page = context.new_page()
                    body, content_type = _fetch_html(url)
                    served = False

                    def intercept(route: Route) -> None:
                        nonlocal served
                        intercepted = route.request
                        if (not served and intercepted.is_navigation_request() and intercepted.frame == page.main_frame
                                and intercepted.url == url and intercepted.method == "GET"):
                            served = True
                            route.fulfill(status=200, body=body, content_type=content_type,
                                          headers={"Content-Security-Policy": _CSP, "X-Content-Type-Options": "nosniff"})
                        else:
                            route.abort()

                    context.route("**/*", intercept)
                    page.goto(url, wait_until="domcontentloaded")
                    if not served or page.url != url:
                        raise BrowserExecutionError("Browser did not load the authorized page")
                    title = page.title()
                    text = page.locator("body").inner_text() if request.action == "browser.read" else None
                    return PageResult(url=url, title=title[:512], text=text[:_MAX_TEXT] if text is not None else None,
                                      truncated=len(title) > 512 or (text is not None and len(text) > _MAX_TEXT))
                finally:
                    browser.close()
        except (httpx2.HTTPError, PlaywrightError):
            raise BrowserExecutionError("Browser execution failed") from None
