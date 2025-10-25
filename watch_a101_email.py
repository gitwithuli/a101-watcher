import os, sys, smtplib, traceback, pathlib
from email.message import EmailMessage
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

URL         = os.getenv("A101_URL", "https://www.a101.com.tr/liste/a101-ekstra-apple")
SEARCH_TEXT = os.getenv("SEARCH_TEXT", "Apple iPhone 17 256 GB Cep")
HEADLESS    = os.getenv("HEADLESS", "1") == "1"

SMTP_HOST   = os.getenv("SMTP_HOST")
SMTP_PORT   = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER   = os.getenv("SMTP_USER")
SMTP_PASS   = os.getenv("SMTP_PASS")
FROM_EMAIL  = os.getenv("FROM_EMAIL", SMTP_USER)
TO_EMAIL    = os.getenv("TO_EMAIL", SMTP_USER)

ARTDIR = pathlib.Path("artifacts")
ARTDIR.mkdir(parents=True, exist_ok=True)

def log(msg: str):
    print(msg, flush=True)

def safe_send_email(subject: str, body: str):
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = FROM_EMAIL
        msg["To"] = TO_EMAIL
        msg.set_content(body)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
            s.ehlo()
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        log("[info] Email sent.")
        return True
    except Exception as e:
        log(f"[warn] Email failed: {e}")
        traceback.print_exc()
        return False

def check_page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        ctx = browser.new_context(
            user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"),
            locale="tr-TR",
            timezone_id="Europe/Istanbul",
            viewport={"width": 1366, "height": 800},
        )
        page = ctx.new_page()
        nav_status = None
        try:
            resp = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            nav_status = resp.status if resp else None
            log(f"[info] goto status={nav_status}")
            for sel in ['button:has-text("Kabul Et")','button:has-text("Tamam")',
                        'button:has-text("Kapat")','button:has-text("Accept")']:
                try:
                    page.locator(sel).first.click(timeout=1000)
                except Exception:
                    pass
            try:
                page.wait_for_load_state("networkidle", timeout=45000)
            except PWTimeout:
                log("[warn] networkidle timeout; continuing")

            html = page.content()
            (ARTDIR / "page.html").write_text(html, encoding="utf-8")
            try:
                page.screenshot(path=str(ARTDIR / "page.png"), full_page=True)
            except Exception:
                pass

            found = (SEARCH_TEXT in html) or (SEARCH_TEXT.lower() in html.lower())
            if not found:
                try:
                    found = page.locator(f"text={SEARCH_TEXT}").count() > 0
                except Exception:
                    found = False
            return found, nav_status
        finally:
            ctx.close()
            browser.close()

if __name__ == "__main__":
    try:
        found, status = check_page()
        log(f"[info] Found={found} for: {SEARCH_TEXT}; http_status={status}")
        if found:
            subject = "[A101] MATCH PRESENT"
            body = f"✅ Phrase is present.\nPhrase: {SEARCH_TEXT}\nURL: {URL}\nHTTP status: {status}"
            safe_send_email(subject, body)
        else:
            log("[info] No match; no email.")
        # Always exit 0 so the workflow doesn’t fail just because email or site was picky
        sys.exit(0)
    except Exception as e:
        log(f"[error] {e}")
        traceback.print_exc()
        # Still exit 0 so schedule keeps running; artifacts/logs will show details
        sys.exit(0)
