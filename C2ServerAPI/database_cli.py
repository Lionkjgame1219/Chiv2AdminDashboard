#!/usr/bin/env python
"""Command-line interface for database management.

This script provides a simple CLI for managing the sanction and redflag database,
including viewing and searching sanctions and redflags.
"""

import argparse
from core.database_manager import SanctionManager, RedFlagManager
from core.database_config import get_database_config, close_database
from core.database_utils import DatabaseUtils


def cmd_list(args):
    """List sanctions."""
    sanctions = SanctionManager.get_all_sanctions(limit=args.limit)

    if not sanctions:
        print("No sanctions found.")
        return

    print(f"\nFound {len(sanctions)} sanctions:\n")
    print(f"{'ID':<6} {'Type':<16} {'Username':<20} {'PlayFab ID':<20} {'Applied':<20} {'Revoked':<8}")
    print("-" * 110)

    for s in sanctions:
        applied = s.applied_at.strftime('%Y-%m-%d %H:%M') if s.applied_at else 'N/A'
        revoked = 'Yes' if s.revoked_at else 'No'
        username = (s.username or 'N/A')
        playfab_id = (s.playfab_id or 'N/A')
        print(f"{s.id:<6} {s.sanction_type:<16} {username[:20]:<20} {playfab_id[:20]:<20} {applied:<20} {revoked:<8}")


def cmd_search(args):
    """Search for sanctions."""
    sanctions = SanctionManager.search_sanctions(
        username=args.username,
        playfab_id=args.playfab_id,
        sanction_type=args.type,
        moderator_id=args.moderator,
        limit=args.limit
    )

    if not sanctions:
        print("No sanctions found matching the criteria.")
        return

    print(f"\nFound {len(sanctions)} matching sanctions:\n")
    for s in sanctions:
        print(f"ID: {s.id} | Type: {s.sanction_type}")
        print(f"  Player: {s.username or 'N/A'} ({s.playfab_id})")
        print(f"  Reason: {s.reason or 'N/A'}")
        print(f"  Applied: {s.applied_at}")
        print(f"  Revoked: {'Yes' if s.revoked_at else 'No'}")
        print()


def cmd_view(args):
    """View a specific sanction."""
    sanction = SanctionManager.get_sanction_by_id(args.id)

    if not sanction:
        print(f"Sanction with ID {args.id} not found.")
        return

    print(f"\nSanction Details (ID: {sanction.id}):")
    print(f"  Type: {sanction.sanction_type}")
    print(f"  Player: {sanction.username or 'N/A'}")
    print(f"  PlayFab ID: {sanction.playfab_id}")
    print(f"  Reason: {sanction.reason or 'N/A'}")

    if sanction.sanction_type == 'ban':
        print(f"  Duration: {sanction.duration_hours} hours")
        print(f"  Expires: {sanction.expires_at}" if sanction.expires_at else "  Expires: N/A")

    print(f"  Moderator: {sanction.moderator_name} ({sanction.moderator_id})")
    print(f"  Applied: {sanction.applied_at}")

    if sanction.revoked_at:
        print(f"  Revoked: {sanction.revoked_at}")
        print(f"  Revoked by: {sanction.revoked_by}")


def cmd_stats(_args):
    """Show database statistics."""
    sanction_stats = SanctionManager.get_statistics()
    redflag_stats = RedFlagManager.get_statistics()

    print("\nSanction Statistics:")
    print(f"  Total sanctions: {sanction_stats.get('total_sanctions', 0)}")
    print(f"  Total bans: {sanction_stats.get('total_bans', 0)}")
    print(f"  Total kicks: {sanction_stats.get('total_kicks', 0)}")
    print(f"  Revoked sanctions: {sanction_stats.get('revoked_sanctions', 0)}")

    print("\nRedFlag Statistics:")
    print(f"  Total redflags: {redflag_stats.get('total_redflags', 0)}")
    print(f"  Resolved redflags: {redflag_stats.get('resolved_redflags', 0)}")


def cmd_player_report(args):
    """Generate player report."""
    report = DatabaseUtils.generate_player_report(args.playfab_id)

    if report.get('total_sanctions', 0) == 0:
        print(f"No sanctions found for PlayFab ID: {args.playfab_id}")
        return

    print(f"\nPlayer Sanction Report:")
    print(f"  PlayFab ID: {report['playfab_id']}")
    print(f"  Username: {report['most_recent_username']}")
    print(f"  Total sanctions: {report['total_sanctions']}")
    print(f"  Total bans: {report['total_bans']}")
    print(f"  Total kicks: {report['total_kicks']}")
    print(f"  Revoked sanctions: {report['revoked_sanctions']}")
    print(f"  First sanction: {report['first_sanction']}")
    print(f"  Last sanction: {report['last_sanction']}")


