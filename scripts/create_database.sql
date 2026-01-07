-- MySQL Database Creation Script for Chatbot Application
-- Run this script as a MySQL root user or a user with CREATE DATABASE privileges

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS chatbot_db 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

-- Use the database
USE chatbot_db;

-- Optional: Create a dedicated user for the application (uncomment if needed)
-- CREATE USER IF NOT EXISTS 'chatbot_user'@'localhost' IDENTIFIED BY 'your_secure_password_here';
-- GRANT ALL PRIVILEGES ON chatbot_db.* TO 'chatbot_user'@'localhost';
-- FLUSH PRIVILEGES;

-- Show database information
SELECT 
    SCHEMA_NAME as 'Database',
    DEFAULT_CHARACTER_SET_NAME as 'Charset',
    DEFAULT_COLLATION_NAME as 'Collation'
FROM information_schema.SCHEMATA 
WHERE SCHEMA_NAME = 'chatbot_db';

