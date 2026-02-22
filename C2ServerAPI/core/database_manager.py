"""Database manager for sanction and redflag operations.

This module provides high-level functions for creating, retrieving, updating,
and deleting sanctions (bans and kicks) and redflags in the database.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import desc, or_
from sqlalchemy.exc import SQLAlchemyError

from .database_models import Sanction, RedFlag, PlayerRecord
from .database_config import get_session


class SanctionManager:
    """Manager class for sanction database operations."""

    @staticmethod
    def create_sanction(
        sanction_type: str,
        playfab_id: str,
        username: str,
        reason: str,
        duration_hours: Optional[float] = None,
        moderator_id: Optional[str] = None,
        moderator_name: Optional[str] = None
    ) -> Optional[Sanction]:
        """Create a new sanction record in the database.

        Args:
            sanction_type: Type of sanction ('ban' or 'kick')
            playfab_id: Player's PlayFab ID
            username: Player's username
            reason: Reason for the sanction
            duration_hours: Duration in hours (for bans, None for kicks)
            moderator_id: Discord ID of the moderator
            moderator_name: Name of the moderator

        Returns:
            Sanction: The created sanction object, or None if creation failed
        """
        session = get_session()

        try:
            applied_at = datetime.utcnow()

            # Ensure player record exists + update identity/name_history as needed
            PlayerManager._upsert_player_identity_in_session(
                session,
                playfab_id=playfab_id,
                username=username,
                last_seen=applied_at,
                moderator_id=moderator_id,
                moderator_name=moderator_name,
                create_username_history=True,
                create_last_seen_history=False,
            )

            expires_at = None
            if sanction_type == 'ban' and duration_hours is not None:
                try:
                    expires_at = applied_at + timedelta(hours=float(duration_hours))
                except Exception:
                    expires_at = None

            # Create sanction object
            sanction = Sanction(
                sanction_type=sanction_type,
                playfab_id=playfab_id,
                username=username,
                reason=reason,
                duration_hours=duration_hours,
                moderator_id=moderator_id,
                moderator_name=moderator_name,
                applied_at=applied_at,
                expires_at=expires_at
            )

            session.add(sanction)
            session.commit()
            session.refresh(sanction)

            print(f"[DATABASE] Created {sanction_type} for {username} (ID: {sanction.id})")
            return sanction

        except SQLAlchemyError as e:
            session.rollback()
            print(f"[DATABASE] Error creating sanction: {e}")
            return None
        finally:
            session.close()
    
    @staticmethod
    def get_all_sanctions(
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Sanction]:
        """Retrieve all sanctions from the database.

        Args:
            limit: Maximum number of sanctions to retrieve (None for all)
            offset: Number of sanctions to skip

        Returns:
            List[Sanction]: List of sanction objects
        """
        session = get_session()

        try:
            query = session.query(Sanction).order_by(desc(Sanction.applied_at))

            if offset > 0:
                query = query.offset(offset)

            if limit is not None:
                query = query.limit(limit)

            sanctions = query.all()
            print(f"[DATABASE] Retrieved {len(sanctions)} sanctions")
            return sanctions

        except SQLAlchemyError as e:
            print(f"[DATABASE] Error retrieving sanctions: {e}")
            return []
        finally:
            session.close()

    @staticmethod
    def get_sanction_by_id(sanction_id: int) -> Optional[Sanction]:
        """Retrieve a specific sanction by ID.

        Args:
            sanction_id: The ID of the sanction to retrieve

        Returns:
            Sanction: The sanction object, or None if not found
        """
        session = get_session()

        try:
            sanction = session.query(Sanction).filter(Sanction.id == sanction_id).first()
            return sanction
        except SQLAlchemyError as e:
            print(f"[DATABASE] Error retrieving sanction {sanction_id}: {e}")
            return None
        finally:
            session.close()

    @staticmethod
    def get_sanctions_by_playfab_id(playfab_id: str) -> List[Sanction]:
        """Retrieve all sanctions for a specific player.

        Args:
            playfab_id: The PlayFab ID of the player

        Returns:
            List[Sanction]: List of sanction objects for the player
        """
        session = get_session()

        try:
            query = session.query(Sanction).filter(Sanction.playfab_id == playfab_id)
            query = query.order_by(desc(Sanction.applied_at))
            sanctions = query.all()

            print(f"[DATABASE] Retrieved {len(sanctions)} sanctions for PlayFab ID: {playfab_id}")
            return sanctions

        except SQLAlchemyError as e:
            print(f"[DATABASE] Error retrieving sanctions for {playfab_id}: {e}")
            return []
        finally:
            session.close()

    @staticmethod
    def get_sanctions_by_moderator(
        moderator_id: str,
        limit: Optional[int] = None
    ) -> List[Sanction]:
        """Retrieve all sanctions applied by a specific moderator.

        Args:
            moderator_id: The Discord ID of the moderator
            limit: Maximum number of sanctions to retrieve

        Returns:
            List[Sanction]: List of sanction objects applied by the moderator
        """
        session = get_session()

        try:
            query = session.query(Sanction).filter(Sanction.moderator_id == moderator_id)
            query = query.order_by(desc(Sanction.applied_at))

            if limit is not None:
                query = query.limit(limit)

            sanctions = query.all()
            print(f"[DATABASE] Retrieved {len(sanctions)} sanctions by moderator: {moderator_id}")
            return sanctions

        except SQLAlchemyError as e:
            print(f"[DATABASE] Error retrieving sanctions by moderator {moderator_id}: {e}")
            return []
        finally:
            session.close()

    @staticmethod
    def search_sanctions(
        username: Optional[str] = None,
        playfab_id: Optional[str] = None,
        sanction_type: Optional[str] = None,
        moderator_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Sanction]:
        """Search for sanctions with various filters.

        Args:
            username: Filter by username (partial match)
            playfab_id: Filter by PlayFab ID (exact match)
            sanction_type: Filter by sanction type ('ban' or 'kick')
            moderator_id: Filter by moderator Discord ID
            limit: Maximum number of results to return

        Returns:
            List[Sanction]: List of matching sanction objects
        """
        session = get_session()

        try:
            query = session.query(Sanction)

            # Apply filters
            if username:
                # Match current/recorded usernames, previous_username from username_update,
                # and also resolve via PlayerRecord.name_history.
                matching_player_ids = session.query(PlayerRecord.playfab_id).filter(
                    or_(
                        PlayerRecord.username.ilike(f"%{username}%"),
                        PlayerRecord.name_history.ilike(f"%{username}%"),
                    )
                )

                query = query.filter(
                    or_(
                        Sanction.username.ilike(f"%{username}%"),
                        Sanction.previous_username.ilike(f"%{username}%"),
                        Sanction.playfab_id.in_(matching_player_ids),
                    )
                )

            if playfab_id:
                query = query.filter(Sanction.playfab_id == playfab_id)

            if sanction_type:
                query = query.filter(Sanction.sanction_type == sanction_type)

            if moderator_id:
                query = query.filter(Sanction.moderator_id == moderator_id)

            query = query.order_by(desc(Sanction.applied_at))

            if limit is not None:
                query = query.limit(limit)

            sanctions = query.all()
            print(f"[DATABASE] Search returned {len(sanctions)} sanctions")
            return sanctions

        except SQLAlchemyError as e:
            print(f"[DATABASE] Error searching sanctions: {e}")
            return []
        finally:
            session.close()

    @staticmethod
    def revoke_sanction(
        sanction_id: int,
        revoked_by: str
    ) -> bool:
        """Revoke a sanction.

        Args:
            sanction_id: The ID of the sanction to revoke
            revoked_by: Discord ID of the moderator revoking the sanction

        Returns:
            bool: True if revocation was successful, False otherwise
        """
        session = get_session()

        try:
            sanction = session.query(Sanction).filter(Sanction.id == sanction_id).first()

            if not sanction:
                print(f"[DATABASE] Sanction {sanction_id} not found")
                return False

            sanction.revoked_at = datetime.utcnow()
            sanction.revoked_by = revoked_by

            session.commit()
            print(f"[DATABASE] Revoked sanction {sanction_id}")
            return True

        except SQLAlchemyError as e:
            session.rollback()
            print(f"[DATABASE] Error revoking sanction {sanction_id}: {e}")
            return False
        finally:
            session.close()

    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        """Get statistics about sanctions in the database.

        Returns:
            dict: Dictionary containing various statistics
        """
        session = get_session()

        try:
            total_entries = session.query(Sanction).count()

            total_bans = session.query(Sanction).filter(Sanction.sanction_type == 'ban').count()
            total_kicks = session.query(Sanction).filter(Sanction.sanction_type == 'kick').count()
            total_username_updates = session.query(Sanction).filter(
                Sanction.sanction_type == 'username_update'
            ).count()
            total_last_seen_updates = session.query(Sanction).filter(
                Sanction.sanction_type == 'last_seen_update'
            ).count()

            # Keep legacy meaning: sanctions == bans+kicks
            total_sanctions = total_bans + total_kicks
            revoked_sanctions = session.query(Sanction).filter(
                Sanction.sanction_type.in_(['ban', 'kick']),
                Sanction.revoked_at.isnot(None)
            ).count()

            stats = {
                'total_entries': total_entries,
                'total_sanctions': total_sanctions,
                'total_bans': total_bans,
                'total_kicks': total_kicks,
                'total_username_updates': total_username_updates,
                'total_last_seen_updates': total_last_seen_updates,
                'revoked_sanctions': revoked_sanctions
            }

            print(f"[DATABASE] Retrieved statistics: {stats}")
            return stats

        except SQLAlchemyError as e:
            print(f"[DATABASE] Error retrieving statistics: {e}")
            return {}
        finally:
            session.close()


class RedFlagManager:
    """Manager class for redflag database operations."""

    @staticmethod
    def create_redflag(
        playfab_id: str,
        username: str,
        reason: str,
        moderator_id: Optional[str] = None,
        moderator_name: Optional[str] = None
    ) -> Optional[RedFlag]:
        """Create a new redflag record in the database.

        Args:
            playfab_id: Player's PlayFab ID
            username: Player's username
            reason: Reason for the redflag
            moderator_id: Discord ID of the moderator
            moderator_name: Name of the moderator

        Returns:
            RedFlag: The created redflag object, or None if creation failed
        """
        session = get_session()

        try:
            created_at = datetime.utcnow()

            # Ensure player record exists + update identity/name_history as needed
            PlayerManager._upsert_player_identity_in_session(
                session,
                playfab_id=playfab_id,
                username=username,
                last_seen=created_at,
                moderator_id=moderator_id,
                moderator_name=moderator_name,
                create_username_history=True,
                create_last_seen_history=False,
            )

            # Create redflag object
            redflag = RedFlag(
                playfab_id=playfab_id,
                username=username,
                reason=reason,
                moderator_id=moderator_id,
                moderator_name=moderator_name,
                created_at=created_at
            )

            session.add(redflag)
            session.commit()
            session.refresh(redflag)

            print(f"[DATABASE] Created redflag for {username} (ID: {redflag.id})")
            return redflag

        except SQLAlchemyError as e:
            session.rollback()
            print(f"[DATABASE] Error creating redflag: {e}")
            return None
        finally:
            session.close()

    @staticmethod
    def get_all_redflags(
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[RedFlag]:
        """Retrieve all redflags from the database.

        Args:
            limit: Maximum number of redflags to retrieve (None for all)
            offset: Number of redflags to skip

        Returns:
            List[RedFlag]: List of redflag objects
        """
        session = get_session()

        try:
            query = session.query(RedFlag).order_by(desc(RedFlag.created_at))

            if offset > 0:
                query = query.offset(offset)

            if limit is not None:
                query = query.limit(limit)

            redflags = query.all()
            print(f"[DATABASE] Retrieved {len(redflags)} redflags")
            return redflags

        except SQLAlchemyError as e:
            print(f"[DATABASE] Error retrieving redflags: {e}")
            return []
        finally:
            session.close()

    @staticmethod
    def get_redflag_by_id(redflag_id: int) -> Optional[RedFlag]:
        """Retrieve a specific redflag by ID.

        Args:
            redflag_id: The ID of the redflag to retrieve

        Returns:
            RedFlag: The redflag object, or None if not found
        """
        session = get_session()

        try:
            redflag = session.query(RedFlag).filter(RedFlag.id == redflag_id).first()
            return redflag
        except SQLAlchemyError as e:
            print(f"[DATABASE] Error retrieving redflag {redflag_id}: {e}")
            return None
        finally:
            session.close()

    @staticmethod
    def get_redflags_by_playfab_id(playfab_id: str) -> List[RedFlag]:
        """Retrieve all redflags for a specific player.

        Args:
            playfab_id: The PlayFab ID of the player

        Returns:
            List[RedFlag]: List of redflag objects for the player
        """
        session = get_session()

        try:
            query = session.query(RedFlag).filter(RedFlag.playfab_id == playfab_id)
            query = query.order_by(desc(RedFlag.created_at))
            redflags = query.all()

            print(f"[DATABASE] Retrieved {len(redflags)} redflags for PlayFab ID: {playfab_id}")
            return redflags

        except SQLAlchemyError as e:
            print(f"[DATABASE] Error retrieving redflags for {playfab_id}: {e}")
            return []
        finally:
            session.close()

    @staticmethod
    def get_redflags_by_moderator(
        moderator_id: str,
        limit: Optional[int] = None
    ) -> List[RedFlag]:
        """Retrieve all redflags created by a specific moderator.

        Args:
            moderator_id: The Discord ID of the moderator
            limit: Maximum number of redflags to retrieve

        Returns:
            List[RedFlag]: List of redflag objects created by the moderator
        """
        session = get_session()

        try:
            query = session.query(RedFlag).filter(RedFlag.moderator_id == moderator_id)
            query = query.order_by(desc(RedFlag.created_at))

            if limit is not None:
                query = query.limit(limit)

            redflags = query.all()
            print(f"[DATABASE] Retrieved {len(redflags)} redflags by moderator: {moderator_id}")
            return redflags

        except SQLAlchemyError as e:
            print(f"[DATABASE] Error retrieving redflags by moderator {moderator_id}: {e}")
            return []
        finally:
            session.close()

    @staticmethod
    def search_redflags(
        username: Optional[str] = None,
        playfab_id: Optional[str] = None,
        moderator_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[RedFlag]:
        """Search for redflags with various filters.

        Args:
            username: Filter by username (partial match)
            playfab_id: Filter by PlayFab ID (exact match)
            moderator_id: Filter by moderator Discord ID
            limit: Maximum number of results to return

        Returns:
            List[RedFlag]: List of matching redflag objects
        """
        session = get_session()

        try:
            query = session.query(RedFlag)

            # Apply filters
            if username:
                matching_player_ids = session.query(PlayerRecord.playfab_id).filter(
                    or_(
                        PlayerRecord.username.ilike(f"%{username}%"),
                        PlayerRecord.name_history.ilike(f"%{username}%"),
                    )
                )
                query = query.filter(
                    or_(
                        RedFlag.username.ilike(f"%{username}%"),
                        RedFlag.playfab_id.in_(matching_player_ids),
                    )
                )

            if playfab_id:
                query = query.filter(RedFlag.playfab_id == playfab_id)

            if moderator_id:
                query = query.filter(RedFlag.moderator_id == moderator_id)

            query = query.order_by(desc(RedFlag.created_at))

            if limit is not None:
                query = query.limit(limit)

            redflags = query.all()
            print(f"[DATABASE] Search returned {len(redflags)} redflags")
            return redflags

        except SQLAlchemyError as e:
            print(f"[DATABASE] Error searching redflags: {e}")
            return []
        finally:
            session.close()

    @staticmethod
    def resolve_redflag(
        redflag_id: int,
        resolved_by: str,
        resolution_note: Optional[str] = None
    ) -> bool:
        """Resolve a redflag.

        Args:
            redflag_id: The ID of the redflag to resolve
            resolved_by: Discord ID of the moderator resolving the redflag
            resolution_note: Optional note about the resolution

        Returns:
            bool: True if resolution was successful, False otherwise
        """
        session = get_session()

        try:
            redflag = session.query(RedFlag).filter(RedFlag.id == redflag_id).first()

            if not redflag:
                print(f"[DATABASE] RedFlag {redflag_id} not found")
                return False

            redflag.resolved_at = datetime.utcnow()
            redflag.resolved_by = resolved_by
            redflag.resolution_note = resolution_note

            session.commit()
            print(f"[DATABASE] Resolved redflag {redflag_id}")
            return True

        except SQLAlchemyError as e:
            session.rollback()
            print(f"[DATABASE] Error resolving redflag {redflag_id}: {e}")
            return False
        finally:
            session.close()

    @staticmethod
    def delete_redflag(redflag_id: int) -> bool:
        """Permanently delete a redflag from the database.

        Warning: This permanently removes the record. Consider using resolve_redflag instead.

        Args:
            redflag_id: The ID of the redflag to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        session = get_session()

        try:
            redflag = session.query(RedFlag).filter(RedFlag.id == redflag_id).first()

            if not redflag:
                print(f"[DATABASE] RedFlag {redflag_id} not found")
                return False

            session.delete(redflag)
            session.commit()
            print(f"[DATABASE] Deleted redflag {redflag_id}")
            return True

        except SQLAlchemyError as e:
            session.rollback()
            print(f"[DATABASE] Error deleting redflag {redflag_id}: {e}")
            return False
        finally:
            session.close()

    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        """Get statistics about redflags in the database.

        Returns:
            dict: Dictionary containing various statistics
        """
        session = get_session()

        try:
            total_redflags = session.query(RedFlag).count()
            resolved_redflags = session.query(RedFlag).filter(RedFlag.resolved_at.isnot(None)).count()

            stats = {
                'total_redflags': total_redflags,
                'resolved_redflags': resolved_redflags
            }

            print(f"[DATABASE] Retrieved redflag statistics: {stats}")
            return stats

        except SQLAlchemyError as e:
            print(f"[DATABASE] Error retrieving redflag statistics: {e}")
            return {}
        finally:
            session.close()


