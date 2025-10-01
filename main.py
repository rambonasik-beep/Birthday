@bot.event
async def on_ready():
    print("=== on_ready debug ===")
    try:
        print("Bot user:", bot.user, "ID:", bot.user.id)
    except Exception as e:
        print("Could not read bot user:", e)

    # show env vars (only show presence, not token)
    print("DISCORD_GUILD_ID present:", "DISCORD_GUILD_ID" in os.environ)
    try:
        print("DISCORD_GUILD_ID (value):", os.environ.get("DISCORD_GUILD_ID"))
    except Exception:
        pass

    # list guilds the bot is in
    try:
        print("Bot is in guild IDs:", [g.id for g in bot.guilds])
    except Exception as e:
        print("Error listing guilds:", e)

    # list currently registered app commands that the tree sees
    try:
        cmds = [c.name for c in tree.walk_commands()]
        print("Commands in bot.tree:", cmds)
    except Exception as e:
        print("Error listing tree commands:", e)

    # try to sync to the specific guild (will raise if GUILD ID missing/wrong)
    try:
        gid = int(os.environ["DISCORD_GUILD_ID"])
        guild = discord.Object(id=gid)
        await tree.sync(guild=guild)
        print(f"✅ Commands synced for guild {gid}")
    except KeyError:
        print("❌ DISCORD_GUILD_ID not set in environment!")
    except Exception as e:
        print("❌ Error while syncing commands:", repr(e))

    # confirm the birthday command exists in the tree after sync
    print("Commands after sync:", [c.name for c in tree.walk_commands()])

    print("=== debug end ===")
    # start birthday check loop if you haven't already
    try:
        check_birthdays.start()
    except Exception as e:
        print("check_birthdays start error (may already be running):", e)
