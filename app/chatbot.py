import streamlit as st
from PIL import Image
import urllib.request 
import os
import pandas as pd
from langchain_openai import OpenAIEmbeddings
import openai
from langchain.vectorstores import FAISS
import os
import re
import replicate
import cv2
from dotenv import load_dotenv
import glob

from io import StringIO, BytesIO
from google.cloud import storage
import replicate
import requests


# open your openai api key in file .env
# Memuat file .env
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# Please fill your openai api key
# openai_api_key = ""
# os.environ["OPENAI_API_KEY"] = openai_api_key

# import dataset from GCS
client = storage.Client()
bucket_name = "demo_ikra"
bucket = client.bucket(bucket_name)

blob_cust_interaction = bucket.blob('Dataset/Customer_Interaction_Data_v3.csv')
blob_product_catalog = bucket.blob('Dataset/final_product_catalog_v2.csv')
cust_interaction = blob_cust_interaction.download_as_text()
prod_catalog = blob_product_catalog.download_as_text()
df = pd.read_csv(StringIO(cust_interaction))
df_products = pd.read_csv(StringIO(prod_catalog))

# df = pd.read_csv('Dataset/Customer_Interaction_Data_v3.csv')
# df_products = pd.read_csv('Dataset/final_product_catalog_v2.csv')

# 1. Create Vector Database
def load_vector_db():
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=openai.api_key)
    #vector_db = FAISS.from_documents(documents, embeddings)
    # index_path = os.path.join(os.path.dirname(__file__), "faiss_index")
    vector_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
    return vector_db

def retrieve_transcation(cust_id):
    return df[df['Customer_ID'] == cust_id].head(3).to_dict()

# 2. Retrieval Agent
def retrieve_documents(query, vector_db, top_k=5):
    # result = vector_db.similarity_search_with_score(query, top_k)
    # filtered_result = []
    # for doc, score in result:
    #     print(score)
    #     if score > 0.4:
    #         filtered_result.append(doc)
    return vector_db.similarity_search(query, top_k)

def generate_streaming_response_openai(query, docs, purchase_hist):
    # Combine retrieved documents into context
    context = "\n\n".join([doc.page_content for doc in docs])
    prompt = (
    "You are an expert product recommendation assistant, designed to provide precise and thoughtful suggestions of fashion. "
    "If the user's input is unclear and meaningless, politely inform the user that you can only assist with recommending products, and do not generate suggestions. "
    "If the product in question is not in the catalog, answer that our product only contain Dress, Jacket, Skirt, Coat, Suit, and Shirt. "
    "If a query requests gender-specific products, respond with: 'Our catalog has no gender-specific products.' "
    "Your primary goal is to recommend up to three products based on the provided context, purchase history, and customer query. "
    "Here’s how you should answer: \n\n"
    "- If the query does not indicate an interest in fashion products, respond with: 'I can only assist with product recommendations. Please provide more details.'\n"
    "- Always analyze and incorporate similarities from the provided purchase history and context.\n"
    "- Provide a clear and concise explanation for why each product is recommended.\n"
    "- Include the product ID for every recommended product.\n"
    "- Maintain friendly tone.\n\n"
    f"Context: {context}\n\n"
    f"Purchase History: {purchase_hist}\n\n"
    f"Question: {query}\n\n"
    "Your response should balance accuracy and detail while remaining concise."
)

    # Call OpenAI API with streaming
    response = openai.chat.completions.create(
        model="gpt-4o",  # Adjust the model name as per availability
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Answer accurately and give reason, but always keep the friendly tone."},
            {"role": "user", "content": prompt}
        ],
        stream=True,  # Enable streaming
        temperature=0.3
    )
     
    # Placeholder for the response
    output_placeholder = st.empty()
    collected_messages = []

    # Stream the response chunks
    for chunk in response:
        chunk_message = chunk.choices[0].delta.content
        if chunk_message:
            collected_messages.append(chunk_message)
            # Update the placeholder with the current response
            output_placeholder.markdown("".join(collected_messages))
    output_placeholder.empty() 
    # Return the full response
    return "".join(collected_messages)

