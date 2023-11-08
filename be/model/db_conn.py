from be.model import store
import pymongo


class DBConn:
    def __init__(self):
        # set local attribute to be database instance from store module
        self.conn = store.get_db_conn()

    def user_id_exist(self, user_id):
        user_collec = self.conn['user']
        assert isinstance(user_collec, pymongo.collection.Collection)
        result = user_collec.find_one({"user_id": user_id})
        if result is None:
            return False
        else:
            return True

    def book_id_exist(self, store_id, book_id):
        book_collec = self.conn['book']
        assert isinstance(book_collec, pymongo.collection.Collection)
        result = book_collec.find_one({"book_id": book_id, "store_id": store_id})
        if result is None:
            return False
        else:
            return True

    def store_id_exist(self, store_id):
        store_collec = self.conn['store']
        assert isinstance(store_collec, pymongo.collection.Collection)
        result = store_collec.find_one({"store_id": store_id})
        if result is None:
            return False
        else:
            return True

    def order_id_exist(self, order_id):
        order_collec = self.conn['order']
        assert isinstance(order_collec, pymongo.collection.Collection)
        result = order_collec.find_one({"order_id": order_id})
        if result is None:
            return False
        else:
            return True
        
