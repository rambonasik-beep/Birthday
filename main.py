import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
import os
from pymongo import MongoClient
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
    DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]        # from Render
    DISCORD_GUILD_ID = int(os.environ["DISCORD_GUILD_ID"])  # from Render
    MONGO_URI = os.environ["MONGO_URI"]                # MongoDB Atlas connection string
except KeyError as e:
    raise RuntimeError(f"❌ Missing environment variable: {e}")

# ---------------- DATABASE SETUP ----------------
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["birthdaybot"]
birthdays_collection = db["birthdays"]

# ---------------- CHANNEL IDS ----------------
ENTRY_CHANNEL_ID = 1422609977587007558   # 🎂┊ʙɪʀᴛʜᴅᴀʏ-entry
WISHES_CHANNEL_ID = 1235118178636664833  # 🎂┊ʙɪʀᴛʜᴅᴀʏ-ᴡɪsʜᴇs

# ---------------- HELPER FUNCTIONS ----------------
def validate_dob(dob: str):
    try:
        datetime.datetime.strptime(dob, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def calculate_age(dob: str):
    try:
        birth_date = datetime.datetime.strptime(dob, "%Y-%m-%d").date()
        today = datetime.date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except:
        return None

def get_user_birthday(user_id: str):
    return birthdays_collection.find_one({"user_id": user_id})

def save_user_birthday(user_id: str, dob: str):
    birthdays_collection.update_one(
        {"user_id": user_id},
        {"$set": {"dob": dob}},
        upsert=True
    )

def delete_user_birthday(user_id: str):
    birthdays_collection.delete_one({"user_id": user_id})

def get_all_birthdays():
    return list(birthdays_collection.find({}))

# ---------------- BIRTHDAY WISH ----------------
async def send_birthday_message(user_id, info, test=False):
    channel = bot.get_channel(WISHES_CHANNEL_ID)
    if channel:
        age_now = calculate_age(info["dob"])

        embed = discord.Embed(
            title=f"🎉 Happy Birthday <@{user_id}>! 🎂",
            description="Wishing you a day filled with love, joy, and laughter",
            color=discord.Color.pink()
        )
        embed.add_field(name="Current Age", value=str(age_now), inline=True)

        if not test:
            content = f"🎂 @everyone Join me in wishing <@{user_id}> a **Happy Birthday!** 🎉🥳"
        else:
            content = f"🧪 Test: This is how your birthday wish would look for <@{user_id}>"

        await channel.send(
            content=content,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(everyone=True, users=True)
        )

        print(f"[BIRTHDAY MESSAGE] Sent for user {user_id} (test={test})")

# ---------------- AUTOMATIC BIRTHDAY CHECK ----------------
@tasks.loop(hours=24)
async def check_birthdays():
    await bot.wait_until_ready()
    today = datetime.datetime.now().strftime("%m-%d")
    data = get_all_birthdays()
    for info in data:
        try:
            dob = datetime.datetime.strptime(info["dob"], "%Y-%m-%d")
            if dob.strftime("%m-%d") == today:
                await send_birthday_message(info["user_id"], info)
                print(f"[AUTO] Birthday detected for {info['user_id']} on {today}")
        except Exception as e:
            print(f"Error checking birthday: {e}")

# ---------------- DOB MODAL ----------------
class DOBModal(Modal):
    def __init__(self, title="Add DOB", is_update=False):
        super().__init__(title=title)
        self.is_update = is_update
        self.add_item(TextInput(label="Date of Birth (YYYY-MM-DD)"))

    async def on_submit(self, interaction: discord.Interaction):
        try:
            dob = self.children[0].value.strip()

            if not validate_dob(dob):
                await interaction.response.send_message(
                    "❌ Invalid DOB! Please use YYYY-MM-DD format (e.g. 1997-10-15).",
                    ephemeral=True
                )
                return

            save_user_birthday(str(interaction.user.id), dob)

            action = "UPDATED" if self.is_update else "REGISTERED"
            print(f"[{action}] User {interaction.user} ({interaction.user.id}) DOB={dob}")

            await interaction.response.send_message(
                f"✅ DOB {action.lower()} successfully!", ephemeral=True
            )

        except Exception as e:
            print(f"[ERROR] DOB register/update failed: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ Something went wrong.\nError: `{e}`",
                    ephemeral=True
                )

# ---------------- VIEW WITH BUTTONS ----------------
class BirthdayView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="➕ Register DOB", style=discord.ButtonStyle.success)
    async def register_callback(self, interaction: discord.Interaction, button: Button):
        try:
            await interaction.response.send_modal(DOBModal(title="Register DOB", is_update=False))
            print(f"[MODAL] Register DOB opened for {interaction.user}")
        except Exception as e:
            print(f"[ERROR] Could not open Register modal: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Failed to open modal.", ephemeral=True)

    @discord.ui.button(label="✏️ Update DOB", style=discord.ButtonStyle.primary)
    async def update_callback(self, interaction: discord.Interaction, button: Button):
        try:
            await interaction.response.send_modal(DOBModal(title="Update DOB", is_update=True))
            print(f"[MODAL] Update DOB opened for {interaction.user}")
        except Exception as e:
            print(f"[ERROR] Could not open Update modal: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Failed to open modal.", ephemeral=True)

    @discord.ui.button(label="🗑️ Delete DOB", style=discord.ButtonStyle.danger)
    async def delete_callback(self, interaction: discord.Interaction, button: Button):
        if get_user_birthday(str(interaction.user.id)):
            delete_user_birthday(str(interaction.user.id))
            print(f"[DELETED] User {interaction.user} ({interaction.user.id}) deleted DOB entry")
            await interaction.response.send_message("🗑️ Your DOB entry has been deleted.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No DOB found to delete.", ephemeral=True)

    @discord.ui.button(label="🧪 Test Birthday", style=discord.ButtonStyle.secondary)
    async def test_callback(self, interaction: discord.Interaction, button: Button):
        info = get_user_birthday(str(interaction.user.id))
        if not info:
            await interaction.response.send_message("❌ No DOB found to test. Register first!", ephemeral=True)
            return
        await send_birthday_message(str(interaction.user.id), info, test=True)
        await interaction.response.send_message("✅ Test message sent to wishes channel!", ephemeral=True)

    @discord.ui.button(label="📅 Upcoming Birthdays", style=discord.ButtonStyle.secondary)
    async def upcoming_callback(self, interaction: discord.Interaction, button: Button):
        data = get_all_birthdays()
        if not data:
            await interaction.response.send_message("📭 No birthdays registered yet.", ephemeral=True)
            return

        today = datetime.datetime.now()
        upcoming = []

        for info in data:
            try:
                dob = datetime.datetime.strptime(info["dob"], "%Y-%m-%d")
                next_bday = dob.replace(year=today.year)
                if next_bday < today:
                    next_bday = dob.replace(year=today.year + 1)
                upcoming.append((next_bday, info["user_id"], info))
            except:
                continue

        upcoming.sort(key=lambda x: x[0])
        next_fifteen = upcoming[:15]

        embed = discord.Embed(
            title="📅 Upcoming Birthdays",
            description="Here are the next 15 birthdays 🎂",
            color=discord.Color.blue()
        )

        for date, user_id, info in next_fifteen:
            age_next = calculate_age(info["dob"])
            embed.add_field(
                name=date.strftime("%b %d"),
                value=f"🎂 <@{user_id}> (Will be {age_next})",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

# ---------------- SLASH COMMAND ----------------
@bot.tree.command(name="birthday", description="Manage your DOB info")
async def birthday(interaction: discord.Interaction):
    if interaction.channel.id != ENTRY_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ Please only use this command in <#{ENTRY_CHANNEL_ID}> channel.", ephemeral=True
        )
        return

    view = BirthdayView()
    await interaction.response.send_message("🎂 Choose an option below:", view=view, ephemeral=True)

# ---------------- EVENTS ----------------
@bot.event
async def on_ready():
    guild = discord.Object(id=DISCORD_GUILD_ID)
    await tree.sync(guild=guild)
    print(f"✅ Logged in as {bot.user} (Commands synced for guild {DISCORD_GUILD_ID})")

    # Persistent view registration
    bot.add_view(BirthdayView())

    # Auto-post menu on startup
    channel = bot.get_channel(ENTRY_CHANNEL_ID)
    if channel:
        view = BirthdayView()
        menu_msg = await channel.send("🎂 Birthday Menu - Choose an option below:", view=view)
        await menu_msg.pin()
        print("[AUTO] Birthday menu posted and pinned.")

    check_birthdays.start()

# ---------------- KEEP-ALIVE ----------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=10000)

Thread(target=run).start()

# ---------------- RUN BOT ----------------
bot.run(DISCORD_TOKEN)
