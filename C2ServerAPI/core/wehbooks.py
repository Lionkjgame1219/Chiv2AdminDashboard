import discord
from discord import SyncWebhook, Embed
import datetime
import os
from PyQt5.QtWidgets import QInputDialog, QMessageBox, QApplication

webhook_primary = None
webhook_secondary = None

def load_config_from_file():
    """Load configuration from localconfig file"""
    localconfig = "localconfig"

    config = {
        'primary_url': None,
        'secondary_url': None,
        'discord_user_id': None,
        'file_exists': False
    }

    if os.path.exists(localconfig):
        config['file_exists'] = True
        try:
            with open(localconfig, 'r', encoding='utf-8') as f:
                lines = f.read().strip().split('\n')
                if len(lines) >= 1 and lines[0] != "None":
                    if lines[0].startswith("https://discord.com/api/webhooks/"):
                        config['primary_url'] = lines[0]
                if len(lines) >= 2 and lines[1] != "None":
                    if lines[1].startswith("https://discord.com/api/webhooks/"):
                        config['secondary_url'] = lines[1]
                if len(lines) >= 3 and lines[2] != "None":
                    config['discord_user_id'] = lines[2]
        except Exception:
            pass

    return config

def get_webhook_urls():
    """Get Discord webhook URLs using the correct startup flow"""
    config = load_config_from_file()

    if config['file_exists']:
        return config['primary_url'], config['secondary_url']

    if not config['file_exists']:
        return prompt_for_initial_setup()

    return config['primary_url'], config['secondary_url']

