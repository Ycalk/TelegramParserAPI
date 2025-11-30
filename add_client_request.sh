#!/bin/bash

# Запрос на добавление клиента в Telegram Parser API
# Использование: ./add_client_request.sh <YOUR_API_KEY>

API_URL="http://45.84.227.48/api/v1/parser/add_client"
API_KEY="${1:-YOUR_API_KEY_HERE}"
ARCHIVE_FILE="917573898573.zip"

if [ "$API_KEY" == "YOUR_API_KEY_HERE" ]; then
    echo "Ошибка: Укажите API ключ как аргумент или измените значение по умолчанию"
    echo "Использование: ./add_client_request.sh YOUR_API_KEY"
    exit 1
fi

echo "Отправка запроса на добавление клиента..."
echo "URL: $API_URL"
echo "Файл: $ARCHIVE_FILE"
echo ""

curl -X POST "$API_URL" \
  -H "Authorization: $API_KEY" \
  -F "archive=@$ARCHIVE_FILE" \
  -v

echo ""
echo "Запрос завершен."


