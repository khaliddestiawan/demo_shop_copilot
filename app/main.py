import streamlit as st
from dashboard import dashboard_function  # Pastikan untuk mengimpor fungsi atau komponen dari Dashboard.py
from chatbot import chatbot_function  # Pastikan untuk mengimpor fungsi atau komponen dari app.py yang berhubungan dengan chatbot
import pandas as pd

from io import StringIO
from google.cloud import storage

# df = pd.read_csv('Dataset/Customer_Interaction_Data_v3.csv')

# import dataset from GCS
client = storage.Client()
bucket_name = "demo_ikra"
bucket = client.bucket(bucket_name)

blob_cust_interaction = bucket.blob('Dataset/Customer_Interaction_Data_v3.csv')
cust_interaction = blob_cust_interaction.download_as_text()
df = pd.read_csv(StringIO(cust_interaction))

# Fungsi untuk halaman login
def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    st.markdown("""
    <style>
    /* Default styling for username and password input fields */
    [data-testid="stTextInput"] input {
        width: 100% !important;
        box-sizing: border-box !important;
        border: 2px solid #FFFFFF !important;
        border-radius: 5px !important;
        padding: 10px !important;
        outline: none !important; 
    }
    [data-testid="stTextInput"] input:focus {
        outline: none !important;
        box-shadow: none !important;
    }

    </style>
    """, unsafe_allow_html=True)

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
        with open("app/style.css") as css:
            st.html(f"<style>{css.read()}</style>")

        with st.container(key="app_title"):
            st.title("Personalized Shopping Copilot")

        st.logo(
        "material/logo_iykra.png",
        icon_image="material/logo_iykra.png",
        )
        #st.header("💬 Product Recommendation Chatbot")
        #  Membuat logo aplikasi
        # st.sidebar.image("material/logo_iykra.png", width=120)  # Ganti dengan logo
        #st.sidebar.title("Pages")
        # Membuat tombol untuk memilih antara chatbot dan dashboard

        menu = st.sidebar.radio("Pages", ("Chatbot", "Dashboard", "Logout"))
        if menu == "Chatbot":
            st.markdown('<p style="font-size:24px;">Product Recommendation Chatbot</p>', unsafe_allow_html=True)
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
            st.markdown('<p style="font-size:24px;">Dashboard Shopping Copilot</p>', unsafe_allow_html=True)
            dashboard_function()  # Menampilkan fungsi dashboard

        elif menu == "Logout":
            st.session_state['logged_in'] = False
            st.session_state.pop('user_email', None)  # Hapus email dari session state saat logout
            st.success("You have been logged out.")

if __name__ == "__main__":
    main()