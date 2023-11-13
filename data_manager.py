from pymongo import MongoClient
from datetime import datetime, timedelta


class DataBase:
    def __init__(self, db, users_collection, requests_collection):
        self._db = MongoClient().get_database(db)
        self._users_collection = self._db.get_collection(users_collection)
        self._requests_collection = self._db.get_collection(requests_collection)

    def upsert_user_info(self, user_id: int, username: str, name: str, location: str, volunteer_status: bool = False):
        """update or insert user to database"""
        user_data = {
            'id_user': user_id,
            "username": username,
            'name': name,
            'location': location,
            'volunteer_status': volunteer_status
        }
        self._users_collection.update_one({'id_user': user_id}, {'$set': user_data}, upsert=True)

    def is_user(self, user_id):
        return bool(self._users_collection.find_one({'id_user': user_id}))

    def is_active_user(self, user_id):
        return self._users_collection.find_one({'id_user': user_id}).get("volunteer_status")

    def get_user_data(self, user_id):
        return self._users_collection.find_one({'id_user': user_id})

    def get_user_requests(self, user_id):
        """:returns: all requests that were written by user"""
        return list(self._requests_collection.find({'user_id': user_id}))

    def update_volunteer_status(self, user_id: int):
        """updates user's status to True/False thar will impact the distribution"""
        new_status = not (self._users_collection.find_one({'id_user': user_id}).get("status"))  # Toggle the status (True to False, False to True)
        self._users_collection.update_one({'id_user': user_id}, {'$set': {'volunteer_status': new_status}})

    def add_request(self, user_id: int, text: str, location: str):
        """add new request to request_collection"""
        request_data = {
            'user_id': user_id,
            'date': datetime.now(),
            'text': text,
            'location': location,
            'status': True
        }
        self._requests_collection.insert_one(request_data)

    def deactivate_request(self, request_id):
        """changes status of request to False"""
        self._requests_collection.update_one({'_id': request_id}, {'$set': {'status': False}})

    def get_all_requests(self):
        """:returns: all requests with active (True) status"""
        return list(self._requests_collection.find({'status': True}))

    def get_local_requests(self, location):
        """:returns: all requests with active (True) status filtered by location"""
        return list(self._requests_collection.find({'status': True, 'location': location}))

    def get_local_requests_by_user_location(self, user_id: int):
        """:returns: all requests with active (True) status filtered by location"""
        location = self._users_collection.find_one({'id_user': user_id}).get('location')
        return self.get_local_requests(location)

    def change_requests_status_from_new_to_old(self):
        # Define the filter criteria
        filter_criteria = {
            'status': True,
            'date': {'$lt': datetime.utcnow() - timedelta(hours=24)}
        }

        # Define the update operation
        update_operation = {
            '$set': {'status': False}
        }

        self._requests_collection.update_many(filter_criteria, update_operation)

    # def add_user_rank(self, user_id):
    #     pass
    # if user helped more than ~5 times - add a star ⭐️ to name

    def get_all_active_volunteers(self):
        return [user for user in self._users_collection.find() if self.is_active_user(user.get("id_user"))]

