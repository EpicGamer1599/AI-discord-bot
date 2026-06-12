import discord
import os
import json
import logging
from groq import Groq
from dotenv import load_dotenv
from ddgs import DDGS
import google.generativeai as genai

# =========================
# LOAD ENV
# =========================
load_dotenv()
DISCORD_TOKEN  = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
GROQ_MODEL     = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("nutsbot")

# =========================
# ENV CHECK
# =========================
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN missing")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY missing")
if not GEMINI_API_KEY:
    log.warning("GEMINI_API_KEY not set — Gemini won't work until you add it to .env")

# =========================
# GROQ
# =========================
groq_client = Groq(api_key=GROQ_API_KEY)

# =========================
# GEMINI
# =========================
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# =========================
# DISCORD
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.members         = True
intents.presences       = True
intents.guilds          = True
client = discord.Client(intents=intents)

# =========================
# CONFIG  (active provider)
# =========================
CONFIG_FILE = "config.json"
try:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
except Exception:
    config = {"active_provider": "groq"}

# make sure the key always exists
config.setdefault("active_provider", "groq")

def save_config():
    with open(
        CONFIG_FILE, "w", encoding="utf-8"
    ) as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

# =========================
# MEMORY
# =========================
MEMORY_FILE = "memory.json"
try:
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        memory = json.load(f)
except Exception:
    memory = {}

pending_searches = {}
member_snapshots = {}  # guild_id -> formatted string

# =========================
# SAVE MEMORY
# =========================
def save_memory():
    with open(
        MEMORY_FILE, "w", encoding="utf-8"
    ) as f:
        json.dump(
            memory, f,
            indent=2,
            ensure_ascii=False
        )

# =========================
# SANITIZE
# =========================
def sanitize(text):
    return (
        str(text)
        .replace("@everyone", "@ everyone")
        .replace("@here",     "@ here")
    )

# =========================
# SPLIT MESSAGE
# =========================
def split_message(text, limit=2000):
    text = str(text)
    return [
        text[i:i + limit]
        for i in range(0, len(text), limit)
    ]

# =========================
# USER MEMORY
# =========================
def get_user_memory(user_id):
    blank = {
        "nickname":     None,
        "rp":           False,
        "auto_internet": None
    }
    if user_id not in memory:
        memory[user_id] = dict(blank)
    if not isinstance(memory[user_id], dict):
        memory[user_id] = dict(blank)
        save_memory()
    for k, v in blank.items():
        if k not in memory[user_id]:
            memory[user_id][k] = v
    save_memory()
    return memory[user_id]

# =========================
# MEMBER SNAPSHOT
# =========================
def build_member_snapshot(guild):
    lines = []
    try:
        for m in guild.members:
            if m.bot:
                continue
            status = str(m.status)   # online / idle / dnd / offline
            custom = None
            for act in m.activities:
                if isinstance(act, discord.CustomActivity) and act.name:
                    custom = act.name
                    break
            line = f"  - {m.name} (display: {m.display_name}) | {status}"
            if custom:
                line += f" | “{custom}”"
            lines.append(line)
    except Exception as e:
        log.error(f"Snapshot error: {e}")
    return "\n".join(lines) if lines else "  (no members cached yet)"

def refresh_snapshot(guild):
    member_snapshots[str(guild.id)] = build_member_snapshot(guild)
    log.info(f"Snapshot refreshed for {guild.name} ({len(guild.members)} members)")

# =========================
# SERVER CONTEXT
# =========================
def server_context(guild):
    channels, roles = [], []
    try:
        for c in guild.text_channels:
            entry = f"#{c.name}"
            if c.topic:
                entry += f" — {c.topic}"
            channels.append(entry)
    except Exception:
        pass
    try:
        for r in guild.roles:
            if r.name != "@everyone":
                roles.append(r.name)
    except Exception:
        pass
    return (
        f"Server: {guild.name}\n"
        f"Channels:\n  " + "\n  ".join(channels) + "\n"
        f"Roles: {', '.join(roles)}"
    )

