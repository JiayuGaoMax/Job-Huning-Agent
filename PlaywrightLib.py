from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import re
def get_html_playwright(url: str) -> str:
    print(f"  Starting Playwright: {url}")

    with sync_playwright() as playwright:
        print("  Launching Chromium...")

        browser = playwright.chromium.launch(
            headless=True
        )

        try:
            page = browser.new_page(
                viewport={
                    "width": 1920,
                    "height": 1080,
                },
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
            )

            page.set_default_timeout(60_000)
            page.set_default_navigation_timeout(120_000)

            print("  Opening career page...")

            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=120_000,
            )

            if response:
                print(f"  HTTP status: {response.status}")
            else:
                print("  No navigation response received.")

            # Allow JavaScript job systems to render.
            page.wait_for_timeout(8_000)

            try:
                page.wait_for_load_state(
                    "networkidle",
                    timeout=20_000,
                )
            except Exception:
                print(
                    "  Network did not become idle; "
                    "continuing with rendered page."
                )

            print(f"  Final URL: {page.url}")
            print(f"  Page title: {page.title()}")

            html = page.content()
            body_text = page.locator("body").inner_text()

            print(f"  Captured HTML: {len(html):,} characters")
            print(f"  Visible text: {len(body_text):,} characters")

            if len(body_text.strip()) < 100:
                raise RuntimeError(
                    "Playwright loaded the page, but almost no visible "
                    "text was returned. The site may be blocking automation, "
                    "using an iframe, or loading jobs through another API."
                )

            return html

        except Exception as error:
            print(
                f"  PLAYWRIGHT FAILED: "
                f"{type(error).__name__}: {error}"
            )
            raise

        finally:
            browser.close()


def html_to_text(html,UNWANTED_WEB_WORDS):
    soup = BeautifulSoup(html, "html.parser")

    # Remove useless tags
    for tag in soup(
        ["script", "style", "noscript", "svg", "img", "footer", "header", "nav", "form"]
    ):
        tag.decompose()

    text = soup.get_text("\n", strip=True)


    cleaned = []

    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()

        if not line:
            continue

        if len(line) < 2:
            continue

        if any(word in line.lower() for word in UNWANTED_WEB_WORDS):
            continue

        cleaned.append(line)

    return "\n".join(cleaned)