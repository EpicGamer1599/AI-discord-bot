# AI-discord-bot
A AI discord bot that uses gemini-groq to talk to discord members via !ask

# What youll need
> Computer
> Python
> Windows/Linux (maybe macos)
> Internet or network to host the bot

# How to install it
Go to and download python from here - https://www.python.org/downloads/ -
After installing open CMD on your computer or terminal
then run this command to install everything you need to run this bot here - pip install discord.py groq python-dotenv duckduckgo-search google-generativeai -
After that make a folder where your going to store bot.py .env etc etc
put bot.py and .env into that folder
EVERYTHING is almost setup BUT you do need to set up the env file soo get ready!

# Setting up the .ENV file
Go here to make the discord bot - https://discord.com/developers/applications -
Press you agree then press "New applications"
Name your bot somthing i would call it "Ai Bot"
Go to bot and give it a profile picture name banner if you have that (optional)
go to QAuth section on the left and scroll till "OAuth2 URL Generator" Press the BOT button only
under that enable these perms on the bot
✅ View Channels
✅ Send Messages
✅ Read Message History
Then under that there should be a link copy it but dont paste it YET 
On the left side press bot then enable
✅ MESSAGE CONTENT INTENT
✅ SERVER MEMBERS INTENT
✅ PRESENCE INTENT
These perms are needed for the bot to work
make a new tab and PASTE that link in then it will ask you what server it should be put it Select the server it should join
