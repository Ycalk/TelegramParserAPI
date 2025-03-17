#!/bin/bash

wait_for_db() {
    while true; do
        python -c "
import pymysql
import os
from urllib.parse import urlparse

url_data = urlparse(os.getenv('MYSQL_URL'))

try:
    pymysql.connect(
        host=url_data.hostname,
        user=url_data.username,
        password=url_data.password,
        db=url_data.path[1:]
    )
    print('Database is ready.')
    exit(0)
except Exception as e:
    print('Waiting for database to be ready...')
    exit(1)
" 2>/dev/null
        if [ $? -eq 0 ]; then
            break
        fi

        sleep 3
    done
}

wait_for_db

echo "Starting service..."
exec "$@"