# 4. Multi-Agent System
def multi_agent_rag(query, vector_db, purchase_hist):
    retrieved_docs = retrieve_documents(query, vector_db)
    #return generate_response_openai(query, retrieved_docs, purchase_hist)
    return generate_streaming_response_openai(query, retrieved_docs, purchase_hist)

# log debug for button click
    
def handle_click(action, product_id, url):
    st.session_state.clicked_button = f"{action} for {product_id}"
    st.session_state.product_id = product_id
    st.session_state.product_url = url
    st.session_state.waiting_for_image = True

# virtual try on function
def virtual_tryon(garment_img_path, person_img_path, prod_id):
    garment_image = download_image_from_gcs(garment_img_path)
    person_image = download_image_from_gcs(person_img_path)
    garment_file = BytesIO()
    person_file = BytesIO()
    if garment_image.mode == "RGBA":
        garment_image = garment_image.convert("RGB")
    if person_image.mode == "RGBA":
        person_image = person_image.convert("RGB")
    garment_image.save(garment_file, format="JPEG")
    person_image.save(person_file, format="JPEG")
    garment_file.seek(0)
    person_file.seek(0)
    type = df_products[df_products['Product_ID'] == prod_id]["Type"].to_string(index=False)
    short_desc = df_products[df_products['Product_ID'] == prod_id]["Category"].to_string(index=False)

    input = {
        "seed": 42,
        "steps": 30,
        "category": type,
        "garm_img": garment_file,
        "human_img": person_file,
        "garment_des": short_desc,
    }

    output = replicate.run(
        "cuuupid/idm-vton:c871bb9b046607b680449ecbae55fd8c6d945e0a1948644bf2361b3d021d3ff4",
        input=input
    )
    response = requests.get(str(output))
    img = Image.open(BytesIO(response.content))
    return img

def upload_image_to_gcs(image_bytes, image_name):
    blob = bucket.blob(image_name)
    blob.upload_from_string(image_bytes, content_type='image/jpeg')
    #return f"gs://{bucket.name}/{image_name}"

def download_image_from_gcs(img_path):
    blob = client.bucket(bucket_name).blob(img_path)

    try:
        image_bytes = blob.download_as_bytes()
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        return image
    except Exception as e:
        raise Exception(f"Error downloading image: {e}")
    
    # image_bytes = blob.download_as_bytes()
    # image = Image.open(BytesIO(image_bytes)).convert("RGB")
    # return image

def render_product(product_id):
    filtered_df = df_products[df_products['Product_ID'] == product_id]
    if not filtered_df.empty:
        # Mendapatkan URL gambar atau file path
        url = filtered_df['Url_Image'].iloc[0]
        img = download_image_from_gcs(url)
        img.thumbnail((300, 600))  # Maksimum lebar dan tinggi

        # Tentukan folder tempat gambar disimpan
        # image_folder = "images"
        
        # # Cari file gambar berdasarkan product_id tanpa memperhatikan ekstensi
        # pattern = os.path.join(image_folder, f"{product_id}.*")  # Pola: images/101.*
        # matching_files = glob.glob(pattern)  # Mencari file dengan ekstensi apapun

        # if matching_files:
        #     image_path = matching_files[0]  # Ambil file pertama yang ditemukan
        #     img = Image.open(image_path)
        #     img.thumbnail((300, 600))  # Atur ukuran maksimum

        # Menggunakan tiga kolom untuk memusatkan elemen
        col1, col2, col3 = st.columns([1, 2, 1])  # Rasio kolom: kiri, tengah, kanan
        with col2:  # Konten di kolom tengah
            st.subheader(f"{product_id}")
            st.image(img)
            st.button(
                f"Virtual Try-On for {product_id}",
                key=f"try_{product_id}",
                on_click=handle_click,
                args=("Try ", product_id, url),
                )
            
    else:
        # Jika gambar tidak ditemukan
        st.error(f"Image for Product {product_id} not found.")

