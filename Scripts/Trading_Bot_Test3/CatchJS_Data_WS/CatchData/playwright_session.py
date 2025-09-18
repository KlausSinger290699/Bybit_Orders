from playwright.sync_api import sync_playwright
from pathlib import Path

PROFILE_DIR = Path(r"C:\Users\Anwender\PlaywrightProfiles\aggr")
URL = "https://charts.aggr.trade/koenzv4"
PREFIX = "[AGGR INDICATOR]"


def open_session():
    """Start Playwright context + page, return (playwright, context, page)."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    playwright = sync_playwright().start()
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
    )
    page = context.new_page()
    page.goto(URL)

    print("🟢 Listening… prefix:", PREFIX)
    return playwright, context, page
