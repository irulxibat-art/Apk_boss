import streamlit as st
import pandas as pd
import os
import hashlib

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
    new_user = pd.DataFrame([[username, pw_hash, role]], columns=['username', 'password_has h', 'role'])
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
users = pd.concat([users, new_user], ignore_index=True)
    users.to_csv(USER_FILE, index=False)
    return True

Setup awal boss jika belum ada
users_df = pd.read_csv(USER_FILE)
if 'adhi' not in users_df['username'].values:
    add_user('adhi', 'adhi123', 'Boss')

-- STREAMLIT APP --
st.title("Aplikasi Stok & Penjualan dengan Login")

if 'login' not in st.session_state:
    st.session_state['login'] = False
    st.session_state['role'] = None
    st.session_state['username'] = None

if not st.session_state['login']:
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        role = check_login(username, password)
        if role:
            st.session_state['login'] = True
            st.session_state['role'] = role
            st.session_state['username'] = username
            st.success(f"Login berhasil sebagai {role}")
        else:
            st.error("Username atau password salah")

else:
    st.sidebar.write(f"Logged in sebagai: *{st.session_state['username']} ({st.session_state['role']})*")
    if st.sidebar.button("Logout"):
        st.session_state['login'] = False
        st.session_state['role'] = None
        st.session_state['username'] = None
        st.experimental_rerun()
        if st.button("Catat Penjualan"):
                stok_saat_ini = stok_df.loc[stok_df['Nama Barang'] == nama, 'Stok'].values[0]
                if stok_saat_ini >= jumlah:
                    stok_df.loc[stok_df['Nama Barang'] == nama, 'Stok'] -= jumlah
                    stok_df.to_csv(STOK_FILE, index=False)
                    penjualan_df = pd.concat(
                        [penjualan_df, pd.DataFrame([[nama, jumlah]], columns=penjualan_df.columns)],
                        ignore_index=True
                    )
                    penjualan_df.to_csv(PENJUALAN_FILE, index=False)
                    st.success("Penjualan dicatat!")
                else:
                    st.error("Stok tidak cukup!")

    # Laporan (Boss & Karyawan)
    if menu == "Laporan":
        st.subheader("Sisa Stok")
        st.dataframe(stok_df)

        st.subheader("Total Penjualan")
        total = penjualan_df.groupby('Nama Barang').sum().reset_index()
        st.dataframe(total)

    # Kelola Akun Karyawan (Boss only)
    if menu == "Kelola Akun Karyawan" and role == 'Boss':
        st.subheader("Tambah Akun Karyawan Baru")
        new_user = st.text_input("Username Karyawan Baru")
        new_pass = st.text_input("Password Karyawan Baru", type="password")
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
