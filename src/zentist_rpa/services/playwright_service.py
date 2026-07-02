from playwright.async_api import Browser, Page, Playwright, async_playwright


class PlaywrightService:
    def __init__(self, *, headless: bool = True) -> None:
        self._headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    def get_browser(self) -> Browser:
        if self._browser is None:
            error_message = "PlaywrightService has not been started"
            raise RuntimeError(error_message)
        return self._browser

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self._headless)

    async def new_page(self, *, is_clear_cookie: bool = False) -> Page:
        if self._browser is None:
            error_message = "PlaywrightService has not been started"
            raise RuntimeError(error_message)

        context = await self._browser.new_context()
        if is_clear_cookie:
            await context.clear_cookies()
        return await context.new_page()

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
