import streamlit as st
from PIL import Image
import os
import pandas as pd
from langchain_openai import OpenAIEmbeddings
import openai
from langchain.vectorstores import FAISS
import os
import re
from gradio_client import Client as GradioClient, file, handle_file
import cv2
from dotenv import load_dotenv
import glob


# open your openai api key in file .env
# Memuat file .env
#load_dotenv()
#openai_api_key = os.getenv("OPENAI_API_KEY")

# Please fill your openai api key
openai_api_key = ""
os.environ["OPENAI_API_KEY"] = openai_api_key

df = pd.read_csv('Dataset/Customer_Interaction_Data_v3.csv')
df_products = pd.read_csv('Dataset/final_product_catalog.csv')

# 1. Create Vector Database
def load_vector_db():
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=openai.api_key)
    #vector_db = FAISS.from_documents(documents, embeddings)
    vector_db = FAISS.load_local('faiss_index', embeddings, allow_dangerous_deserialization=True)
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
        "Your primary goal is to recommend up to three products based on the provided context, purchase history, and customer query. "
        "If a question is unrelated to product recommendations, politely inform the user that you can only assist with product-related topics. "
        "If a query requests gender-specific products, respond with: 'Our catalog has no gender-specific products.' "
        "Here’s how you should answer: \n\n"
        "- Always analyze and incorporate similarities from the provided purchase history and context. \n"
        "- Provide a clear and concise explanation for why each product is recommended. \n"
        "- Include the product ID for every recommended product. \n"
        "- Maintain a polite and friendly tone.\n\n"
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
def virtual_tryon(garment_img_path, person_img_path):
    gradio_client = GradioClient("Nymbo/Virtual-Try-On")
    result = gradio_client.predict(
                dict={"background": file(person_img_path), "layers": [], "composite": None},
                garm_img=handle_file(garment_img_path),
                garment_des="",
                is_checked=True,
                is_checked_crop=False,
                denoise_steps=30,
                seed=42,
                api_name="/tryon"
            )
    try_on_image_path = result[0]
    img = cv2.imread(try_on_image_path)
    cv2.imwrite("result.png", img)

    return Image.open("result.png")

def render_product(product_id):
    filtered_df = df_products[df_products['Product_ID'] == product_id]
    if not filtered_df.empty:
        # Tentukan folder tempat gambar disimpan
        image_folder = "images"
        
        # Cari file gambar berdasarkan product_id tanpa memperhatikan ekstensi
        pattern = os.path.join(image_folder, f"{product_id}.*")  # Pola: images/101.*
        matching_files = glob.glob(pattern)  # Mencari file dengan ekstensi apapun

        if matching_files:
            image_path = matching_files[0]  # Ambil file pertama yang ditemukan
            img = Image.open(image_path)
            img.thumbnail((300, 600))  # Atur ukuran maksimum

            # Menggunakan tiga kolom untuk memusatkan elemen
            col1, col2, col3 = st.columns([1, 2, 1])  # Rasio kolom: kiri, tengah, kanan
            with col2:  # Konten di kolom tengah
                st.subheader(f"{product_id}")
                st.image(img)
                st.button(
                    f"Virtual Try-On for {product_id}",
                    key=f"try_{product_id}",
                    on_click=handle_click,
                    args=("Try ", product_id, image_path),
                )
        else:
            # Jika gambar tidak ditemukan
            st.error(f"Gambar untuk produk {product_id} tidak ditemukan.")

# Fungsi utama chatbot
def chatbot_function(email):
    # Streamlit Interface
    st.header("💬 Product Recommendation Chatbot")

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
        st.chat_message(msg["role"]).markdown(msg["content"])
    # Input pengguna
    if prompt := st.chat_input(placeholder="Type here for recommend product..."):
        # Simpan dan tampilkan input pengguna
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        try:
            inputs = {"query": prompt, "customer": st.session_state["customer_id"]}
            vector_db = load_vector_db()
            transaction_data = retrieve_transcation(st.session_state["customer_id"])
            response = multi_agent_rag(inputs['query'], vector_db, transaction_data)
        except Exception as e:
            response = f"An error occurred: {e}"

        # Simpan dan tampilkan respons dari asisten
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.chat_message("assistant").markdown(response)

        # Extract raw output
        output = response
        # Regular expression pattern to extract Product ID
        pattern = r"(?i)\b(PROD\d+)\b"
        product_ids = re.findall(pattern, output)
        unique_product_ids = list(set(product_ids))
        st.session_state.product_ids = unique_product_ids

    if st.session_state.product_ids:
        for product_id in st.session_state.product_ids:
            # Validasi product_ids di df_product
            with st.container():
                render_product(product_id)

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
            with open(uploaded_image.name, "wb") as f:
                f.write(uploaded_image.getbuffer())
            st.success(f"Image uploaded and saved successfully!")

            with st.spinner('Virtual try on is running...'):
                print(st.session_state.product_url)
                result_vto = virtual_tryon(st.session_state.product_url, uploaded_image.name)
            st.success("Done!")

            # tampilkan hasilnya
            result_vto.thumbnail((300, 600))
            st.image(result_vto, caption=f"Try on for {st.session_state.product_id}")

            # Stop asking for the image
            st.session_state.waiting_for_image = False
