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

# ---------------- CUSTOM CAKE IMAGE ----------------
# Replace this link with your uploaded cake image from Discord
BIRTHDAY_IMAGE = "https://cdn.discordapp.com/attachments/XXXX/XXXX/mycake.png"

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

# ---------------- HELPER FUNCTIONS ----------------
def load_data():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def validate_dob(dob: str):
    try:
        datetime.datetime.strptime(dob, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def validate_age(age: str):
    return age.isdigit()

async def send_birthday_message(user_id, info, test=False):
    channel = bot.get_channel(WISHES_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="🎉 Happy Birthday!",
            description="Happy Birthday! Wishing you a day filled with love, joy, and laughter",
            color=discord.Color.pink()
        )
        embed.set_image(url=BIRTHDAY_IMAGE)
        embed.add_field(name="Age", value=info["age"], inline=True)

        content = (
            f"🎂 @everyone Join me in wishing <@{user_id}> a **Happy Birthday!** 🎉🥳"
            if not test else f"🧪 Test: This is how your birthday wish would look for <@{user_id}>"
        )

        await channel.send(content=content, embed=embed)
        print(f"[BIRTHDAY MESSAGE] Sent for user {user_id} (test={test})")

# ---------------- AUTOMATIC BIRTHDAY CHECK ----------------
@tasks.loop(hours=24)
async def check_birthdays():
    await bot.wait_until_ready()
    today = datetime.datetime.now().strftime("%m-%d")
    data = load_data()
    for user_id, info in data.items():
        try:
            dob = datetime.datetime.strptime(info["dob"], "%Y-%m-%d")
            if dob.strftime("%m-%d") == today:
                await send_birthday_message(user_id, info)
                print(f"[AUTO] Birthday detected for {user_id} on {today}")
        except Exception as e:
            print(f"Error checking birthday: {e}")

# ---------------- DOB MODAL ----------------
class DOBModal(Modal):
    def __init__(self, title="Add DOB", is_update=False):
        super().__init__(title=title)
        self.is_update = is_update
        self.add_item(TextInput(label="Date of Birth (YYYY-MM-DD)"))
        self.add_item(TextInput(label="Age (Number Only)"))

    async def on_submit(self, interaction: discord.Interaction):
        dob = self.children[0].value
        age = self.children[1].value

        if not validate_dob(dob):
            await interaction.response.send_message("❌ Invalid DOB! Use YYYY-MM-DD format.", ephemeral=True)
            return

        if not validate_age(age):
            await interaction.response.send_message("❌ Age must be a number.", ephemeral=True)
            return

        data = load_data()
        if self.is_update and str(interaction.user.id) not in data:
            await interaction.response.send_message("❌ No DOB found to update. Use Register first.", ephemeral=True)
            return

        data[str(interaction.user.id)] = {
            "dob": dob,
            "age": age
        }
        save_data(data)

        action = "UPDATED" if self.is_update else "REGISTERED"
        print(f"[{action}] User {interaction.user} ({interaction.user.id}) DOB={dob}, Age={age}")

        await interaction.response.send_message(
            f"✅ DOB {action.lower()}!", ephemeral=True
        )

# ---------------- VIEW WITH BUTTONS ----------------
class BirthdayView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="➕ Register DOB", style=discord.ButtonStyle.success)
    async def register_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(DOBModal(title="Register DOB", is_update=False))

    @discord.ui.button(label="✏️ Update DOB", style=discord.ButtonStyle.primary)
    async def update_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(DOBModal(title="Update DOB", is_update=True))

    @discord.ui.button(label="🗑️ Delete DOB", style=discord.ButtonStyle.danger)
    async def delete_callback(self, interaction: discord.Interaction, button: Button):
        data = load_data()
        if str(interaction.user.id) in data:
            del data[str(interaction.user.id)]
            save_data(data)
            print(f"[DELETED] User {interaction.user} ({interaction.user.id}) deleted DOB entry")
            await interaction.response.send_message("🗑️ Your DOB entry has been deleted.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No DOB found to delete.", ephemeral=True)

    @discord.ui.button(label="🧪 Test Birthday", style=discord.ButtonStyle.secondary)
    async def test_callback(self, interaction: discord.Interaction, button: Button):
        data = load_data()
        if str(interaction.user.id) not in data:
            await interaction.response.send_message("❌ No DOB found to test. Register first!", ephemeral=True)
            return
        await send_birthday_message(str(interaction.user.id), data[str(interaction.user.id)], test=True)
        print(f"[TEST] User {interaction.user} ({interaction.user.id}) tested birthday message")
        await interaction.response.send_message("✅ Test message sent to wishes channel!", ephemeral=True)

    @discord.ui.button(label="📅 Upcoming Birthdays", style=discord.ButtonStyle.secondary)
    async def upcoming_callback(self, interaction: discord.Interaction, button: Button):
        data = load_data()
        if not data:
            await interaction.response.send_message("📭 No birthdays registered yet.")
            return

        today = datetime.datetime.now()
        upcoming = []

        for user_id, info in data.items():
            try:
                dob = datetime.datetime.strptime(info["dob"], "%Y-%m-%d")
                next_bday = dob.replace(year=today.year)
                if next_bday < today:
                    next_bday = dob.replace(year=today.year + 1)
                upcoming.append((next_bday, user_id, info))
            except:
                continue

        upcoming.sort(key=lambda x: x[0])
        next_five = upcoming[:5]

        embed = discord.Embed(
            title="📅 Upcoming Birthdays",
            description="Here are the next birthdays in our server 🎂",
            color=discord.Color.blue()
        )

        for date, user_id, info in next_five:
            embed.add_field(
                name=date.strftime("%b %d"),
                value=f"🎂 <@{user_id}> (Age: {info['age']})",
                inline=False
            )

        print(f"[UPCOMING] User {interaction.user} requested upcoming birthdays list")
        await interaction.response.send_message(embed=embed)

# ---------------- SLASH COMMAND ----------------
@tree.command(name="birthday", description="Manage your DOB info")
async def birthday(interaction: discord.Interaction):
    if interaction.channel.id != ENTRY_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ Please only use this command in <#{ENTRY_CHANNEL_ID}> channel.", ephemeral=True)
        return

    view = BirthdayView()
    print(f"[COMMAND] User {interaction.user} ({interaction.user.id}) used /birthday")
    await interaction.response.send_message("🎂 Choose an option below:", view=view, ephemeral=True)

# ---------------- EVENTS ----------------
@bot.event
async def on_ready():
    guild = discord.Object(id=DISCORD_GUILD_ID)
    await tree.sync(guild=guild)  # sync commands only for your server
    print(f"✅ Logged in as {bot.user} (Commands synced for guild {DISCORD_GUILD_ID})")
    print("⚠️ Reminder: Run /birthday once in 🎂┊ʙɪʀᴛʜᴅᴀʏ-entry and PIN it!")
    check_birthdays.start()

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
