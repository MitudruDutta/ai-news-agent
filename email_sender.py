# file: email_sender.py
"""
Enhanced Email Sender for AI News Briefings
Supports HTML templates, multiple providers, attachments, and scheduling
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import re
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

# Safe symbol detection
_DEF_ENCODING = sys.stdout.encoding or 'utf-8'
try:
    '✓'.encode(_DEF_ENCODING)
    _CHECK = '✓'
except Exception:
    _CHECK = 'OK'
try:
    '✗'.encode(_DEF_ENCODING)
    _CROSS = '✗'
except Exception:
    _CROSS = 'X'

# ==================== CONFIGURATION ====================

# Email provider settings
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "gmail").lower()  # gmail, outlook, smtp

# SMTP Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

# Credentials
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")  # App password for Gmail
SENDER_NAME = os.getenv("SENDER_NAME", "AI Intelligence Hub")

# Default recipient
DEFAULT_RECIPIENT = os.getenv("RECIPIENT_EMAIL", "")

# Email settings
ENABLE_HTML = os.getenv("EMAIL_HTML", "true").lower() == "true"
ATTACH_AUDIO = os.getenv("EMAIL_ATTACH_AUDIO", "false").lower() == "true"

# Provider presets
PROVIDER_CONFIGS = {
    'gmail': {
        'server': 'smtp.gmail.com',
        'port': 587,
        'tls': True
    },
    'outlook': {
        'server': 'smtp-mail.outlook.com',
        'port': 587,
        'tls': True
    },
    'yahoo': {
        'server': 'smtp.mail.yahoo.com',
        'port': 587,
        'tls': True
    },
    'sendgrid': {
        'server': 'smtp.sendgrid.net',
        'port': 587,
        'tls': True
    }
}

# ==================== HTML TEMPLATE ====================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 10px;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px 10px 0 0;
            margin: -40px -40px 30px -40px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 700;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 14px;
        }}
        .meta-info {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 30px;
            border-left: 4px solid #667eea;
        }}
        .meta-info p {{
            margin: 5px 0;
            font-size: 14px;
            color: #666;
        }}
        .content {{
            color: #444;
        }}
        .content h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-top: 30px;
        }}
        .content h2 {{
            color: #34495e;
            margin-top: 25px;
            font-size: 22px;
        }}
        .content h3 {{
            color: #555;
            margin-top: 20px;
            font-size: 18px;
        }}
        .content p {{
            margin: 15px 0;
            line-height: 1.8;
        }}
        .content a {{
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }}
        .content a:hover {{
            text-decoration: underline;
        }}
        .content ul, .content ol {{
            padding-left: 25px;
            margin: 15px 0;
        }}
        .content li {{
            margin: 8px 0;
        }}
        .content code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        .content blockquote {{
            border-left: 4px solid #667eea;
            margin: 20px 0;
            padding: 10px 20px;
            background: #f8f9fa;
            font-style: italic;
        }}
        .story-card {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #eee;
            text-align: center;
            color: #999;
            font-size: 12px;
        }}
        .button {{
            display: inline-block;
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 10px 0;
        }}
        .button:hover {{
            opacity: 0.9;
        }}
        @media (max-width: 600px) {{
            body {{
                padding: 10px;
            }}
            .container {{
                padding: 20px;
            }}
            .header {{
                padding: 20px;
                margin: -20px -20px 20px -20px;
            }}
            .header h1 {{
                font-size: 22px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 {title}</h1>
            <p>{subtitle}</p>
        </div>

        <div class="meta-info">
            <p><strong>📅 Date:</strong> {date}</p>
            <p><strong>⏰ Generated:</strong> {time}</p>
            <p><strong>📊 Sources:</strong> {source_count}</p>
        </div>

        <div class="content">
            {content}
        </div>

        <div class="footer">
            <p>AI Intelligence Hub • Automated News Aggregation</p>
            <p>Generated on {datetime} UTC</p>
            <p style="margin-top: 15px; font-size: 11px;">
                This briefing was automatically generated by AI agents.<br>
                Configure your preferences or unsubscribe in settings.
            </p>
        </div>
    </div>
</body>
</html>
"""


# ==================== MARKDOWN TO HTML CONVERSION ====================

