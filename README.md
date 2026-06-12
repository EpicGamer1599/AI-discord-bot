# AI-discord-bot

An AI Discord bot that uses gemini-groq to talk to Discord members via `!ask`.

# What You'll Need

- Computer
- Python
- Windows/Linux (maybe macOS)
- Internet or a network to host the bot

# How to Install It

Go and download Python from here:

https://www.python.org/downloads/

After installing, open CMD on your computer or Terminal, then run this command to install everything you need to run this bot:

```bash
pip install discord.py groq python-dotenv duckduckgo-search google-generativeai
```

After that, make a folder where you're going to store `bot.py`, `.env`, etc.

Put `bot.py` in that folder and make a file named `.env` in the same folder.

Put this inside that blank `.env` file:

```env
DISCORD_TOKEN=(TOKENHERE)
GROQ_API_KEY=(TOKENHERE)
GEMINI_API_KEY=(TOKENHERE)
```

Everything is almost set up, but you do need to set up the Discord bot, so get ready!

## Making the Discord Bot

Go here to make the Discord bot:

https://discord.com/developers/applications

Press **Agree**, then press **"New Application"**.

Name your bot something. I would call it **"AI Bot"**.

Go to the **Bot** section and give it a profile picture and banner if you have one (optional).

Go to the **OAuth** section on the left and scroll until **"OAuth2 URL Generator"**. Press the **BOT** button only.

Under that, enable these permissions:

- ✅ View Channels
- ✅ Send Messages
- ✅ Read Message History

Then there should be a link. Copy it, but don't paste it yet.

On the left side, press **Bot**, then enable:

- ✅ MESSAGE CONTENT INTENT
- ✅ SERVER MEMBERS INTENT
- ✅ PRESENCE INTENT

These permissions are needed for the bot to work.

Make a new tab and paste that link in. It will ask you what server it should be added to. Select the server it should join.

Now go back to your application and go to the **Bot** section.

Press **Reset Token**. This requires you to type your password or complete other verification.

Then you'll get a massive line of text.

> ⚠️ **DO NOT SEND THESE WORDS TO OTHERS. THIS IS YOUR BOT TOKEN.** ⚠️

Put that token in `DISCORD_TOKEN=(TOKENHERE)` and replace `(TOKENHERE)` with your Discord token.

## Getting Your Groq Token

Go to:

https://console.groq.com/keys

You'll be asked to sign in with your email.

When you're on the page, press **"Create API Key"**.

Name it something, for example:

`Discord Bot`

Make it never expire.

You should get a new key.

> ⚠️ **DO NOT SEND THESE WORDS TO OTHERS. THIS IS YOUR GROQ TOKEN.** ⚠️

Put that token in the `.env` file, replacing `(TOKENHERE)` for `GROQ_API_KEY`.

## Getting Your Gemini Key

Make sure you're logged into a Google account.

Go to:

https://aistudio.google.com/app/api-keys

After logging in, press **"Create an API Key"**.

Name it something, and if you want to spend money on this bot, get a paid model.

After creating the key, it should give you a random string of characters.

> ⚠️ **DO NOT SEND THESE WORDS TO OTHERS. THIS IS YOUR GEMINI TOKEN.** ⚠️

Replace `(TOKENHERE)` in the `.env` file for `GEMINI_API_KEY`.

# Done!

After you have done all of this, double-click the `.py` file. It should open the console, and everything should have gone to plan. :D

If you have any issues, contact me for help. :3
