# Database System Quick Reference

Quick reference guide for common database operations.

## Installation

```bash
# Basic installation (SQLite only)
poetry install

# With PostgreSQL support
poetry install --extras postgresql

# With MySQL support
poetry install --extras mysql

# With all database support
poetry install --extras all-databases
```

## Configuration

Create `database_config.json`:

```json
{
    "type": "sqlite",
    "path": "sanctions.db"
}
```

Or for remote PostgreSQL:

```json
{
    "type": "postgresql",
    "host": "your-server.com",
    "port": 5432,
    "database": "sanctions",
    "username": "your_user",
    "password": "your_password"
}
```

## Common Operations

### Import

```python
from core.database_manager import SanctionManager
from core.database_config import get_database_config, close_database
```

### Initialize Database

```python
# Initialize (call once at startup)
db_config = get_database_config()

# Test connection
if db_config.test_connection():
    print("Connected!")
```

### Create a Ban

```python
ban = SanctionManager.create_sanction(
    sanction_type='ban',
    playfab_id='ABC123',
    username='PlayerName',
    reason='FFA on duel server',
    duration_hours=24.0,
    moderator_id='123456789',
    moderator_name='ModName',
    notified_ingame=True,
    notified_discord=True,
    server_name='My Server'
)
```

### Create a Kick

```python
kick = SanctionManager.create_sanction(
    sanction_type='kick',
    playfab_id='DEF456',
    username='PlayerName',
    reason='Inappropriate language',
    moderator_id='123456789',
    moderator_name='ModName'
)
```

### Get All Sanctions

```python
# Get all sanctions
all_sanctions = SanctionManager.get_all_sanctions()

# Get only active sanctions
active = SanctionManager.get_all_sanctions(active_only=True)

# Get with pagination
page1 = SanctionManager.get_all_sanctions(limit=50, offset=0)
page2 = SanctionManager.get_all_sanctions(limit=50, offset=50)
```

### Get Player History

```python
# All sanctions for a player
history = SanctionManager.get_sanctions_by_playfab_id('ABC123')

# Only active sanctions
active = SanctionManager.get_sanctions_by_playfab_id('ABC123', active_only=True)
```

### Search Sanctions

```python
# Search by username
results = SanctionManager.search_sanctions(username='Player')

# Search active bans
bans = SanctionManager.search_sanctions(
    sanction_type='ban',
    active_only=True
)

# Complex search
results = SanctionManager.search_sanctions(
    username='Player',
    server_name='My Server',
    moderator_id='123456789',
    active_only=True,
    limit=100
)
```

### Revoke a Sanction (Unban)

```python
success = SanctionManager.revoke_sanction(
    sanction_id=123,
    revoked_by='987654321',
    revoke_reason='Appeal accepted'
)
```

### Update a Sanction

```python
success = SanctionManager.update_sanction(
    sanction_id=123,
    additional_notes='Updated information',
    reason='Updated reason'
)
```

### Get Statistics

```python
stats = SanctionManager.get_statistics()
print(f"Total bans: {stats['total_bans']}")
print(f"Active bans: {stats['active_bans']}")
```

### Export Data

```python
from core.database_utils import DatabaseUtils

# Export to JSON
DatabaseUtils.export_to_json('sanctions.json')

# Export to CSV
DatabaseUtils.export_to_csv('sanctions.csv')

# Export only active sanctions
DatabaseUtils.export_to_json('active.json', active_only=True)
```

### Generate Reports

```python
from core.database_utils import DatabaseUtils

# Player report
report = DatabaseUtils.generate_player_report('ABC123')
print(f"Total sanctions: {report['total_sanctions']}")

# Moderator report
report = DatabaseUtils.generate_moderator_report('123456789')
print(f"Total actions: {report['total_sanctions']}")
```

### Close Database (at shutdown)

```python
close_database()
```

## CLI Commands

```bash
# List sanctions
python database_cli.py list --limit 50 --active

# Search
python database_cli.py search --username Player --active

# View specific sanction
python database_cli.py view 123

# Statistics
python database_cli.py stats

# Export
python database_cli.py export output.json --format json --active
python database_cli.py export output.csv --format csv

# Player report
python database_cli.py player-report ABC123
```

## Integration Example

```python
# In your ban function
def apply_ban(playfab_id, username, reason, duration_hours):
    # ... existing ban logic ...
    
    # Add to database
    from core.database_manager import SanctionManager
    
    sanction = SanctionManager.create_sanction(
        sanction_type='ban',
        playfab_id=playfab_id,
        username=username,
        reason=reason,
        duration_hours=duration_hours,
        moderator_id=get_current_moderator_id(),
        moderator_name=get_current_moderator_name(),
        notified_ingame=True,
        notified_discord=True,
        server_name=get_server_name()
    )
    
    if sanction:
        print(f"Ban recorded in database (ID: {sanction.id})")
```

## Error Handling

```python
try:
    sanction = SanctionManager.create_sanction(...)
    if sanction:
        print("Success!")
    else:
        print("Failed to create sanction")
except Exception as e:
    print(f"Error: {e}")
```

## Best Practices

1. **Initialize once**: Call `get_database_config()` once at application startup
2. **Close on exit**: Call `close_database()` when application closes
3. **Use active_only**: Filter for active sanctions when checking current bans
4. **Store sanction IDs**: Keep track of sanction IDs for later revocation
5. **Add notes**: Use `additional_notes` for important context
6. **Regular backups**: Export data regularly or set up database backups

## Troubleshooting

**Can't connect to database:**
- Check `database_config.json` exists and is valid
- Verify database server is running (for remote databases)
- Check credentials and permissions

**Tables not created:**
```python
from core.database_config import get_database_config
from core.database_models import Base

db = get_database_config()
Base.metadata.create_all(db.engine)
```

**Import errors:**
```bash
# Make sure you're in the right directory
cd C2ServerAPI

# Install dependencies
poetry install
```