def markdown_to_html(markdown_text: str) -> str:
    """
    Convert markdown to HTML with basic formatting.

    Args:
        markdown_text: Markdown formatted text

    Returns:
        HTML formatted text
    """

    html = markdown_text

    # Headers
    html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Bold
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'__(.*?)__', r'<strong>\1</strong>', html)

    # Italic
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    html = re.sub(r'_(.*?)_', r'<em>\1</em>', html)

    # Links
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

    # Code
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

    # Unordered lists
    html = re.sub(r'^\s*[-*+]\s+(.*?)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*?</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)

    # Ordered lists
    html = re.sub(r'^\s*\d+\.\s+(.*?)$', r'<li>\1</li>', html, flags=re.MULTILINE)

    # Paragraphs
    html = re.sub(r'\n\n+', '</p><p>', html)
    html = f'<p>{html}</p>'

    # Clean up empty tags
    html = re.sub(r'<p>\s*</p>', '', html)

    # Line breaks
    html = html.replace('\n', '<br>')

    return html


# ==================== EMAIL SENDING ====================

def send_email_briefing(
        recipient: str,
        subject: str,
        content: str,
        attachments: Optional[List[str]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
) -> bool:
    """
    Send an email briefing with optional HTML formatting and attachments.

    Args:
        recipient: Email address of recipient
        subject: Email subject line
        content: Briefing content (markdown or plain text)
        attachments: List of file paths to attach
        cc: List of CC recipients
        bcc: List of BCC recipients

    Returns:
        True if email sent successfully, False otherwise
    """

    print("\n" + "=" * 60)
    print("📧 EMAIL SENDING")
    print("=" * 60)

    # Validate configuration
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("❌ Email credentials not configured")
        print("   Set SENDER_EMAIL and SENDER_PASSWORD environment variables")
        return False

    if not recipient:
        recipient = DEFAULT_RECIPIENT

    if not recipient:
        print("❌ No recipient specified")
        return False

    print(f"📤 From: {SENDER_EMAIL}")
    print(f"📥 To: {recipient}")
    if cc:
        print(f"📋 CC: {', '.join(cc)}")

    # Get provider configuration
    provider_config = PROVIDER_CONFIGS.get(EMAIL_PROVIDER, {})
    smtp_server = provider_config.get('server', SMTP_SERVER)
    smtp_port = provider_config.get('port', SMTP_PORT)
    use_tls = provider_config.get('tls', SMTP_USE_TLS)

    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg['To'] = recipient
        msg['Subject'] = subject

        if cc:
            msg['Cc'] = ', '.join(cc)

        # Prepare content
        plain_text = content

        if ENABLE_HTML:
            # Convert markdown to HTML
            html_content = markdown_to_html(content)

            # Fill template
            now = datetime.now()
            html_email = HTML_TEMPLATE.format(
                title="AI Intelligence Briefing",
                subtitle="Your daily digest of AI news and developments",
                date=now.strftime("%B %d, %Y"),
                time=now.strftime("%H:%M UTC"),
                source_count="40+ sources",
                content=html_content,
                datetime=now.strftime("%Y-%m-%d %H:%M:%S")
            )

            # Attach both plain text and HTML
            part1 = MIMEText(plain_text, 'plain')
            part2 = MIMEText(html_email, 'html')

            msg.attach(part1)
            msg.attach(part2)
        else:
            # Plain text only
            part = MIMEText(plain_text, 'plain')
            msg.attach(part)

        # Add attachments
        if attachments:
            print(f"\n📎 Adding {len(attachments)} attachment(s)...")
            for file_path in attachments:
                if Path(file_path).exists():
                    with open(file_path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())

                    encoders.encode_base64(part)
                    filename = Path(file_path).name
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {filename}'
                    )
                    msg.attach(part)
                    print(f"   {_CHECK} {filename}")
                else:
                    print(f"   {_CROSS} File not found: {file_path}")

        # Connect to SMTP server
        print(f"\n🔌 Connecting to {smtp_server}:{smtp_port}...")

        if use_tls:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)

        # Login
        print("🔐 Authenticating...")
        server.login(SENDER_EMAIL, SENDER_PASSWORD)

        # Send email
        print("📨 Sending email...")
        recipients_list = [recipient]
        if cc:
            recipients_list.extend(cc)
        if bcc:
            recipients_list.extend(bcc)

        server.sendmail(SENDER_EMAIL, recipients_list, msg.as_string())

        # Cleanup
        server.quit()

        print("\n✅ Email sent successfully!")
        print("=" * 60 + "\n")
        return True

    except smtplib.SMTPAuthenticationError:
        print("\n❌ Authentication failed")
        print("   For Gmail: Enable 2FA and use an App Password")
        print("   https://support.google.com/accounts/answer/185833")
        return False

    except smtplib.SMTPException as e:
        print(f"\n❌ SMTP error: {e}")
        return False

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


