ARG IMAGE_WITH_MODELS=telegram-parser-api-python-with-shared-models
FROM $IMAGE_WITH_MODELS

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "run.py"]