from playwright.async_api import async_playwright, Browser, Page
import logging
import config

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages Playwright browser for rendering JavaScript pages"""
    
    def __init__(self):
        self.playwright = None
        self.browser: Browser = None
        self.page: Page = None
    
    async def start(self):
        """Initialize browser"""
        logger.info("Starting browser...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        logger.info("Browser started successfully")
    
    async def new_page(self) -> Page:
        """Create a new page"""
        if not self.browser:
            await self.start()
        
        page = await self.browser.new_page()
        # Set a reasonable timeout
        page.set_default_timeout(config.BROWSER_TIMEOUT)
        return page
    
    async def fetch_page_content(self, url: str) -> str:
        """
        Visit a URL and return the rendered HTML content
        """
        logger.info(f"Fetching page: {url}")
        page = await self.new_page()
        
        try:
            # Navigate to the page
            await page.goto(url, wait_until="networkidle")
            
            # Wait a bit for any dynamic content to load
            await page.wait_for_timeout(2000)
            
            # Get the full HTML content
            content = await page.content()
            
            # Also get the text content from the body
            body_text = await page.evaluate("() => document.body.innerText")
            
            logger.info(f"Successfully fetched page content ({len(content)} chars)")
            
            return body_text
            
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            raise
        finally:
            await page.close()
    
    async def close(self):
        """Close browser and cleanup"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")


# Singleton instance
_browser_manager = None


async def get_browser_manager() -> BrowserManager:
    """Get or create browser manager singleton"""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
        await _browser_manager.start()
    return _browser_manager