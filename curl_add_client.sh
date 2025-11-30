#!/bin/bash

# Правильный curl запрос для добавления клиента
# API работает на порту 8080, а не 80!

curl -X POST "http://45.84.227.48:8080/api/v1/parser/add_client" \
  -H "Authorization: 9e8112abfd20467f9812b5903d4aa4f8" \
  -F "archive=@917573898573.zip" \
  -v


