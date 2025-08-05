import discord
from discord.ext import commands, tasks
import logging
from dotenv import load_dotenv
import os
from discord.ext.commands import BucketType
import math
import sqlite3
import asyncio
import random

# --- ENV & LOGGING ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

# --- BOT CONFIG ---
GENERAL_CHAT_ID = 1255719327353671780
GAME_ROLE_ID = 1402155771147583578
REVIVE_ROLE_ID = 1309705645003374725  # role to ping with !ping
SUGGEST_CHANNEL_ID = 1402152463074594961 # The channel where suggestions should go

WIN_TARGET = 15  # Wins needed for the role

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# --- DATABASE SETUP ---
conn = sqlite3.connect('gamebot.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS wins (
    user_id INTEGER PRIMARY KEY,
    wins INTEGER DEFAULT 0
)''')
conn.commit()

# --- REVIVE QUESTIONS ---
questions = [
    # 🔥 Hypotheticals & Discussion (50)
    'If you could pause time for one hour every day, what would you do during that hour? ⏰✨',
    'You wake up as the opposite gender for 24 hours—what’s the first thing you do? 👩➡️👨',
    'If you could instantly master any skill in the world, which one would you pick? 🎨🎸',
    'You get $10,000 but can only spend it in 24 hours—what do you buy? 💰🛍️',
    'If you could swap lives with any fictional character for a week, who would it be? 🎥📖',
    'You can teleport anywhere, but you can never return to the place you leave. Where’s the first place you go? 🌍✈️',
    'If the internet suddenly disappeared for a week, how would you spend your time? 🌲📴',
    'You can time travel, but only once—do you go to the past or the future? ⏳🔮',
    'If you could speak every language fluently, what would you do first? 🗣️🌐',
    'Imagine Earth gets visited by aliens tomorrow. What’s the first thing you’d ask them? 👽🌎',
    'Would you rather live in a world without music or without video games? 🎵🎮',
    'If you had to delete one app from existence forever, which would it be? 📱🚫',
    'Would you rather always have slow Wi-Fi or always low battery? 📶🔋',
    'Which is better: being rich but unknown, or famous but broke? 💸🌟',
    'Unlimited tacos 🌮 or unlimited pizza 🍕 for life?',
    'What’s a small decision that changed your life in a big way? 🌱✨',
    'If you could redo one day in your life, which would it be? 🔄📅',
    'What’s the most underrated hobby or interest people should try? 🧩🎣',
    'If you had a warning label, what would yours say? ⚠️📝',
    'What’s a childhood dream you still secretly want to achieve? 🌈🚀',
    'If emotions were colors, what color is today for you? 🎨💖',
    'If you had to live in any video game world for a month, which would you choose? 🎮🏰',
    'Would you rather always be 10 minutes late or 20 minutes early? ⏰🤷',
    'If you could swap places with your pet for a day, what would you do? 🐶😹',
    'Which holiday would you celebrate every day if you could? 🎄🎉',
    'Would you rather explore the deep ocean or outer space? 🌊🚀',
    'If you could only keep 3 apps on your phone, which would they be? 📱3️⃣',
    'Would you rather live in the 1800s or 2100s? 🕰️🔮',
    'If you could turn any hobby into a full-time career, what would it be? 🎨🎤',
    'Would you rather never age physically or never age mentally? 🧠💪',
    'If you could add one law to the world, what would it be? ⚖️🌎',
    'If you could have dinner with any fictional character, who would it be? 🍽️📖',
    'Would you rather speak to animals or read minds? 🐕🧠',
    'If you could erase one thing from existence, what would it be? ❌🌍',
    'Would you rather always have perfect weather or never get sick? ☀️💊',
    'If money didn’t exist, what would you spend your life doing? 🏝️🎨',
    'Would you rather always know when someone is lying or get away with every lie? 🤥🕵️',
    'If you could swap lives with a celebrity for a day, who would it be? 🎤🎬',
    'Would you rather have free travel anywhere or free food forever? ✈️🍽️',
    'If you had to live in one season forever, which would you pick? ❄️☀️',
    'Would you rather breathe underwater or fly? 🌊🕊️',
    'If you could revive one extinct animal, which would it be? 🦣🦤',
    'Would you rather live in a treehouse or on a boat? 🌳🚤',
    'If you had to eat the same meal for a month, what would it be? 🍜🍔',
    'Would you rather live with no music or no movies forever? 🎬🚫',
    'If you had a theme song that played every time you entered a room, what would it be? 🎵🚪',
    'Would you rather have a talking pet or a self-cleaning house? 🐕🧹',
    'If you could trade lives with someone in this server for a day, who would it be? 🔄💬',
    'Would you rather only whisper or only shout for the rest of your life? 🤫📢',
]

# --- FUNCTIONS ---
async def add_win(user: discord.Member):
    """Add a win to a user, check for role assignment."""
    c.execute('SELECT wins FROM wins WHERE user_id=?', (user.id,))
    row = c.fetchone()

    if row:
        new_wins = row[0] + 1
        c.execute('UPDATE wins SET wins=? WHERE user_id=?', (new_wins, user.id))
    else:
        new_wins = 1
        c.execute('INSERT INTO wins (user_id, wins) VALUES (?, ?)', (user.id, new_wins))
    conn.commit()

    # Check for role reward
    if new_wins == WIN_TARGET:
        role = user.guild.get_role(GAME_ROLE_ID)
        if role:
            await user.add_roles(role)
            channel = bot.get_channel(GENERAL_CHAT_ID)
            embed = discord.Embed(
                title='🏆 Role Earned!',
                description=f'{user.mention} has reached **{WIN_TARGET} wins** and earned the **{role.name}** role!',
                colour=discord.Colour.pink()
            )
            await channel.send(embed=embed)

async def start_game():
    """Randomly start a mini-game in general chat."""
    channel = bot.get_channel(GENERAL_CHAT_ID)
    game = random.choice(['reaction', 'typerace', 'trivia', 'guess'])

    if game == 'reaction':
        word = random.choice(['BANANA', 'PINK', 'WINNER', 'DISCORD'])
        embed = discord.Embed(
            title='⚡ Speed Reaction!',
            description=f'First to type **{word}** wins!',
            colour=discord.Colour.pink()
        )
        await channel.send(embed=embed)

        def check(m):
            return m.content.upper() == word and m.channel.id == channel.id

        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            await add_win(msg.author)
            await channel.send(f'🎉 {msg.author.mention} wins!')
        except asyncio.TimeoutError:
            await channel.send('⏱️ Nobody reacted in time!')

    elif game == 'typerace':
        sentence = random.choice([
            'Akat is the most tuffest owner!',
            'I am the best admin between nori and wasabi!',
            'Dg sucks!', 'You are very lame!'
        ])
        embed = discord.Embed(
            title='⌨️ Typing Race!',
            description=f'First to type this **exactly** wins:\n\n`{sentence}`',
            colour=discord.Colour.pink()
        )
        await channel.send(embed=embed)

        def check(m):
            return m.content == sentence and m.channel.id == channel.id

        try:
            msg = await bot.wait_for('message', check=check, timeout=40.0)
            await add_win(msg.author)
            await channel.send(f'🎉 {msg.author.mention} wins the typing race!')
        except asyncio.TimeoutError:
            await channel.send('⏱️ No one finished in time!')

    elif game == 'trivia':
        qa = random.choice([
            ('What is the largest planet in our solar system?', 'jupiter'),
            ('Which ocean is the deepest in the world?', 'pacific'),
            ('What is the chemical symbol for gold?', 'au'),
            ('Who painted the Mona Lisa?', 'leonardo da vinci'),
            ('Which country has the most islands in the world?', 'sweden'),
            ('What is the rarest blood type?', 'ab-'),
            ('What is the fastest land animal?', 'cheetah'),
            ('How many bones are in the human body?', '206'),
            ('Which planet has the most moons?', 'saturn'),
            ('What is the largest desert in the world?', 'sahara'),
            ('Who wrote "Romeo and Juliet"?', 'shakespeare'),
            ('What is the capital of Canada?', 'ottawa'),
            ('What gas do plants absorb from the air?', 'carbon dioxide'),
            ('Which country invented pizza?', 'italy'),
            ('What is the smallest prime number?', '2'),
            ('Which continent is also a country?', 'australia'),
            ('What is the hardest natural substance?', 'diamond'),
            ('Which sea creature has three hearts?', 'octopus'),
            ('What is the largest mammal in the world?', 'blue whale'),
            ('How many stripes are on the US flag?', '13'),
        ])
        question, answer = qa
        embed = discord.Embed(
            title='❓ Trivia Time!',
            description=f'{question}\n*(Answer in 30s!)*',
            colour=discord.Colour.pink()
        )
        await channel.send(embed=embed)

        def check(m):
            return m.content.lower() == answer.lower() and m.channel.id == channel.id

        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            await add_win(msg.author)
            await channel.send(f'🎉 Correct! {msg.author.mention} wins!')
        except asyncio.TimeoutError:
            await channel.send('⏱️ Nobody got the answer!')

    elif game == 'guess':
        number = random.randint(1, 50)
        embed = discord.Embed(
            title='🔢 Number Guess!',
            description='Guess a number between **1 and 50**. First correct wins!',
            colour=discord.Colour.pink()
        )
        await channel.send(embed=embed)

        def check(m):
            return m.channel.id == channel.id and m.content.isdigit() and int(m.content) == number

        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            await add_win(msg.author)
            await channel.send(f'🎉 {msg.author.mention} guessed the number **{number}**!')
        except asyncio.TimeoutError:
            await channel.send(f'⏱️ Time’s up! The number was **{number}**.')

# --- COMMANDS ---
@bot.command()
@commands.cooldown(1, 7200, BucketType.guild)
async def ping(ctx):
    role = ctx.guild.get_role(REVIVE_ROLE_ID)
    question = random.choice(questions)
    await ctx.send(f'{role.mention} **{question}**')

@ping.error
async def ping_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        hours = math.floor(error.retry_after / 3600)
        minutes = math.floor((error.retry_after % 3600) / 60)
        embed = discord.Embed(
            title='⏳ Command on Cooldown',
            description=f'You can ping again in **{hours}h {minutes}m**',
            colour=discord.Colour.pink()
        )
        await ctx.send(embed=embed)


@bot.command()
async def suggest(ctx, *, suggestion: str):
    """Send a suggestion to the staff channel."""
    if len(suggestion) < 5:
        await ctx.send("❌ Your suggestion is too short!")
        return

    # 1. Confirm in chat
    await ctx.send("✅ Your suggestion has been sent to the staff team!")

    # 2. Send the suggestion to staff channel
    staff_channel = bot.get_channel(SUGGEST_CHANNEL_ID)
    if staff_channel:
        embed = discord.Embed(
            title="💡 New Suggestion",
            description=suggestion,
            color=discord.Color.pink()
        )
        embed.set_footer(text=f"Suggested by {ctx.author} • ID: {ctx.author.id}")

        msg = await staff_channel.send(embed=embed)
        await msg.add_reaction("✅")  # Staff can react to approve
        await msg.add_reaction("❌")  # Staff can react to reject
    else:
        await ctx.send("⚠️ Suggestion channel not found!")


# --- EVENTS ---
@bot.event
async def on_ready():
    print(f'✅ {bot.user} is online!')
    chat_reminder.start()

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(GENERAL_CHAT_ID)
    if channel:
        embed = discord.Embed(
            title='🎉 Welcome to the server!',
            description=f'Welcome **{member.mention}** to the basement!',
            colour=discord.Colour.pink()
        )
        await channel.send(embed=embed)

# --- LOOPS ---
@tasks.loop(minutes=30)
async def chat_reminder():
    """Send revive embed every 30 mins, then 10 mins later start a mini-game."""
    channel = bot.get_channel(GENERAL_CHAT_ID)
    if channel:
        embed = discord.Embed(
            title='💬 Chat Feeling Quiet?',
            description='Use `!ping` to revive the chat!',
            colour=discord.Colour.pink()
        )
        embed.set_footer(text='Your landlord is watching over the basement!')
        await channel.send(embed=embed)

    # Wait 10 mins, then start a mini-game
    await asyncio.sleep(600)
    await start_game()


# --- RUN ---
bot.run(TOKEN, log_handler=handler, log_level=logging.DEBUG)

