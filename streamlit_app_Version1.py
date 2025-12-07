# streamlit_inventory_app_full.py
# Inventory & Sales Streamlit App
# - Role: boss (admin) and karyawan (employee)
# - Boss can manage products (incl. cost), users, edit stock
# - Karyawan can only record sales and view history
# - P&L harian ditampilkan di Histori Penjualan
# NOTE: If you already have an existing inventory.db, remove it so the new schema is used.

import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import datetime
import io
import os

DB_PATH = "inventory.db"

# -------------------------
# Utility: DB init & helpers
# -------------------------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    # If DB file exists but schema is old, you'll need to remove it to apply schema changes.
    conn = get_conn()
    c = conn.cursor()
    # users: id, username(unique), password_hash, role ('boss' or 'karyawan'), created_at
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )""")
    # products: id, sku, name, cost, price, stock, created_at
    c.execute("""CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sku TEXT UNIQUE,
                    name TEXT NOT NULL,
                    cost REAL NOT NULL,
                    price REAL NOT NULL,
                    stock INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )""")
    # sales: id, product_id, qty, cost_each, price_each, total, profit, sold_by (user id), sold_at
    c.execute("""CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    qty INTEGER NOT NULL,
                    cost_each REAL NOT NULL,
                    price_each REAL NOT NULL,
                    total REAL NOT NULL,
                    profit REAL NOT NULL,
                    sold_by INTEGER NOT NULL,
                    sold_at TEXT NOT NULL,
                    FOREIGN KEY(product_id) REFERENCES products(id),
                    FOREIGN KEY(sold_by) REFERENCES users(id)
                )""")
    conn.commit()

    # create default boss account if not exists
    if not get_user_by_username("boss"):
        create_user("boss", "boss123", "boss")
    conn.close()

def hash_password(password: str) -> str:
    # simple sha256, include static salt (for demo). In prod use better hashing (bcrypt).
    salt = "static_salt_demo_v1"
    return hashlib.sha256((salt + password).encode()).hexdigest()

# -------------------------
# User management
# -------------------------

def create_user(username: str, password: str, role: str="karyawan"):
    conn = get_conn()
    c = conn.cursor()
    ph = hash_password(password)
    now = datetime.datetime.datetime.utcnow().isoformat() if hasattr(datetime, 'datetime') else datetime.datetime.utcnow().isoformat()
    try:
        c.execute("INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                  (username, ph, role, now))
        conn.commit()
        return True, "User dibuat."
    except sqlite3.IntegrityError as e:
        return False, "Username sudah ada."
    finally:
        conn.close()

def get_user_by_username(username: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, username, password_hash, role, created_at FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    return row

def authenticate(username: str, password: str):
    row = get_user_by_username(username)
    if not row:
        return False, "User tidak ditemukan."
    stored_hash = row[2]
    if stored_hash == hash_password(password):
        user = {"id": row[0], "username": row[1], "role": row[3]}
        return True, user
    else:
        return False, "Password salah."

# -------------------------
# Product & Sales
# -------------------------

def add_product(sku: str, name: str, cost: float, price: float, stock: int):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.datetime.datetime.utcnow().isoformat() if hasattr(datetime, 'datetime') else datetime.datetime.utcnow().isoformat()
    try:
        c.execute("INSERT INTO products (sku, name, cost, price, stock, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                  (sku if sku else None, name, cost, price, stock, now))
        conn.commit()
        return True, "Produk berhasil ditambahkan."
    except sqlite3.IntegrityError:
        return False, "SKU sudah ada."
    finally:
        conn.close()


def update_product(product_id: int, name: str, cost: float, price: float, stock: int, sku: str=None):
    conn = get_conn()
    c = conn.cursor()
    try:
        if sku:
            c.execute("UPDATE products SET sku=?, name=?, cost=?, price=?, stock=? WHERE id=?",
                      (sku, name, cost, price, stock, product_id))
        else:
            c.execute("UPDATE products SET name=?, cost=?, price=?, stock=? WHERE id=?",
                      (name, cost, price, stock, product_id))
        conn.commit()
        return True, "Produk diperbarui."
    except sqlite3.IntegrityError:
        return False, "SKU duplikat."
    finally:
        conn.close()


def list_products_df():
    conn = get_conn()
    df = pd.read_sql_query("SELECT id, sku, name, cost, price, stock, created_at FROM products ORDER BY name", conn)
    conn.close()
    return df


def record_sale(product_id: int, qty: int, sold_by: int):
    conn = get_conn()
    c = conn.cursor()
    # check stock, cost, price
    c.execute("SELECT stock, cost, price FROM products WHERE id = ?", (product_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, "Produk tidak ditemukan."
    stock, cost, price = row
    if qty <= 0:
        conn.close()
        return False, "Jumlah harus > 0."
    if stock < qty:
        conn.close()
        return False, f"Stok tidak cukup. Sisa: {stock}"
    new_stock = stock - qty
    total = round(price * qty, 2)
    profit = round((price - cost) * qty, 2)
    sold_at = datetime.datetime.datetime.utcnow().isoformat() if hasattr(datetime, 'datetime') else datetime.datetime.utcnow().isoformat()
    try:
        c.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, product_id))
        c.execute("INSERT INTO sales (product_id, qty, cost_each, price_each, total, profit, sold_by, sold_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (product_id, qty, cost, price, total, profit, sold_by, sold_at))
        conn.commit()
        return True, f"Penjualan dicatat. Total: {total}"
    except Exception as e:
        conn.rollback()
        return False, "Gagal mencatat penjualan."
    finally:
        conn.close()


def get_sales_df():
    conn = get_conn()
    query = """
    SELECT s.id, p.name as product_name, p.sku, s.qty, s.cost_each, s.price_each, s.total, s.profit, u.username as sold_by, s.sold_at
    FROM sales s
    JOIN products p ON s.product_id = p.id
    JOIN users u ON s.sold_by = u.id
    ORDER BY s.sold_at DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# -------------------------
