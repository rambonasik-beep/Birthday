import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
import os
from pymongo import MongoClient
from discord.ui import Modal, TextInput, View, Button
from flask import Flask
from threading import Thread
import requests

# ---------------- BOT SETUP ----------------
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
intents.members = True  # for role checks

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
tree = bot.tree

# ---------------- ENVIRONMENT VARIABLES ----------------
try:
    DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
    DISCORD_GUILD_ID = int(os.environ["DISCORD_GUILD_ID"])
    MONGO_URI = os.environ["MONGO_URI"]
except KeyError as e:
    raise RuntimeError(f"Missing environment variable: {e}")

# ---------------- MONGO DB ----------------
mongo_client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
db = mongo_client["birthdaybot"]
birthdays_collection = db["birthdays"]

# ---------------- CHANNEL IDS ----------------
ENTRY_CHANNEL_ID = 1422609977587007558   # 🎂┊ʙɪʀᴛʜᴅᴀʏ-entry
WISHES_CHANNEL_ID = 1235118178636664833  # 🎂┊ʙɪʀᴛʜᴅᴀʏ-ᴡɪsʜᴇs

# ---------------- HELPERS ----------------
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

def get_outbound_ip():
    try:
        ip = requests.get("https://checkip.amazonaws.com").text.strip()
        print(f"🌍 Outbound IP: {ip}")
        return ip
    except Exception as e:
        print(f"Could not fetch outbound IP: {e}")
        return None

def get_all_birthdays():
    return list(birthdays_collection.find({}))

def set_birthday(user_id, dob):
    birthdays_collection.update_one({"user_id": str(user_id)}, {"$set": {"dob": dob}}, upsert=True)

def delete_birthday(user_id):
    birthdays_collection.delete_one({"user_id": str(user_id)})

# ---------------- BIRTHDAY WISH ----------------
async def send_birthday_message(user_id, info, test=False):
    channel = bot.get_channel(WISHES_CHANNEL_ID)
    if not channel:
        return

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

    # Post your GIF/MP4 link right after
    await channel.send("🎂 Here’s your birthday GIF:\nhttps://images-ext-1.discordapp.net/external/wMG1LsMTVXxap4M8nZPUfieEeRCcBdOqRV_vK_fypx0/https/media.tenor.com/Oew16xC0ydcAAAPo/happy-birthday-happybirthday.mp4")

    print(f"[BIRTHDAY MESSAGE] Sent for user {user_id} (test={test})")

# ---------------- AUTOMATIC CHECK ----------------
@tasks.loop(hours=24)
async def check_birthdays():
    await bot.wait_until_ready()
    today = datetime.datetime.now().strftime("%m-%d")
    data = get_all_birthdays()
    for record in data:
        try:
            dob = datetime.datetime.strptime(record["dob"], "%Y-%m-%d")
            if dob.strftime("%m-%d") == today:
                await send_birthday_message(record["user_id"], record)
                print(f"[AUTO] Birthday for {record['user_id']} on {today}")
        except Exception as e:
            print(f"Error in birthday check: {e}")

# ---------------- DOB MODAL ----------------
class DOBModal(Modal):
    def __init__(self, title="Add DOB", is_update=False):
        super().__init__(title=title)
        self.is_update = is_update
        self.add_item(TextInput(label="Date of Birth (YYYY-MM-DD)"))

    async def on_submit(self, interaction: discord.Interaction):
        dob = self.children[0].value.strip()
        if not validate_dob(dob):
            await interaction.response.send_message("❌ Invalid DOB! Use YYYY-MM-DD format.", ephemeral=True)
            return
        set_birthday(interaction.user.id, dob)
        action = "UPDATED" if self.is_update else "REGISTERED"
        print(f"[{action}] {interaction.user} DOB = {dob}")
        await interaction.response.send_message(f"✅ DOB {action.lower()} saved!", ephemeral=True)