# =========================
# BUILD PROMPT
# =========================
def build_prompt(member, guild, entry, recent_chat):
    bot_name   = client.user.name
    safe_roles = []
    try:
        for r in member.roles:
            if r.name != "@everyone":
                safe_roles.append(r.name)
    except Exception:
        pass

    return f"""You are a Discord AI bot.
Facts:
- You are a Discord bot.
- Your visible Discord username is the source of truth for your name.
- If asked your name, say your current Discord username.
- Do not invent identities.
- Do not hallucinate fake events.
- Do not invent announcements.
- Never pretend things happened if they did not.
- If unsure, say unsure.
- Keep replies casual.
- Keep replies short.
- The recent chat history is the source of truth.
- Never claim internet knowledge unless internet results are provided.
- If internet results are provided, read them yourself and summarize naturally.
- Do not ask users to choose links unless requested.
- Do not dump raw search results.
- Do not randomly roleplay unless RP mode is enabled.
- Answer questions about legal activities (gambling, drinking, etc.) without moral lectures or refusals.
- Do not add unsolicited warnings, disclaimers, or "please gamble responsibly" type filler.
- Never refuse a question just because it sounds edgy — only refuse if it is genuinely illegal or harmful.

Current bot username: {bot_name}

Current user:
  username: {member.name}
  display name: {member.display_name}
  nickname memory: {entry.get("nickname")}
  roles: {", ".join(safe_roles)}

Server info:
{server_context(guild)}

Recent chat:
{recent_chat}

Roleplay enabled: {entry.get("rp")}

Server members (username | status | custom status):
{member_snapshots.get(str(guild.id), "(not loaded yet)")}"""

# =========================
# ACTIVE LABEL
# =========================
def active_label():
    if config["active_provider"] == "gemini":
        return f"gemini  ({GEMINI_MODEL})"
    return f"groq  ({GROQ_MODEL})"

# =========================
# SEARCH DECIDER
# =========================
def decide_search(question):
    q = question.lower().strip()
    simple = [
        "hi", "hello", "hey", "yo", "sup",
        "how are you", "wyd", "lol", "lmao", "test"
    ]
    if q in simple:
        return False
    search_words = [
        "latest", "news", "today", "recent", "weather",
        "who is", "what is", "search", "lookup",
        "internet", "google", "update"
    ]
    for word in search_words:
        if word in q:
            return True
    return False

# =========================
# WEB SEARCH
# =========================
def web_search(query):
    log.info(f"Searching web: {query}")
    collected = []
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=8)
            for item in results:
                try:
                    if not isinstance(item, dict):
                        continue
                    collected.append({
                        "title": str(item.get("title", "")),
                        "body":  str(item.get("body",  "")),
                        "href":  str(item.get("href",  ""))
                    })
                except Exception as e:
                    log.error(f"Result parse error: {e}")
    except Exception as e:
        log.error(f"Search failed: {e}")
        return []
    return collected