def render_product_horizontal():
    if st.session_state.product_ids:
        # image_folder = "images"
        cols = st.columns(len(st.session_state.product_ids))  # Buat kolom berdasarkan jumlah produk
        
        for idx, product_id in enumerate(st.session_state.product_ids):
            filtered_df = df_products[df_products['Product_ID'] == product_id]
            if not filtered_df.empty:
                # pattern = os.path.join(image_folder, f"{product_id}.*")
                # matching_files = glob.glob(pattern)
                
                url = filtered_df['Url_Image'].iloc[0]
                img = download_image_from_gcs(url)
                img = img.resize((300, 400))

                # if matching_files:
                #     image_path = matching_files[0]
                #     img = Image.open(image_path)
                #     img = img.resize((300, 400))  # Pastikan semua gambar memiliki rasio 3:4
                    
                with cols[idx]:  # Menempatkan konten dalam kolom
                    st.markdown(f"<h3 style='text-align: center;'>{product_id}</h3>", unsafe_allow_html=True)
                    st.image(img)
                    # Gunakan markdown untuk layout tombol ke tengah
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:  # Pusatkan tombol
                        st.button(
                            "Try-On",
                            key=f"try_{product_id}_{idx}",  # Tambahkan indeks untuk keunikan
                            on_click=handle_click,
                            args=("Try ", product_id, url),
                            )
            else:
                with cols[idx]:
                    st.error(f"Image for Product {product_id} not found.")

# Function to display styled chat messages
def chat_message(role, content):
    if role == "user":
        # User message aligned right
        st.markdown(
            f"""
            <div style='text-align: right; background-color: #3a3d43; padding: 10px; border-radius: 10px; margin: 5px 0; width: fit-content; max-width: 70%; float: right;'>
                {content}
            </div>
            <div style='clear: both;'></div>
            """,
            unsafe_allow_html=True
        )
    else:
        # Assistant message aligned left
        st.chat_message(role, avatar="material/bot_icon2.png").markdown(content)
        
        
