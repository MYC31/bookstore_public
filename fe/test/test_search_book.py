import pytest
import uuid
from fe.access.new_buyer import register_new_buyer
from fe.access.new_seller import register_new_seller
from fe.access import book
import fe.conf


class TestSearchBook:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.user_id = "test_add_funds_{}".format(str(uuid.uuid1()))
        self.buyer_password = self.user_id
        self.buyer = register_new_buyer(self.user_id, self.buyer_password)

        self.seller_id = "test_add_books_seller_id_{}".format(str(uuid.uuid1()))
        self.store_id = "test_add_books_store_id_{}".format(str(uuid.uuid1()))
        self.seller_password = self.seller_id
        self.seller = register_new_seller(self.seller_id, self.seller_password)

        # one store
        code = self.seller.create_store(self.store_id)
        assert code == 200
        book_db = book.BookDB(fe.conf.Use_Large_DB)
        self.book_num = 10
        self.books = book_db.get_book_info(0, self.book_num)
        self.keywords = []
        
        # 10 books in store
        for b in self.books:
            code = self.seller.add_book(self.store_id, 1, b)
            self.keywords.append(b.title)
            assert code == 200
        assert len(self.keywords) == self.book_num
        yield

    def test_ok(self):
        for k in self.keywords:
            assert isinstance(k, str)
            code, books = self.buyer.search_book(self.store_id, k)
            assert code == 200
            assert len(books) > 0
            assert books[0]["book_info"]["title"] == k 

            code, books = self.buyer.search_book(None, k)
            assert code == 200
            assert len(books) > 0
            assert books[0]["book_info"]["title"] == k 

    def test_error_store_id(self):
        self.store_id = self.store_id + "_x"
        code, books = self.buyer.search_book(self.store_id, "")
        assert code == 513

    def test_error_user_id(self):
        self.buyer.user_id = self.buyer.user_id + "_x"
        code, books = self.buyer.search_book(self.store_id, "")
        assert code == 511
