"""Database models for the sanction tracking system.

This module defines the database schema for storing:
- Player history entries (sanctions + identity updates)
- Player records (latest username, last_seen, name history, moderator notes)
- Redflags

NOTE: The schema is created via SQLAlchemy's ``Base.metadata.create_all``.
If you already have an existing database file, adding columns requires a
migration (``create_all`` will not alter existing tables).
"""

import json

from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class PlayerRecord(Base):
    """Current player identity + moderator-maintained metadata.

    A single row per PlayFab ID, used to keep the *latest* username/last_seen,
    plus long-lived metadata like name_history and an editable note.
    """

    __tablename__ = 'player_records'

    # Use playfab_id as primary key so upserts are simple and stable.
    playfab_id = Column(String(255), primary_key=True)

    username = Column(String(255), nullable=True, index=True)
    last_seen = Column(DateTime, nullable=True, index=True)

    # JSON-encoded list of previous usernames (oldest -> newest).
    name_history = Column(Text, nullable=False, default='[]')

    # Free-form moderator note (editable/deletable).
    note = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_name_history(self):
        """Return name history as a Python list (never None)."""
        try:
            data = json.loads(self.name_history or '[]')
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def set_name_history(self, names):
        """Set name history from a list-like value."""
        if not names:
            self.name_history = '[]'
            return
        self.name_history = json.dumps(list(names))

    def to_dict(self):
        return {
            'playfab_id': self.playfab_id,
            'username': self.username,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'name_history': self.get_name_history(),
            'note': self.note,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Sanction(Base):
    """History entry for a player.

    This is a classic append-only-ish history table. Most rows are sanctions
    (``ban`` or ``kick``) but the same table also stores lightweight identity
    updates like username changes and last_seen updates.

    ``sanction_type`` now acts as a generic entry type.
    Allowed values (convention):
      - 'ban'
      - 'kick'
      - 'username_update'
      - 'last_seen_update'

    Attributes:
        id: Primary key, auto-incrementing integer
        sanction_type: Type of sanction ('ban' or 'kick')
        playfab_id: Player's PlayFab ID
        username: Player's username at the time of sanction
        reason: Reason for the sanction
        duration_hours: Duration in hours (for bans, None for kicks)
        moderator_id: Discord ID of the moderator who applied the sanction
        moderator_name: Name of the moderator (optional)
        applied_at: Timestamp when the sanction was applied
        expires_at: Timestamp when the sanction expires (for bans, None for kicks)
        revoked_at: Timestamp when the sanction was revoked (if applicable)
        revoked_by: Discord ID of the moderator who revoked the sanction
    """

    __tablename__ = 'sanctions'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Entry details
    sanction_type = Column(String(32), nullable=False, index=True)
    playfab_id = Column(String(255), nullable=False, index=True)

    # Identity snapshot at time of entry
    username = Column(String(255), nullable=True, index=True)
    previous_username = Column(String(255), nullable=True)

    # Sanction fields (only for ban/kick)
    reason = Column(Text, nullable=True)
    duration_hours = Column(Float, nullable=True)  # bans only

    # Moderator information
    moderator_id = Column(String(255), nullable=True)
    moderator_name = Column(String(255), nullable=True)

    # Timestamps
    applied_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)

    # Identity update fields (for last_seen_update)
    last_seen = Column(DateTime, nullable=True)

    # Revocation information
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(String(255), nullable=True)
    
    def __repr__(self):
        """String representation of the Sanction object."""
        return (f"<Sanction(id={self.id}, type={self.sanction_type}, "
                f"playfab_id={self.playfab_id}, username={self.username}, "
                f"applied_at={self.applied_at})>")

    def to_dict(self):
        """Convert the Sanction object to a dictionary.

        Returns:
            dict: Dictionary representation of the sanction
        """
        return {
            'id': self.id,
            'sanction_type': self.sanction_type,
            'playfab_id': self.playfab_id,
            'username': self.username,
            'previous_username': self.previous_username,
            'reason': self.reason,
            'duration_hours': self.duration_hours,
            'moderator_id': self.moderator_id,
            'moderator_name': self.moderator_name,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'revoked_by': self.revoked_by
        }


class RedFlag(Base):
    """Model representing a redflag (warning/note) for a player.

    Redflags are used to mark players for moderator attention without
    applying a formal sanction. They serve as warnings or notes about
    player behavior.

    Attributes:
        id: Primary key, auto-incrementing integer
        playfab_id: Player's PlayFab ID
        username: Player's username at the time of redflag
        reason: Reason for the redflag
        moderator_id: Discord ID of the moderator who created the redflag
        moderator_name: Name of the moderator (optional)
        created_at: Timestamp when the redflag was created
        resolved_at: Timestamp when the redflag was resolved (if applicable)
        resolved_by: Discord ID of the moderator who resolved the redflag
        resolution_note: Note about how/why the redflag was resolved
    """

    __tablename__ = 'redflags'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # RedFlag details
    playfab_id = Column(String(255), nullable=False, index=True)
    username = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)

    # Moderator information
    moderator_id = Column(String(255), nullable=True)
    moderator_name = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Resolution information
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(255), nullable=True)
    resolution_note = Column(Text, nullable=True)

    def __repr__(self):
        """String representation of the RedFlag object."""
        return (f"<RedFlag(id={self.id}, "
                f"playfab_id={self.playfab_id}, username={self.username}, "
                f"created_at={self.created_at})>")

    def to_dict(self):
        """Convert the RedFlag object to a dictionary.

        Returns:
            dict: Dictionary representation of the redflag
        """
        return {
            'id': self.id,
            'playfab_id': self.playfab_id,
            'username': self.username,
            'reason': self.reason,
            'moderator_id': self.moderator_id,
            'moderator_name': self.moderator_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': self.resolved_by,
            'resolution_note': self.resolution_note
        }

