#### <center> design of database <center/>  

1. user:
   user_id: str     Primary key
   password: str
   balance: int
   token: str
   terminal: str
   user_store: list - [store_id]
   user_order: list - [order_id]
   

2. store:
   store_id: str    Primary key
   user_id: str     (to be discussed)
   book: list - [book_id]


3. order:
   order_id: str    Primary key
   user_id: str
   store_id: str
   book_id: str
   count: int
   price: int


4. book:
   book_id: str    Primary key
   title: str
   author: str
   publisher: str
   original_title: str
   translator: str
   pub_year: str
   pages: int
   price: int
   currency_unit: str
   binding: str
   isbn: str
   author_intro: str
   book_intro: str
   content: str
   tags: str
   picture: str


