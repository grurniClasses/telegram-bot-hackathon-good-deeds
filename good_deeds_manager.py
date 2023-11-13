from datetime import datetime, timedelta
from data_manager import DataBase

class GoodDeedsManager:
    def __init__(self, telebot, database):
        self.telebot = telebot
        self.database = database
        self.job_queue = self.telebot.updater.job_queue

    def start_scheduler(self):
        # Schedule the job to run every hour
        self.job_queue.run_repeating(self.change_old_requests_status, interval=3600, first=0)

    def change_old_requests_status(self, context):
        # Perform the desired operation
        self.database.change_requests_status_from_new_to_old()

    """
    def stop_scheduler(self):
        # Stop the scheduler when needed
        self.telebot.updater.stop()
    """