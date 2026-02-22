"""Demo script for the sanction and redflag database system.

This script demonstrates how to use the database manager to create,
retrieve, update, and manage sanctions (bans and kicks) and redflags.
"""

from database_manager import SanctionManager, RedFlagManager
from database_config import get_database_config, close_database


def demo_create_sanctions():
    """Demonstrate creating sanctions (bans and kicks)."""
    print("\n=== Creating Sanctions ===")

    # Create a temporary ban
    ban = SanctionManager.create_sanction(
        sanction_type='ban',
        playfab_id='ABC123456789',
        username='PlayerOne',
        reason='FFA on duel server',
        duration_hours=24.0,
        moderator_id='123456789012345678',
        moderator_name='ModeratorName'
    )

    if ban:
        print(f"Created ban: {ban}")

    # Create a kick
    kick = SanctionManager.create_sanction(
        sanction_type='kick',
        playfab_id='DEF987654321',
        username='PlayerTwo',
        reason='Inappropriate language',
        moderator_id='123456789012345678',
        moderator_name='ModeratorName'
    )

    if kick:
        print(f"Created kick: {kick}")

    # Create a long-term ban
    long_ban = SanctionManager.create_sanction(
        sanction_type='ban',
        playfab_id='GHI111222333',
        username='Cheater123',
        reason='Cheating/Hacking',
        duration_hours=999999.0,
        moderator_id='123456789012345678',
        moderator_name='ModeratorName'
    )

    if long_ban:
        print(f"Created long-term ban: {long_ban}")


def demo_retrieve_sanctions():
    """Demonstrate retrieving sanctions."""
    print("\n=== Retrieving Sanctions ===")

    # Get all sanctions
    all_sanctions = SanctionManager.get_all_sanctions(limit=10)
    print(f"\nTotal sanctions (limited to 10): {len(all_sanctions)}")
    for sanction in all_sanctions:
        print(f"  - {sanction}")

    # Get sanctions for a specific player
    player_sanctions = SanctionManager.get_sanctions_by_playfab_id('ABC123456789')
    print(f"\nSanctions for player ABC123456789: {len(player_sanctions)}")
    for sanction in player_sanctions:
        print(f"  - {sanction}")


def demo_search_sanctions():
    """Demonstrate searching for sanctions."""
    print("\n=== Searching Sanctions ===")

    # Search by username
    results = SanctionManager.search_sanctions(username='Player')
    print(f"\nSearch results for username containing 'Player': {len(results)}")

    # Search for bans only
    bans = SanctionManager.search_sanctions(sanction_type='ban')
    print(f"\nBans only: {len(bans)}")

    # Search for kicks only
    kicks = SanctionManager.search_sanctions(sanction_type='kick')
    print(f"\nKicks only: {len(kicks)}")

    # Search by moderator
    mod_sanctions = SanctionManager.search_sanctions(moderator_id='123456789012345678')
    print(f"\nSanctions by moderator 123456789012345678: {len(mod_sanctions)}")


def demo_revoke():
    """Demonstrate revoking sanctions."""
    print("\n=== Revoking Sanctions ===")

    # Get a sanction to work with
    sanctions = SanctionManager.get_all_sanctions(limit=1)
    if not sanctions:
        print("No sanctions available to revoke")
        return

    sanction = sanctions[0]
    print(f"\nWorking with sanction: {sanction}")

    # Revoke the sanction
    success = SanctionManager.revoke_sanction(
        sanction.id,
        revoked_by='987654321098765432'
    )
    print(f"Revoke successful: {success}")


def demo_create_redflags():
    """Demonstrate creating redflags."""
    print("\n=== Creating RedFlags ===")

    # Create a redflag
    redflag = RedFlagManager.create_redflag(
        playfab_id='JKL444555666',
        username='SuspiciousPlayer',
        reason='Potential griefing behavior - needs monitoring',
        moderator_id='123456789012345678',
        moderator_name='ModeratorName'
    )

    if redflag:
        print(f"Created redflag: {redflag}")

    # Create another redflag
    redflag2 = RedFlagManager.create_redflag(
        playfab_id='MNO777888999',
        username='ToxicPlayer',
        reason='Multiple complaints about behavior',
        moderator_id='123456789012345678',
        moderator_name='ModeratorName'
    )

    if redflag2:
        print(f"Created redflag: {redflag2}")


def demo_retrieve_redflags():
    """Demonstrate retrieving redflags."""
    print("\n=== Retrieving RedFlags ===")

    # Get all redflags
    all_redflags = RedFlagManager.get_all_redflags(limit=10)
    print(f"\nTotal redflags (limited to 10): {len(all_redflags)}")
    for redflag in all_redflags:
        print(f"  - {redflag}")


def demo_resolve_redflag():
    """Demonstrate resolving a redflag."""
    print("\n=== Resolving RedFlags ===")

    # Get a redflag to work with
    redflags = RedFlagManager.get_all_redflags(limit=1)
    if not redflags:
        print("No redflags available to resolve")
        return

    redflag = redflags[0]
    print(f"\nWorking with redflag: {redflag}")

    # Resolve the redflag
    success = RedFlagManager.resolve_redflag(
        redflag.id,
        resolved_by='987654321098765432',
        resolution_note='Player behavior improved after warning'
    )
    print(f"Resolve successful: {success}")


def demo_statistics():
    """Demonstrate getting statistics."""
    print("\n=== Database Statistics ===")

    sanction_stats = SanctionManager.get_statistics()
    print("\nSanction Statistics:")
    for key, value in sanction_stats.items():
        print(f"  {key}: {value}")

    redflag_stats = RedFlagManager.get_statistics()
    print("\nRedFlag Statistics:")
    for key, value in redflag_stats.items():
        print(f"  {key}: {value}")


def main():
    """Run all demonstrations."""
    print("=" * 60)
    print("Sanction & RedFlag Database System Demo")
    print("=" * 60)

    # Initialize database
    db_config = get_database_config(echo=False)

    # Test connection
    if not db_config.test_connection():
        print("Failed to connect to database!")
        return

    print("\nDatabase connection successful!")

    # Run demonstrations
    demo_create_sanctions()
    demo_retrieve_sanctions()
    demo_search_sanctions()
    demo_revoke()
    demo_create_redflags()
    demo_retrieve_redflags()
    demo_resolve_redflag()
    demo_statistics()

    # Close database
    close_database()

    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)


if __name__ == '__main__':
    main()

