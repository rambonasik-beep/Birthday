import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
import os
import json
from discord.ui import Modal, TextInput, View, Button
from flask import Flask
from threading import Thread

# ---------------- BOT SETUP ----------------
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
tree = bot.tree

# ---------------- ENVIRONMENT VARIABLES ----------------
try:
    DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]       # from Render
    DISCORD_GUILD_ID = int(os.environ["DISCORD_GUILD_ID"])  # from Render
except KeyError as e:
    raise RuntimeError(f"❌ Missing environment variable: {e}")

# ---------------- CHANNEL IDS ----------------
ENTRY_CHANNEL_ID = 1422609977587007558   # 🎂┊ʙɪʀᴛʜᴅᴀʏ-entry
WISHES_CHANNEL_ID = 1235118178636664833  # 🎂┊ʙɪʀᴛʜᴅᴀʏ-ᴡɪsʜᴇs

DB_FILE = "birthdays.json"

# ---------------- DEBUG ON_READY ----------------
@bot.event
async def on_ready():
    print("=== on_ready debug ===")
    try:
        print("Bot user:", bot.user, "ID:", bot.user.id)
    except Exception as e:
        print("Could not read bot user:", e)

    print("DISCORD_GUILD_ID present:", "DISCORD_GUILD_ID" in os.environ)
    print("DISCORD_GUILD_ID (value):", os.environ.get("DISCORD_GUILD_ID"))

    try:
        print("Bot is in guild IDs:", [g.id for g in bot.guilds])
    except Exception as e:
        print("Error listing guilds:", e)

    try:
        cmds = [c.name for c in tree.walk_commands()]
        print("Commands in bot.tree:", cmds)
    except Exception as e:
        print("Error listing tree commands:", e)

    try:
        gid = int(os.environ["DISCORD_GUILD_ID"])
        guild = discord.Object(id=gid)
        await tree.sync(guild=guild)
        print(f"✅ Commands synced for guild {gid}")
    except KeyError:
        print("❌ DISCORD_GUILD_ID not set in environment!")
    except Exception as e:
        print("❌ Error while syncing commands:", repr(e))

    print("Commands after sync:", [c.name for c in tree.walk_commands()])
    print("=== debug end ===")

# ---------------- SLASH COMMAND ----------------
@bot.tree.command(name="birthday", description="Manage your DOB info")
async def birthday(interaction: discord.Interaction):
    if interaction.channel.id != ENTRY_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ Please only use this command in <#{ENTRY_CHANNEL_ID}> channel.", ephemeral=True
        )
        return

    view = View(timeout=None)
    view.add_item(Button(label="Example Button", style=discord.ButtonStyle.primary))
    await interaction.response.send_message("🎂 Choose an option below:", view=view, ephemeral=True)

# ---------------- KEEP-ALIVE (Render) ----------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=10000)

Thread(target=run).start()

# ---------------- RUN BOT ----------------
bot.run(DISCORD_TOKEN)
