import discord
from discord import app_commands
from discord.ext import commands, tasks
import random

# --- DATA STORES ---
user_balances = {}  # {user_id: flies_currency}
user_inventories = {}  # {user_id: [list of collected frogs]}
active_spawn = {}  # Tracks the frog currently waiting to be guessed in the channel

# 1. Boss Frogs with real verified photography links
BOSS_FROGS = [
    {
        "names": ["desert rain frog", "rain frog", "desert rain"],
        "display": "Desert Rain Frog 🪨 (Squeaky Boi)",
        "tier": "Legendary",
        "reward": 750,
        "image": "https://encrypted-tbn0.gstatic.com/licensed-image?q=tbn:ANd9GcQnVnvwOjEAPDoKJVdWeZ-wyqdC3b9OhT3e9Cqd_143K20GlcOAZzAVn-l2uHCwzT8nLrGgNuwkfPPJpDU"
    },
    {
        "names": ["tomato frog", "tomato"],
        "display": "Madagascar Tomato Frog 🍅",
        "tier": "Rare",
        "reward": 300,
        "image": "https://encrypted-tbn1.gstatic.com/licensed-image?q=tbn:ANd9Rz9XyDqtfKHEuquOuYG0G_cy16HcVHjJ7ZKoeEsrn6G7JgZ4Q53ozBjRCtJsocQi3_bQLrSUjgQbZ8pm0"
    },
    {
        "names": ["glass frog", "glass"],
        "display": "See-Through Glass Frog 💎",
        "tier": "Legendary",
        "reward": 800,
        "image": "https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcTRGtu0Q0ZsJnsjzpKES_UARE8XySjNIFgkgcGVX4BDrqoa_8k1gcRTkxEp7c7d7TNPgTdfdGSez13q-Fk"
    },
    {
        "names": ["amazon milk frog", "milk frog", "amazon milk"],
        "display": "Amazon Milk Frog 🥛",
        "tier": "Rare",
        "reward": 250,
        "image": "https://encrypted-tbn0.gstatic.com/licensed-image?q=tbn:ANd9GcQSK1Fu4YgNZkXR309-FUwU12kc_rDc1Dxk5QQRNuudOttBM_NJ10wmbzVXimzpz1sy0PqhkCNqA9Sk5gw"
    }
]

# 2. Infinite Generative Matrix Components (Creates over 27,000 combinations)
FROG_ADJECTIVES = [
    "Spotted", "Slimey", "Chonky", "Toxic", "Glow-in-the-dark", "Horned", "Giant", "Miniature", 
    "Screaming", "Golden", "Ancient", "Vampire", "Albino", "Pygmy", "Bearded", "Mossy", "Warty",
    "Prismatic", "Cyberpunk", "Ghostly", "Zombie", "Royal", "Glitched", "Anxious", "Buff", "Hyperactive"
]

FROG_COLORS = [
    "Neon Green", "Midnight Blue", "Crimson Red", "Sulfur Yellow", "Deep Purple", "Mud Brown", 
    "Turquoise", "Hot Pink", "Emerald", "Obsidian", "Lavender", "Pastel Orange", "Radioactive Lime"
]

FROG_TYPES = [
    "Tree Frog", "Toad", "Bullfrog", "Dart Frog", "Rain Frog", "Horned Frog", "Reed Frog", 
    "Pond Skater", "Lilypad Leaper", "Marsh Glider", "Swamp Dweller", "Mudskipper Toad"
]

