import smtplib
from email.mime.text import MIMEText
from config import GMAIL_USER, GMAIL_APP_PASSWORD


def send_error(subject: str, body: str):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print(f"[NOTIFIER] 알림 미설정: {subject}: {body}")
        return
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"[macro-dashboard] {subject}"
    msg["From"] = GMAIL_USER
    msg["To"] = GMAIL_USER
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"[NOTIFIER] 이메일 전송 실패: {e}")
