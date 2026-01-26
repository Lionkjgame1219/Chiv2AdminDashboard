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
pyinstaller --onefile --noconsole --icon=[PathToAn".ico"Image] --name=[NameOfTheCompiledProgram] --add-data "core;core" --hidden-import pyperclip --hidden-import PyQt5.QtWidgets --hidden-import PyQt5.QtGui --hidden-import PyQt5.QtCore --hidden-import=discord --hidden-import=win32gui --hidden-import=win32con --hidden-import=win32process --hidden-import=win32api interface.py
```

### First launch

---------

***Disclaimer : Due to how Chivalry 2 client API is *(inexisting)*, the program is working by directly simulating keyboard presses into your game to type commands in your console.***

***By using this method, the program will sort of "block" your inputs until the command processing is done.***

***It should be pretty quick (between one and five seconds at most), but still noticeable.***

***Sending inputs on your side (pressing keys on your keyboard) will either, do nothing, or just introduce bugs, so please let the program be done with the command processing before trying to do anything in the game.***

---------

- As soon as you will open up the program, you will be prompted to add a Discord Webhook link, so that the script can send a message in the channel of your Webhook for every action you made.

  <img width="896" height="160" alt="image" src="https://github.com/user-attachments/assets/146dd603-8d89-43d6-86e6-efcb44a18a5c" />

  <img width="896" height="159" alt="image" src="https://github.com/user-attachments/assets/bc2f2a30-82fe-4a01-8bb3-98547332d196" />

  Useful for keeping a per server history of bans, allowing anyone to review the name of the person who did the action, the duration and the reason of a kick / ban, and the PlayFabID, in case you want to undo a ban.

  If you don't have a link, either create one in the server settings (for the server that will be notified), and create a Webhook in "**Server settings** -> **Integrations** -> **Webhooks** -> **New webhook**".

  Be sure to select the proper channel in which the notifications will be sent to.

  Note that it is possible to set a second Webhook link. Can be used to send the same notifications to another server, in case you want to have a discord server with a ban history shared to another clan or in-game server owner.

- Then, you will be prompted to enter your Discord ID (only if you're using Webhooks). Necessary to let the bot know that **you** did the command.

  <img width="249" height="174" alt="image" src="https://github.com/user-attachments/assets/9c1ff164-7b82-40d7-9353-b9179e5960b7" />

  Here's how to find it :

  Get into your discord window, go to "**User settings**", then scroll down to find "**Advanced**", and then, **enable** "**Developer mode*".

  With that done, get out of the settings menu, right click on your name **within any chat or server member list**, and click on the last option, which should be something like "**Copy user ID**".

  This ID is the one you need to enter.

### Once everything is done

You will now have access to the dashboard. Everything should be pretty straightforward.

<img width="1398" height="836" alt="image" src="https://github.com/user-attachments/assets/3d35ea77-4746-4baf-ab72-9c1b94ffb5ba" />

- **"Players List"** is going to open up a new window, in which you are gonna have an empty board and a button to refresh the list of all the players connected to the server you are currently playing on.

   <img width="596" height="831" alt="image" src="https://github.com/user-attachments/assets/5f8edc12-2039-4b5b-b114-9f837605e40e" />

---------

   This feature may, sometimes, not work at every refreshes.   
   
---------

  After the board is populated, you can click on a player to have access to three buttons :

  <img width="378" height="238" alt="image" src="https://github.com/user-attachments/assets/f4098304-c866-4068-8799-a226497c08c0" />  

   1. One for banning him, which will ask you for every informations needed for the ban.

      Required informations are :

         a - Ban duration **(in hours)**

         b - Ban reason **(e.g. "This is a duel server, FFA / RDM is prohibited.")**

      <img width="464" height="526" alt="image" src="https://github.com/user-attachments/assets/d5cc85aa-ec32-4d7b-94a5-0792ea683fb9" />

      **New** - You can now use three quick preset buttons to quickly apply a ban for the most common reasons (FFA 24h, FFA permaban, and cheating permaban).
      

   2. Another one to simply kick him. Only a reason is gonna be required, not a duration (kicking via command has no duration, the player can come back right after).

      <img width="463" height="486" alt="image" src="https://github.com/user-attachments/assets/7c922f41-a045-4c88-8673-9dcbe19cc6d5" />   

---------

   Note : By default, an adminsay message will also be broadcasted in the game to notify of a kick or a ban. The tickbox "Notify in-game" can be unchecked to prevent that, but a discord notification will still be sent if a webhook has been configured.
   
---------

   3. The third button is gonna be a redirect link to the player's tracker profile on the website **"chivalry2stats.com"**, the most visited site for this matter. Useful to find any old username associated to the player's account.

   4. And the forth will just let you copy in your clipboard the player's PlayFabID.

Next buttons in the main dashboard :

- **"Add Time"** is just a button to add time to the map. Note that you can provide a negative value to substract time to the map.
(e.g. "-10" to substract 10 minutes)

   <img width="259" height="130" alt="image" src="https://github.com/user-attachments/assets/4c59d75d-6b20-4794-b1cc-cb611073352b" />

- **New** - **"Unban Player"** is gonna open up a small window in which you can enter a PlayFabID to execute an unban and write a serversay message to confirm the effectiveness of the action.


- **"Match Arbitration"** is a menu that allow you to act as a referee in a match. Here are the options :

   <img width="1097" height="733" alt="image" src="https://github.com/user-attachments/assets/4d6936b9-bf42-40c0-9575-3f26e92669bf" />

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

Let's get back to the main dashboard.

- **"Admin Message"** is going to be sending an "adminsay" command, along with the text you provided.

   <img width="676" height="262" alt="image" src="https://github.com/user-attachments/assets/74d05f32-4ed0-45b6-ae0f-36dc68323e94" />

- **"Server Message"** is basically the same as the admin one, but using the "serversay" command instead.

   <img width="677" height="263" alt="image" src="https://github.com/user-attachments/assets/d1ebd53b-16ec-4872-82cb-fbf64728c6f3" />

- **"Configure Discord Webhook"** is here if need to update or remove a webhook link you provided previously. You can also add one if you never provided it.

   <img width="896" height="160" alt="image" src="https://github.com/user-attachments/assets/146dd603-8d89-43d6-86e6-efcb44a18a5c" />

   <img width="896" height="159" alt="image" src="https://github.com/user-attachments/assets/bc2f2a30-82fe-4a01-8bb3-98547332d196" />

- **"Configure Discord User ID"** is also made to add, update, or remove your Discord User ID.

   <img width="249" height="174" alt="image" src="https://github.com/user-attachments/assets/9c1ff164-7b82-40d7-9353-b9179e5960b7" />

- **"Configure Console Key"** is here if you need to change the key used to open the in-game console.

   <img width="418" height="211" alt="image" src="https://github.com/user-attachments/assets/f31bfd77-c185-4b6f-b605-b494b0efb220" />

- **"Light / Dark Mode"** is just here for your visual comfort, so if, for some reason, you desire to get flashbanged, all of a sudden, you are free to.

   <img width="1396" height="833" alt="image" src="https://github.com/user-attachments/assets/cc6bf5d9-bf76-4bd6-b9eb-a8f9f298fec9" />

   Can also be used to enlighten your bedroom, since Chiv server mods are known to live in darkness and loneliness.

### Presets usage

For kicks, bans, admin messages, and server messages, you can use preset slots to save and quickly retrieve sentences.

Let's imagine you want to save the sentence "This is a duel server, FFA / RDM is prohibited." as a server message preset.

<img width="673" height="259" alt="image" src="https://github.com/user-attachments/assets/a1f58e1e-858c-4728-97f5-8c1148d66f37" />

You would type the sentence in the "Server Message" input text box, and then click on the "Save / Overwrite" button in any slot you want. For the sake of the example, let's say you want to save it in slot 0.

<img width="331" height="136" alt="image" src="https://github.com/user-attachments/assets/57f0952b-1ac0-43c2-8132-cf39d5b97ae2" />

Now, the "Load button" will turn to the green color, which means something is saved in this slot.

<img width="216" height="64" alt="image" src="https://github.com/user-attachments/assets/435cb714-4f43-43a6-a935-b0294c41554f" />

Whenever you want to send this message again, you can simply click on the "Load" button in the "Slot 0" column, and the message will be automatically filled in the input text box. You can then simply click on the "Send Server Message" button to send the message.

<img width="302" height="137" alt="image" src="https://github.com/user-attachments/assets/0a996f26-e44d-4ed2-a549-53e281339290" />

Note that you can hover your cursor over a "Load" button to see what's the text saved into the slot.

<img width="496" height="80" alt="image" src="https://github.com/user-attachments/assets/85159b2f-ab61-4c4a-9be7-890c6daf2963" />

Same concept applies to the presets used for kicks and bans. Note that ban presets also saves the ban duration, along with the reason.

### Features planned for possible future releases

1. Toggleable automated player list refreshes (would also act as an anti-idle bot, bonus feature)

2. ???