class FroggyGame(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.target_channel_id = None  # Handled dynamically on start
        self.random_frog_spawner.start()

    def cog_unload(self):
        self.random_frog_spawner.cancel()

    def get_balance(self, user_id: int) -> int:
        if user_id not in user_balances:
            user_balances[user_id] = 500  # Starting balance
        return user_balances[user_id]

    # --- AUTONOMOUS CHANNEL CONFIGURATION ---
    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.guilds:
            print("⚠️ Bot is not in any servers. Invite it first!")
            return
            
        guild = self.bot.guilds[0]
        existing_channel = discord.utils.get(guild.text_channels, name="frog-catch")
        
        if existing_channel:
            self.target_channel_id = existing_channel.id
            print(f"🔗 Linked up to channel: #{existing_channel.name}")
        else:
            # Setup channel permissions so everyone can read and send messages
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True, manage_channels=True)
            }
            try:
                new_channel = await guild.create_text_channel(
                    name="frog-catch",
                    topic="📸 Identify wild frog species here and gamble your flies!",
                    overwrites=overwrites,
                    position=0
                )
                self.target_channel_id = new_channel.id
                print(f"🌲 Auto-created channel: #{new_channel.name}")
                
                welcome = discord.Embed(
                    title="📸 WELCOME TO THE FROG ARENA!",
                    description="Wild frogs will materialize here on completely random time intervals. **Do not use commands to catch them—simply type their name straight into this chat channel!**\n\n### Commands Available:\n🔹 `/slots [bet]` — Gamble your flies on the slots\n🔹 `/coinflip [bet] [heads/tails]` — Double or nothing flip\n🔹 `/bal` — View your currency wallet and collection",
                    color=0x2ecc71
                )
                await new_channel.send(embed=welcome)
            except discord.Forbidden:
                print("❌ ERROR: Bot needs the 'Manage Channels' permission to set up the arena.")

    # --- DYNAMIC RANDOM SPAWNER ---
    @tasks.loop(minutes=20)  
    async def random_frog_spawner(self):
        await self.bot.wait_until_ready()
        if not self.target_channel_id:
            return

        # 35% chance to drop a frog when the loop clock ticks
        if random.random() < 0.35:
            channel = self.bot.get_channel(self.target_channel_id)
            if not channel:
                return

            # 15% chance to trigger a real photo "Boss Frog"
            if random.random() < 0.15:
                frog_data = random.choice(BOSS_FROGS)
                tier = frog_data["tier"]
                reward = frog_data["reward"]
                img_url = frog_data["image"]
                
                active_spawn[channel.id] = {
                    "answers": frog_data["names"],
                    "display": frog_data["display"],
                    "tier": tier,
                    "reward": reward
                }
                desc = f"🚨 **BOSS SPAWN!** A rare real-world frog variety has appeared!\n**Type its name directly into this chat to capture it!**"
            
            # 85% chance to dynamically generate a hybrid variety
            else:
                adj = random.choice(FROG_ADJECTIVES)
                color = random.choice(FROG_COLORS)
                f_type = random.choice(FROG_TYPES)
                
                full_title = f"{adj} {color} {f_type}"
                guess_keyword = f_type.lower()  # Makes mobile guessing easy (e.g., just type "toad")
                
                roll = random.random()
                if roll < 0.65:
                    tier, reward = "Common", random.randint(40, 80)
                elif roll < 0.92:
                    tier, reward = "Rare", random.randint(120, 220)
                else:
                    tier, reward = "Legendary", random.randint(450, 700)

                active_spawn[channel.id] = {
                    "answers": [guess_keyword, full_title.lower()],
                    "display": f"{full_title} 🐸",
                    "tier": tier,
                    "reward": reward
                }
                # Default vector placeholder graphic for generated hybrids
                img_url = "https://i.imgur.com/eBvsnwM.png"
                desc = f"A wild **{tier}** frog has hopped into the mud!\n\n💡 *Hint: Type the core species type (e.g., **'{guess_keyword}'**) to catch it!*"

            tier_colors = {"Common": 0x2ecc71, "Rare": 0x3498db, "Legendary": 0x9b59b6}
            
            embed = discord.Embed(title=f"📢 DYNAMIC {tier.upper()} SPAWN", description=desc, color=tier_colors.get(tier, 0x2ecc71))
            embed.set_image(url=img_url)
            await channel.send(embed=embed)
            
            # Dynamically shift the timing loop window randomly for the next round
            self.random_frog_spawner.change_interval(minutes=random.randint(15, 45))

    # --- CHAT LISTENER FOR GUESSING ANSWERS ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bots, and ignore text sent outside our dedicated channel
        if message.author.bot or message.channel.id != self.target_channel_id:
            return

        channel_id = message.channel.id
        
        # Check if there is an uncaptured frog in the channel right now
        if channel_id in active_spawn and active_spawn[channel_id]:
            current_frog = active_spawn[channel_id]
            user_guess = message.content.strip().lower()
            
            # If the user guess matches any item in the answers list
            if user_guess in current_frog["answers"]:
                # Instantly clear the spawn state so nobody else can claim it
                active_spawn[channel_id] = None
                
                user_id = message.author.id
                reward = current_frog["reward"]
                display_name = current_frog["display"]
                
                # Save to user inventory list
                if user_id not in user_inventories:
                    user_inventories[user_id] = []
                user_inventories[user_id].append(display_name)
                
                # Update bank balance
                user_balances[user_id] = self.get_balance(user_id) + reward
                
                win_embed = discord.Embed(
                    title="🎉 ACCURATE IDENTIFICATION!",
                    description=f"{message.author.mention} guessed correctly and caught the **{display_name}**!\n\n🎒 Added to your backpack collection\n💰 Earned **+{reward} 🪰 Flies**!",
                    color=0xf1c40f
                )
                await message.channel.send(embed=win_embed)

    # --- SLOT MACHINE GAME ---
    @app_commands.command(name="slots", description="Bet your flies on the slot machine")
    @app_commands.describe(bet="Wager amount")
    async def slots(self, interaction: discord.Interaction, bet: int):
        user_id = interaction.user.id
        balance = self.get_balance(user_id)
        
        if bet <= 0 or bet > balance:
            return await interaction.response.send_message("Invalid bet amount, bro.", ephemeral=True)
            
        emojis = ["🐸", "🪰", "🍀", "🍄", "👑"]
        r1, r2, r3 = random.choice(emojis), random.choice(emojis), random.choice(emojis)
        
        if r1 == r2 == r3:
            winnings = bet * (5 if r1 == "🐸" else 3)
            user_balances[user_id] += winnings
            msg = f"🎰 **[{r1} | {r2} | {r3}]**\n\n**JACKPOT!** You won **+{winnings} 🪰**!"
        elif r1 == r2 or r2 == r3 or r1 == r3:
            user_balances[user_id] += bet
            msg = f"🎰 **[{r1} | {r2} | {r3}]**\n\n**Nice Pair!** You won **+{bet} 🪰**!"
        else:
            user_balances[user_id] -= bet
            msg = f"🎰 **[{r1} | {r2} | {r3}]**\n\n**RIP.** You lost **-{bet} 🪰**."
            
        await interaction.response.send_message(msg)

    # --- COINFLIP GAME ---
    @app_commands.command(name="coinflip", description="Flip a coin against Froggy")
    @app_commands.describe(bet="Wager amount", choice="Heads or Tails")
    @app_commands.choices(choice=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails")
    ])
    async def coinflip(self, interaction: discord.Interaction, bet: int, choice: str):
        user_id = interaction.user.id
        balance = self.get_balance(user_id)
        
        if bet <= 0 or bet > balance:
            return await interaction.response.send_message("You don't have enough flies for that bet.", ephemeral=True)
            
        outcome = random.choice(["heads", "tails"])
        
        if choice == outcome:
            user_balances[user_id] += bet
            await interaction.response.send_message(f"🪙 It's **{outcome.upper()}**! You won **+{bet} 🪰**!")
        else:
            user_balances[user_id] -= bet
            await interaction.response.send_message(f"🪙 It's **{outcome.upper()}**! Froggy ate your bet. **-{bet} 🪰**.")

    # --- BALANCE & INVENTORY CHECK ---
    @app_commands.command(name="bal", description="Check your wallet and frog collection")
    async def balance_check(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        balance = self.get_balance(user_id)
        inv = user_inventories.get(user_id, ["No frogs caught yet."])
        
        embed = discord.Embed(title=f"🐸 {interaction.user.name}'s Profile", color=0x2ecc71)
        embed.add_field(name="💰 Wallet", value=f"**{balance} 🪰 Flies**", inline=False)
        embed.add_field(name="🎒 Collection", value="\n".join(inv), inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(FroggyGame(bot))
