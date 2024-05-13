
FROM python:3.10.5-slim-buster

WORKDIR /app

COPY requirements.txt .

RUN mkdir media

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5050", "--log-level=debug"]
