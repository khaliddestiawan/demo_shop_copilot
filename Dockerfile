FROM python:3.10

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip3 install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy directories explicitly
COPY ./app /code/app
COPY ./faiss_index /code/faiss_index
COPY ./material /code/material
COPY ./.streamlit /code/.streamlit

EXPOSE 8080

CMD ["streamlit", "run", "app/main.py", "--server.port=8080", "--server.address=0.0.0.0"]