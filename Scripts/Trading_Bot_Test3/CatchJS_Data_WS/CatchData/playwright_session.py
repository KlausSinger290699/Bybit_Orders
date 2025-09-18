from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE_DIR = Path(r"C:\Users\Anwender\PlaywrightProfiles\aggr")
URL = "https://charts.aggr.trade/koenzv4"
PREFIX = "[AGGR INDICATOR]"

def open_session():
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
