from azure.cosmos import CosmosClient, exceptions
import uuid
import os
import importlib

#Organização das classes // Ligação com o CosmosDB

class CosmosDB:

    def __init__(self):
        os.environ['COSMOS_DB_URL'] = 'https://academia2023a.documents.azure.com:443'
        os.environ['COSMOS_DB_KEY'] = '8mmMNPiZqLgGK5em6ZicrcLFyER6aQBoJm2wfJJWzRxJO4IDDyqJbqG0BgwgxNuBULscHc20HihoACDbyYRd0g=='

        url = os.environ['COSMOS_DB_URL']
        key = os.environ['COSMOS_DB_KEY']

        self.client = CosmosClient(url, credential=key)
        self.database = self.client.get_database_client('fernando')

        self.products = self.database.get_container_client('artigos')
        self.orders = self.database.get_container_client('orders')
        self.users = self.database.get_container_client('users')
        self.carts = self.database.get_container_client('carts')
        self.billing_infos = self.database.get_container_client('billing_infos')


        #Funções relacionadas à operação//PRODUTOS

    def get_product_by_id(self, product_id):
        query = f'SELECT * FROM products p WHERE p.id = "{product_id}"'
        result = list(self.products.query_items(query=query, enable_cross_partition_query=True))
        return result[0] if result else None

    def get_all_products(self):
        query = 'SELECT * FROM products'
        return list(self.products.query_items(query=query, enable_cross_partition_query=True))

    def add_product(self, product_details):
        self.products.create_item(body=product_details)

    def update_product(self, product_id, product_details):
        product = self.get_product_by_id(product_id)
        if product:
            for key, value in product_details.items():
                product[key] = value
            self.products.replace_item(item=product, item_link=product['id'])

    def delete_product(self, product_id):
        product = self.get_product_by_id(product_id)
        if product:
            self.products.delete_item(item=product, item_link=product['id'])


        #Funções relacionadas à pedidos // COMPRAS // LOJA
    def get_sales_data(self, start_date, end_date):
        start_date = start_date.isoformat()
        end_date = end_date.isoformat()

        query = f'SELECT o.date, o.total FROM orders o WHERE o.date >= "{start_date}" AND o.date < "{end_date}" AND o.status = "completed"'
        sales_data = list(self.orders.query_items(query=query, enable_cross_partition_query=True))

        return sales_data

    def get_order_history_by_user(self, user_id):
        query = f'SELECT * FROM orders o WHERE o.user_id = "{user_id}"'
        return list(self.orders.query_items(query=query, enable_cross_partition_query=True))

    def get_product(self, product_id):
        query = f"SELECT * FROM products p WHERE p.id = '{product_id}'"
        items = list(self.products.query_items(query=query, enable_cross_partition_query=True))
        if items:
            return items[0]
        return None

    def get_orders(self):
        query = "SELECT * FROM orders o"
        items = list(self.orders.query_items(query=query, enable_cross_partition_query=True))
        return items
    
    def get_users(self):
        query = "SELECT * FROM users u WHERE u.is_online = true"
        items = list(self.users.query_items(query=query, enable_cross_partition_query=True))
        return items

        #Funções à respeito do carrinho de compra e funcionalidade.

    def update_cart(self, user_id, product_id, quantity):
        query = f"SELECT * FROM carts c WHERE c.user_id = '{user_id}' AND c.product_id = '{product_id}'"
        items = list(self.carts.query_items(query=query, enable_cross_partition_query=True))

        if items:
            item = items[0]
            if quantity > 0:
                item['quantity'] = quantity
                self.carts.replace_item(item, item)
            else:
                self.carts.delete_item(item, partition_key=item['user_id'])
        else:
            if quantity > 0:
                item = {
                    'id': str(uuid.uuid4()),
                    'user_id': user_id,
                    'product_id': product_id,
                    'quantity': quantity
                }
                self.carts.create_item(item)

    def get_order_by_id(self, order_id):
        query = f'SELECT * FROM orders o WHERE o.id = "{order_id}"'
        result = list(self.orders.query_items(query=query, enable_cross_partition_query=True))
        return result[0] if result else None
    
    def create_order(self, user_id, order_details):
        order_details['user_id'] = user_id
        self.orders.create_item(body=order_details)

    def get_all_orders(self):
        query = 'SELECT * FROM orders'
        return list(self.orders.query_items(query=query, enable_cross_partition_query=True))

    def update_order_status(self, order_id, new_status):
        order = self.get_order_by_id(order_id)
        if order:
            order['status'] = new_status
            self.orders.replace_item(item=order, item_link=order['id'])

        #Funções com ligação ao banco de dados //////////////////////////////

    def get_user_by_email(self, email):
        query = f"SELECT * FROM users WHERE users.email = '{email}'"
        users = list(self.users.query_items(query=query, enable_cross_partition_query=True))
        return users[0] if users else None


    def get_user_by_id(self, user_id):
        try:
            return self.users.read_item(item=user_id, partition_key=user_id)
        except exceptions.CosmosResourceNotFoundError:
            return None

    def create_user(self, name, lastname, email, password):
        user = {
            "id": str(uuid.uuid4()),
            "name": name,
            "lastname": lastname,
            "email": email,
            "password": password
        }
        print(f"Creating user: {user}")
        self.users.create_item(user)
        print("User created successfully")

                                                        #////////////////
    def authenticate_user(self, email, password):
        query = f"SELECT * FROM users WHERE users.email = '{email}' AND users.password = '{password}'"
        users = list(self.users.query_items(query=query, enable_cross_partition_query=True))
        return users[0] if users else None


    def update_user(self, user_id, user_details):
        user = self.get_user_by_id(user_id)
        if user:
            for key, value in user_details.items():
                user[key] = value
            self.users.replace_item(item=user, partition_key=user_id)

    def delete_user(self, user_id):
        self.users.delete_item(item=user_id, partition_key=user_id)


        #Funções do carrinho de compra relacionado ao SQLAlchemy
    def get_items_in_cart(self, user_id):
        query = f'SELECT * FROM carts c WHERE c.user_id = "{user_id}"'
        items_in_cart = list(self.carts.query_items(query=query, enable_cross_partition_query=True))
        items = []
        for item in items_in_cart:
            item_data = self.get_product_by_id(item['item_id'])
            items.append(item_data)
        return items

    def clear_cart(self, user_id):
        query = f'SELECT * FROM carts c WHERE c.user_id = "{user_id}"'
        cart_items = list(self.carts.query_items(query=query, enable_cross_partition_query=True))
        for item in cart_items:
            self.carts.delete_item(item=item, partition_key=user_id)

    def remove_product_from_cart(self, user_id, product_id):
        query = f'SELECT * FROM carts c WHERE c.user_id = "{user_id}" AND c.item_id = "{product_id}"'
        cart_items = list(self.carts.query_items(query=query, enable_cross_partition_query=True))
        if cart_items:
            item = cart_items[0]
            self.carts.delete_item(item=item, partition_key=user_id)



def get_billing_info(self, user_id):
    query = f"SELECT * FROM c WHERE c.user_id = '{user_id}'"
    billing_info = list(self.billing_infos.query_items(query=query, enable_cross_partition_query=True))
    return billing_info[0] if billing_info else None

def get_billing_info_by_user_id(self, user_id):
    return self.get_billing_info(user_id)

def add_billing_info(self, user_id, card_number, cardholder_name, expiration_month, expiration_year, cvv):
    billing_info = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "card_number": card_number,
        "cardholder_name": cardholder_name,
        "expiration_month": expiration_month,
        "expiration_year": expiration_year,
        "cvv": cvv
    }
    self.billing_infos.create_item(billing_info)

def update_billing_info(self, user_id, billing_info_details):
    billing_info = self.get_billing_info(user_id)
    if billing_info:
        for key, value in billing_info_details.items():
            billing_info[key] = value
        self.billing_infos.replace_item(item=billing_info, partition_key=user_id)

def delete_billing_info(self, user_id):
    billing_info = self.get_billing_info(user_id)
    if billing_info:
        self.billing_infos.delete_item(item=billing_info['id'], partition_key=user_id)

