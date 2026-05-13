# Chivalry 2 GUI Server Moderation Panel

## **This program is only meant to work on Windows systems for now, future Linux support _might_ come someday**_, or not..._

### Setup

**This section is only of interest if you plan to work with the source files directly. If you plan to use the compiled version from the [releases page](https://github.com/Lionkjgame1219/ModerationOVALOGICIEL/releases), you can skip this part.**

Make sure to have all of the required Python libraries for the GUI (no OCR needed):
```
pip install PyQt5
pip install pyperclip
pip install pywin32
pip install discord.py
```

Normally, everything should be working from there.

To run the script, you can run this command into a terminal, either using **cmd** or **powershell**, **within the "C2ServerAPI" folder**:
```
python interface.py
```

If you want to compile the script to a .exe file (GUI only), run from the C2ServerAPI folder:
```
py versionmetadata.py
pyinstaller --onefile --noconsole --icon=[PathToAn".ico"Image] --name=[NameOfTheCompiledProgram] --version-file build\versionfile.txt --add-data "core;core" --hidden-import pyperclip --hidden-import PyQt5.QtWidgets --hidden-import PyQt5.QtGui --hidden-import PyQt5.QtCore --hidden-import=discord --hidden-import=win32gui --hidden-import=win32con --hidden-import=win32process --hidden-import=win32api interface.py
```

### First launch

---------

***Disclaimer : Due to how Chivalry 2 client API is *(inexisting)*, the program is working by directly simulating keyboard presses into your game to type commands in your console.***

***By using this method, the program will sort of "block" your inputs until the command processing is done.***

***It should be pretty quick (between one and five seconds at most), but still noticeable.***

***Sending inputs on your side (pressing keys on your keyboard) will either, do nothing, or just introduce bugs, so please let the program be done with the command processing before trying to do anything in the game.***

---------

- On launch, if Chivalry 2 is not already running, you will be greeted by a waiting dialog that pings every second for the game window. You can either let it wait, skip it manually, or use the **"Launch via Steam"**, **"Launch via Epic Games"** or **"Launch via Xbox"** shortcut buttons to start the game directly from the dashboard.

  <img width="518" height="388" alt="image" src="https://github.com/user-attachments/assets/669323dc-d1b3-48eb-9dd8-3de9acb24be9" />

- The compiled version of the program will also check GitHub for a new release at startup. If one is available, it will silently download and apply it before relaunching itself, so you should always be running the latest version without any manual intervention. After an autoupdate, a **"What's new?"** dialog will pop up on the next launch to display the release notes of the version that was just installed.

- As soon as you will open up the program, you will be prompted to add a Discord Webhook link, so that the script can send a message in the channel of your Webhook for every action you made.

  Useful for keeping a per server history of bans, allowing anyone to review the name of the person who did the action, the duration and the reason of a kick / ban, and the PlayFabID, in case you want to undo a ban.

  If you don't have a link, either create one in the server settings (for the server that will be notified), and create a Webhook in "**Server settings** -> **Integrations** -> **Webhooks** -> **New webhook**".

  Be sure to select the proper channel in which the notifications will be sent to.

  Note that it is possible to set a second Webhook link. Can be used to send the same notifications to another server, in case you want to have a discord server with a ban history shared to another clan or in-game server owner.

- Then, you will be prompted to enter your Discord ID (only if you're using Webhooks). Necessary to let the bot know that **you** did the command.

  Here's how to find it :

  Get into your discord window, go to "**User settings**", then scroll down to find "**Advanced**", and then, **enable** "**Developer mode*".

  With that done, get out of the settings menu, right click on your name **within any chat or server member list**, and click on the last option, which should be something like "**Copy user ID**".

  This ID is the one you need to enter.

### Once everything is done

You will now have access to the dashboard. Everything should be pretty straightforward.

<img width="1400" height="1132" alt="image" src="https://github.com/user-attachments/assets/b60a9fef-aa48-401e-ae7e-26773741c6ff" />

- **"Players List"** is going to open up a new window, in which you are gonna have an empty board and a button to refresh the list of all the players connected to the server you are currently playing on.

  After the board is populated, you can click on a player to have access to five buttons, and the right side of the window will display the full sanction history of the selected player (pulled from the Discord logs scrapping feature described further below) :

   1. One for banning him, which will ask you for every informations needed for the ban.

      Required informations are :

         a - Ban duration **(in hours)**

         b - Ban reason **(e.g. "This is a duel server, FFA / RDM is prohibited.")**

      You can use quick preset buttons to quickly apply a ban for the most common reasons (FFA 24h, FFA permaban, and cheating permaban).      

   2. Another one to simply kick him. Only a reason is gonna be required, not a duration (kicking via command has no duration, the player can come back right after).

---------

   Note : By default, an adminsay message will also be broadcasted in the game to notify of a kick or a ban. The tickbox "Notify in-game" can be unchecked to prevent that, but a discord notification will still be sent if a webhook has been configured.
   
---------

   3. The third is a Discord-only action. It is meant to record a soft warning or any comment about the player that you want future-you (or other admins watching the same Discord channel) to see when this player is met again. The most recent note within the last 30 days is pinned at the top of the sanction history panel as an "Active Note", which makes repeat offenders easy to spot at a glance.

   4. The fourth button is gonna be a redirect link to the player's tracker profile on the website **"chivalry2stats.com"**, the most visited site for this matter. Useful to find any old username associated to the player's account.

   5. And the fifth will just let you copy in your clipboard the player's PlayFabID.

Next buttons in the main dashboard :

- **"Add Time"** is just a button to add time to the map. Note that you can provide a negative value to substract time to the map.
(e.g. "-10" to substract 10 minutes)

- **"Unban Player"** is gonna open up a small window in which you can enter a PlayFabID to execute an unban and write a serversay message to confirm the effectiveness of the action.


- **"Match Arbitration"** is a menu that allow you to act as a referee in a match. Here are the options :

  a - **Rounds to win** let's you configure the number of rounds to win before declaring the end of the match.

  b - **Start message** allow you to setup a serversay message that will just tell everyone that the match is starting.
 
  c - **End message** is the same, but for when a player / a team wins the match.
 
  d - **Tag prefix** let's you insert a tag for every messages sent in the context of the match arbitration (e.g. (Tournament) Player 1 : 3 - 1 : Player 2).
 
  e - **Announce the start of the match** is pretty self-explanatory.

  f - **Broadcast match results to Discord** allows you to specify if a discord notification should be sent to the channel linked to the webhook(s) you entered, if any.
 
  g - **Name** let's you provide the names of the players / teams participating.
 
  h - **Add / Remove 1 Point**, do I really need to explain ?
 
  i - **Reset score** let's you set the score to 0 - 0.
 
  j - **Reset board** allow you reset every options listed above.

- **New** - **"Random Pick"** is a companion button to Match Arbitration. It opens a window with two editable tables (a weapon pool and a player pool) and rolls a random pairing on demand. Useful for any "pick a weapon" / "pick a duelist" style of tournament or warm-up :

   - The weapon pool stores a per-row hand tag (1H / 2H) and a per-row "Exclude" flag so you can keep a weapon in the list but skip it from the current roll.
   - The player pool is the same idea, just with a single "Exclude" column.
   - **"One-handed only"** and **"Two-handed only"** are global filters that restrict the weapon pool for the current roll.
   - **"Assign weapon (1 Player)"** rolls one weapon for one player. **"Assign weapons (2 Players)"** rolls two distinct weapons for two distinct players.
   - The result can be broadcasted to the server through a serversay message directly from the dialog.
   - Both tables (and the filters) are persisted between launches, so your roster doesn't have to be rebuilt every time.

Let's get back to the main dashboard.

- **"Admin Message"** is going to be sending an "adminsay" command, along with the text you provided.

- **"Server Message"** is basically the same as the admin one, but using the "serversay" command instead.

- **"Configure Discord Webhook"** is here if need to update or remove a webhook link you provided previously. You can also add one if you never provided it.

- **"Configure Discord User ID"** is also made to add, update, or remove your Discord User ID.

- **"Set Discord Bot Token"** and **"Set Discord Channel ID"** are the two pieces of configuration needed to enable the Discord logs scrapping feature (detailed in its own section below). The token is the secret of any Discord bot you've invited to your server with read access on the channel where the dashboard's webhooks land; the channel ID is the numeric ID of that very channel (right-click the channel with developer mode enabled, then "Copy Channel ID"). Leave either empty to disable the feature.

- **"Fetch Discord Channel Messages"** triggers a manual scrap of the configured Discord channel. A progress dialog is displayed while the scrap is running. You normally won't need to click it yourself, since the dashboard also runs silent auto-scraps at startup and a couple of seconds after each kick / ban / note, but it is here in case you need to force a refresh (e.g. you just imported a backlog of old logs).

- **"Configure Console Key"** is here if you need to change the key used to open the in-game console.

- **"Light / Dark Mode"** is just here for your visual comfort, so if, for some reason, you desire to get flashbanged, all of a sudden, you are free to.

   Can also be used to enlighten your bedroom, since Chiv server mods are known to live in darkness and loneliness.

### Presets usage

For kicks, bans, admin messages, and server messages, you can use preset slots to save and quickly retrieve sentences.

Let's imagine you want to save the sentence "This is a duel server, FFA / RDM is prohibited." as a server message preset.

You would type the sentence in the "Server Message" input text box, and then click on the "Save / Overwrite" button in any slot you want. For the sake of the example, let's say you want to save it in slot 0.

Now, the "Load button" will turn to the green color, which means something is saved in this slot.

Whenever you want to send this message again, you can simply click on the "Load" button in the "Slot 0" column, and the message will be automatically filled in the input text box. You can then simply click on the "Send Server Message" button to send the message.

Note that you can hover your cursor over a "Load" button to see what's the text saved into the slot.

Same concept applies to the presets used for kicks and bans. Note that ban presets also saves the ban duration, along with the reason.

### Discord logs scrapping

The dashboard can read back the webhook messages it has sent over time and build a local sanction history out of them. Once enabled, every kick / ban / note / unban / arbitration message that has ever been posted by your dashboard in the configured channel will be parsed, deduplicated, and cached locally.

This unlocks two main features :

- **Per-player sanction history** : right column of the player action panel. As soon as you click a player in the Players List, the panel will display every recorded sanction against that PlayFabID, with the most recent note within the last 30 days pinned at the top as an "Active Note".

- **"Sanction History"** button on the main dashboard : opens a full-history search dialog where you can filter all the cached records by Username and/or PlayFabID. Useful for browsing the historical record without having to first refresh the Players List or know who you're looking for in advance.

To enable the feature, you need to provide two values via the Settings panel :

   1. A **Discord Bot Token** (**"Set Discord Bot Token"**). The bot only needs read access to the log channel — no other permission or message intent is required on the dashboard's side.

   2. The **numeric ID of the log channel** (**"Set Discord Channel ID"**). To copy it, enable Developer Mode in Discord (User Settings -> Advanced -> Developer Mode), then right-click the channel and click "Copy Channel ID".

Once both are set, the scrapping process runs automatically (silently in the background) at startup and shortly after every action you do, so the sanction history stays in sync without any manual click. You can still trigger a manual scrap with the **"Fetch Discord Channel Messages"** button if needed.