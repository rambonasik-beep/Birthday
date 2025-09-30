import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
from replit import db
import os

# ---------------- BOT SETUP ----------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree  # For slash commands

BIRTHDAY_IMAGE = "https://i.imgur.com/tXnYQ.png"

# ---------------- CHANNEL IDs ----------------
ENTRY_CHANNEL_ID = 1422609977587007558      # 🎂┊ʙɪʀᴛʜᴅᴀʏ-entry
WISHES_CHANNEL_ID = 1235118178636664833     # 🎂┊ʙɪʀᴛʜᴅᴀʏ-ᴡɪsʜᴇs

# ---------------- HELPER FUNCTIONS ----------------
def load_data():
    return db.get("birthdays", {})

def save_data(data):
    db["birthdays"] = data

# ---------------- VALIDATION ----------------
def validate_dob(dob: str):
    try:
        datetime.datetime.strptime(dob, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def validate_age(age: str):
    return age.isdigit()

# ---------------- BIRTHDAY MESSAGE ----------------
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

# ---------------- SLASH COMMANDS ----------------
@tree.command(name="addbirthday", description="Add your birthday info")
@app_commands.describe(
    dob="Enter your Date of Birth (YYYY-MM-DD)",
    game_name="Enter your Game Name",
    actual_name="Enter your Actual Name",
    age="Enter your Age in numbers"
)
async def addbirthday(interaction: discord.Interaction, dob: str, game_name: str, actual_name: str, age: str):
    if interaction.channel.id != ENTRY_CHANNEL_ID:
        await interaction.response.send_message(
            "❌ Please use this command in the 🎂┊ʙɪʀᴛʜᴅᴀʏ-entry channel!", ephemeral=True)
        return

    if not validate_dob(dob):
        await interaction.response.send_message("❌ Invalid DOB! Use YYYY-MM-DD format.", ephemeral=True)
        return

    if not validate_age(age):
        await interaction.response.send_message("❌ Age must be a number.", ephemeral=True)
        return

    data = load_data()
    data[str(interaction.user.id)] = {
        "dob": dob,
        "game_name": game_name,
        "actual_name": actual_name,
        "age": age
    }
    save_data(data)
    await interaction.response.send_message("✅ Your birthday info has been saved!", ephemeral=True)


@tree.command(name="updatebirthday", description="Update your birthday info")
@app_commands.describe(
    dob="Enter your Date of Birth (YYYY-MM-DD)",
    game_name="Enter your Game Name",
    actual_name="Enter your Actual Name",
    age="Enter your Age in numbers"
)
async def updatebirthday(interaction: discord.Interaction, dob: str, game_name: str, actual_name: str, age: str):
    if interaction.channel.id != ENTRY_CHANNEL_ID:
        await interaction.response.send_message(
            "❌ Please use this command in the 🎂┊ʙɪʀᴛʜᴅᴀʏ-entry channel!", ephemeral=True)
        return

    data = load_data()
    if str(interaction.user.id) not in data:
        await interaction.response.send_message("❌ No info found. Use /addbirthday first.", ephemeral=True)
        return

    if not validate_dob(dob):
        await interaction.response.send_message("❌ Invalid DOB! Use YYYY-MM-DD format.", ephemeral=True)
        return

    if not validate_age(age):
        await interaction.response.send_message("❌ Age must be a number.", ephemeral=True)
        return

    data[str(interaction.user.id)] = {
        "dob": dob,
        "game_name": game_name,
        "actual_name": actual_name,
        "age": age
    }
    save_data(data)
    await interaction.response.send_message("✅ Your birthday info has been updated!", ephemeral=True)


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
        await interaction.response.send_message("❌ No birthday info found for you.", ephemeral=True)


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
    GUILD_ID = int(os.environ["DISCORD_GUILD_ID"])  # Set this in Replit secrets
    guild = discord.Object(id=GUILD_ID)
    await tree.sync(guild=guild)  # instant command registration
    print(f"✅ Logged in as {bot.user} (Commands synced for guild {GUILD_ID})")
    check_birthdays.start()

# ---------------- RUN ----------------
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]  # Set this in Replit secrets
bot.run(DISCORD_TOKEN)