def cmd_redflag_list(args):
    """List redflags."""
    redflags = RedFlagManager.get_all_redflags(limit=args.limit)

    if not redflags:
        print("No redflags found.")
        return

    print(f"\nFound {len(redflags)} redflags:\n")
    print(f"{'ID':<6} {'Username':<20} {'PlayFab ID':<20} {'Created':<20} {'Resolved':<8}")
    print("-" * 90)

    for r in redflags:
        created = r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else 'N/A'
        resolved = 'Yes' if r.resolved_at else 'No'
        username = (r.username or 'N/A')
        playfab_id = (r.playfab_id or 'N/A')
        print(f"{r.id:<6} {username[:20]:<20} {playfab_id[:20]:<20} {created:<20} {resolved:<8}")


def cmd_redflag_view(args):
    """View a specific redflag."""
    redflag = RedFlagManager.get_redflag_by_id(args.id)

    if not redflag:
        print(f"RedFlag with ID {args.id} not found.")
        return

    print(f"\nRedFlag Details (ID: {redflag.id}):")
    print(f"  Player: {redflag.username or 'N/A'}")
    print(f"  PlayFab ID: {redflag.playfab_id}")
    print(f"  Reason: {redflag.reason}")
    print(f"  Moderator: {redflag.moderator_name} ({redflag.moderator_id})")
    print(f"  Created: {redflag.created_at}")

    if redflag.resolved_at:
        print(f"  Resolved: {redflag.resolved_at}")
        print(f"  Resolved by: {redflag.resolved_by}")
        print(f"  Resolution note: {redflag.resolution_note}")


def cmd_redflag_player(args):
    """View all redflags for a player."""
    redflags = RedFlagManager.get_redflags_by_playfab_id(args.playfab_id)

    if not redflags:
        print(f"No redflags found for PlayFab ID: {args.playfab_id}")
        return

    print(f"\nFound {len(redflags)} redflags for {args.playfab_id}:\n")
    for r in redflags:
        print(f"ID: {r.id} | Resolved: {'Yes' if r.resolved_at else 'No'}")
        print(f"  Reason: {r.reason}")
        print(f"  Created: {r.created_at}")
        if r.resolved_at:
            print(f"  Resolved: {r.resolved_at}")
        print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='Sanction & RedFlag Database Management CLI')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # List command
    list_parser = subparsers.add_parser('list', help='List sanctions')
    list_parser.add_argument('--limit', type=int, default=50, help='Maximum number of results')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search for sanctions')
    search_parser.add_argument('--username', help='Search by username')
    search_parser.add_argument('--playfab-id', help='Search by PlayFab ID')
    search_parser.add_argument('--type', choices=['ban', 'kick'], help='Filter by sanction type')
    search_parser.add_argument('--moderator', help='Filter by moderator ID')
    search_parser.add_argument('--limit', type=int, default=50, help='Maximum number of results')

    # View command
    view_parser = subparsers.add_parser('view', help='View a specific sanction')
    view_parser.add_argument('id', type=int, help='Sanction ID')

    # Stats command
    subparsers.add_parser('stats', help='Show database statistics')

    # Player report command
    report_parser = subparsers.add_parser('player-report', help='Generate player sanction report')
    report_parser.add_argument('playfab_id', help='PlayFab ID of the player')

    # RedFlag commands
    redflag_list_parser = subparsers.add_parser('redflag-list', help='List redflags')
    redflag_list_parser.add_argument('--limit', type=int, default=50, help='Maximum number of results')

    redflag_view_parser = subparsers.add_parser('redflag-view', help='View a specific redflag')
    redflag_view_parser.add_argument('id', type=int, help='RedFlag ID')

    redflag_player_parser = subparsers.add_parser('redflag-player', help='View redflags for a player')
    redflag_player_parser.add_argument('playfab_id', help='PlayFab ID of the player')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize database
    db_config = get_database_config()
    if not db_config.test_connection():
        print("ERROR: Failed to connect to database!")
        return

    # Execute command
    commands = {
        'list': cmd_list,
        'search': cmd_search,
        'view': cmd_view,
        'stats': cmd_stats,
        'player-report': cmd_player_report,
        'redflag-list': cmd_redflag_list,
        'redflag-view': cmd_redflag_view,
        'redflag-player': cmd_redflag_player
    }

    if args.command in commands:
        commands[args.command](args)

    # Close database
    close_database()


if __name__ == '__main__':
    main()

