import sqlite3
import socket
import json
import inflect
import threading

"""
The func connects the server to the client, then place the req of the client in the right func.

"""

DB_FILE_NAME = "tables.db"

SIGN_UP = 100
LOG_IN = 101
UPDATE_USER_PRODUCTS_REQ = 102
CHECK_RECIPE_REQ = 103
UPDATE_PRODUCTS_REQ = 104
SHOW_USER_EXIST_LIST = 105
SORT_USER_LIST = 106

SECCESSFUL_SIGN_UP = 1000
ERROR_USER_LOGGED_IN_BEFORE = 1001
ERROR_USER_DIDNT_SIGN_UP = 1002
SECCUSSFUL_LOG_IN = 1003
USER_EXIST_LIST = 1004

"""
this func listen to clients and connects them to thread (also connecting db to the server).

    input:
      port - the connection port.
      host - who to listen ('0.0.0.0' - listening to all devices).

    output:
      None.
"""


def server(port, host):
    connection = sqlite3.connect(DB_FILE_NAME, check_same_thread=False)
    db = connection.cursor()
    server_socket = socket.socket()
    server_socket.bind((host, port))
    server_socket.listen(10)

    while True:
        conn, client_address = server_socket.accept()
        print conn, client_address
        # gives the new client a thread of himself.
        threading.Thread(target=client_handler, args=(conn, client_address, db, connection)).start()

    server_socket.close()
    connection.close()


"""
this func handles clients and their requests.
    input:
      db - the database.
      connection - the connection to the database.
      server_conn - the connection between the client to the server.
      client_addr - the client adress.

    output:
      None.
"""


def client_handler(server_conn, client_addr, db, connection):
    while True:
        json_msg = server_conn.recv(1024)
        print json_msg
        msg_to_usr = ""
        if json_msg == "" or json_msg is None:
            print "lost connection with: " + client_addr[0]
            break

        msg = json.loads(json_msg)

        if msg["code"] == SIGN_UP:
            msg_to_usr = sign_in(db, connection, msg["username"], msg["pass"])

        elif msg["code"] == LOG_IN:
            msg_to_usr = log_in(db, msg["username"])

        elif msg["code"] == UPDATE_USER_PRODUCTS_REQ:
            user_id = get_user_id(db, msg["username"])
            update_user_products(db, connection, msg["product"], msg["amount"], user_id)

        elif msg["code"] == CHECK_RECIPE_REQ:
            user_id = get_user_id(db, msg["username"])
            msg_to_usr = check_recipes(db, user_id, msg["recipe"])

        elif msg["code"] == UPDATE_PRODUCTS_REQ:
            user_id = get_user_id(db, msg["username"])
            update_products(db, connection, msg["product"], msg["amount"], user_id)

        elif msg["code"] == SHOW_USER_EXIST_LIST:
            user_id = get_user_id(db, msg["username"])
            msg_to_usr = user_exist_list(db, user_id)

        elif msg["code"] == SORT_USER_LIST:
            user_id = get_user_id(db, msg["username"])
            msg_to_usr = sort_user_list(db, user_id, msg["product"])

        server_conn.send(msg_to_usr)


"""
this func updates the products' amounts after the user's changes with the speech recognition.

    input:
      db - the database.
      connection - the connection with the db.
      new_product - the changed product.
      new_amount - its new amount.
      user_id - the id of the specific user.

    output:
      None.
"""


def update_products(db, connection, new_product, new_amount, user_id):
    user_list = user_exist_list(db, user_id)
    p = inflect.engine()
    one_product = p.singular_noun(new_product)
    if not one_product:
        one_product = new_product
    products = json.loads(user_list)["products"]
    amounts = json.loads(user_list)["amounts"]
    if one_product in products and (amounts[products.index(one_product)] + int(new_amount)) > 0:
        new_amount = str(amounts[products.index(one_product)] + int(new_amount))
    elif int(new_amount) < 0:
        new_amount = "0"

    update_user_products(db, connection, one_product, new_amount, user_id)


