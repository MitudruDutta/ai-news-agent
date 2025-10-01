# file: email_sender.py
"""Utility for sending the AI news briefing via email.

Requires environment variables (usually in a .env file):
- SENDER_EMAIL
- SENDER_APP_PASSWORD  (e.g., Gmail App Password or SMTP auth token)
- SMTP_SERVER (default: smtp.gmail.com)
- SMTP_PORT (default: 587)
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file if present
load_dotenv()


def _normalize_app_password(pwd: str | None) -> str | None:
    """Normalize a Gmail-style app password (remove quotes & spaces).
    Returns cleaned password or None.
    """
    if not pwd:
        return None
    cleaned = pwd.strip().strip('"\'')  # remove surrounding quotes if any
    # Gmail 16-char app passwords sometimes copied with spaces; remove them
    if len(cleaned.replace(" ", "")) == 16:
        cleaned = cleaned.replace(" ", "")
    return cleaned


def send_email_briefing(recipient_email: str, subject: str, content: str, *, sender_email: Optional[str] = None) -> bool:
    """Send the AI news briefing to a recipient.

    Args:
        recipient_email: Destination email address.
        subject: Subject line.
        content: Body text (plain text expected).
        sender_email: Override the sender (falls back to env SENDER_EMAIL).

    Returns:
        True on success, False otherwise.
    """
    sender_email = sender_email or os.getenv("SENDER_EMAIL")
    sender_password_raw = os.getenv("SENDER_APP_PASSWORD")  # Use an app password for Gmail accounts
    sender_password = _normalize_app_password(sender_password_raw)
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    if not sender_email or not sender_password:
        print("Error: Missing SENDER_EMAIL or SENDER_APP_PASSWORD in environment variables.")
        print("Set them in a .env file, e.g.\nSENDER_EMAIL=you@example.com\nSENDER_APP_PASSWORD=xxxxxxxxxxxxxxxx (16-char app password)")
        return False

    if not recipient_email:
        print("Error: recipient_email is required.")
        return False

    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg.set_content(content)
    except Exception as e:
        print(f"Error constructing email message: {e}")
        return False

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print(f"Email briefing successfully sent to {recipient_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("Error: SMTP authentication failed. Check credentials or app password.")
        return False
    except Exception as e:
        print(f"An error occurred while sending the email: {e}")
        return False


if __name__ == '__main__':  # Simple manual test harness
    test_subject = "Today's AI Intelligence Briefing"
    test_content = (
        "Here is your daily summary of the top AI news:\n\n"
        "1. OpenAI Announces New Model\n"
        "   - Summary: OpenAI has released a new, more efficient language model...\n\n"
        "2. Google DeepMind Achieves Breakthrough in Robotics\n"
        "   - Summary: Researchers at DeepMind have developed a new algorithm..."
    )
    test_recipient = os.getenv('TEST_RECIPIENT_EMAIL') or os.getenv('RECIPIENT_EMAIL', 'recipient@example.com')
    send_email_briefing(test_recipient, test_subject, test_content)