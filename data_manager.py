import datetime
from typing import Optional, Dict

from pymongo import MongoClient
from pymongo.cursor import Cursor


class Database:
    def __init__(self):
        db = MongoClient().get_database("GoodDeeds")
        self._users_collection = db.get_collection("users")
        self._requests_collection = db.get_collection("help_requests")

    def insert_user_info(
            self,
            user_id: int,
            username: str,
            name: str,
            location: str,
            volunteer_status: bool = False,
    ) -> None:
        """update or insert user to database"""
        self._users_collection.insert_one({
            "user_id": user_id,
            "location": location,
            "name": name,
            "username": username,
            "volunteer_status": volunteer_status,
        })

    def is_user_exists(self, user_id: int) -> bool:
        """checks if user is in db"""
        return bool(self.get_user_data(user_id))

    def is_active_user(self, user_id: int) -> bool:
        """checks if user is a volunteer"""
        return self.get_user_data(user_id).get("volunteer_status", False)

    def get_user_data(self, user_id: int) -> Optional[Dict]:
        """:returns: user data from db"""
        return self._users_collection.find_one({"user_id": user_id})

    def get_user_requests(self, user_id: int) -> Cursor:
        """:returns: all requests that were written by user"""
        return self._requests_collection.find({"user_id": user_id})

    def update_volunteer_status(self, user_id: int) -> None:
        """updates user's status to True/False thar will impact the distribution"""
        # Toggle the status (True to False, False to True)
        new_status = not (self._users_collection.find_one({"user_id": user_id}).get("volunteer_status"))
        self._users_collection.update_one({"user_id": user_id}, {"$set": {"volunteer_status": new_status}})

    def get_all_active_volunteers(self) -> Cursor:
        """return list of users that are volunteers"""
        return self._users_collection.find({"volunteer_status": True})

    def add_request(self, user_id: int, username: str, text: str, location: str) -> None:
        """add new request to request_collection"""
        self._requests_collection.insert_one({
            "date": datetime.datetime.now(),
            "location": location,
            "status": True,
            "text": text,
            "user_id": user_id,
            "username": username,
        })

    def get_all_active_requests(self) -> Cursor:
        """:returns: all active requests"""
        return self._requests_collection.find({
            "date": {"$gt": datetime.datetime.utcnow() - datetime.timedelta(hours=24)},
        })

    def get_local_requests_by_user_location(self, user_id: int) -> Cursor:
        """:returns: all active requests filtered by user location"""
        location = self.get_user_data(user_id).get("location")
        return self._requests_collection.find({
            "date": {"$gt": datetime.datetime.utcnow() - datetime.timedelta(hours=24)},
            "location": location,
        })
