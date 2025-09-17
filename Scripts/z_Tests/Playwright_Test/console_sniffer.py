import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright

PREFIX = "[AGGR INDICATOR]"
URL = "https://charts.aggr.trade/koenzv4"
PROFILE_DIR = r"C:\Users\Anwender\PlaywrightProfiles\aggr"  # persistent profile dir

def extract_payload(console_text: str):
    if PREFIX not in console_text:
        return False, None
    after = console_text.split(PREFIX, 1)[1].strip()
    if after.startswith("{") or after.startswith("["):
        try:
            return True, json.loads(after)
        except json.JSONDecodeError:
            return True, after
    return True, after

async def main():
    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False
        )
        page = await context.new_page()

        def on_console(msg):
            text = getattr(msg, "text", msg)  # text is a property in your version
            ok, payload = extract_payload(str(text))
            if ok:
                print("📥 CONSOLE →", payload)

        page.on("console", on_console)
        await page.goto(URL)
        print("🟢 Listening… prefix:", PREFIX)

        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