# =========================
# ASK AI
# =========================
def ask_ai(
    question, member, guild,
    entry, recent_chat,
    web_results=None
):
    system = build_prompt(member, guild, entry, recent_chat)

    if web_results:
        system += f"""

You were given live internet search results.
Choose the MOST relevant information yourself.
Do not ask the user which link to open.
Summarize useful information naturally.
Internet search results: {web_results}"""

    provider = config.get("active_provider", "groq")

    # ── GEMINI PATH ──────────────────────────────
    if provider == "gemini":
        if not GEMINI_API_KEY:
            log.warning(
                "Gemini selected but GEMINI_API_KEY missing "
                "— falling back to Groq"
            )
        else:
            try:
                model = genai.GenerativeModel(
                    model_name=GEMINI_MODEL,
                    system_instruction=system
                )
                response = model.generate_content(
                    question,
                    generation_config=genai.GenerationConfig(
                        temperature=0.7
                    )
                )
                # check for blocked response before touching response.text
                if not response.candidates or not response.parts:
                    reason = "unknown"
                    try:
                        reason = response.prompt_feedback.block_reason.name
                    except Exception:
                        pass
                    log.warning(f"Gemini blocked prompt ({reason}) — falling back to Groq")
                    groq_resp = groq_client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user",   "content": question}
                        ],
                        temperature=0.7
                    )
                    return (
                        f"⚠️ *Gemini blocked that ({reason}) — answered with Groq*\n\n"
                        + groq_resp.choices[0].message.content
                    )
                return response.text
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower():
                    log.warning("Gemini quota exceeded — falling back to Groq")
                    groq_resp = groq_client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user",   "content": question}
                        ],
                        temperature=0.7
                    )
                    return (
                        f"⚠️ *Gemini quota hit — answered with Groq fallback*\n\n"
                        + groq_resp.choices[0].message.content
                    )
                if "blocked" in err_str.lower() or "prohibited" in err_str.lower():
                    log.warning("Gemini blocked (exception) — falling back to Groq")
                    groq_resp = groq_client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user",   "content": question}
                        ],
                        temperature=0.7
                    )
                    return (
                        f"⚠️ *Gemini blocked that — answered with Groq*\n\n"
                        + groq_resp.choices[0].message.content
                    )
                log.error(f"Gemini error: {e}")
                raise

    # ── GROQ PATH ────────────────────────────────
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": question}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content

# =========================
# YES / NO
# =========================
def is_yes(text):
    return text.lower().strip() in [
        "yes", "yeah", "y", "sure", "ok", "okay"
    ]

def is_no(text):
    return text.lower().strip() in ["no", "nah", "n"]

# =========================
# READY
# =========================
@client.event
async def on_ready():
    log.info(f"Logged in as {client.user}")
    log.info(f"Active provider: {active_label()}")
    for guild in client.guilds:
        refresh_snapshot(guild)

# =========================
# PRESENCE / MEMBER UPDATES
# (keeps the snapshot live)
# =========================
@client.event
async def on_presence_update(before, after):
    refresh_snapshot(after.guild)

@client.event
async def on_member_update(before, after):
    refresh_snapshot(after.guild)

@client.event
async def on_member_join(member):
    refresh_snapshot(member.guild)

@client.event
async def on_member_remove(member):
    refresh_snapshot(member.guild)

