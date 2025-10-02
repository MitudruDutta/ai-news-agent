# file: main_scheduled.py
import schedule
import time
from main import execute_daily_briefing # Import the main function

# Schedule the job to run every day at 07:00
schedule.every().day.at("07:00").do(execute_daily_briefing)

print("Scheduler started. Waiting for the scheduled time (07:00) to run the briefing.")

# An infinite loop to keep the scheduler running
while True:
    schedule.run_pending()
    time.sleep(60) # Check every minute if a scheduled task is due