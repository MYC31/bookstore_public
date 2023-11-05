from be.model import error
from be.model import db_conn
import pymongo
from pymongo.errors import PyMongoError
import json


class Seller(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def add_book(
        self,
        user_id: str,
        store_id: str,
        book_id: str,
        book_json_str: str,
        stock_level: int,
    ):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)

            # you should insert data into both store and book !!!
            # be carefull with jason string !!!
            # subtract id from book_json_str
            book_info = json.loads(book_json_str)
            assert isinstance(book_info, dict)
            del book_info["id"]
            book_doc = {"book_id": book_id, 
                        "store_id": store_id, 
                        "book_info": book_info, 
                        "stock_level": stock_level}
            book_collec = self.conn['book']
            assert isinstance(book_collec, pymongo.collection.Collection)
            book_collec.insert_one(book_doc)

            store_collec = self.conn['store']
            assert isinstance(store_collec, pymongo.collection.Collection)
            store_collec.update_one(
                {"store_id": store_id}, 
                {"$push": {"book": book_id}})

        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def add_stock_level(
        self, user_id: str, store_id: str, book_id: str, add_stock_level: int
    ):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)

            book_collec = self.conn['book']
            assert isinstance(book_collec, pymongo.collection.Collection)
            filter_condition = {"book_id": book_id, "store_id": store_id}
            update_operation = {"$inc": {"stock_level": add_stock_level}}
            book_collec.update_one(filter_condition, update_operation)

        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)
    
            user_collec = self.conn['user']
            assert isinstance(user_collec, pymongo.collection.Collection)
            user_collec.update_one(
                {"user_id": user_id}, 
                {"$push": {"user_store": store_id}})

            store_collec = self.conn['store']
            assert isinstance(store_collec, pymongo.collection.Collection)
            store_collec.insert_one({"store_id": store_id, 
                                     "user_id": user_id, 
                                     "book": []})

        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"