class PlayerManager:
    """Manager class for player record database operations."""

    @staticmethod
    def _get_or_create_player_record_in_session(
        session,
        playfab_id: str
    ) -> Tuple[PlayerRecord, bool]:
        """Get or create a PlayerRecord within an existing session."""
        record = session.query(PlayerRecord).filter(
            PlayerRecord.playfab_id == playfab_id
        ).first()
        if record:
            return record, False

        record = PlayerRecord(playfab_id=playfab_id)
        session.add(record)
        return record, True

    @staticmethod
    def _append_name_history(record: PlayerRecord, previous_username: Optional[str]) -> None:
        if not previous_username:
            return
        history = record.get_name_history()
        if previous_username not in history:
            history.append(previous_username)
            record.set_name_history(history)

    @staticmethod
    def _upsert_player_identity_in_session(
        session,
        playfab_id: str,
        username: Optional[str] = None,
        last_seen: Optional[datetime] = None,
        moderator_id: Optional[str] = None,
        moderator_name: Optional[str] = None,
        create_username_history: bool = True,
        create_last_seen_history: bool = True,
    ) -> PlayerRecord:
        """Upsert PlayerRecord and optionally create history entries in Sanction.

        Notes:
          - Username changes append the previous username to PlayerRecord.name_history.
          - Username changes create a 'username_update' history row.
          - last_seen updates create a 'last_seen_update' history row.
        """
        now = datetime.utcnow()
        record, created = PlayerManager._get_or_create_player_record_in_session(
            session,
            playfab_id,
        )

        # Username update + name_history
        if username is not None and username != record.username:
            previous = record.username

            if previous:
                PlayerManager._append_name_history(record, previous)

            record.username = username

            # Avoid generating a noisy "initial" username history row on brand-new records
            if create_username_history and (not created):
                session.add(
                    Sanction(
                        sanction_type='username_update',
                        playfab_id=playfab_id,
                        username=username,
                        previous_username=previous,
                        moderator_id=moderator_id,
                        moderator_name=moderator_name,
                        applied_at=now,
                        expires_at=None,
                    )
                )

        # last_seen update
        if last_seen is not None:
            record.last_seen = last_seen

            # When first creating a record, it's still useful to store last_seen history
            if create_last_seen_history:
                session.add(
                    Sanction(
                        sanction_type='last_seen_update',
                        playfab_id=playfab_id,
                        username=record.username or username,
                        last_seen=last_seen,
                        moderator_id=moderator_id,
                        moderator_name=moderator_name,
                        applied_at=now,
                        expires_at=None,
                    )
                )

        return record

    @staticmethod
    def update_last_seen(
        playfab_id: str,
        username: str,
        moderator_id: Optional[str] = None,
        moderator_name: Optional[str] = None,
        seen_at: Optional[datetime] = None,
    ) -> Optional[PlayerRecord]:
        """Create or update the last_seen entry for a player.

        If a record for the given playfab_id already exists it is updated
        in-place (username + last_seen). Otherwise a new row is inserted.

        Args:
            playfab_id: Player's PlayFab ID
            username: Player's current username

        Returns:
            PlayerRecord: The created or updated record, or None on failure
        """
        session = get_session()

        try:
            effective_seen_at = seen_at or datetime.utcnow()

            record = PlayerManager._upsert_player_identity_in_session(
                session,
                playfab_id=playfab_id,
                username=username,
                last_seen=effective_seen_at,
                moderator_id=moderator_id,
                moderator_name=moderator_name,
                create_username_history=True,
                create_last_seen_history=True,
            )

            if seen_at is None:
                print(f"[DATABASE] Updated last_seen for {username} ({playfab_id})")
            else:
                print(f"[DATABASE] Updated last_seen for {username} ({playfab_id}) at {effective_seen_at}")

            session.commit()
            session.refresh(record)
            return record

        except SQLAlchemyError as e:
            session.rollback()
            print(f"[DATABASE] Error updating last_seen for {playfab_id}: {e}")
            return None
        finally:
            session.close()

    @staticmethod
    def set_note(
        playfab_id: str,
        note: Optional[str],
        moderator_id: Optional[str] = None,
        moderator_name: Optional[str] = None,
    ) -> Optional[PlayerRecord]:
        """Set (or overwrite) the moderator note for a player.

        Passing note=None will clear the note.
        """
        session = get_session()
        try:
            record, _created = PlayerManager._get_or_create_player_record_in_session(
                session,
                playfab_id,
            )
            record.note = note
            session.commit()
            session.refresh(record)
            print(f"[DATABASE] Updated note for {playfab_id}")
            return record
        except SQLAlchemyError as e:
            session.rollback()
            print(f"[DATABASE] Error updating note for {playfab_id}: {e}")
            return None
        finally:
            session.close()

    @staticmethod
    def clear_note(playfab_id: str) -> bool:
        """Clear the moderator note for a player."""
        updated = PlayerManager.set_note(playfab_id, None)
        return updated is not None

    @staticmethod
    def search_players(
        query: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[PlayerRecord]:
        """Search players by current username, historical usernames, or PlayFab ID.

        This supports identifying a player by any name they previously used.
        """
        session = get_session()
        try:
            q = (query or '').strip()
            if not q:
                return []

            db_query = session.query(PlayerRecord).filter(
                or_(
                    PlayerRecord.playfab_id.ilike(f"%{q}%"),
                    PlayerRecord.username.ilike(f"%{q}%"),
                    PlayerRecord.name_history.ilike(f"%{q}%"),
                )
            ).order_by(desc(PlayerRecord.last_seen))

            if offset > 0:
                db_query = db_query.offset(offset)
            if limit is not None:
                db_query = db_query.limit(limit)

            return db_query.all()
        except SQLAlchemyError as e:
            print(f"[DATABASE] Error searching players for '{query}': {e}")
            return []
        finally:
            session.close()

    @staticmethod
    def get_player(playfab_id: str) -> Optional[PlayerRecord]:
        """Retrieve the player record for a given PlayFab ID.

        Args:
            playfab_id: The PlayFab ID of the player

        Returns:
            PlayerRecord: The player record, or None if not found
        """
        session = get_session()

        try:
            record = session.query(PlayerRecord).filter(
                PlayerRecord.playfab_id == playfab_id
            ).first()
            return record
        except SQLAlchemyError as e:
            print(f"[DATABASE] Error retrieving player {playfab_id}: {e}")
            return None
        finally:
            session.close()

    @staticmethod
    def get_all_players(
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[PlayerRecord]:
        """Retrieve all player records ordered by most recently seen.

        Args:
            limit: Maximum number of records to retrieve (None for all)
            offset: Number of records to skip

        Returns:
            List[PlayerRecord]: List of player record objects
        """
        session = get_session()

        try:
            query = session.query(PlayerRecord).order_by(desc(PlayerRecord.last_seen))

            if offset > 0:
                query = query.offset(offset)

            if limit is not None:
                query = query.limit(limit)

            records = query.all()
            print(f"[DATABASE] Retrieved {len(records)} player records")
            return records

        except SQLAlchemyError as e:
            print(f"[DATABASE] Error retrieving player records: {e}")
            return []
        finally:
            session.close()
