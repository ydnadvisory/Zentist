# ruff: noqa: C901

import asyncio

import pytest

from zentist_rpa.services import playwright_service
from zentist_rpa.services.playwright_service import PlaywrightService


def test_playwright_service_requires_started_browser() -> None:
    service = PlaywrightService()

    with pytest.raises(RuntimeError, match="not been started"):
        service.get_browser()

    with pytest.raises(RuntimeError, match="not been started"):
        asyncio.run(service.new_page())


def test_playwright_service_lifecycle_uses_browser_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeContext:
        def __init__(self) -> None:
            self.cookies_cleared = False
            self.page = object()

        async def clear_cookies(self) -> None:
            self.cookies_cleared = True

        async def new_page(self) -> object:
            return self.page

    class FakeBrowser:
        def __init__(self) -> None:
            self.context = FakeContext()
            self.closed = False

        async def new_context(self) -> FakeContext:
            return self.context

        async def close(self) -> None:
            self.closed = True

    class FakeChromium:
        def __init__(self, browser: FakeBrowser) -> None:
            self.browser = browser
            self.headless: bool | None = None

        async def launch(self, *, headless: bool) -> FakeBrowser:
            self.headless = headless
            return self.browser

    class FakePlaywright:
        def __init__(self) -> None:
            self.browser = FakeBrowser()
            self.chromium = FakeChromium(self.browser)
            self.stopped = False

        async def stop(self) -> None:
            self.stopped = True

    class FakePlaywrightStarter:
        def __init__(self, instance: FakePlaywright) -> None:
            self.instance = instance

        async def start(self) -> FakePlaywright:
            return self.instance

    fake_playwright = FakePlaywright()
    monkeypatch.setattr(
        playwright_service,
        "async_playwright",
        lambda: FakePlaywrightStarter(fake_playwright),
    )

    service = PlaywrightService(headless=False)

    asyncio.run(service.start())
    browser = service.get_browser()
    page = asyncio.run(service.new_page(is_clear_cookie=True))
    asyncio.run(service.stop())

    assert browser is fake_playwright.browser
    assert page is fake_playwright.browser.context.page
    assert fake_playwright.chromium.headless is False
    assert fake_playwright.browser.context.cookies_cleared is True
    assert fake_playwright.browser.closed is True
    assert fake_playwright.stopped is True