"""
this func gets the user's id based on his username.

    input:
      db - the database.
      username - the user's username.

    output:
      the user's id.
"""


def get_user_id(db, username):
    sql_cmd = "SELECT id FROM t_users WHERE username = '" + username + "';"
    db_res = db.execute(sql_cmd)
    for i in db_res:
        return str(i[0])


"""
this func checks if the user isn't sign in already, and if he isn't, it registers him.

    input:
      db - the database.
      connection - the connection to the DB.
      username - the user's username.
      password - the user's password.

    output:
      JSON object that contains whatever success or not.
"""


def sign_in(db, connection, username, password):
    if json.loads(log_in(db, username))["code"] == ERROR_USER_DIDNT_SIGN_UP:
        sql_cmd = "INSERT INTO t_users (username, password) VALUES('" + username + "', '" + password + "');"
        db.execute(sql_cmd)
        connection.commit()
        user_id = get_user_id(db, username)
        create_user_basic_list(db, user_id, connection)
        return json.dumps({"code": SECCESSFUL_SIGN_UP})
    return json.dumps({"code": ERROR_USER_LOGGED_IN_BEFORE})


"""
the func checks if the user is registered and logs him in.

    input:
      db - the database.
      username - the user's username.

    output:
       JSON object contains whatever success or not.
"""


def log_in(db, username):
    sql_cmd = "SELECT * FROM t_users WHERE username = '" + username + "';"
    db.execute(sql_cmd)
    db_res = db.fetchone()
    if db_res is None:
        return json.dumps({"code": ERROR_USER_DIDNT_SIGN_UP})
    return json.dumps({"code": SECCUSSFUL_LOG_IN})


"""
this func returns a JSON object of the user's products and amounts.

    input:
      db - the database.
      user_id - the id of the specific user.

    output:
      JSON object that contains the user's products and amounts.
"""


def user_exist_list(db, user_id):
    sql_cmd = "SELECT * FROM t_products WHERE user_id = " + user_id + ";"
    db_res = db.execute(sql_cmd)
    products = []
    amounts = []
    types = []
    for product in db_res:
        products.append(product[0])
        amounts.append(product[1])
        types.append(product[2])

    return json.dumps({"code": USER_EXIST_LIST, "products": products, "amounts": amounts, "types": types})


"""
this func updates the products' amounts after the user's changes.

    input:
      db - the database.
      connection - the connection to the DB.
      product - the changed product.
      amount - its new amount.
      user_id - the id of the specific user.

    output:
      None.
"""


def update_user_products(db, connection, product, amount, user_id):
    sql_cmd = "UPDATE t_products SET amnt = " + str(amount) + \
              " WHERE name = '" + product + "' AND user_id = " + user_id + ";"
    db_res = db.execute(sql_cmd)
    connection.commit()
    if db_res.rowcount == 0:
        sql_cmd = "INSERT INTO t_products (name, amnt, user_id)" \
                  " VALUES('" + product + "', " + str(amount) + ", " + user_id + ");"
        db.execute(sql_cmd)
        connection.commit()


"""
this func checks what the user is missing to make his desirable food based on a recipe the program has in the DB.

    input:
      db - the database.
      user_id - the id of the specific user.
      recipe - the user's desirable food's name (Pizza, Pasta, etc.).
"""


def check_recipes(db, user_id, recipe):
    products_to_buy = []
    amounts_to_buy = []
    user_json_list = user_exist_list(db, user_id)
    user_list = json.loads(user_json_list)["products"]
    user_amounts = json.loads(user_json_list)["amounts"]
    sql_cmd = "SELECT instructions FROM t_recipes WHERE name = '" + recipe + "';"
    recipes = db.execute(sql_cmd)
    for i in recipes:
        instructions = i[0]

    sql_cmd = "SELECT * FROM t_indgredients WHERE recipe_name = '" + recipe + "';"
    db_res = db.execute(sql_cmd)

    for dbLine in db_res:
        if dbLine[0] in user_list:
            if dbLine[1] > user_amounts[user_list.index(dbLine[0])]:
                products_to_buy.append(dbLine[0])
                amounts_to_buy.append(str(dbLine[1] - user_amounts[user_list.index(dbLine[0])]))
        else:
            products_to_buy.append(dbLine[0])
            amounts_to_buy.append(str(dbLine[1]))

    return json.dumps({"products": products_to_buy, "amounts": amounts_to_buy, "Instructions":
        instructions})


