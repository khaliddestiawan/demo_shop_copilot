FROM python:3.10

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip3 install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

EXPOSE 8501

CMD ["streamlit", "run", "app/main.py", "--server.port=8080", "--server.address=0.0.0.0"]