# ==================== BATCH SENDING ====================

def send_to_multiple_recipients(
        recipients: List[str],
        subject: str,
        content: str,
        attachments: Optional[List[str]] = None
) -> dict:
    """
    Send email to multiple recipients.

    Returns:
        Dictionary of {email: success_bool}
    """

    results = {}

    print(f"\n📬 Sending to {len(recipients)} recipients...\n")

    for i, recipient in enumerate(recipients, 1):
        print(f"[{i}/{len(recipients)}] Sending to {recipient}...")
        success = send_email_briefing(recipient, subject, content, attachments)
        results[recipient] = success

    successful = sum(1 for v in results.values() if v)
    print(f"\n{_CHECK if successful == len(recipients) else _CROSS} Sent to {successful}/{len(recipients)} recipients")

    return results


# ==================== SCHEDULING ====================

def schedule_daily_briefing(hour: int = 8, minute: int = 0):
    """
    Schedule daily briefing emails (requires schedule library).

    Args:
        hour: Hour to send (0-23)
        minute: Minute to send (0-59)
    """
    try:
        import schedule
        import time

        def send_briefing():
            from agent_crew import run_crew
            briefing = run_crew()

            if briefing:
                send_email_briefing(
                    DEFAULT_RECIPIENT,
                    f"AI Intelligence Briefing - {datetime.now().strftime('%Y-%m-%d')}",
                    briefing
                )

        schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(send_briefing)

        print(f"📅 Briefing scheduled for {hour:02d}:{minute:02d} daily")
        print("Press Ctrl+C to stop")

        while True:
            schedule.run_pending()
            time.sleep(60)

    except ImportError:
        print("❌ schedule library not installed")
        print("   Install with: pip install schedule")
    except KeyboardInterrupt:
        print("\n✋ Scheduler stopped")


# ==================== STANDALONE TESTING ====================

if __name__ == '__main__':
    # Test email sending
    test_subject = f"AI Intelligence Briefing - {datetime.now().strftime('%B %d, %Y')}"

    test_content = """
# Daily AI Intelligence Briefing

**Date:** October 2, 2025

## Executive Summary

Today's briefing covers three major developments in artificial intelligence:
groundbreaking advancements in language models, new computer vision techniques,
and important policy updates regarding AI governance.

## Top Stories

### 1. Revolutionary Language Model Architecture

Researchers have unveiled a novel transformer architecture that achieves 
**40% better performance** while using 30% fewer parameters. This breakthrough
could democratize access to advanced AI capabilities.

- **Key Metric:** 95% accuracy on complex reasoning tasks
- **Impact:** Enables deployment on edge devices
- **Availability:** Open-source release planned for Q1 2026

[Read more](https://example.com/story1)

### 2. Computer Vision Breakthrough

A new approach to real-time object detection shows remarkable improvements:
- 98% accuracy across diverse environments
- 10x faster inference speed
- Works with limited training data

This development has significant implications for autonomous systems and robotics.

### 3. AI Governance Framework

Major tech companies announce unified ethical AI framework:
- Transparency requirements
- Bias mitigation standards
- Independent auditing processes

## Trends & Insights

The convergence of efficiency and capability continues to be the dominant theme,
with multiple breakthroughs focusing on doing more with less computational resources.

## Looking Ahead

Watch for upcoming announcements from major AI labs in the coming weeks,
particularly around multi-modal AI systems and improved reasoning capabilities.

---

*This briefing was generated by AI Intelligence Hub*
*Configure your preferences or unsubscribe in settings*
    """

    # Get recipient from environment or use test email
    test_recipient = os.getenv('TEST_RECIPIENT_EMAIL') or os.getenv('RECIPIENT_EMAIL', 'user@example.com')

    print("🧪 Testing email sending...\n")
    print(f"Configuration:")
    print(f"  Provider: {EMAIL_PROVIDER}")
    print(f"  SMTP Server: {SMTP_SERVER}:{SMTP_PORT}")
    print(f"  HTML Enabled: {ENABLE_HTML}")
    print(f"  Recipient: {test_recipient}")

    if SENDER_EMAIL and SENDER_PASSWORD:
        result = send_email_briefing(test_recipient, test_subject, test_content)

        if result:
            print("\n✅ Test email sent successfully!")
            print(f"   Check {test_recipient} for the briefing")
        else:
            print("\n❌ Test failed. Check configuration and credentials")
    else:
        print("\n⚠️  Email credentials not configured")
        print("   Set SENDER_EMAIL and SENDER_PASSWORD to test")