"""
this func creates a basic list of products for the user after signing up.

    input:
      db - the database.
      user_id - the id of the specific user.
      connection - the connection to the DB.

    output:
      None.
"""


def create_user_basic_list(db, user_id, connection):
    sql_cmd = "INSERT INTO t_products (name, amnt, product_type, user_id) VALUES ('milk', 0, 'milks and eggs', " \
              + user_id + ");"
    db.execute(sql_cmd)
    connection.commit()
    sql_cmd = "INSERT INTO t_products (name, amnt, product_type, user_id) VALUES ('tomato', 0, 'vegetables', " \
              + user_id + ");"
    db.execute(sql_cmd)
    connection.commit()
    sql_cmd = "INSERT INTO t_products (name, amnt, product_type, user_id) VALUES ('cucumber', 0, 'vegetables', " \
              + user_id + ");"
    db.execute(sql_cmd)
    connection.commit()
    sql_cmd = "INSERT INTO t_products (name, amnt, product_type, user_id) VALUES ('apple', 0, 'fruits', " \
              + user_id + ");"
    db.execute(sql_cmd)
    connection.commit()
    sql_cmd = "INSERT INTO t_products (name, amnt, product_type, user_id) VALUES ('lemon', 0, 'fruits', " \
              + user_id + ");"
    db.execute(sql_cmd)
    connection.commit()
    sql_cmd = "INSERT INTO t_products (name, amnt, product_type, user_id) VALUES ('white bread', 0, 'breads', " \
              + user_id + ");"
    db.execute(sql_cmd)
    connection.commit()
    sql_cmd = "INSERT INTO t_products (name, amnt, product_type, user_id) VALUES ('cheese', 0, 'milks and eggs', " \
              + user_id + ");"
    db.execute(sql_cmd)
    connection.commit()
    sql_cmd = "INSERT INTO t_products (name, amnt, product_type, user_id) VALUES ('water', 0, 'drinks', " \
              + user_id + ");"
    db.execute(sql_cmd)
    connection.commit()
    sql_cmd = "INSERT INTO t_products (name, amnt, product_type, user_id) VALUES ('egg', 0, 'milks and eggs', " \
              + user_id + ");"
    db.execute(sql_cmd)
    connection.commit()
    sql_cmd = "INSERT INTO t_products (name, amnt, product_type, user_id) VALUES ('canned corn', 0, 'canned food', " \
              + user_id + ");"
    db.execute(sql_cmd)
    connection.commit()
    sql_cmd = "INSERT INTO t_products (name, amnt, product_type, user_id) VALUES ('chocolate', 0, 'candies', " \
              + user_id + ");"
    db.execute(sql_cmd)
    connection.commit()


"""
this func sorts the user's list based on the given product type.

    input:
      db - the database.
      user_id - the id of the specific user.
      product_type - the given product type.

    output:
     whats left from the user's list.
"""


def sort_user_list(db, user_id, product_type):
    sql_cmd = "SELECT name, amnt FROM t_products WHERE product_type = '" + product_type + "' AND user_id = " \
              + user_id + ";"
    db_res = db.execute(sql_cmd)
    products = []
    amounts = []
    for product in db_res:
        products.append(product[0])
        amounts.append(product[1])

    return json.dumps({"code": 106, "products": products, "amounts": amounts})


"""
this func is the main of the program (only calls the server func).

    input:
      None.

    output:
      None.
"""


def main():
    server(port=8000, host="0.0.0.0")


if __name__ == '__main__':
    main()