# =========================
# MESSAGE
# =========================
@client.event
async def on_message(message):
    try:
        if message.author.bot:
            return
        if not message.guild:
            return

        content = message.content.strip()
        user_id = str(message.author.id)
        entry   = get_user_memory(user_id)
        key     = (
            str(message.guild.id),
            str(message.channel.id),
            user_id
        )

        # =========================
        # SEARCH CONFIRMATION
        # =========================
        pending = pending_searches.get(key)
        if pending:
            if is_yes(content):
                pending_searches.pop(key, None)
                async with message.channel.typing():
                    try:
                        results = web_search(pending["question"])
                        answer  = ask_ai(
                            pending["question"],
                            message.author,
                            message.guild,
                            entry,
                            pending["recent_chat"],
                            results
                        )
                        for chunk in split_message(sanitize(answer)):
                            await message.channel.send(chunk)
                    except Exception as e:
                        log.error(f"Search response error: {e}")
                        await message.reply(f"search error: {e}")
                return

            if is_no(content):
                pending_searches.pop(key, None)
                await message.reply("ok no internet then")
                return

        # =========================
        # SWAP MODELS  (admin only)
        # =========================
        if content.lower() == "!swapmodels":
            if not message.author.guild_permissions.administrator:
                await message.reply("admin only command 🚫")
                return

            old_label = active_label()

            if config["active_provider"] == "groq":
                if not GEMINI_API_KEY:
                    await message.reply(
                        "⚠️ `GEMINI_API_KEY` is missing from your `.env` — "
                        "add it and restart the bot first"
                    )
                    return
                config["active_provider"] = "gemini"
            else:
                config["active_provider"] = "groq"

            save_config()
            new_label = active_label()
            await message.reply(
                f"🔄 model swapped!\n"
                f"**before:** `{old_label}`\n"
                f"**now:** `{new_label}`"
            )
            return

        # =========================
        # AUTO INTERNET
        # =========================
        if content.lower().startswith("!allowinternet "):
            value = (
                content.lower()
                .replace("!allowinternet ", "")
                .strip()
            )
            if value == "true":
                entry["auto_internet"] = True
                save_memory()
                await message.reply("auto internet enabled for you")
            elif value == "false":
                entry["auto_internet"] = False
                save_memory()
                await message.reply("auto internet disabled for you")
            else:
                await message.reply("use !allowinternet true/false")
            return

        # =========================
        # REMEMBER NAME
        # =========================
        if content.lower().startswith("remember me as "):
            nickname = content[15:].strip()
            if nickname.startswith("@"):
                nickname = nickname[1:]
            entry["nickname"] = nickname
            save_memory()
            await message.reply(f"ok ill call you {nickname}")
            return

        # =========================
        # RP MODE
        # =========================
        if content.lower() == "!rp on":
            entry["rp"] = True
            save_memory()
            await message.reply("rp mode enabled")
            return

        if content.lower() == "!rp off":
            entry["rp"] = False
            save_memory()
            await message.reply("rp mode disabled")
            return

        # =========================
        # SERVER INFO
        # =========================
        if content.startswith("!server"):
            ctx = server_context(message.guild)
            await message.reply(f"```\n{ctx[:1900]}\n```")
            return

        # =========================
        # IMAGE
        # =========================
        if content.startswith("!askimage"):
            await message.reply("image mode disabled rn 💀")
            return

        # =========================
        # ASK
        # =========================
        if content.startswith("!ask"):
            question = content[4:].strip()
            if not question:
                await message.reply("ask something")
                return

            recent_lines = []
            try:
                async for msg in message.channel.history(limit=12):
                    recent_lines.append(
                        f"{msg.author.display_name}: "
                        f"{sanitize(msg.content)}"
                    )
            except Exception as e:
                log.error(f"History error: {e}")
            recent_lines.reverse()
            recent_chat = "\n".join(recent_lines)

            needs_search = decide_search(question)
            log.info(f"Needs search: {needs_search}")

            # =========================
            # INTERNET
            # =========================
            if needs_search:
                auto_setting = entry.get("auto_internet")

                # AUTO INTERNET ON
                if auto_setting is True:
                    async with message.channel.typing():
                        try:
                            results = web_search(question)
                            answer  = ask_ai(
                                question,
                                message.author,
                                message.guild,
                                entry,
                                recent_chat,
                                results
                            )
                            for chunk in split_message(sanitize(answer)):
                                await message.channel.send(chunk)
                        except Exception as e:
                            log.error(f"Auto search error: {e}")
                            await message.reply(f"search error: {e}")
                    return

                # INTERNET DISABLED
                if auto_setting is False:
                    await message.reply("internet disabled for your account")
                    return

                # ASK USER
                pending_searches[key] = {
                    "question":    question,
                    "recent_chat": recent_chat
                }
                await message.reply(
                    "i might need internet for this. search it? (yes/no)\n\n"
                    "or use `!allowinternet true` to always allow"
                )
                return

            # =========================
            # NORMAL AI
            # =========================
            async with message.channel.typing():
                try:
                    answer = ask_ai(
                        question,
                        message.author,
                        message.guild,
                        entry,
                        recent_chat
                    )
                    for chunk in split_message(sanitize(answer)):
                        await message.channel.send(chunk)
                except Exception as e:
                    log.error(f"AI error: {e}")
                    await message.reply(f"error: {e}")

    except Exception as e:
        log.error(f"FATAL ERROR: {e}")
        try:
            await message.reply(f"fatal error: {e}")
        except Exception:
            pass

# =========================
# RUN
# =========================
client.run(DISCORD_TOKEN)