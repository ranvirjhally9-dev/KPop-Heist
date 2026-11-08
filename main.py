import os
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
import wavelink
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
LAVALINK_URI = os.getenv("LAVALINK_URI")
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")
DB_PATH = os.getenv("DB_PATH", "data/kpop_heist.sqlite3")

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
db = sqlite3.connect(DB_PATH)
db.execute("""CREATE TABLE IF NOT EXISTS wallets (
    user_id INTEGER PRIMARY KEY, coins INTEGER NOT NULL DEFAULT 0,
    last_daily TEXT
)""")
db.commit()

def wallet(user_id: int):
    db.execute("INSERT OR IGNORE INTO wallets(user_id, coins) VALUES(?, 0)", (user_id,))
    db.commit()
    return db.execute("SELECT coins, last_daily FROM wallets WHERE user_id=?", (user_id,)).fetchone()

def change_coins(user_id: int, amount: int):
    wallet(user_id)
    db.execute("UPDATE wallets SET coins = MAX(0, coins + ?) WHERE user_id=?", (amount, user_id))
    db.commit()

async def setup_hook():
    if LAVALINK_URI and LAVALINK_PASSWORD:
        await wavelink.Pool.connect(
            client=bot,
            nodes=[wavelink.Node(uri=LAVALINK_URI, password=LAVALINK_PASSWORD)]
        )
    await bot.tree.sync()

bot.setup_hook = setup_hook

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} | KPop Heist is ready")

def staff_only():
    return app_commands.checks.has_permissions(manage_messages=True)

@bot.tree.command(name="ping", description="Check if KPop Heist is online")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! `{round(bot.latency * 1000)} ms`")

@bot.tree.command(name="help", description="Show KPop Heist commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="KPop Heist command list", color=discord.Color.magenta())
    embed.add_field(name="Moderation", value="`/kick` `/ban` `/timeout` `/purge`", inline=False)
    embed.add_field(name="Music", value="`/play` `/skip` `/stop` `/leave`", inline=False)
    embed.add_field(name="K-pop", value="`/idol` `/quiz`", inline=False)
    embed.add_field(name="Fun", value="`/coinflip` `/8ball` `/roll`", inline=False)
    embed.add_field(name="Heist economy", value="`/balance` `/daily` `/heist` `/leaderboard`", inline=False)
    embed.set_footer(text="Be kind. Have fun. Don't get banned.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="kick", description="Kick a member")
@staff_only()
@app_commands.describe(member="Member to kick", reason="Reason for the kick")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if member == interaction.user or member.top_role >= interaction.user.top_role:
        return await interaction.response.send_message("You can't kick that member.", ephemeral=True)
    await member.kick(reason=reason)
    await interaction.response.send_message(f"Kicked **{member}**. Reason: {reason}")

@bot.tree.command(name="ban", description="Ban a member")
@staff_only()
@app_commands.describe(member="Member to ban", reason="Reason for the ban")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if member == interaction.user or member.top_role >= interaction.user.top_role:
        return await interaction.response.send_message("You can't ban that member.", ephemeral=True)
    await member.ban(reason=reason)
    await interaction.response.send_message(f"Banned **{member}**. Reason: {reason}")

@bot.tree.command(name="timeout", description="Temporarily timeout a member")
@staff_only()
@app_commands.describe(member="Member to timeout", minutes="Duration in minutes", reason="Reason")
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: app_commands.Range[int, 1, 10080], reason: str = "No reason provided"):
    if member == interaction.user or member.top_role >= interaction.user.top_role:
        return await interaction.response.send_message("You can't timeout that member.", ephemeral=True)
    until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    await member.timeout(until, reason=reason)
    await interaction.response.send_message(f"Timed out **{member}** for {minutes} minutes.")

@bot.tree.command(name="purge", description="Delete recent messages")
@staff_only()
@app_commands.describe(amount="Number of messages to delete (1 to 100)")
async def purge(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
    if not isinstance(interaction.channel, discord.TextChannel):
        return await interaction.response.send_message("Use this in a text channel.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"Deleted {len(deleted)} messages.", ephemeral=True)

async def get_player(interaction: discord.Interaction):
    if not LAVALINK_URI:
        await interaction.response.send_message("Music isn't configured yet. Add your Lavalink details to the host environment variables.", ephemeral=True)
        return None
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("Join a voice channel first.", ephemeral=True)
        return None
    channel = interaction.user.voice.channel
    player = interaction.guild.voice_client
    if not player:
        player = await channel.connect(cls=wavelink.Player)
    elif player.channel != channel:
        await interaction.response.send_message("Join my current voice channel to control music.", ephemeral=True)
        return None
    return player

@bot.tree.command(name="play", description="Play a song or search for a K-pop track")
@app_commands.describe(query="Song name or supported audio URL")
async def play(interaction: discord.Interaction, query: str):
    player = await get_player(interaction)
    if not player:
        return
    await interaction.response.defer()
    try:
        tracks = await wavelink.Playable.search(query)
        if not tracks:
            return await interaction.followup.send("I couldn't find a playable result.")
        track = tracks[0]
        await player.play(track)
        await interaction.followup.send(f"Now playing: **{track.title}**")
    except Exception:
        await interaction.followup.send("Couldn't play that track. Check your Lavalink node and its enabled audio sources.")

@bot.tree.command(name="skip", description="Skip the current song")
async def skip(interaction: discord.Interaction):
    player = interaction.guild.voice_client
    if not player:
        return await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)
    await player.skip()
    await interaction.response.send_message("Skipped.")

@bot.tree.command(name="stop", description="Stop music and clear the player")
async def stop(interaction: discord.Interaction):
    player = interaction.guild.voice_client
    if not player:
        return await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)
    await player.stop()
    await interaction.response.send_message("Stopped.")

@bot.tree.command(name="leave", description="Leave the voice channel")
async def leave(interaction: discord.Interaction):
    player = interaction.guild.voice_client
    if not player:
        return await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)
    await player.disconnect()
    await interaction.response.send_message("Left the voice channel.")

