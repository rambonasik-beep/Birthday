import discord
from discord.ext import commands, tasks
import datetime
from replit import db
import os
import re

# ---------------- BOT SETUP ----------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

BIRTHDAY_IMAGE = "https://i.imgur.com/tXnYQ.png"  # 🎂 Cake image link

# ---------------- CHANNEL IDs ----------------
ENTRY_CHANNEL_ID = 1422609977587007558
WISHES_CHANNEL_ID = 1235118178636664833

# ---------------- HELPER FUNCTIONS ----------------
def load_data():
    return db.get("birthdays", {})

def save_data(data):
    db["birthdays"] = data

async def get_input(ctx, prompt):
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    await ctx.send(prompt)
    msg = await bot.wait_for("message", check=check)
    return msg.content.strip()

# ---------------- VALIDATION FUNCTIONS ----------------
async def get_valid_dob(ctx, prompt):
    while True:
        dob_str = await get_input(ctx, prompt)
        # Check format YYYY-MM-DD
        if re.match(r"^\d{4}-\d{2}-\d{2}$", dob_str):
            try:
                datetime.datetime.strptime(dob_str, "%Y-%m-%d")
                return dob_str
            except ValueError:
                await ctx.send("❌ Invalid date! Please enter a valid date in YYYY-MM-DD format.")
        else:
            await ctx.send("❌ Invalid format! Please use YYYY-MM-DD (numbers only).")

async def get_valid_age(ctx, prompt):
    while True:
        age_str = await get_input(ctx, prompt)
        if age_str.isdigit():
            return age_str
        else:
            await ctx.send("❌ Age must be a number. Please enter your age in digits.")

# =====================================================
# USER INPUT COMMANDS
# =====================================================
@bot.command()
async def addbirthday(ctx):
    if ctx.channel.id != ENTRY_CHANNEL_ID:
        await ctx.send(f"❌ Please use this command in the 🎂┊ʙɪʀᴛʜᴅᴀʏ-entry channel!")
        return

    await ctx.send("🎂 Let's add your birthday details! Please answer the following:")

    dob = await get_valid_dob(ctx, "Enter your Date of Birth (YYYY-MM-DD):")
    game_name = await get_input(ctx, "Enter your Game Name:")
    actual_name = await get_input(ctx, "Enter your Actual Name:")
    age = await get_valid_age(ctx, "Enter your Age:")

    data = load_data()
    data[str(ctx.author.id)] = {
        "dob": dob,
        "game_name": game_name,
        "actual_name": actual_name,
        "age": age
    }
    save_data(data)
    await ctx.send("✅ Your birthday info has been saved!")

@bot.command()
async def updatebirthday(ctx):
    if ctx.channel.id != ENTRY_CHANNEL_ID:
        await ctx.send(f"❌ Please use this command in the 🎂┊ʙɪʀᴛʜᴅᴀʏ-entry channel!")
        return

    data = load_data()
    if str(ctx.author.id) not in data:
        await ctx.send("❌ You don't have birthday info saved yet. Use `!addbirthday` first.")
        return

    await ctx.send("🔄 Let's update your birthday details:")

    dob = await get_valid_dob(ctx, "Enter your Date of Birth (YYYY-MM-DD):")
    game_name = await get_input(ctx, "Enter your Game Name:")
    actual_name = await get_input(ctx, "Enter your Actual Name:")
    age = await get_valid_age(ctx, "Enter your Age:")

    data[str(ctx.author.id)] = {
        "dob": dob,
        "game_name": game_name,
        "actual_name": actual_name,
        "age": age
    }
    save_data(data)
    await ctx.send("✅ Your birthday info has been updated!")

@bot.command()
async def deletebirthday(ctx):
    if ctx.channel.id != ENTRY_CHANNEL_ID:
        await ctx.send(f"❌ Please use this command in the 🎂┊ʙɪʀᴛʜᴅᴀʏ-entry channel!")
        return

    data = load_data()
    if str(ctx.author.id) in data:
        del data[str(ctx.author.id)]
        save_data(data)
        await ctx.send("🗑️ Your birthday info has been deleted.")
    else:
        await ctx.send("❌ No birthday info found for you.")

# =====================================================
# DISPLAY BIRTHDAY MESSAGES
# =====================================================
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

# =====================================================
# TEST COMMAND
# =====================================================
@bot.command()
async def testbirthday(ctx):
    data = load_data()
    if str(ctx.author.id) not in data:
        await ctx.send("❌ You haven't added your birthday info yet. Use `!addbirthday` first.")
        return

    info = data[str(ctx.author.id)]
    await send_birthday_message(str(ctx.author.id), info)

# ---------------- EVENTS ----------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    check_birthdays.start()

# ---------------- RUN ----------------
bot.run(os.environ["DISCORD_TOKEN"])
