# file: main.py
from agent_crew import run_crew, recent_articles_list
from email_sender import send_email_briefing
from datetime import datetime
import os


def resolve_recipient() -> str:
    """Determine recipient email from environment.
    Priority: RECIPIENT_EMAIL -> TEST_RECIPIENT_EMAIL -> fallback placeholder.
    """
    return os.getenv("RECIPIENT_EMAIL") or os.getenv("TEST_RECIPIENT_EMAIL") or "your_email@example.com"


def execute_daily_briefing(send_email: bool = True) -> None:
    """Execute the entire daily news briefing workflow.

    Args:
        send_email: If False, will skip the email sending step (useful for local tests).
    """
    start = datetime.now()
    print(f"[Daily Briefing] Start at {start.isoformat()} (send_email={send_email})", flush=True)

    if not recent_articles_list:
        print("No new articles found in the last 24 hours. No briefing will be sent.", flush=True)
        return

    print(f"{len(recent_articles_list)} new articles found. Running the AI crew to generate the briefing...", flush=True)
    try:
        final_briefing_raw = run_crew()
        # Coerce to string defensively
        if isinstance(final_briefing_raw, str):
            final_briefing = final_briefing_raw
        else:
            try:
                import json
                final_briefing = json.dumps(final_briefing_raw, ensure_ascii=False, indent=2)
            except Exception:
                final_briefing = str(final_briefing_raw)

        length_info = len(final_briefing.strip()) if isinstance(final_briefing, str) else 0
        preview = final_briefing.strip()[:160].replace('\n', ' ') if final_briefing else ''
        print(f"[Debug] Briefing length={length_info} preview='{preview}...'", flush=True)

        if final_briefing and isinstance(final_briefing, str) and final_briefing.strip():
            print("Crew finished. Briefing generated.", flush=True)
            if send_email:
                today_date = datetime.now().strftime("%Y-%m-%d")
                subject = f"AI Intelligence Briefing for {today_date}".strip()
                recipient = resolve_recipient()
                print(f"Sending email to: {recipient}", flush=True)
                send_email_briefing(recipient, subject, final_briefing)
            else:
                print("Email sending skipped (send_email=False).", flush=True)
        else:
            print("Crew did not produce a briefing. Email not sent.", flush=True)

    except Exception as e:
        print(f"An error occurred during the daily briefing workflow: {e}", flush=True)

    finally:
        print(f"[Daily Briefing] Finished at {datetime.now().isoformat()} (elapsed {(datetime.now()-start).total_seconds():.2f}s)", flush=True)


if __name__ == '__main__':
    execute_daily_briefing()