def prompt_for_initial_setup():
    """Prompt user for initial webhook and Discord ID setup"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        temp_app = True
    else:
        temp_app = False

    try:
        primary_url, ok = QInputDialog.getText(
            None,
            "Initial Setup - Primary Discord Webhook",
            "Please enter your primary Discord Webhook URL:\n"
            "(Leave empty to disable Discord notifications)",
            text=""
        )

        if not ok:
            save_initial_config(None, None, None)
            return None, None

        primary_url = primary_url.strip()
        if primary_url and not primary_url.startswith("https://discord.com/api/webhooks/"):
            QMessageBox.warning(
                None,
                "Invalid URL",
                "Discord webhook URL must start with:\n"
                "https://discord.com/api/webhooks/\n\n"
                "The program will continue running. You can configure\n"
                "the webhook later using the configuration button."
            )
            save_initial_config(None, None, None)
            return None, None

        primary_url = primary_url if primary_url else None
        secondary_url = None
        discord_user_id = None

        if primary_url:
            secondary_url_input, ok2 = QInputDialog.getText(
                None,
                "Initial Setup - Secondary Discord Webhook",
                "Please enter your secondary Discord Webhook URL (optional):\n"
                "(Leave empty to use only the primary webhook)",
                text=""
            )

            if ok2 and secondary_url_input.strip():
                secondary_url_input = secondary_url_input.strip()
                if secondary_url_input.startswith("https://discord.com/api/webhooks/"):
                    secondary_url = secondary_url_input
                else:
                    QMessageBox.warning(
                        None,
                        "Invalid Secondary URL",
                        "Secondary Discord webhook URL must start with:\n"
                        "https://discord.com/api/webhooks/\n\n"
                        "Only the primary webhook will be configured."
                    )

            discord_user_id, ok3 = QInputDialog.getText(
                None,
                "Initial Setup - Discord User ID",
                "Please enter your Discord User ID:\n"
                "(This will be used for @mentions in notifications)\n"
                "(Leave empty to skip)",
                text=""
            )

            if ok3:
                discord_user_id = discord_user_id.strip() if discord_user_id.strip() else None

        save_initial_config(primary_url, secondary_url, discord_user_id)

        return primary_url, secondary_url

    finally:
        if temp_app:
            app.quit()

def save_initial_config(primary_url, secondary_url, discord_user_id):
    """Save initial configuration to localconfig file"""
    localconfig = "localconfig"
    try:
        with open(localconfig, 'w', encoding='utf-8') as f:
            f.write(f"{primary_url if primary_url else 'None'}\n")
            f.write(f"{secondary_url if secondary_url else 'None'}\n")
            f.write(f"{discord_user_id if discord_user_id else 'None'}\n")
            for _ in range(10):
                f.write("\n")
            f.write("dark\n")
    except Exception as e:
        QMessageBox.warning(
            None,
            "Save Error",
            f"Unable to save initial configuration:\n{str(e)}"
        )

    return primary_url, secondary_url

def initialize_webhook():
    """Initialize the Discord webhooks"""
    global webhook_primary, webhook_secondary
    primary_url, secondary_url = get_webhook_urls()

    primary_success = False
    secondary_success = False

    if primary_url:
        try:
            webhook_primary = SyncWebhook.from_url(primary_url)
            primary_success = True
        except Exception as e:
            app = QApplication.instance()
            if app:
                QMessageBox.warning(
                    None,
                    "Primary Webhook Error",
                    f"Unable to initialize primary Discord webhook:\n{str(e)}"
                )
            webhook_primary = None
    else:
        webhook_primary = None

    if secondary_url:
        try:
            webhook_secondary = SyncWebhook.from_url(secondary_url)
            secondary_success = True
        except Exception as e:
            app = QApplication.instance()
            if app:
                QMessageBox.warning(
                    None,
                    "Secondary Webhook Error",
                    f"Unable to initialize secondary Discord webhook:\n{str(e)}"
                )
            webhook_secondary = None
    else:
        webhook_secondary = None

    return primary_success or secondary_success

def get_webhook_status():
    """Get the current status of both webhooks"""
    return {
        'primary_active': webhook_primary is not None,
        'secondary_active': webhook_secondary is not None,
        'any_active': webhook_primary is not None or webhook_secondary is not None
    }

def MessageForAdmin(user_id, username, reason, duration_or_msg, category):
    if webhook_primary is None and webhook_secondary is None:
        print(f"[WEBHOOK] Discord webhooks not configured, skipping notification for {category}")
        return

    config = load_config_from_file()
    moderator_id = config['discord_user_id'] if config['discord_user_id'] else "Unknown"

    embed = Embed(
        title="Admin Log Notification",
        color=0xF52D05,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    if category == "ban":
        embed.description = "A **ban** has been executed"
        embed.add_field(
            name="Information",
            value=f"\nPlayFabID: {user_id}\nUsername: {username}\nReason: {reason}\nDuration: {duration_or_msg}h",
            inline=False
        )

    elif category == "unban":
        embed.description = "An **unban** has been executed"
        embed.add_field(
            name="Information",
            value=f"\nPlayFabID: {user_id}",
            inline=False
        )

    elif category == "kick":
        embed.description = "A **kick** has been executed"
        embed.add_field(
            name="Information",
            value=f"\nPlayFabID: {user_id}\nUsername: {username}\nReason: {reason}",
            inline=False
        )

    elif category == "ft":
        embed.description = "A **First To match** has been completed"
        embed.add_field(
            name="Results",
            value=f"\n{reason}",
            inline=False
        )

    if category != "ft":
        embed.add_field(name="Moderator",
                        value=f"<@{moderator_id}>",
                        inline=False)
    else:
        embed.add_field(name="Referee",
                        value=f"<@{moderator_id}>",
                        inline=False)

    embed.set_footer(text="AdminDashboard")

    if webhook_primary:
        try:
            webhook_primary.send(username="Admin Bot", embed=embed)
            print(f"[WEBHOOK] Primary Discord notification sent for {category}")
        except Exception as e:
            print(f"[WEBHOOK] Failed to send primary Discord notification: {str(e)}")

    if webhook_secondary:
        try:
            webhook_secondary.send(username="Admin Bot", embed=embed)
            print(f"[WEBHOOK] Secondary Discord notification sent for {category}")
        except Exception as e:
            print(f"[WEBHOOK] Failed to send secondary Discord notification: {str(e)}")

