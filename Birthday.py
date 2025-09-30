import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
from replit import db
import os
from discord.ui import Modal, InputText

# ---------------- BOT SETUP ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True  # required for slash commands

# Remove command_prefix entirely since we only use slash commands
bot = commands.Bot(command_prefix=None, intents=intents)
tree = bot.tree

BIRTHDAY_IMAGE = "https://i.imgur.com/tXnYQ.png"

# ---------------- CHANNEL IDS ----------------
ENTRY_CHANNEL_ID = 1422609977587007558      # 🎂┊ʙɪʀᴛʜᴅᴀʏ-entry
WISHES_CHANNEL_ID = 1235118178636664833     # 🎂┊ʙɪʀᴛʜᴅᴀʏ-ᴡɪsʜᴇs

# ---------------- HELPER FUNCTIONS ----------------
def load_data():
    return db.get("birthdays", {})

def save_data(data):
    db["birthdays"] = data

def validate_dob(dob: str):
    try:
        datetime.datetime.strptime(dob, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def validate_age(age: str):
    return age.isdigit()

async def send_birthday_message(user_id, info):
    channel = bot.get_channel(WISHES_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="🎉 Happy Birthday!",
            description="Happy Birthday! Wishing you a day filled with love, joy, and laughter",
            color=discord.Color.pink()
        )
        embed.set_image(url=BIRTHDAY_IMAGE)
        embed.add_field(name="Game Name", value=info["game_name"], inline=True)
        embed.add_field(name="Actual Name", value=info["actual_name"], inline=True)
        embed.add_field(name="Age", value=info["age"], inline=True)

        await channel.send(
            content=f"🎂 @everyone Join me in wishing <@{user_id}> a **Happy Birthday!** 🎉🥳",
            embed=embed
        )

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
        except Exception as e:
            print(f"Error checking birthday: {e}")

# ---------------- MODALS FOR ADD/UPDATE ----------------
class BirthdayModal(Modal):
    def __init__(self, title="Add Birthday Info", is_update=False):
        super().__init__(title=title)
        self.is_update = is_update
        self.add_item(InputText(label="Date of Birth (YYYY-MM-DD)"))
        self.add_item(InputText(label="Game Name"))
        self.add_item(InputText(label="Actual Name"))
        self.add_item(InputText(label="Age"))

    async def on_submit(self, interaction: discord.Interaction):
        dob = self.children[0].value
        game_name = self.children[1].value
        actual_name = self.children[2].value
        age = self.children[3].value

        if interaction.channel.id != ENTRY_CHANNEL_ID:
            await interaction.response.send_message(
                "❌ Please use this in the 🎂┊ʙɪʀᴛʜᴅᴀʏ-entry channel!", ephemeral=True)
            return

        if not validate_dob(dob):
            await interaction.response.send_message("❌ Invalid DOB! Use YYYY-MM-DD.", ephemeral=True)
            return

        if not validate_age(age):
            await interaction.response.send_message("❌ Age must be a number.", ephemeral=True)
            return

        data = load_data()
        if self.is_update and str(interaction.user.id) not in data:
            await interaction.response.send_message("❌ No info found to update. Use /addbirthday first.", ephemeral=True)
            return

        data[str(interaction.user.id)] = {
            "dob": dob,
            "game_name": game_name,
            "actual_name": actual_name,
            "age": age
        }
        save_data(data)
        await interaction.response.send_message(
            "✅ Birthday info updated!" if self.is_update else "✅ Birthday info saved!", ephemeral=True
        )

# ---------------- SLASH COMMANDS ----------------
@tree.command(name="addbirthday", description="Add your birthday info via modal")
async def addbirthday(interaction: discord.Interaction):
    await interaction.response.send_modal(BirthdayModal(title="Add Birthday Info"))

@tree.command(name="updatebirthday", description="Update your birthday info via modal")
async def updatebirthday(interaction: discord.Interaction):
    await interaction.response.send_modal(BirthdayModal(title="Update Birthday Info", is_update=True))

@tree.command(name="deletebirthday", description="Delete your birthday info")
async def deletebirthday(interaction: discord.Interaction):
    if interaction.channel.id != ENTRY_CHANNEL_ID:
        await interaction.response.send_message(
            "❌ Please use this command in the 🎂┊ʙɪʀᴛʜᴅᴀʏ-entry channel!", ephemeral=True)
        return

    data = load_data()
    if str(interaction.user.id) in data:
        del data[str(interaction.user.id)]
        save_data(data)
        await interaction.response.send_message("🗑️ Your birthday info has been deleted.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ No birthday info found.", ephemeral=True)

@tree.command(name="testbirthday", description="Test your birthday message")
async def testbirthday(interaction: discord.Interaction):
    data = load_data()
    if str(interaction.user.id) not in data:
        await interaction.response.send_message("❌ You haven't added your birthday info yet.", ephemeral=True)
        return
    info = data[str(interaction.user.id)]
    await send_birthday_message(str(interaction.user.id), info)
    await interaction.response.send_message("✅ Birthday message sent to the wishes channel.", ephemeral=True)

# ---------------- EVENTS ----------------
@bot.event
async def on_ready():
    GUILD_ID = int(os.environ["DISCORD_GUILD_ID"])  # server ID in Replit secrets
    guild = discord.Object(id=GUILD_ID)
    await tree.sync(guild=guild)  # instant command registration
    print(f"✅ Logged in as {bot.user} (Commands synced for guild {GUILD_ID})")
    check_birthdays.start()

# ---------------- RUN ----------------
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]  # bot token in Replit secrets
bot.run(DISCORD_TOKEN)