def chat_message_two_icon(role, content):
    if role == "user":
        st.markdown(
            f"""
            <div style='display: flex; justify-content: flex-end; align-items: center; margin: 5px 0;'>
                <div style='background-color: #1F45FC; padding: 10px; border-radius: 10px; max-width: 80%; text-align: right;'>
                    {content}
                </div>
                <img src="https://cdn-icons-png.flaticon.com/512/9131/9131529.png" width="30" height="30" style="border-radius: 50%; margin-left: 10px;">
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div style='display: flex; align-items: top; margin: 5px 0;'>
                <img src="https://cdn-icons-png.flaticon.com/512/4712/4712035.png" width="30" height="30" style="border-radius: 50%; margin-right: 10px;">
                <div style='background-color: #808080; padding: 10px; border-radius: 10px; max-width: 80%; text-align: left;'>
                    {content}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
  

# Fungsi utama chatbot
def chatbot_function(email):
    # Streamlit Interface
    # st.header("💬 Product Recommendation Chatbot")

    # Inisialisasi sesi untuk menyimpan percakapan dan ID pelanggan
    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "assistant", "content": "Welcome! I'm here to help you choose products based on your preferences. How can I assist you today?"}]
        
    if "customer_id" not in st.session_state:
        customer_id = df[df['Email'] == email]['Customer_ID']
        print(customer_id.iloc[0])
        if not customer_id.empty:
            st.session_state["customer_id"] = customer_id.iloc[0]
        else:
            st.error("Customer ID not found for the provided email.")
            return  # Keluar dari fungsi jika tidak ada Customer ID
        
    if "clicked_button" not in st.session_state:
        st.session_state.clicked_button = None
    if "product_ids" not in st.session_state:
        st.session_state.product_ids = []
    if "uploaded_image" not in st.session_state:
        st.session_state.uploaded_image = None
    if "product_url" not in st.session_state:
        st.session_state.product_url = None
    if "uploaded_image_name" not in st.session_state:
        st.session_state.uploaded_image_name = None
    if "waiting_for_image" not in st.session_state:
        st.session_state.waiting_for_image = False

    # Menampilkan percakapan sebelumnya
    for msg in st.session_state.messages:
        chat_message(msg["role"], msg["content"])

    # Input pengguna
    prompt = st.chat_input(placeholder="Type here for recommend product...")
    st.markdown("""
    <style>
    /* text area chat input */
    [data-testid="stChatInput"] textarea {
        border: 1px solid #ffffff !important;
        border-radius: 8px !important; 
    }

    /* Chat input submit button */
    [data-testid="stChatInputSubmitButton"] {
        border-radius: 50% !important;
        padding: 0 !important; 
        background-color: #334092 !important;
        border: none !important;
        width: 30px !important;
        height: 30px !important;
        position: absolute !important;
        right: 10px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        display: flex !important;
        align-items: center !important;  
        justify-content: center !important;
    }

    </style>
    """, unsafe_allow_html=True)
    if prompt:
        # Simpan dan tampilkan input pengguna
        st.session_state.messages.append({"role": "user", "content": prompt})
        chat_message("user", prompt)
        
        try:
            inputs = {"query": prompt, "customer": st.session_state["customer_id"]}
            vector_db = load_vector_db()
            transaction_data = retrieve_transcation(st.session_state["customer_id"])
            response = multi_agent_rag(inputs['query'], vector_db, transaction_data)
        except Exception as e:
            response = f"An error occurred: {e}"

        # Simpan dan tampilkan respons dari asisten
        st.session_state.messages.append({"role": "assistant", "content": response})
        chat_message("assistant", response)

        # Extract raw output
        output = response
        # Regular expression pattern to extract Product ID
        pattern = r"(?i)\b(PROD\d+)\b"
        product_ids = re.findall(pattern, output)
        unique_product_ids = list(set(product_ids))
        st.session_state.product_ids = unique_product_ids

    render_product_horizontal()
    # if st.session_state.product_ids:
    #     for product_id in st.session_state.product_ids:
    #         # Validasi product_ids di df_product
    #         with st.container():
    #             render_product(product_id)

        # Jika sedang menunggu gambar
    if st.session_state.waiting_for_image:
        # Unggah gambar
        uploaded_image = st.file_uploader("Please upload person image:", type=["jpg", "png", "jpeg"])
        if uploaded_image:
            st.session_state.uploaded_image = uploaded_image  # Simpan gambar yang diunggah di session state
            st.session_state.uploaded_image_name = uploaded_image.name  # Simpan nama gambar
            image = Image.open(uploaded_image)
            image.thumbnail((300, 600))
            st.image(image, caption="Your image")
            # with open(uploaded_image.name, "wb") as f:
            #     f.write(uploaded_image.getbuffer())

            image_bytes = uploaded_image.getvalue()
            upload_image_to_gcs(image_bytes, uploaded_image.name)
            st.success(f"Image uploaded and saved successfully!")

            with st.spinner('Virtual try on is running...'):
                print(st.session_state.product_url)
                result_vto = virtual_tryon(st.session_state.product_url, uploaded_image.name, st.session_state.product_id)
            st.success("Done!")

            # urllib.request.urlretrieve( 
            # result_vto, 
            # "result_vto.png")

            # Save the Image object directly
            result_vto.save("result_vto.png")

            # tampilkan hasilnya
            result = Image.open("result_vto.png") 
            result.thumbnail((300, 600))
            st.image(result, caption=f"Try on for {st.session_state.product_id}")

            # Stop asking for the image
            st.session_state.waiting_for_image = False
