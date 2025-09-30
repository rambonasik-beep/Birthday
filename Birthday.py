import discord
from discord.ext import commands, tasks
import datetime
from replit import db
import os

# ---------------- BOT SETUP ----------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

BIRTHDAY_IMAGE = "https://i.imgur.com/tXnYQ.png"  # 🎂 Cake image link


# ---------------- HELPER FUNCTIONS ----------------
def load_data():
    return db.get("birthdays", {})

def save_data(data):
    db["birthdays"] = data


# =====================================================
# USER INPUT COLLECTION (DOB, Name, Age, Game)
# =====================================================
@bot.command()
async def addbirthday(ctx):
    await ctx.send("🎂 Let's add your birthday details! Please answer the following:")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send("Enter your Date of Birth (YYYY-MM-DD):")
    dob_msg = await bot.wait_for("message", check=check)
    dob = dob_msg.content.strip()

    await ctx.send("Enter your Game Name:")
    game_msg = await bot.wait_for("message", check=check)
    game_name = game_msg.content.strip()

    await ctx.send("Enter your Actual Name:")
    name_msg = await bot.wait_for("message", check=check)
    actual_name = name_msg.content.strip()

    await ctx.send("Enter your Age:")
    age_msg = await bot.wait_for("message", check=check)
    age = age_msg.content.strip()

    data = load_data()
    data[str(ctx.author.id)] = {
        "dob": dob,
        "game_name": game_name,
        "actual_name": actual_name,
        "age": age,
        "channel_id": ctx.channel.id
    }
    save_data(data)
    await ctx.send("✅ Your birthday info has been saved!")


@bot.command()
async def updatebirthday(ctx):
    data = load_data()
    if str(ctx.author.id) not in data:
        await ctx.send("❌ You don't have birthday info saved yet. Use `!addbirthday` first.")
        return

    await ctx.send("🔄 Let's update your birthday details. Follow the prompts:")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send("Enter your Date of Birth (YYYY-MM-DD):")
    dob_msg = await bot.wait_for("message", check=check)
    dob = dob_msg.content.strip()

    await ctx.send("Enter your Game Name:")
    game_msg = await bot.wait_for("message", check=check)
    game_name = game_msg.content.strip()

    await ctx.send("Enter your Actual Name:")
    name_msg = await bot.wait_for("message", check=check)
    actual_name = name_msg.content.strip()

    await ctx.send("Enter your Age:")
    age_msg = await bot.wait_for("message", check=check)
    age = age_msg.content.strip()

    data[str(ctx.author.id)] = {
        "dob": dob,
        "game_name": game_name,
        "actual_name": actual_name,
        "age": age,
        "channel_id": ctx.channel.id
    }
    save_data(data)
    await ctx.send("✅ Your birthday info has been updated!")


@bot.command()
async def deletebirthday(ctx):
    data = load_data()
    if str(ctx.author.id) in data:
        del data[str(ctx.author.id)]
        save_data(data)
        await ctx.send("🗑️ Your birthday info has been deleted.")
    else:
        await ctx.send("❌ No birthday info found for you.")


# =====================================================
# DISPLAY BIRTHDAY MESSAGE
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
    channel = bot.get_channel(info.get("channel_id"))
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
