# Sanction Database System

This document describes the database system for tracking sanctions (bans and kicks) in the Chivalry 2 Admin Dashboard.

## Overview

The database system provides a centralized way to store and retrieve sanction history across multiple users and servers. It supports both local SQLite databases (for testing/development) and remote databases like PostgreSQL or MySQL (recommended for production).

## Architecture

The system consists of three main components:

1. **`database_models.py`** - Defines the database schema (tables and columns)
2. **`database_config.py`** - Handles database connection and configuration
3. **`database_manager.py`** - Provides high-level functions for CRUD operations

## Database Schema

### Sanctions Table

The `sanctions` table stores all sanction records with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key (auto-increment) |
| `sanction_type` | String | Type of sanction ('ban' or 'kick') |
| `playfab_id` | String | Player's PlayFab ID |
| `username` | String | Player's username at time of sanction |
| `reason` | Text | Reason for the sanction |
| `duration_hours` | Float | Duration in hours (NULL for kicks) |
| `moderator_id` | String | Discord ID of moderator who applied sanction |
| `moderator_name` | String | Name of the moderator |
| `applied_at` | DateTime | When the sanction was applied |
| `expires_at` | DateTime | When the sanction expires (NULL for permanent bans) |
| `is_permanent` | Boolean | Whether the ban is permanent |
| `is_active` | Boolean | Whether the sanction is currently active |
| `revoked_at` | DateTime | When the sanction was revoked |
| `revoked_by` | String | Discord ID of moderator who revoked it |
| `revoke_reason` | Text | Reason for revocation |
| `notified_ingame` | Boolean | Whether in-game notification was sent |
| `notified_discord` | Boolean | Whether Discord notification was sent |
| `server_name` | String | Name of the server |
| `additional_notes` | Text | Additional notes about the sanction |

## Configuration

### Database Configuration File

Create a `database_config.json` file in the `C2ServerAPI` directory. You can copy `database_config.example.json` as a starting point.

#### SQLite (Local Database)

```json
{
    "type": "sqlite",
    "path": "sanctions.db"
}
```

#### PostgreSQL (Remote Database - Recommended)

```json
{
    "type": "postgresql",
    "host": "your-database-server.com",
    "port": 5432,
    "database": "sanctions",
    "username": "your_username",
    "password": "your_password",
    "pool_size": 5,
    "max_overflow": 10,
    "pool_timeout": 30
}
```

#### MySQL/MariaDB (Remote Database)

```json
{
    "type": "mysql",
    "host": "your-database-server.com",
    "port": 3306,
    "database": "sanctions",
    "username": "your_username",
    "password": "your_password",
    "pool_size": 5,
    "max_overflow": 10,
    "pool_timeout": 30
}
```

## Installation

### Required Dependencies

Add the following to your `pyproject.toml` or install via pip:

```bash
# For SQLite (included with Python)
# No additional dependencies needed

# For PostgreSQL
pip install sqlalchemy psycopg2-binary

# For MySQL/MariaDB
pip install sqlalchemy pymysql
```

Or using Poetry:

```bash
poetry add sqlalchemy
poetry add psycopg2-binary  # For PostgreSQL
poetry add pymysql          # For MySQL
```

## Usage Examples

### Initialize the Database

```python
from core.database_config import get_database_config

# Initialize database (automatically loads config from database_config.json)
db_config = get_database_config()

# Test the connection
if db_config.test_connection():
    print("Database connected successfully!")
```

### Create a Sanction

```python
from core.database_manager import SanctionManager

# Create a ban
ban = SanctionManager.create_sanction(
    sanction_type='ban',
    playfab_id='ABC123456789',
    username='PlayerName',
    reason='FFA on duel server',
    duration_hours=24.0,
    moderator_id='123456789012345678',
    moderator_name='ModeratorName',
    notified_ingame=True,
    notified_discord=True,
    server_name='My Server'
)

# Create a kick
kick = SanctionManager.create_sanction(
    sanction_type='kick',
    playfab_id='DEF987654321',
    username='AnotherPlayer',
    reason='Inappropriate language',
    moderator_id='123456789012345678',
    moderator_name='ModeratorName'
)
```

### Retrieve Sanctions

```python
# Get all sanctions
all_sanctions = SanctionManager.get_all_sanctions(limit=100)

# Get only active sanctions
active_sanctions = SanctionManager.get_all_sanctions(active_only=True)

# Get sanctions for a specific player
player_sanctions = SanctionManager.get_sanctions_by_playfab_id('ABC123456789')

# Get sanctions by a specific moderator
mod_sanctions = SanctionManager.get_sanctions_by_moderator('123456789012345678')
```

### Search Sanctions

```python
# Search by username
results = SanctionManager.search_sanctions(username='Player')

# Search active bans only
active_bans = SanctionManager.search_sanctions(
    sanction_type='ban',
    active_only=True
)

# Complex search
results = SanctionManager.search_sanctions(
    username='Player',
    server_name='My Server',
    moderator_id='123456789012345678',
    active_only=True,
    limit=50
)
```

### Update and Revoke Sanctions

```python
# Update a sanction
SanctionManager.update_sanction(
    sanction_id=1,
    additional_notes='Updated information',
    reason='Updated reason'
)

# Revoke a sanction
SanctionManager.revoke_sanction(
    sanction_id=1,
    revoked_by='987654321098765432',
    revoke_reason='Appeal accepted'
)
```

### Get Statistics

```python
stats = SanctionManager.get_statistics()
print(f"Total sanctions: {stats['total_sanctions']}")
print(f"Active bans: {stats['active_bans']}")
print(f"Permanent bans: {stats['permanent_bans']}")
```

## Running the Demo

To see the system in action, run the demo script:

```bash
cd C2ServerAPI/core
python database_demo.py
```

## Notes

- The database tables are created automatically on first run
- For production use, it's recommended to use PostgreSQL with a remote server
- All timestamps are stored in UTC
- The system uses connection pooling for remote databases to handle multiple concurrent users
- Sanctions are soft-deleted (marked as inactive) rather than permanently deleted by default

## Security Considerations

- **Never commit `database_config.json` with real credentials to version control**
- Use environment variables for sensitive information in production
- Ensure your database server has proper firewall rules
- Use SSL/TLS connections for remote databases
- Regularly backup your database

