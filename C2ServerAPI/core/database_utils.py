"""Utility functions for database management and maintenance.

This module provides helper functions for common database tasks like
generating reports and database maintenance.
"""

from typing import List
from .database_manager import SanctionManager, RedFlagManager


class DatabaseUtils:
    """Utility class for database management tasks."""
    
    @staticmethod
    def generate_player_report(playfab_id: str) -> dict:
        """Generate a comprehensive report for a specific player.

        Args:
            playfab_id: The PlayFab ID of the player

        Returns:
            dict: Report containing player sanction history and statistics
        """
        sanctions = SanctionManager.get_sanctions_by_playfab_id(playfab_id)

        if not sanctions:
            return {
                'playfab_id': playfab_id,
                'total_sanctions': 0,
                'message': 'No sanctions found for this player'
            }

        # Calculate statistics
        total_bans = sum(1 for s in sanctions if s.sanction_type == 'ban')
        total_kicks = sum(1 for s in sanctions if s.sanction_type == 'kick')
        revoked_sanctions = sum(1 for s in sanctions if s.revoked_at is not None)

        # Get most recent username
        most_recent = max(sanctions, key=lambda s: s.applied_at)

        report = {
            'playfab_id': playfab_id,
            'most_recent_username': most_recent.username,
            'total_sanctions': len(sanctions),
            'total_bans': total_bans,
            'total_kicks': total_kicks,
            'revoked_sanctions': revoked_sanctions,
            'first_sanction': min(sanctions, key=lambda s: s.applied_at).applied_at.isoformat(),
            'last_sanction': most_recent.applied_at.isoformat(),
            'sanctions': [s.to_dict() for s in sanctions]
        }

        return report

    @staticmethod
    def generate_moderator_report(moderator_id: str, limit: int = 100) -> dict:
        """Generate a report of sanctions applied by a specific moderator.

        Args:
            moderator_id: The Discord ID of the moderator
            limit: Maximum number of sanctions to include

        Returns:
            dict: Report containing moderator activity statistics
        """
        sanctions = SanctionManager.get_sanctions_by_moderator(moderator_id, limit=limit)

        if not sanctions:
            return {
                'moderator_id': moderator_id,
                'total_sanctions': 0,
                'message': 'No sanctions found for this moderator'
            }

        # Calculate statistics
        total_bans = sum(1 for s in sanctions if s.sanction_type == 'ban')
        total_kicks = sum(1 for s in sanctions if s.sanction_type == 'kick')
        revoked_sanctions = sum(1 for s in sanctions if s.revoked_at is not None)

        report = {
            'moderator_id': moderator_id,
            'moderator_name': sanctions[0].moderator_name if sanctions else None,
            'total_sanctions': len(sanctions),
            'total_bans': total_bans,
            'total_kicks': total_kicks,
            'revoked_sanctions': revoked_sanctions,
            'first_sanction': min(sanctions, key=lambda s: s.applied_at).applied_at.isoformat(),
            'last_sanction': max(sanctions, key=lambda s: s.applied_at).applied_at.isoformat(),
            'sanctions': [s.to_dict() for s in sanctions[:limit]]
        }

        return report

    @staticmethod
    def generate_player_redflag_report(playfab_id: str) -> dict:
        """Generate a report of redflags for a specific player.

        Args:
            playfab_id: The PlayFab ID of the player

        Returns:
            dict: Report containing player redflag history and statistics
        """
        redflags = RedFlagManager.get_redflags_by_playfab_id(playfab_id)

        if not redflags:
            return {
                'playfab_id': playfab_id,
                'total_redflags': 0,
                'message': 'No redflags found for this player'
            }

        # Calculate statistics
        resolved_redflags = sum(1 for r in redflags if r.resolved_at is not None)

        # Get most recent username
        most_recent = max(redflags, key=lambda r: r.created_at)

        report = {
            'playfab_id': playfab_id,
            'most_recent_username': most_recent.username,
            'total_redflags': len(redflags),
            'resolved_redflags': resolved_redflags,
            'first_redflag': min(redflags, key=lambda r: r.created_at).created_at.isoformat(),
            'last_redflag': most_recent.created_at.isoformat(),
            'redflags': [r.to_dict() for r in redflags]
        }

        return report

