# Database System Setup Guide

This guide will help you set up the sanction database system for the Chivalry 2 Admin Dashboard.

## Quick Start (Local SQLite)

For testing or single-user setups, you can use SQLite (no server required):

1. **Install dependencies:**
   ```bash
   cd C2ServerAPI
   poetry install
   # or
   pip install sqlalchemy
   ```

2. **Create configuration file:**
   ```bash
   # Copy the example config
   cp database_config.example.json database_config.json
   ```
   
   The default configuration uses SQLite, so no changes needed for local testing.

3. **Test the system:**
   ```bash
   cd core
   python database_demo.py
   ```

That's it! The database file `sanctions.db` will be created automatically.

## Production Setup (Remote PostgreSQL)

For multi-user environments with a centralized database:

### 1. Install PostgreSQL Dependencies

```bash
cd C2ServerAPI
poetry install --extras postgresql
# or
pip install sqlalchemy psycopg2-binary
```

### 2. Set Up PostgreSQL Server

You'll need access to a PostgreSQL server. Options include:

- **Self-hosted:** Install PostgreSQL on your own server
- **Cloud providers:** AWS RDS, Google Cloud SQL, Azure Database, DigitalOcean
- **Free tier options:** ElephantSQL, Supabase, Neon

### 3. Create Database

Connect to your PostgreSQL server and create a database:

```sql
CREATE DATABASE sanctions;
CREATE USER sanctions_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE sanctions TO sanctions_user;
```

### 4. Configure Connection

Edit `database_config.json`:

```json
{
    "type": "postgresql",
    "host": "your-server.com",
    "port": 5432,
    "database": "sanctions",
    "username": "sanctions_user",
    "password": "your_secure_password",
    "pool_size": 5,
    "max_overflow": 10,
    "pool_timeout": 30
}
```

### 5. Test Connection

```bash
cd core
python -c "from database_config import get_database_config; db = get_database_config(); print('Success!' if db.test_connection() else 'Failed!')"
```

## Production Setup (Remote MySQL)

### 1. Install MySQL Dependencies

```bash
cd C2ServerAPI
poetry install --extras mysql
# or
pip install sqlalchemy pymysql
```

### 2. Set Up MySQL Server

Similar to PostgreSQL, you'll need access to a MySQL/MariaDB server.

### 3. Create Database

```sql
CREATE DATABASE sanctions;
CREATE USER 'sanctions_user'@'%' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON sanctions.* TO 'sanctions_user'@'%';
FLUSH PRIVILEGES;
```

### 4. Configure Connection

Edit `database_config.json`:

```json
{
    "type": "mysql",
    "host": "your-server.com",
    "port": 3306,
    "database": "sanctions",
    "username": "sanctions_user",
    "password": "your_secure_password",
    "pool_size": 5,
    "max_overflow": 10,
    "pool_timeout": 30
}
```

## Security Best Practices

### 1. Protect Your Configuration File

Add to `.gitignore`:
```
database_config.json
sanctions.db
```

### 2. Use Environment Variables (Advanced)

Instead of storing passwords in the config file, you can use environment variables:

```python
import os
config = {
    "type": "postgresql",
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "sanctions"),
    "username": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    # ...
}
```

### 3. Enable SSL/TLS for Remote Connections

For PostgreSQL, add to your config:
```json
{
    "type": "postgresql",
    "host": "your-server.com",
    "sslmode": "require"
}
```

### 4. Regular Backups

Set up automated backups of your database:

**PostgreSQL:**
```bash
pg_dump -U sanctions_user sanctions > backup_$(date +%Y%m%d).sql
```

**MySQL:**
```bash
mysqldump -u sanctions_user -p sanctions > backup_$(date +%Y%m%d).sql
```

## Troubleshooting

### Connection Refused

- Check firewall rules on your database server
- Verify the host and port are correct
- Ensure the database server is running

### Authentication Failed

- Double-check username and password
- Verify user has proper permissions
- For PostgreSQL, check `pg_hba.conf` settings

### Module Not Found

- Make sure you installed the correct database driver:
  - PostgreSQL: `psycopg2-binary`
  - MySQL: `pymysql`

### Tables Not Created

The tables are created automatically on first connection. If they're not appearing:

```python
from core.database_config import get_database_config
from core.database_models import Base

db = get_database_config()
Base.metadata.create_all(db.engine)
```

## Migration from SQLite to PostgreSQL/MySQL

If you start with SQLite and want to migrate to a remote database:

1. Export data from SQLite
2. Set up your remote database
3. Update `database_config.json`
4. Import data to the new database

Tools like `pgloader` can help automate this process.

## Next Steps

- Read `DATABASE_README.md` for detailed API documentation
- Run `database_demo.py` to see examples
- Integrate the database system with your interface code

