import os, sys, smtplib
from email.message import EmailMessage
from playwright.sync_api import sync_playwright
from datetime import datetime
from zoneinfo import ZoneInfo

URL         = os.getenv("A101_URL", "https://www.a101.com.tr/liste/a101-ekstra-apple")
SEARCH_TEXT = os.getenv("SEARCH_TEXT", "Apple iPhone 17 256 GB Cep")
HEADLESS    = os.getenv("HEADLESS", "1") == "1"

SMTP_HOST   = os.getenv("SMTP_HOST")
SMTP_PORT   = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER   = os.getenv("SMTP_USER")
SMTP_PASS   = os.getenv("SMTP_PASS")
FROM_EMAIL  = os.getenv("FROM_EMAIL", SMTP_USER)
TO_EMAIL    = os.getenv("TO_EMAIL", SMTP_USER)

def send_email(subject: str, body: str):
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
        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            for sel in ['button:has-text("Kabul Et")','button:has-text("Tamam")',
                        'button:has-text("Kapat")','button:has-text("Accept")']:
                try:
                    page.locator(sel).first.click(timeout=1000)
                except Exception:
                    pass
            page.wait_for_load_state("networkidle", timeout=45000)

            html = page.content()
            if (SEARCH_TEXT in html) or (SEARCH_TEXT.lower() in html.lower()):
                return True
            try:
                return page.locator(f"text={SEARCH_TEXT}").count() > 0
            except Exception:
                return False
        finally:
            ctx.close()
            browser.close()

if __name__ == "__main__":
    try:
        found = check_page()
        print(f"[info] Found={found} for: {SEARCH_TEXT}")
        if found:
            now_tr = datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d %H:%M:%S %Z")
            subject = f"[A101] MATCH PRESENT — {now_tr}"
            body = (f"✅ The phrase is present on the page.\n"
                    f"Phrase: {SEARCH_TEXT}\nURL: {URL}\nTime: {now_tr}\n")
            send_email(subject, body)
            print("[info] Email sent.")
        else:
            print("[info] No match; no email.")
    except Exception as e:
        print(f"[error] {e}", file=sys.stderr)
        sys.exit(1)
