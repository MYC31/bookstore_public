import pytest
from fe.access.new_buyer import register_new_buyer
from fe.access.new_seller import register_new_seller
from fe.access import book
import uuid
import fe.conf
from fe.access import auth


class TestOrderState:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.auth = auth.Auth(fe.conf.URL)
        self.seller_id = "test_order_state_seller_id_{}".format(str(uuid.uuid1()))
        self.store_id = "test_order_state_store_id_{}".format(str(uuid.uuid1()))
        self.buyer_id = "test_order_state_buyer_id_{}".format(str(uuid.uuid1()))
        self.seller_password = self.seller_id
        self.buyer_password = self.buyer_id

        # register new buyer, seller and store
        self.seller = register_new_seller(self.seller_id, self.seller_password)
        code = self.seller.create_store(self.store_id)
        assert code == 200
        self.buyer = register_new_buyer(self.buyer_id, self.buyer_password)

        # generate books, and insert them into seller's store, while increase buyer's balance
        # each book's stock level is correctly set here
        book_db = book.BookDB(fe.conf.Use_Large_DB)
        self.books = book_db.get_book_info(0, 10)
        balance = 0
        buy_book_id_list = []
        for b in self.books:
            assert isinstance(b, book.Book)
            # stock level of each book is 5
            code = self.seller.add_book(self.store_id, 5, b)
            assert code == 200
            balance += b.price  # purchase only one piece
            buy_book_id_list.append((b.id, 1))
        code = self.buyer.add_funds(balance)
        assert code == 200

        # make buyer launch order for books
        code, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        self.order_id = order_id
        assert code == 200

        yield

    def test_unpaid_order_deliver(self):
        for b in self.books:
            assert isinstance(b, book.Book)
            book_id = b.id
            code = self.seller.deliver_book(self.buyer_id, self.order_id, self.store_id, book_id)
            assert code == 521
    
    def test_undelivered_order_pay(self):
        for b in self.books:
            assert isinstance(b, book.Book)
            book_id = b.id
            code = self.buyer.receive_book(self.order_id, self.store_id, book_id)
            assert code == 521
    
    def test_ok(self):
        code = self.buyer.payment(self.order_id)
        assert code == 200
        for b in self.books:
            assert isinstance(b, book.Book)
            book_id = b.id
            code = self.seller.deliver_book(self.buyer_id, self.order_id, self.store_id, book_id)
            assert code == 200
            code = self.buyer.receive_book(self.order_id, self.store_id, book_id)
            assert code == 200

    def test_check_and_cancell_order(self):
        user = self.auth
        code, user_order = user.check_order(self.buyer_id)
        assert code == 200
        for order in user_order:
            assert isinstance(order, dict)
            assert order["order_id"] == self.order_id
            book_id = order["book_id"]
            code = user.cancell_order(self.buyer_id, self.order_id, self.store_id, book_id)
            assert code == 200


