ARG IMAGE_WITH_MODELS=telegram-parser-api-python-with-shared-models
FROM $IMAGE_WITH_MODELS

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "run.py"]