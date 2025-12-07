import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import datetime

st.set_page_config(page_title="Inventory & Sales App", layout="wide")

DB_NAME = "inventory.db"

# ========== DATABASE ==========
def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        created_at TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE,
        name TEXT,
        cost REAL,
        price REAL,
        stock INTEGER,
        created_at TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        qty INTEGER,
        cost_each REAL,
        price_each REAL,
        total REAL,
        profit REAL,
        sold_by INTEGER,
        sold_at TEXT
    )""")

    conn.commit()
    return conn

conn = init_db()

# ========== AUTH ==========
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_default_user():
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = 'boss'")
    if not c.fetchone():
        now = datetime.datetime.utcnow().isoformat()
        c.execute("INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
                  ("boss", hash_password("boss123"), "boss", now))
        conn.commit()

create_default_user()

def login_user(username, password):
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?",
              (username, hash_password(password)))
    return c.fetchone()

def create_user(username, password, role):
    if not username or not password:
        return False, "Username dan password wajib diisi"

    try:
        c = conn.cursor()
        now = datetime.datetime.utcnow().isoformat()
        c.execute("INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
                  (username, hash_password(password), role, now))
        conn.commit()
        return True, "User berhasil dibuat"
    except sqlite3.IntegrityError:
        return False, "Username sudah digunakan"


# ========== PRODUCT ==========
def add_product(sku, name, cost, price, stock):
    c = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    c.execute("INSERT INTO products (sku, name, cost, price, stock, created_at) VALUES (?, ?, ?, ?, ?, ?)",
              (sku, name, cost, price, stock, now))
    conn.commit()

def update_product(pid, name, cost, price, stock):
    c = conn.cursor()
    c.execute("UPDATE products SET name=?, cost=?, price=?, stock=? WHERE id=?",
              (name, cost, price, stock, pid))
    conn.commit()

def get_products():
    return pd.read_sql_query("SELECT * FROM products ORDER BY name", conn)

# ========== SALES ==========
def record_sale(product_id, qty, sold_by):
    c = conn.cursor()

    c.execute("SELECT stock, cost, price FROM products WHERE id = ?", (product_id,))
    row = c.fetchone()
    if not row:
        return False, "Produk tidak ditemukan"

    stock, cost, price = row

    if qty > stock:
        return False, "Stok tidak mencukupi"

    total = price * qty
    profit = (price - cost) * qty
    sold_at = datetime.datetime.utcnow().isoformat()

    c.execute("""INSERT INTO sales
        (product_id, qty, cost_each, price_each, total, profit, sold_by, sold_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (product_id, qty, cost, price, total, profit, sold_by, sold_at))

    c.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (qty, product_id))
    conn.commit()
    return True, "Penjualan berhasil"

def get_sales():
    return pd.read_sql_query("""
        SELECT s.id, p.name, s.qty, s.price_each, s.total, s.profit, s.sold_at, u.username
        FROM sales s
        JOIN products p ON s.product_id = p.id
        JOIN users u ON s.sold_by = u.id
        ORDER BY s.sold_at DESC
    """, conn)

# ========== SESSION ==========
if "user" not in st.session_state:
    st.session_state.user = None


# ========== UI ==========
if st.session_state.user is None:
    st.title("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state.user = {
                "id": user[0],
                "username": user[1],
                "role": user[3]
            }
            st.rerun()
        else:
            st.error("Login gagal")

else:
    user = st.session_state.user
    role = user["role"]

    st.sidebar.write(f"Login sebagai: {user['username']} ({role})")

    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    if role == "boss":
        menu = st.sidebar.selectbox("Menu", ["Home", "Produk & Stok", "Penjualan", "Histori Penjualan", "Manajemen User"])
    else:
        menu = st.sidebar.selectbox("Menu", ["Home", "Penjualan", "Histori Penjualan"])

    # ========== HOME ==========
    if menu == "Home":
        st.title("Dashboard")

    # ========== PRODUK ==========
    elif menu == "Produk & Stok":
        if role != "boss":
            st.error("Tidak ada akses")
            st.stop()

        st.subheader("Tambah Produk")

        with st.form("add_prod"):
            sku = st.text_input("SKU")
            name = st.text_input("Nama Produk")
            cost = st.number_input("Harga Modal", min_value=0.0)
            price = st.number_input("Harga Jual", min_value=0.0)
            stock = st.number_input("Stok", min_value=0, step=1)

            if st.form_submit_button("Tambah User"):
                ok, msg = create_user(username, password, role_user)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


    # ========== PENJUALAN ==========
    elif menu == "Penjualan":
        st.subheader("Input Penjualan")

        df = get_products()
        if df.empty:
            st.info("Belum ada produk")
        else:
            product_map = {f"{r['name']} (Stok: {r['stock']})": r['id'] for _, r in df.iterrows()}
            selected = st.selectbox("Pilih Produk", list(product_map.keys()))
            qty = st.number_input("Qty", min_value=1, step=1)

            if st.button("Simpan Penjualan"):
                pid = product_map[selected]
                ok, msg = record_sale(pid, qty, user["id"])
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # ========== HISTORI ==========
    elif menu == "Histori Penjualan":
        st.subheader("Histori & P&L Harian")

        sales_df = get_sales()

        if sales_df.empty:
            st.info("Belum ada transaksi")
        else:
            sales_df["sold_at"] = pd.to_datetime(sales_df["sold_at"])
            sales_df["tanggal"] = sales_df["sold_at"].dt.date

            st.dataframe(sales_df)

            daily = sales_df.groupby("tanggal").agg(
                total_penjualan=("total", "sum"),
                total_profit=("profit", "sum")
            ).reset_index()

            st.markdown("### P&L Harian")
            st.dataframe(daily)

    # ========== USER ==========
    elif menu == "Manajemen User":
        if role != "boss":
            st.error("Tidak ada akses")
            st.stop()

        st.subheader("Tambah User")

        with st.form("add_user"):
            username = st.text_input("Username baru")
            password = st.text_input("Password", type="password")
            role_user = st.selectbox("Role", ["boss", "karyawan"])

            if st.form_submit_button("Tambah User"):
                create_user(username, password, role_user)
                st.success("User berhasil dibuat")
                st.rerun()