# Streamlit App
# -------------------------
st.set_page_config(page_title="Inventory & Sales App", layout="wide")
init_db()

# Session state for login
if "user" not in st.session_state:
    st.session_state.user = None

if "_just_logged_in" not in st.session_state:
    st.session_state._just_logged_in = False


def logout():
    st.session_state.user = None
    st.success("Logged out.")

# Sidebar: Login / User actions
with st.sidebar:
    st.title("Inventory App")
    if st.session_state.user is None:
        st.subheader("Login")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            ok, resp = authenticate(username.strip(), password)
            if ok:
                st.session_state.user = resp
                # use st.rerun (Streamlit newer API)
                st.rerun()
            else:
                st.error(resp)
        st.markdown("---")
        st.subheader("Register (boss only can create after login)")
        st.info("Jika baru pakai, gunakan akun boss: boss / boss123")
    else:
        st.markdown(f"**Logged in as:** {st.session_state.user['username']} ({st.session_state.user['role']})")
        if st.button("Logout"):
            logout()
            st.rerun()

# Main UI
user = st.session_state.user

if user is None:
    st.header("Selamat datang")
    st.write("Silakan login untuk mengelola stok dan penjualan.")
    st.write("Aplikasi ini adalah demo sederhana: default boss: `boss` / `boss123`.")
    st.write("Setelah login sebagai boss, kamu dapat membuat akun karyawan.")
