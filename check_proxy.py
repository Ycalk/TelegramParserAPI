#!/usr/bin/env python3
"""
Скрипт для проверки настроек прокси в проекте.
Проверяет переменные окружения и показывает, используется ли прокси.
"""
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()


def check_proxy():
    """Проверяет настройки прокси из переменных окружения"""
    print("=" * 60)
    print("Проверка настроек прокси")
    print("=" * 60)
    
    # Вариант 1: Полная строка прокси
    proxy_url = os.getenv("PROXY")
    if proxy_url:
        print(f"\n✓ Найдена переменная PROXY: {proxy_url}")
        try:
            parsed = urlparse(proxy_url)
            if parsed.hostname and parsed.port:
                print(f"  - Хост: {parsed.hostname}")
                print(f"  - Порт: {parsed.port}")
                print(f"  - Пользователь: {parsed.username or 'не указан'}")
                print(f"  - Пароль: {'***' if parsed.password else 'не указан'}")
                print("\n✓ Прокси будет использоваться!")
                return True
            else:
                print("  ⚠ Ошибка: не указан хост или порт")
        except Exception as e:
            print(f"  ⚠ Ошибка при парсинге: {e}")
    else:
        print("\n✗ Переменная PROXY не найдена")
    
    # Вариант 2: Отдельные переменные
    proxy_host = os.getenv("PROXY_HOST")
    proxy_port = os.getenv("PROXY_PORT")
    
    if proxy_host or proxy_port:
        print(f"\n✓ Найдены переменные PROXY_HOST/PROXY_PORT:")
        print(f"  - PROXY_HOST: {proxy_host or 'не указан'}")
        print(f"  - PROXY_PORT: {proxy_port or 'не указан'}")
        print(f"  - PROXY_USERNAME: {os.getenv('PROXY_USERNAME', 'не указан')}")
        print(f"  - PROXY_PASSWORD: {'***' if os.getenv('PROXY_PASSWORD') else 'не указан'}")
        
        if proxy_host and proxy_port:
            try:
                port = int(proxy_port)
                print(f"\n✓ Прокси будет использоваться: {proxy_host}:{port}")
                return True
            except ValueError:
                print(f"\n  ⚠ Ошибка: PROXY_PORT должен быть числом")
        else:
            print("\n  ⚠ Ошибка: необходимо указать и PROXY_HOST, и PROXY_PORT")
    else:
        print("\n✗ Переменные PROXY_HOST/PROXY_PORT не найдены")
    
    print("\n" + "=" * 60)
    print("✗ Прокси НЕ настроен и НЕ будет использоваться")
    print("=" * 60)
    return False


if __name__ == "__main__":
    check_proxy()

