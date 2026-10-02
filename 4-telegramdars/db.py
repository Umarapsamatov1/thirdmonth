import sqlite3

DB_NAME = "user.db"


def connect():
    return sqlite3.connect(DB_NAME)


def create_table():
    with connect() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY,
            full_name TEXT,
            phone TEXT,
            lat REAL,
            lon REAL
        )
        """)

        con.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            code TEXT UNIQUE 
        )
        """)

        con.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_code TEXT,
            name TEXT UNIQUE,
            price INTEGER,
            description TEXT,
            image TEXT
        )
        """)


def get_product_by_category(code):
    with connect() as con:
        cur = con.cursor()
        cur.execute("""
        SELECT id, name FROM products WHERE category_code = ?
        """, (code,))
        return cur.fetchall()


def get_products(product_id):
    with connect() as con:
        cur = con.cursor()
        cur.execute("""
        SELECT id, name, price, description, image
        FROM products WHERE id=?
        """, (product_id,))
        return cur.fetchone()


def add_user(tg_id, full_name, phone, lat, lon):
    with connect() as con:
        con.execute("""
        INSERT OR REPLACE INTO users (tg_id, full_name, phone, lat, lon)
        VALUES (?, ?, ?, ?, ?)
        """, (tg_id, full_name, phone, lat, lon))


def get_user(tg_id):
    with connect() as con:
        cur = con.cursor()
        cur.execute("""
        SELECT * FROM users WHERE tg_id = ? 
        """, (tg_id,))
        return cur.fetchone()


def update_name(tg_id, full_name):
    with connect() as con:
        con.execute("UPDATE users SET full_name=? WHERE tg_id=?",
                    (full_name, tg_id))


def update_phone(tg_id, phone):
    with connect() as con:
        con.execute("UPDATE users SET phone=? WHERE tg_id=?",
                    (phone, tg_id))


def get_categories():
    with connect() as con:
        cur = con.cursor()
        cur.execute("SELECT code, name FROM categories")
        return cur.fetchall()


def get_categories_code_by_name(name):
    with connect() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT code FROM categories WHERE name=?",
            (name,)
        )
        row = cur.fetchone()
        return row[0] if row else None


def category_exists(code):
    with connect() as con:
        cur = con.cursor()
        cur.execute("SELECT 1 FROM categories WHERE code=?", (code,))
        return cur.fetchone() is not None


def add_category(name, code):
    with connect() as con:
        con.execute(
            "INSERT OR IGNORE INTO categories (name, code) VALUES (?, ?)",
            (name, code)
        )


def add_product(category_code, name, price, description, image):
    with connect() as con:
        con.execute("""
            INSERT INTO products (category_code, name, price, description, image)
            VALUES (?, ?, ?, ?, ?)  
        """, (category_code, name, price, description, image))