# ---------------- VIEW ----------------
class BirthdayView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="➕ Register DOB", style=discord.ButtonStyle.success, custom_id="register_dob")
    async def register_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(DOBModal(title="Register DOB", is_update=False))

    @discord.ui.button(label="✏️ Update DOB", style=discord.ButtonStyle.primary, custom_id="update_dob")
    async def update_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(DOBModal(title="Update DOB", is_update=True))

    @discord.ui.button(label="🗑️ Delete DOB", style=discord.ButtonStyle.danger, custom_id="delete_dob")
    async def delete_callback(self, interaction: discord.Interaction, button: Button):
        delete_birthday(interaction.user.id)
        print(f"[DELETE] {interaction.user} deleted DOB entry")
        await interaction.response.send_message("🗑️ Deleted your DOB entry.", ephemeral=True)

    @discord.ui.button(label="🧪 Test Birthday", style=discord.ButtonStyle.secondary, custom_id="test_bday")
    async def test_callback(self, interaction: discord.Interaction, button: Button):
        rec = birthdays_collection.find_one({"user_id": str(interaction.user.id)})
        if not rec:
            await interaction.response.send_message("❌ You haven't registered DOB yet.", ephemeral=True)
            return
        await send_birthday_message(str(interaction.user.id), rec, test=True)
        await interaction.response.send_message("✅ Test birthday posted.", ephemeral=True)

    @discord.ui.button(label="📅 Upcoming Birthdays", style=discord.ButtonStyle.secondary, custom_id="upcoming_bday")
    async def upcoming_callback(self, interaction: discord.Interaction, button: Button):
        data = get_all_birthdays()
        if not data:
            await interaction.response.send_message("📭 No birthdays registered yet.", ephemeral=True)
            return

        today = datetime.datetime.now()
        upcoming = []
        for rec in data:
            try:
                dob = datetime.datetime.strptime(rec["dob"], "%Y-%m-%d")
                nxt = dob.replace(year=today.year)
                if nxt < today:
                    nxt = dob.replace(year=today.year + 1)
                upcoming.append((nxt, rec["user_id"], rec))
            except:
                continue
        upcoming.sort(key=lambda x: x[0])
        next_fifteen = upcoming[:15]

        embed = discord.Embed(
            title="📅 Upcoming Birthdays",
            description="Here are the next birthdays 🎂",
            color=discord.Color.blue()
        )
        for date, uid, rec in next_fifteen:
            age_next = calculate_age(rec["dob"]) + 1
            embed.add_field(
                name=date.strftime("%b %d"),
                value=f"🎂 <@{uid}> (Will be {age_next})",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ---------------- SLASH COMMANDS ----------------
@tree.command(name="birthday", description="Manage your DOB info")
async def birthday(interaction: discord.Interaction):
    if interaction.channel.id != ENTRY_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Use only <#{ENTRY_CHANNEL_ID}> channel.", ephemeral=True)
        return
    await interaction.response.send_message("🎂 Choose an option below:", view=BirthdayView(), ephemeral=True)

@tree.command(name="dbcheck", description="Check DB (Admin only)")
async def dbcheck(interaction: discord.Interaction):
    if not any(r.name == "Admin" for r in interaction.user.roles):
        await interaction.response.send_message("❌ You need the Admin role.", ephemeral=True)
        return
    try:
        count = birthdays_collection.count_documents({})
        await interaction.response.send_message(f"✅ DB OK. Registered users: {count}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ DB error: {e}", ephemeral=True)

# ---------------- EVENTS ----------------
@bot.event
async def on_ready():
    guild = discord.Object(id=DISCORD_GUILD_ID)
    await tree.sync(guild=guild)
    print(f"✅ Logged in as {bot.user}")
    get_outbound_ip()
    bot.add_view(BirthdayView())
    channel = bot.get_channel(ENTRY_CHANNEL_ID)
    if channel:
        msg = await channel.send("🎂 Birthday Menu - Choose option:", view=BirthdayView())
        await msg.pin()
        print("[AUTO] Menu posted and pinned.")
    check_birthdays.start()

# ---------------- KEEP-ALIVE ----------------
app = Flask('')
@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=10000)

Thread(target=run).start()

bot.run(DISCORD_TOKEN)
