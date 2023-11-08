import jwt
import time
import logging
from be.model import error
from be.model import db_conn

import pymongo
from pymongo.errors import PyMongoError
import json
import traceback


# encode a json string like:
#   {
#       "user_id": [user name],
#       "terminal": [terminal code],
#       "timestamp": [ts]} to a JWT
#   }


def jwt_encode(user_id: str, terminal: str) -> str:
    encoded = jwt.encode(
        {"user_id": user_id, "terminal": terminal, "timestamp": time.time()},
        key=user_id,
        algorithm="HS256",
    )
    return encoded.encode("utf-8").decode("utf-8")

# decode a JWT to a json string like:
#   {
#       "user_id": [user name],
#       "terminal": [terminal code],
#       "timestamp": [ts]} to a JWT
#   }
def jwt_decode(encoded_token, user_id: str) -> str:
    decoded = jwt.decode(encoded_token, key=user_id, algorithms="HS256")
    return decoded


class User(db_conn.DBConn):
    token_lifetime: int = 3600  # 3600 second

    def __init__(self):
        db_conn.DBConn.__init__(self)

    def __check_token(self, user_id, db_token, token) -> bool:
        try:
            if db_token != token:
                return False
            jwt_text = jwt_decode(encoded_token=token, user_id=user_id)
            ts = jwt_text["timestamp"]
            if ts is not None:
                now = time.time()
                if self.token_lifetime > now - ts >= 0:
                    return True
        except jwt.exceptions.InvalidSignatureError as e:
            logging.error(str(e))
            return False

    def register(self, user_id: str, password: str):
        try:
            # this code should be replaced by index creating !!!
            if self.user_id_exist(user_id):
                return error.error_exist_user_id(user_id)
            
            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)

            user_doc = {
                "user_id" : user_id,
                "password" : password,
                "balance" : 0,
                "token" : token,
                "terminal" : terminal, 
                "user_store" : [], 
                "user_order" : []}
            user_collec = self.conn['user']
            assert isinstance(user_collec, pymongo.collection.Collection)
            user_collec.insert_one(user_doc)

        except PyMongoError:
            error_message = str(e)
            traceback_info = traceback.format_exc()
            with open('/Users/mayechi/MAJOR/f-junior/database/P1/bookstore/model_log.txt', 'w') as file:
                file.write(error_message + "\n")
                file.write(traceback_info)
            return error.error_exist_user_id(user_id)
        except BaseException as e:
            return 530, "{}".format(str(e)), ""
        return 200, "ok"

    def check_token(self, user_id: str, token: str) -> (int, str):
        
        user_collec = self.conn['user']
        assert isinstance(user_collec, pymongo.collection.Collection)
        result = user_collec.find_one({"user_id": user_id})
        
        #row = cursor.fetchone()
        if result is None:
            return error.error_authorization_fail()
        db_token = result["token"]
        if not self.__check_token(user_id, db_token, token):
            return error.error_authorization_fail()
        return 200, "ok"

    def check_password(self, user_id: str, password: str) -> (int, str):
        
        # cursor = self.conn.execute(
        #     "SELECT password from user where user_id=?", (user_id,)
        # )
        # row = cursor.fetchone()

        user_collec = self.conn['user']
        assert isinstance(user_collec, pymongo.collection.Collection)
        result = user_collec.find_one({"user_id": user_id})
        
        if result is None:
            return error.error_authorization_fail()

        if password != result["password"]:
            return error.error_authorization_fail()

        return 200, "ok"

    def login(self, user_id: str, password: str, terminal: str) -> (int, str, str):
        token = ""
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message, ""

            token = jwt_encode(user_id, terminal)
            # cursor = self.conn.execute(
            #     "UPDATE user set token= ? , terminal = ? where user_id = ?",
            #     (token, terminal, user_id),
            # )

            user_collec = self.conn['user']
            assert isinstance(user_collec, pymongo.collection.Collection)
            filter_condition = {"user_id": user_id}
            update_operation = {"$set": {"token": token, "terminal": terminal}}
            result = user_collec.update_one(filter_condition, update_operation)

            if result.modified_count == 0:
                return error.error_authorization_fail() + ("",)
        except PyMongoError as e:
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            return 530, "{}".format(str(e)), ""
        return 200, "ok", token

    def logout(self, user_id: str, token: str) -> bool:
        try:
            code, message = self.check_token(user_id, token)
            if code != 200:
                return code, message

            terminal = "terminal_{}".format(str(time.time()))
            dummy_token = jwt_encode(user_id, terminal)

            # cursor = self.conn.execute(
            #     "UPDATE user SET token = ?, terminal = ? WHERE user_id=?",
            #     (dummy_token, terminal, user_id),
            # )

            user_collec = self.conn['user']
            assert isinstance(user_collec, pymongo.collection.Collection)
            filter_condition = {"user_id": user_id}
            update_operation = {"$set": {"token": dummy_token, "terminal": terminal}}
            result = user_collec.update_one(filter_condition, update_operation)

            if result.modified_count == 0:
                return error.error_authorization_fail()

        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def unregister(self, user_id: str, password: str) -> (int, str):
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message

            #cursor = self.conn.execute("DELETE from user where user_id=?", (user_id,))
            
            user_collec = self.conn['user']
            assert isinstance(user_collec, pymongo.collection.Collection)
            result = user_collec.delete_one({"user_id": user_id})
            
            if result.deleted_count == 0:
                return error.error_authorization_fail()
        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> bool:
        try:
            code, message = self.check_password(user_id, old_password)
            if code != 200:
                return code, message

            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)

            # cursor = self.conn.execute(
            #     "UPDATE user set password = ?, token= ? , terminal = ? where user_id = ?",
            #     (new_password, token, terminal, user_id),
            # )

            user_collec = self.conn['user']
            assert isinstance(user_collec, pymongo.collection.Collection)
            filter_condition = {"user_id": user_id}
            update_operation = {"$set": {"token": token, "terminal": terminal, "password": new_password}}
            
            result = user_collec.update_one(filter_condition, update_operation)

            if result.modified_count == 0:
                return error.error_authorization_fail()

        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def check_order(self, user_id: str) -> (int, str, list):
        user_orders = []
        try:    
            order_collec = self.conn['order']
            assert isinstance(order_collec, pymongo.collection.Collection)
            user_collec = self.conn['user']
            assert isinstance(user_collec, pymongo.collection.Collection)

            order_id_exist = []
            cursor = order_collec.find({"user_id": user_id})
            for order in cursor:
                assert isinstance(order, dict)  
                order['_id'] = str(order['_id'])
                user_orders.append(order)
                order_id_exist.append(order["order_id"])
            filter_condition = {"user_id": user_id}
            update_operation = {"$set": {"user_order": order_id_exist}}
            user_collec.update_one(filter_condition, update_operation)

        except PyMongoError as e:
            return 528, "{}".format(str(e)), []
        except BaseException as e:
            error_message = str(e)
            traceback_info = traceback.format_exc()
            with open('/Users/mayechi/MAJOR/f-junior/database/P1/bookstore/model_log.txt', 'w') as file:
                file.write(error_message + "\n")
                file.write(traceback_info)
            return 530, "{}".format(str(e)), []

        return 200, "ok", user_orders

    def cancell_order(self, user_id: str, order_id: str, store_id: str, book_id: str) -> (int, str):
        try:    
            order_collec = self.conn['order']
            assert isinstance(order_collec, pymongo.collection.Collection)
            user_collec = self.conn['user']
            assert isinstance(user_collec, pymongo.collection.Collection)

            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)

            filter_condition = {"user_id": user_id, "order_id": order_id,
                                "store_id": store_id, "book_id": book_id,}
            result = order_collec.delete_one(filter_condition)
            if result.deleted_count == 0:
                return error.error_non_exist_order_id(order_id)
            
            filter_condition = {"user_id": user_id}
            update_operation = {"$pull": {"user_order": order_id}}
            result = user_collec.update_one(filter_condition, update_operation)

        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            error_message = str(e)
            traceback_info = traceback.format_exc()
            with open('/Users/mayechi/MAJOR/f-junior/database/P1/bookstore/model_log.txt', 'w') as file:
                file.write(error_message + "\n")
                file.write(traceback_info)
            return 530, "{}".format(str(e))

        return 200, "ok"


