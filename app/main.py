import streamlit as st
from dashboard import dashboard_function  # Pastikan untuk mengimpor fungsi atau komponen dari Dashboard.py
from chatbot import chatbot_function  # Pastikan untuk mengimpor fungsi atau komponen dari app.py yang berhubungan dengan chatbot
import pandas as pd

df = pd.read_csv('Dataset/Customer_Interaction_Data_v3.csv')

# Fungsi untuk halaman login
def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # Ganti dengan logika autentikasi yang sesuai
        if username in df['Email'].values:  # Contoh kredensial
            st.session_state['logged_in'] = True
            st.session_state['user_email'] = username  # Simpan email pengguna yang berhasil login
            st.success("Login successful!")
        else:
            st.error("Invalid username or password")

def main():
    # Cek apakah pengguna sudah login
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        login()  # Tampilkan halaman login
    else:
        st.title("Personalized Shopping Copilot")

        # Membuat tombol untuk memilih antara chatbot dan dashboard
        menu = st.sidebar.radio("Select Page", ("Chatbot", "Dashboard", "Logout"))

        if menu == "Chatbot":
            information = (
                "**How to Use:**\n"
                "- Describe the clothing you're looking for from the available options: **Dress, Jacket, Skirt, Coat, Suit, Shirt.**.\n"
                "- To try on a product virtually, click the **Virtual Try-On** button and upload your image.\n\n"
                "**Example Queries:**\n"
                "- *Show me blue suits for a conference.*\n"
                "- *I need a shirt for a winter hangout.*\n"
                "- *M-size red skirt, please.*"
            )
            st.sidebar.info(information, icon="ℹ️")
            email = st.session_state['user_email']  # Ambil email dari session state
            chatbot_function(email)  # Menampilkan fungsi chatbot dengan email sebagai parameter

        elif menu == "Dashboard":
            dashboard_function()  # Menampilkan fungsi dashboard

        elif menu == "Logout":
            st.session_state['logged_in'] = False
            st.session_state.pop('user_email', None)  # Hapus email dari session state saat logout
            st.success("You have been logged out.")

if __name__ == "__main__":
    main()