import logging
import os
import pymongo


class Store:
    db_name: str
    database: pymongo.database.Database

    def __init__(self, db_name):
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        
        # delete all mongodb databases, 
        # this operation should be deleted when app onlne
        database_names = client.list_database_names()
        if db_name in database_names:
            client.drop_database(db_name)
            
        self.db_name = db_name
        self.database = client[self.db_name]
        self.init_tables()

    def init_tables(self):
        client = self.get_db_conn()
        try:
            user_collection = client["user"]
            # user_collection.create_index([("user_id", 1)], name="user_id_index", unique=True)

            store_collection = client["store"]
            # store_collection.create_index([("store_id", 1)], name="store_id_index", unique=True)

            order_collection = client["order"]
            # order_collection.create_index([("order_id", 1)], name="order_id_index", unique=True)

            book_collection = client["book"]
            # book_collection.create_index([("book_id", 1), ("store_id", 1)], name="book_id_store_id_index", unique=True)

        except Exception as e:
            logging.error(e)

    def get_db_conn(self) -> pymongo.database.Database:
        return self.database    # establish databse connection suing self.database


# global variable for database instance
database_instance: Store = None


# init function of global variable 
# should be callled before get_db_conn
def init_database(db_name):
    global database_instance
    database_instance = Store(db_name)


# outer plugin for obtaining database instance
# store.get_db_conn
def get_db_conn():
    global database_instance
    return database_instance.get_db_conn()







