# Database System Overview

This document provides an overview of the sanction database system implementation.

## System Architecture

The database system is designed to track sanctions (bans and kicks) in a centralized database that can be accessed by multiple users. It supports both local SQLite databases (for development/testing) and remote databases like PostgreSQL or MySQL (for production).

## Files Created

### Core Database Files (in `core/` directory)

1. **`database_models.py`**
   - Defines the database schema using SQLAlchemy ORM
   - Contains the `Sanction` model with all fields for tracking bans and kicks
   - Includes helper methods like `to_dict()` for serialization

2. **`database_config.py`**
   - Handles database connection configuration
   - Supports SQLite, PostgreSQL, and MySQL
   - Manages connection pooling for remote databases
   - Provides session management for thread-safe database access

3. **`database_manager.py`**
   - High-level API for database operations (CRUD)
   - Contains the `SanctionManager` class with methods for:
     - Creating sanctions
     - Retrieving sanctions (all, by ID, by player, by moderator)
     - Searching sanctions with filters
     - Updating and revoking sanctions
     - Getting statistics

4. **`database_utils.py`**
   - Utility functions for database management
   - Export functions (JSON, CSV)
   - Report generation (player reports, moderator reports)

5. **`database_demo.py`**
   - Demonstration script showing how to use the database system
   - Includes examples of all major operations

### Configuration Files

6. **`database_config.example.json`**
   - Example configuration file
   - Shows configuration for SQLite, PostgreSQL, and MySQL
   - Should be copied to `database_config.json` and customized

### CLI Tool

7. **`database_cli.py`**
   - Command-line interface for database management
   - Commands: list, search, view, stats, export, player-report
   - Useful for testing and manual database operations

### Documentation

8. **`DATABASE_README.md`**
   - Comprehensive documentation of the database system
   - API reference with code examples
   - Database schema documentation

9. **`DATABASE_SETUP.md`**
   - Step-by-step setup guide
   - Instructions for SQLite, PostgreSQL, and MySQL
   - Security best practices
   - Troubleshooting guide

10. **`DATABASE_SYSTEM_OVERVIEW.md`** (this file)
    - High-level overview of the system
    - File structure and purpose

### Updated Files

11. **`pyproject.toml`**
    - Added SQLAlchemy dependency
    - Added optional dependencies for PostgreSQL and MySQL
    - Configured extras for easy installation

## Key Features

### Multi-Database Support
- **SQLite**: Local database, no server required, perfect for testing
- **PostgreSQL**: Recommended for production, excellent for multi-user environments
- **MySQL/MariaDB**: Alternative production option

### Comprehensive Sanction Tracking
- Ban and kick records
- Duration tracking with automatic expiration calculation
- Moderator information
- Notification status (in-game and Discord)
- Revocation support with audit trail
- Server name tracking
- Additional notes field

### Powerful Query Capabilities
- Get all sanctions with pagination
- Filter by active/inactive status
- Search by player, moderator, server, or sanction type
- Get player history
- Get moderator activity

### Data Export
- Export to JSON format
- Export to CSV format
- Generate player reports
- Generate moderator reports

### Thread-Safe Design
- Uses SQLAlchemy's scoped sessions
- Connection pooling for remote databases
- Safe for use in multi-threaded applications (like PyQt5)

## Database Schema

### Sanctions Table

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| sanction_type | String | 'ban' or 'kick' |
| playfab_id | String | Player's PlayFab ID (indexed) |
| username | String | Player's username |
| reason | Text | Reason for sanction |
| duration_hours | Float | Duration in hours (NULL for kicks) |
| moderator_id | String | Discord ID of moderator |
| moderator_name | String | Name of moderator |
| applied_at | DateTime | When applied (indexed) |
| expires_at | DateTime | When expires (NULL for permanent) |
| is_permanent | Boolean | Whether ban is permanent |
| is_active | Boolean | Whether currently active (indexed) |
| revoked_at | DateTime | When revoked |
| revoked_by | String | Who revoked it |
| revoke_reason | Text | Why revoked |
| notified_ingame | Boolean | In-game notification sent |
| notified_discord | Boolean | Discord notification sent |
| server_name | String | Server name |
| additional_notes | Text | Additional notes |

## Usage Flow

1. **Setup**: Install dependencies and configure database connection
2. **Initialize**: Database tables are created automatically on first run
3. **Create**: When a ban/kick is applied, create a sanction record
4. **Retrieve**: Query sanctions for display in UI or reports
5. **Update**: Modify sanction details as needed
6. **Revoke**: Mark sanctions as inactive when unbanning

## Integration Points

The database system is designed to be integrated with the existing interface code:

- **When applying a ban**: Call `SanctionManager.create_sanction()` with ban details
- **When applying a kick**: Call `SanctionManager.create_sanction()` with kick details
- **When unbanning**: Call `SanctionManager.revoke_sanction()` with the sanction ID
- **Viewing history**: Use search and retrieval methods to display past sanctions
- **Reports**: Use utility functions to generate player/moderator reports

## Next Steps

1. Install dependencies: `poetry install` or `pip install sqlalchemy`
2. Configure database: Copy and edit `database_config.example.json`
3. Test the system: Run `python core/database_demo.py`
4. Integrate with interface: Add database calls to existing ban/kick functions
5. (Optional) Set up remote database for production use

## Security Considerations

- Never commit `database_config.json` with real credentials
- Use environment variables for sensitive data in production
- Enable SSL/TLS for remote database connections
- Implement regular database backups
- Use proper user permissions on the database server

## Support

For detailed documentation, see:
- `DATABASE_README.md` - API reference and examples
- `DATABASE_SETUP.md` - Setup and configuration guide
- `database_demo.py` - Working code examples

