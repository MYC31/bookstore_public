import logging
import os
import pymongo
from pymongo.errors import PyMongoError
import traceback


class Store:
    db_name: str
    database: pymongo.database.Database

    def __init__(self, db_name):
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        
        # delete all mongodb databases, 
        # this operation should be deleted when app onlne
        # database_names = client.list_database_names()
        # if db_name in database_names:
        #     client.drop_database(db_name)
            
        self.db_name = db_name
        self.database = client[self.db_name]
        self.init_tables()

    def init_tables(self):
        client = self.get_db_conn()
        try:
            user_collection = client["user"]
            user_collection.delete_many({})
            user_collection.create_index([( "user_id", 1 )], name="user_id_index", unique=False)

            store_collection = client["store"]
            store_collection.delete_many({})
            store_collection.create_index([( "store_id", 1 )], name="store_id_index", unique=True)

            order_collection = client["order"]
            store_collection.delete_many({})
            order_collection.create_index([( "order_id", 1 ), ("user_id", 1)], name="order_id_index")

            book_collection = client["book"]
            book_collection.delete_many({})
            book_collection.create_index([("book_id", 1), ("store_id", 1)], name="book_id_store_id_index", unique=True)
            # index creating is not correct !!!

            index_keys = [("book_info.title", pymongo.TEXT), ("book_info.content", pymongo.TEXT),
              ("book_info.tags", pymongo.TEXT), ("book_info.book_intro", pymongo.TEXT), ]
            book_collection.create_index(index_keys, default_language="english")

        except PyMongoError as e:
            error_message = str(e)
            traceback_info = traceback.format_exc()
            with open('/Users/mayechi/MAJOR/f-junior/database/P1/bookstore/store_log.txt', 'w') as file:
                file.write(error_message + "\n")
                file.write(traceback_info)
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