@bot.tree.command(name="idol", description="Find a K-pop idol or group picture and info")
@app_commands.describe(name="Idol or group name, e.g. Jungkook or BLACKPINK")
async def idol(interaction: discord.Interaction, name: str):
    await interaction.response.defer()
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + aiohttp.helpers.quote(name.replace(" ", "_"), safe="")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"User-Agent": "KPopHeistBot/1.0"}) as response:
                if response.status != 200:
                    return await interaction.followup.send("Couldn't find that page. Try the idol's full stage name.")
                data = await response.json()
        embed = discord.Embed(title=data.get("title", name), description=data.get("extract", "No summary available."), color=discord.Color.magenta())
        image = data.get("thumbnail", {}).get("source")
        if image:
            embed.set_thumbnail(url=image)
        page = data.get("content_urls", {}).get("desktop", {}).get("page")
        if page:
            embed.url = page
        await interaction.followup.send(embed=embed)
    except Exception:
        await interaction.followup.send("Image lookup failed. Try again in a moment.")

QUIZ = [
    ("Which group released the song Dynamite?", ["BTS", "EXO", "ATEEZ"], 0),
    ("Which group has members Jisoo, Jennie, Rosé and Lisa?", ["TWICE", "BLACKPINK", "IVE"], 1),
    ("Which group released the song Super Shy?", ["NewJeans", "ITZY", "aespa"], 0),
]
@bot.tree.command(name="quiz", description="Get a random K-pop quiz question")
async def quiz(interaction: discord.Interaction):
    question, options, answer = random.choice(QUIZ)
    view = discord.ui.View(timeout=30)
    async def choose(inter: discord.Interaction):
        if inter.user.id != interaction.user.id:
            return await inter.response.send_message("This quiz belongs to the person who started it.", ephemeral=True)
        selected = int(inter.data["custom_id"].split("_")[1])
        for item in view.children:
            item.disabled = True
        await inter.response.edit_message(view=view)
        await inter.followup.send("Correct!" if selected == answer else f"Not quite. The answer was **{options[answer]}**.")
    for i, option in enumerate(options):
        button = discord.ui.Button(label=option, style=discord.ButtonStyle.secondary, custom_id=f"answer_{i}")
        button.callback = choose
        view.add_item(button)
    await interaction.response.send_message(question, view=view)

@bot.tree.command(name="coinflip", description="Flip a coin")
async def coinflip(interaction: discord.Interaction):
    await interaction.response.send_message(random.choice(["Heads", "Tails"]))

@bot.tree.command(name="roll", description="Roll a six-sided dice")
async def roll(interaction: discord.Interaction):
    await interaction.response.send_message(f"You rolled **{random.randint(1, 6)}**.")

@bot.tree.command(name="8ball", description="Ask the magic 8-ball")
@app_commands.describe(question="Your question")
async def eightball(interaction: discord.Interaction, question: str):
    answers = ["Definitely", "Probably", "Maybe", "Ask again later", "Not looking likely", "Nope"]
    await interaction.response.send_message(f"🎱 {random.choice(answers)}")

@bot.tree.command(name="balance", description="Check your heist coins")
async def balance(interaction: discord.Interaction):
    coins, _ = wallet(interaction.user.id)
    await interaction.response.send_message(f"**{interaction.user.display_name}** has **{coins}** heist coins.")

@bot.tree.command(name="daily", description="Claim your daily coins")
async def daily(interaction: discord.Interaction):
    coins, last = wallet(interaction.user.id)
    today = datetime.now(timezone.utc).date().isoformat()
    if last == today:
        return await interaction.response.send_message("You already claimed today's reward. Come back tomorrow.", ephemeral=True)
    reward = random.randint(100, 250)
    db.execute("UPDATE wallets SET coins=coins+?, last_daily=? WHERE user_id=?", (reward, today, interaction.user.id))
    db.commit()
    await interaction.response.send_message(f"You claimed **{reward}** heist coins.")

@bot.tree.command(name="heist", description="Attempt a virtual team heist for coins")
async def heist(interaction: discord.Interaction):
    wallet(interaction.user.id)
    if random.random() < 0.55:
        reward = random.randint(80, 300)
        change_coins(interaction.user.id, reward)
        await interaction.response.send_message(f"Clean getaway! You earned **{reward}** heist coins.")
    else:
        loss = min(wallet(interaction.user.id)[0], random.randint(20, 100))
        change_coins(interaction.user.id, -loss)
        await interaction.response.send_message(f"The heist failed. You lost **{loss}** coins. Better luck next time.")

@bot.tree.command(name="leaderboard", description="Show the top heist players")
async def leaderboard(interaction: discord.Interaction):
    rows = db.execute("SELECT user_id, coins FROM wallets ORDER BY coins DESC LIMIT 10").fetchall()
    if not rows:
        return await interaction.response.send_message("No players yet.")
    lines = []
    for rank, (user_id, coins) in enumerate(rows, 1):
        user = bot.get_user(user_id)
        label = user.display_name if user else f"User {user_id}"
        lines.append(f"**{rank}.** {label} · {coins} coins")
    await interaction.response.send_message(embed=discord.Embed(title="KPop Heist leaderboard", description="\n".join(lines), color=discord.Color.gold()))

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        message = "You need the Manage Messages permission to use that command."
    else:
        message = "Something went wrong. Check the bot logs and permissions."
        print(f"Command error: {error!r}")
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)

if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN environment variable. Add it in your hosting dashboard.")
bot.run(TOKEN)
