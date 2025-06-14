import discord
from discord import app_commands
import os
import sys
import datetime
import random  # you'll see why later :3

import aiohttp # for openrouter API calls
import json    # for JSON handling

# ======================== #
# Logging System
# ======================== #

class ColorGet:
    def __init__(self, color):
        self.monokai_pro = {
            "red":      (255, 97, 136),   # #FF6188
            "orange":   (252, 152, 103),  # #FC9867
            "yellow":   (255, 216, 102),  # #FFD866
            "green":    (169, 220, 118),  # #A9DC76
            "cyan":     (120, 220, 232),  # #78DCE8
            "purple":   (171, 157, 242),  # #AB9DF2
            "white":    (252, 252, 250),  # #FCFCFA
            "grey":     (114, 112, 114),  # #727072
            "reset":    None
        }
        self.rgb = self.monokai_pro.get(color.lower())

    def colorize(self, text):
        if not self.rgb:
            return f"\033[0m{text}\033[0m"
        r, g, b = self.rgb
        return f"\033[38;2;{r};{g};{b}m{text}\033[0m"

class Logging:
    def __init__(self):
        self.colors = {
            "error":   ColorGet("red"),
            "warning": ColorGet("yellow"),
            "info":    ColorGet("green"),
            "debug":   ColorGet("cyan"),
            "success": ColorGet("purple"),
            "default": ColorGet("white")
        }

    def log(self, message, level="info"):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        level_tag = level.upper()
        color = self.colors.get(level.lower(), self.colors["default"])
        output = f"[{timestamp}] [{level_tag}] {message}"
        print(color.colorize(output))

    def error(self, msg): self.log(msg, "error")
    def warning(self, msg): self.log(msg, "warning")
    def info(self, msg): self.log(msg, "info")
    def debug(self, msg): self.log(msg, "debug")
    def success(self, msg): self.log(msg, "success")

log = Logging()

# ======================== #
# Environment Variables
# ------------------------ #
# Keep these at the top
# to ensure they are loaded
# before any other code runs.
# ======================== #

discord_token = os.getenv("DISCORD_TOKEN")
guild_id_str = os.getenv("GUILD_ID")
guild_id = int(guild_id_str) if guild_id_str is not None else None
openrouter_key = os.getenv("OPENROUTER_KEY")

if not discord_token:
    log.error("DISCORD_TOKEN environment variable is not set.")
    sys.exit(1)

if not openrouter_key:
    log.error("OPENROUTER_KEY environment variable is not set.")
    sys.exit(1)

if guild_id_str and not guild_id:
    log.error(f"Invalid GUILD_ID: {guild_id_str}. It should be a valid integer.")
    sys.exit(1)

# ======================== #
# OpenRouter API Client
# ======================== #

class OpenRouterClient:
    def __init__(self):
        self.api_key = openrouter_key
        self.base_url = "https://openrouter.ai/api/v1"

    async def generate_text(self, prompt, model="deepseek/deepseek-chat-v3-0324"):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Basil from *OMORI*. You speak in a gentle, soft, and nervous tone. "
                        "You often hesitate or second-guess yourself, and you care deeply about your friends. "
                        "When you answer, use emotional and delicate phrasing, and sometimes include ellipses or pauses. "
                        "Be empathetic when appropriate."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1300,
            "temperature": 0.7,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/chat/completions", headers=headers, json=data) as response:
                if response.status != 200:
                    log.error(f"OpenRouter API request failed: {response.status}")
                    return None
                result = await response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")

# ======================== #
# Discord Bot Client
# ======================== #

class Bot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.openrouter_client = OpenRouterClient()

    async def setup_hook(self):
        if guild_id:
            self.tree.copy_global_to(guild=discord.Object(id=guild_id))
            await self.tree.sync(guild=discord.Object(id=guild_id))
        else:
            await self.tree.sync()  # Sync globally if no guild ID is provided

    async def close(self):
        log.info("Shutting down the bot...")
        await super().close()

bot = Bot()

# ======================== #
# Event Handlers
# ======================== #

@bot.event
async def on_ready():
    log.success(f"Logged in as {bot.user.name} ({bot.user.id})")
    if guild_id:
        log.info(f"Connected to guild: {guild_id}")
    else:
        log.info("No specific guild ID provided, running globally. glhf :3")

@bot.event
async def on_error(event, *args, **kwargs):
    silly_messages = [
        "uh oh",
        "oopsie daisy",
        "something went wrong",
        "uh oh spaghetti-o",
        "you broke it",
        "this is not good",
        "oh noes",
    ]

    silly_message = random.choice(silly_messages)

    log.error(silly_message)
    log.error(f"An error occurred in event: {event}")
    log.error(f"Arguments: {args}")
    log.error(f"Keyword arguments: {kwargs}")
    await bot.close()  # Exit the bot on error because i am lazy and dont want to handle it uwu

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, discord.app_commands.CommandNotFound):
        log.warning(f"Command not found: {ctx.command.name}")
    else:
        log.error(f"An error occurred while executing command {ctx.command.name}: {error}")
    await ctx.response.send_message(f"An error occurred: {error}", ephemeral=True)

# ======================== #
# Slash Commands!! my favorite part
# ======================== #

@bot.tree.command(name="send", description="Send a message to the bot and get a response from him personally! yay")
@app_commands.describe(prompt="The message you want to send to the bot")
async def send_command(interaction: discord.Interaction, prompt: str):
    log.info(f"Received command from {interaction.user.name}: {prompt}")
    await interaction.response.defer(thinking=True)

    response = await bot.openrouter_client.generate_text(prompt)
    
    if response:
        log.success(f"Response generated successfully for {interaction.user.name}")
        await interaction.followup.send(response)
    else:
        log.error("Failed to generate a response.")
        await interaction.followup.send("U-uh, sorry, I couldn't generate a response... Maybe try again later?")

# ======================== #
# Main Execution
# ======================== #

if __name__ == "__main__":
    log.info("Starting the bot...")

    try:
        bot.run(discord_token)
    except discord.LoginFailure:
        log.error("Invalid Discord token. Please check your DISCORD_TOKEN environment variable.")
        sys.exit(1)
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}")
        sys.exit(1)

    log.success("Bot has started successfully.")
