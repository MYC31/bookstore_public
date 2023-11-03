import logging
import os
import pymongo


class Store:
    db_name: str
    database: pymongo.database.Database

    def __init__(self, db_name):
        # self.database = os.path.join(db_path, "be.db")
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        self.db_name = db_name
        self.database = client[self.database]
        self.init_tables()

    def init_tables(self):
        client = self.get_db_conn()
        with client.start_session() as session:
            with session.start_transaction():
                try:
                    user_collection = client["user"]
                    store_collection = client["store"]
                    order_collection = client["order"]
                    book_collection = client["book"]
                except Exception as e:
                    session.abort_transaction()
                    logging.error(e)
            session.end_session()

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







