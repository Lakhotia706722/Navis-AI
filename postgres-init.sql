-- Initialize Maritime Studio database
-- This script runs automatically when postgres container starts

-- Grant all privileges to the maritime_user on the maritime_studio database
GRANT ALL PRIVILEGES ON DATABASE maritime_studio TO maritime_user;

-- Connect to the database and grant schema privileges
\c maritime_studio;
GRANT ALL ON SCHEMA public TO maritime_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO maritime_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO maritime_user;