else:
    role = user["role"]
    st.header("Dashboard")
    menu = None
    # Boss sees product menu, karyawan doesn't
    if role == "boss":
        menu = st.sidebar.selectbox("Menu", ["Home", "Produk & Stok", "Penjualan", "Histori Penjualan", "Manajemen User"])
    else:
        menu = st.sidebar.selectbox("Menu", ["Home", "Penjualan", "Histori Penjualan"])

    if menu == "Home":
        st.subheader("Ringkasan")
        prod_df = list_products_df()
        total_products = len(prod_df)
        total_stock = int(prod_df["stock"].sum()) if total_products>0 else 0
        total_value = float((prod_df["price"] * prod_df["stock"]).sum()) if total_products>0 else 0.0
        sales_df = get_sales_df()
        total_sales = sales_df["total"].sum() if not sales_df.empty else 0.0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Jumlah Produk", total_products)
        col2.metric("Total Unit Stok", total_stock)
        col3.metric("Nilai Stok (estimasi)", f"Rp {total_value:,.2f}")
        col4.metric("Total Penjualan (semua waktu)", f"Rp {total_sales:,.2f}")
        st.markdown("### Produk terbaru")
        st.dataframe(prod_df.sort_values("created_at", ascending=False).reset_index(drop=True))

    elif menu == "Produk & Stok":
        # Protect this page even if someone tampers with URL
        if role != "boss":
            st.error("Akses ditolak. Hanya boss yang boleh mengubah stok.")
            st.stop()

        st.subheader("Kelola Produk")
        prod_df = list_products_df()
        st.markdown("#### Daftar Produk")
        st.dataframe(prod_df)

        st.markdown("---")
        st.markdown("#### Tambah Produk Baru")
        with st.form("add_product_form", clear_on_submit=True):
            sku = st.text_input("SKU (boleh kosong)")
            name = st.text_input("Nama Produk", value="")
            cost = st.number_input("Harga modal per unit (Rp)", min_value=0.0, value=0.0, format="%.2f")
            price = st.number_input("Harga jual per unit (Rp)", min_value=0.0, value=0.0, format="%.2f")
            stock = st.number_input("Stok awal (unit)", min_value=0, value=0, step=1)
            submitted = st.form_submit_button("Tambah Produk")
            if submitted:
                if not name:
                    st.error("Nama produk wajib diisi.")
                else:
                    ok, msg = add_product(sku.strip(), name.strip(), float(cost), float(price), int(stock))
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        st.markdown("---")
        st.markdown("#### Edit Produk")
        prod_list = prod_df[["id", "name"]].set_index("id")["name"].to_dict()
        if prod_list:
            selected_id = st.selectbox("Pilih produk untuk edit", options=list(prod_list.keys()),
                                       format_func=lambda x: f"{x} - {prod_list[x]}")
            if selected_id:
                row = prod_df[prod_df["id"] == selected_id].iloc[0]
                with st.form("edit_product_form"):
                    new_sku = st.text_input("SKU", value=row["sku"] if row["sku"] else "")
                    new_name = st.text_input("Nama", value=row["name"])
                    new_cost = st.number_input("Harga modal per unit (Rp)", min_value=0.0, value=float(row["cost"]), format="%.2f")
                    new_price = st.number_input("Harga jual per unit (Rp)", min_value=0.0, value=float(row["price"]), format="%.2f")
                    new_stock = st.number_input("Stok (unit)", min_value=0, value=int(row["stock"]), step=1)
                    updated = st.form_submit_button("Simpan Perubahan")
                    if updated:
                        ok, msg = update_product(int(selected_id), new_name.strip(), float(new_cost), float(new_price), int(new_stock), new_sku.strip() if new_sku else None)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
        else:
            st.info("Belum ada produk. Tambahkan produk baru di atas.")

    elif menu == "Penjualan":
        st.subheader("Catat Penjualan")
        prod_df = list_products_df()
        if prod_df.empty:
            st.info("Belum ada produk. Tambahkan produk dulu (boss saja).")
        else:
            prod_map = prod_df.set_index("id").to_dict(orient="index")
            options = [(row["id"], f"{row['name']} (stok: {row['stock']}, Rp {row['price']:.2f})") for _, row in prod_df.iterrows()]
            prod_choice = st.selectbox("Pilih produk", options=options, format_func=lambda x: x[1])
            prod_id = prod_choice[0] if isinstance(prod_choice, tuple) else prod_choice
            qty = st.number_input("Jumlah terjual", min_value=1, value=1, step=1)
            if st.button("Catat Penjualan"):
                ok, msg = record_sale(int(prod_id), int(qty), int(user["id"]))
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    elif menu == "Histori Penjualan":
        st.subheader("Histori Penjualan")
        sales_df = get_sales_df()
        if sales_df.empty:
            st.info("Belum ada penjualan.")
        else:
            sales_df["sold_at"] = pd.to_datetime(sales_df["sold_at"])
            st.dataframe(sales_df)

            # === P&L Harian ===
            sales_df["tanggal"] = sales_df["sold_at"].dt.date
            daily_pnl = sales_df.groupby("tanggal").agg(
                total_penjualan=("total", "sum"),
                total_profit=("profit", "sum")
            ).reset_index()

            st.markdown("---")
            st.markdown("### P&L Harian")
            st.dataframe(daily_pnl)

            # filter & export
            st.markdown("---")
            st.markdown("### Export")
            buf = io.StringIO()
            sales_df.to_csv(buf, index=False)
            csv_bytes = buf.getvalue().encode()
            st.download_button("Download CSV histori penjualan", data=csv_bytes, file_name="sales_history.csv", mime="text/csv")
            # basic summary
            total_rev = sales_df["total"].sum()
            total_items = sales_df["qty"].sum()
            st.markdown(f"**Total pendapatan:** Rp {total_rev:,.2f}")
            st.markdown(f"**Total item terjual:** {total_items}")

            st.markdown("#### Ringkasan Hari Ini")
            today = datetime.date.today()
            today_data = daily_pnl[daily_pnl["tanggal"] == today]

            if not today_data.empty:
                st.success(f"Penjualan hari ini: Rp {today_data.iloc[0]['total_penjualan']:,.0f}")
                st.success(f"Profit hari ini: Rp {today_data.iloc[0]['total_profit']:,.0f}")
            else:
                st.info("Belum ada transaksi hari ini.")

    elif menu == "Manajemen User":
        st.subheader("Manajemen User (boss only)")
        if role != "boss":
            st.error("Hanya boss yang dapat mengakses halaman ini.")
        else:
            st.markdown("#### Buat akun karyawan")
            with st.form("create_user_form"):
                new_username = st.text_input("Username baru")
                new_password = st.text_input("Password", type="password")
                role_select = st.selectbox("Role", options=["karyawan"], index=0)
                create_sub = st.form_submit_button("Buat Akun")
                if create_sub:
                    if not new_username or not new_password:
                        st.error("Username dan password wajib diisi.")
                    else:
                        ok, msg = create_user(new_username.strip(), new_password, role_select)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
            st.markdown("---")
            st.markdown("#### Daftar user")
            conn = get_conn()
            users_df = pd.read_sql_query("SELECT id, username, role, created_at FROM users ORDER BY created_at DESC", conn)
            conn.close()
            st.dataframe(users_df)

# Footer / small note
st.sidebar.markdown("---")
st.sidebar.markdown("Aplikasi demo — jangan gunakan password default di lingkungan produksi.")
