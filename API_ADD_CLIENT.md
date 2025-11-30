# Запрос на добавление клиента в Telegram Parser API

## Эндпоинт
```
POST http://45.84.227.48/api/v1/parser/add_client
```

## Параметры авторизации
- **Заголовок**: `Authorization`
- **Значение**: Ваш API ключ (из переменной окружения `SECRET_KEY`)

## Формат запроса
- **Content-Type**: `multipart/form-data`
- **Параметр**: `archive` (тип файла: ZIP архив)

## Пример с curl

### Вариант 1: Базовый запрос
```bash
curl -X POST "http://45.84.227.48/api/v1/parser/add_client" \
  -H "Authorization: YOUR_API_KEY_HERE" \
  -F "archive=@917573898573.zip"
```

### Вариант 2: С подробным выводом
```bash
curl -X POST "http://45.84.227.48/api/v1/parser/add_client" \
  -H "Authorization: YOUR_API_KEY_HERE" \
  -F "archive=@917573898573.zip" \
  -v
```

### Вариант 3: С сохранением ответа
```bash
curl -X POST "http://45.84.227.48/api/v1/parser/add_client" \
  -H "Authorization: YOUR_API_KEY_HERE" \
  -F "archive=@917573898573.zip" \
  -o response.json \
  -w "\nHTTP Status: %{http_code}\n"
```

## Пример с Python (requests)

```python
import requests

url = "http://45.84.227.48/api/v1/parser/add_client"
api_key = "YOUR_API_KEY_HERE"
archive_file = "917573898573.zip"

headers = {
    "Authorization": api_key
}

with open(archive_file, "rb") as f:
    files = {
        "archive": (archive_file, f, "application/zip")
    }
    response = requests.post(url, headers=headers, files=files)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")
```

## Пример с JavaScript (fetch)

```javascript
const formData = new FormData();
const fileInput = document.querySelector('input[type="file"]');
formData.append('archive', fileInput.files[0]);

fetch('http://45.84.227.48/api/v1/parser/add_client', {
  method: 'POST',
  headers: {
    'Authorization': 'YOUR_API_KEY_HERE'
  },
  body: formData
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('Error:', error));
```

## Формат ZIP архива

Архив должен содержать:
- Файл с расширением `.session` (SQLite сессия Telegram)
- Файл с расширением `.json` (опционально, содержит параметры подключения)

## Возможные ответы

### Успешное добавление (200)
```json
{
  "message": "Client added successfully"
}
```

### Ошибка авторизации (403)
```json
{
  "detail": "Invalid API Key"
}
```

### Ошибка валидации (400)
```json
{
  "error": "SessionPasswordNeeded",
  "message": "..."
}
```

### Внутренняя ошибка (500)
```json
{
  "message": "Error description"
}
```

## Проверка через Swagger UI

Также можно использовать документацию API по адресу:
```
http://45.84.227.48/docs
```

Там будет доступна интерактивная форма для отправки запроса.


