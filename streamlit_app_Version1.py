
import streamlit as st
import pandas as pd
import os

Inisialisasi file CSV
STOK_FILE = 'stok.csv'
PENJUALAN_FILE = 'penjualan.csv'

Buat file jika belum ada
def init_file(file, columns):
    if not os.path.exists(file):
        pd.DataFrame(columns=columns).to_csv(file, index=False)

init_file(STOK_FILE, ['Nama Barang', 'Stok'])
init_file(PENJUALAN_FILE, ['Nama Barang', 'Jumlah Terjual'])

Data login sederhana
USERS = {
    'bos': {'password': '1234', 'role': 'Bos'},
    'karyawan': {'password': '1111', 'role': 'Karyawan'}
}

Login section
st.title("Login Aplikasi Stok & Penjualan")
username = st.text_input("Username")
password = st.text_input("Password", type="password")
login_btn = st.button("Login")

if login_btn:
    if username in USERS and USERS[username]['password'] == password:
        role = USERS[username]['role']
        st.success(f"Login berhasil sebagai {role}")
        st.session_state['role'] = role
        st.session_state['login'] = True
    else:
        st.error("Username atau password salah")

Setelah login
if st.session_state.get('login'):
role = st.session_state['role']
    stok_df = pd.read_csv(STOK_FILE)
    penjualan_df = pd.read_csv(PENJUALAN_FILE)

    st.sidebar.title(f"Menu - {role}")
    
    if role == "Bos":
        menu = st.sidebar.selectbox("Pilih Menu", ["Input Stok", "Input Penjualan", "Laporan"])
    else:
        menu = st.sidebar.selectbox("Pilih Menu", ["Input Penjualan", "Laporan"])

    if menu == "Input Stok" and role == "Bos":
        nama = st.text_input("Nama Barang")
        jumlah = st.number_input("Jumlah Stok", min_value=1, step=1)
        if st.button("Tambah / Update"):
            if nama in stok_df['Nama Barang'].values:
                stok_df.loc[stok_df['Nama Barang'] == nama, 'Stok'] += jumlah
            else:
                stok_df = pd.concat([stok_df, pd.DataFrame([[nama, jumlah]], columns=stok_df.columns)], ignore_index=True)
            stok_df.to_csv(STOK_FILE, index=False)
            st.success("Stok diperbarui!")

    if menu == "Input Penjualan":
        if stok_df.empty:
            st.warning("Belum ada data stok.")
        else:
            nama = st.selectbox("Pilih Barang", stok_df['Nama Barang'])
            jumlah = st.number_input("Jumlah Terjual", min_value=1, step=1)
            if st.button("Catat Penjualan"):stok_saat_ini = stok_df.loc[stok_df['Nama Barang'] == nama, 'Stok'].values[0]
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

    if menu == "Laporan":
        st.subheader("Sisa Stok")
        st.dataframe(stok_df)

        st.subheader("Total Penjualan")
        total = penjualan_df.groupby('Nama Barang').sum().reset_index()
        st.dataframe(total)
```