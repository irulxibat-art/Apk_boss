```python
import streamlit as st
import pandas as pd
import os
import hashlib

File data
STOK_FILE = 'stok.csv'
PENJUALAN_FILE = 'penjualan.csv'
USER_FILE = 'users.csv'

Inisialisasi file jika belum ada
def init_file(file, columns):
    if not os.path.exists(file):
        pd.DataFrame(columns=columns).to_csv(file, index=False)

init_file(STOK_FILE, ['Nama Barang', 'Stok'])
init_file(PENJUALAN_FILE, ['Nama Barang', 'Jumlah Terjual'])
init_file(USER_FILE, ['username', 'password_hash', 'role'])

Hash password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

Cek login
def check_login(username, password):
    users = pd.read_csv(USER_FILE)
    pw_hash = hash_password(password)
    user_row = users[(users['username'] == username) & (users['password_hash'] == pw_hash)]
    if not user_row.empty:
        return user_row.iloc[0]['role']
    return None

Tambah user (hanya boss)
def add_user(username, password, role):
    users = pd.read_csv(USER_FILE)
    if username in users['username'].values:
        return False
    pw_hash = hash_password(password)
    new_user = pd.DataFrame([[username, pw_hash, role]], columns=['username', 'password_hash', 'role'])
    stok_df = pd.read_csv(STOK_FILE)
    penjualan_df = pd.read_csv(PENJUALAN_FILE)

    role = st.session_state['role']

    if role == 'Boss':
        menu = st.sidebar.selectbox("Menu", ["Input Stok", "Input Penjualan", "Laporan", "Kelola Akun Karyawan"])
    else:
        menu = st.sidebar.selectbox("Menu", ["Input Penjualan", "Laporan"])

    # Input Stok (Boss only)
    if menu == "Input Stok" and role == 'Boss':
        nama = st.text_input("Nama Barang")
        jumlah = st.number_input("Jumlah Stok", min_value=1, step=1)
        if st.button("Tambah / Update Stok"):
            if nama in stok_df['Nama Barang'].values:
                stok_df.loc[stok_df['Nama Barang'] == nama, 'Stok'] += jumlah
            else:
                stok_df = pd.concat([stok_df, pd.DataFrame([[nama, jumlah]], columns=stok_df.columns)], ignore_index=True)
            stok_df.to_csv(STOK_FILE, index=False)
            st.success("Stok diperbarui!")

    # Input Penjualan (Boss & Karyawan)
    if menu == "Input Penjualan":
        if stok_df.empty:
            st.warning("Belum ada data stok.")
        else:
            nama = st.selectbox("Pilih Barang", stok_df['Nama Barang'])
            jumlah = st.number_input("Jumlah Terjual", min_value=1, step=1)
            if st.button("Buat Akun Karyawan"):
            if new_user and new_pass:
                success = add_user(new_user, new_pass, 'Karyawan')
                if success:
                    st.success(f"Akun karyawan '{new_user}' berhasil dibuat!")
                else:
                    st.error("Username sudah ada, coba yang lain.")
            else:
                st.error("Username dan password tidak boleh kosong.")
        
        st.subheader("Daftar Akun Karyawan")
        users_df = pd.read_csv(USER_FILE)
        karyawans = users_df[users_df['role'] == 'Karyawan'][['username']]
        st.table(karyawans)
```
