import uuid
import json
import logging
from be.model import db_conn
from be.model import error
import pymongo
from pymongo.errors import PyMongoError
import traceback
from be.model.db_conf import order_state, order_expire_time
import traceback
from datetime import datetime, timedelta


class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    # 下单
    def new_order(
        self, user_id: str, store_id: str, id_and_count: [(str, int)]
    ) -> (int, str, str):
        order_id = ""
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)
            uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))

            book_collec = self.conn['book']
            assert isinstance(book_collec, pymongo.collection.Collection)
            order_collec = self.conn['order']
            assert isinstance(order_collec, pymongo.collection.Collection)
            user_collec = self.conn['user']
            assert isinstance(user_collec, pymongo.collection.Collection)

            # this loop should be optimized to be aggregation operation
            for book_id, count in id_and_count:
                # select specific book info from book doc set

                # cursor = self.conn.execute(
                #     "SELECT book_id, stock_level, book_info FROM store "
                #     "WHERE store_id = ? AND book_id = ?;",
                #     (store_id, book_id),
                # )
                # row = cursor.fetchone()
                result = book_collec.find_one({"book_id": book_id, "store_id": store_id})

                if result is None:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = result['stock_level']
                book_info = result['book_info']
                assert isinstance(book_info, dict)
                price = book_info['price']

                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)

                # update book stock level in book doc set

                # cursor = self.conn.execute(
                #     "UPDATE store set stock_level = stock_level - ? "
                #     "WHERE store_id = ? and book_id = ? and stock_level >= ?; ",
                #     (count, store_id, book_id, count),
                # )
                # if cursor.rowcount == 0:
                #     return error.error_stock_level_low(book_id) + (order_id,)
                query = {"store_id": store_id, "book_id": book_id, "stock_level": {"$gte": count}}
                update_operation = {"$inc": {"stock_level": -count}}
                result = book_collec.update_one(query, update_operation)

                if result.modified_count == 0:
                    return error.error_stock_level_low(book_id) + (order_id,)
                
                # here you should insert each order doc into order doc set,
                # and insert the order_id into user's order list

                # self.conn.execute(
                #     "INSERT INTO new_order_detail(order_id, book_id, count, price) "
                #     "VALUES(?, ?, ?, ?);",
                #     (uid, book_id, count, price),
                # )
                expiration_time = datetime.now() + timedelta(seconds=order_expire_time)
                new_order = {"order_id": uid, "user_id": user_id, 
                             "store_id": store_id ,"book_id": book_id, 
                             "count": count, "price": price, "state": order_state["new_order"], 
                             "expiration_time": expiration_time}
                result = order_collec.insert_one(new_order)   
                query = {"user_id": user_id}
                update_operation = {"$push": {"user_order": uid}}
                result = user_collec.update_one(query, update_operation)

            order_id = uid
        except PyMongoError as e:
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), ""

        return 200, "ok", order_id

    # 付款
    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        conn = self.conn
        try:
            order_collec = conn['order']
            assert isinstance(order_collec, pymongo.collection.Collection)
            user_collec = conn['user']
            assert isinstance(user_collec, pymongo.collection.Collection)
            store_collec = conn['store']
            assert isinstance(store_collec, pymongo.collection.Collection)

            # check if order is present
            # cursor = conn.execute(
            #     "SELECT order_id, user_id, store_id FROM new_order WHERE order_id = ?",
            #     (order_id,),
            # )
            # row = cursor.fetchone()
            order_result = order_collec.find_one({"order_id": order_id})

            if order_result is None:
                return error.error_invalid_order_id(order_id)

            assert isinstance(order_result, dict)
            order_id = order_result["order_id"]
            buyer_id = order_result["user_id"]
            store_id = order_result["store_id"]

            if buyer_id != user_id:
                return error.error_authorization_fail()

            # get buyer's info from user doc set
            # cursor = conn.execute(
            #     "SELECT balance, password FROM user WHERE user_id = ?;", (buyer_id,)
            # )
            # row = cursor.fetchone()
            result = user_collec.find_one({"user_id": buyer_id})

            if result is None:
                return error.error_non_exist_user_id(buyer_id)
            assert isinstance(result, dict)
            balance = result["balance"]
            if password != result["password"]:
                return error.error_authorization_fail()
            
            # check if store is present
            # cursor = conn.execute(
            #     "SELECT store_id, user_id FROM user_store WHERE store_id = ?;",
            #     (store_id,),
            # )
            # row = cursor.fetchone()
            result = store_collec.find_one({"store_id": store_id})
            if result is None:
                return error.error_non_exist_store_id(store_id)

            assert isinstance(result, dict)
            seller_id = result["user_id"]

            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            # get order's info from order doc set
            # cursor = conn.execute(
            #     "SELECT book_id, count, price FROM new_order_detail WHERE order_id = ?;",
            #     (order_id,),
            # )
            cursor = order_collec.find({"order_id": order_id})
            assert cursor.alive
            total_price = 0
            for order in cursor:
                count = order["count"]
                price = order["price"]
                total_price = total_price + price * count
            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)
            
            # change every order state to be paid
            filter = {"order_id": order_id, "state": order_state["new_order"]}
            update = {"$set": {"state": order_state["paid"]}}
            result = order_collec.update_many(filter, update)

            # cut down specfic buyer's balance from user doc set
            # cursor = conn.execute(
            #     "UPDATE user set balance = balance - ?"
            #     "WHERE user_id = ? AND balance >= ?",
            #     (total_price, buyer_id, total_price),
            # )
            filter_condition = {"user_id": buyer_id, "balance": {"$gte": total_price}}
            update_operation = {"$inc": {"balance": -total_price}}
            result = user_collec.update_one(filter_condition, update_operation)
            if result.modified_count == 0:
                return error.error_not_sufficient_funds(order_id)

            # do not understand what's going on ???

            # cursor = conn.execute(
            #     "UPDATE user set balance = balance + ?" "WHERE user_id = ?",
            #     (total_price, buyer_id),
            # )


            # result = user_collec.update_one({"user_id": buyer_id}, 
            #                                 {"$inc": {"balance": total_price}})
            # if result.modified_count == 0:
            #     return error.error_non_exist_user_id(buyer_id)


            # delete the finished order
            # cursor = conn.execute(
            #     "DELETE FROM new_order WHERE order_id = ?", (order_id,)
            # )

            # after order state is introduced, paid order is not deleted at once !!!

            # result = order_collec.delete_one({"order_id": order_id})
            # if result.deleted_count == 0:
            #     return error.error_invalid_order_id(order_id)
            # filter_condition = {"user_id": buyer_id}
            # update_operation = {"$pull": {"user_order": order_id}}
            # user_collec.update_one(filter_condition, update_operation)

        except PyMongoError as e:
            return 528, "{}".format(str(e))

        except BaseException as e:
            with open('./model_log.txt', 'w') as file:
                # Print the traceback information to the file
                traceback.print_exc(file=file)
            return 530, "{}".format(str(e))

        return 200, "ok"

    # 充值
    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            user_collec = self.conn['user']
            assert isinstance(user_collec, pymongo.collection.Collection)
            # cursor = self.conn.execute(
            #     "SELECT password  from user where user_id=?", (user_id,)
            # )
            result = user_collec.find_one({"user_id": user_id})
            if result is None:
                return error.error_authorization_fail()

            assert isinstance(result, dict)
            if result["password"] != password:
                return error.error_authorization_fail()

            # cursor = self.conn.execute(
            #     "UPDATE user SET balance = balance + ? WHERE user_id = ?",
            #     (add_value, user_id),
            # )
            result = user_collec.update_one({"user_id": user_id}, {"$inc": {"balance": add_value}})
            if result.modified_count == 0:
                return error.error_non_exist_user_id(user_id)

        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    # title, tags, book_intro, content, searching by keyword
    # return whole book document 
    def search_book(self, user_id, store_id, keyword: str) -> (int, str, list):
        try:
            match = []
            user_collec = self.conn['user']
            assert isinstance(user_collec, pymongo.collection.Collection)

            result = user_collec.find_one({"user_id": user_id})
            if result is None:
                return error.error_non_exist_user_id(user_id) + (match, )

            query = {"$text": {"$search": keyword}}

            if store_id is not None:
                store_collec = self.conn['store']
                assert isinstance(store_collec, pymongo.collection.Collection)
                result = store_collec.find_one({"store_id": store_id})
                if result is None:
                    return error.error_non_exist_store_id(store_id) + (match, )
                query = {"$and": [{"$text": {"$search": keyword}}, {"store_id": store_id}]}

            book_collec = self.conn['book']
            assert isinstance(book_collec, pymongo.collection.Collection)     

            query = {"$text": {"$search": keyword}}
            projection = {"score": {"$meta": "textScore"}}
            cursor = book_collec.find(query, projection).sort([("score", {"$meta": "textScore"})])
            # match = [book for book in cursor]
            for book in cursor:
                book['_id'] = str(book['_id'])
                match.append(book)

        except PyMongoError as e:
            error_message = str(e)
            traceback_info = traceback.format_exc()
            with open('/Users/mayechi/MAJOR/f-junior/database/P1/bookstore/model_log.txt', 'w') as file:
                file.write(error_message + "\n")
                file.write(traceback_info)
            return 528, "{}".format(str(e)), match
        except BaseException as e:
            return 530, "{}".format(str(e)), match
        return 200, "ok", match

    def receive_book(self, user_id: str, order_id: str, store_id: str, book_id: str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)
            
            order_collec = self.conn['order']
            assert isinstance(order_collec, pymongo.collection.Collection)
            filter_condition = {"book_id": book_id, "store_id": store_id, 
                                "user_id": user_id, "order_id": order_id}
            order = order_collec.find_one(filter_condition)
            # check whether the state of order is cancelled or delivered
            # avoid repeated delivery of order
            if order is None:
                return error.error_non_exist_order_id(order_id)
            if order["state"] != order_state["delivered"]:
                return error.error_wrong_order_state(order_id + " -- " + str(order["state"]))
            
            assert isinstance(order_collec, pymongo.collection.Collection)
            update_operation = {"$set": {"state": order_state["received"]}}
            order_collec.update_one(filter_condition, update_operation)

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
    
