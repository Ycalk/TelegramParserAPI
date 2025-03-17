CREATE DATABASE IF NOT EXISTS telegram_db;
CREATE DATABASE IF NOT EXISTS channels_db;

CREATE USER IF NOT EXISTS 'telegram'@'%' IDENTIFIED BY 'telegram_password';
CREATE USER IF NOT EXISTS 'channels'@'%' IDENTIFIED BY 'channels_password';

GRANT ALL PRIVILEGES ON telegram_db.* TO 'telegram'@'%';
GRANT ALL PRIVILEGES ON channels_db.* TO 'channels'@'%';

FLUSH PRIVILEGES;