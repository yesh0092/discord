import os
import asyncio
import discord
from discord.ext import commands
from transformers import AutoTokenizer, AutoModelForCausalLM

# ========= SHORT SYSTEM PROMPT (<= 100 chars) =========
SYSTEM_PROMPT = "You are Adam Bhai. Casual Hinglish. Confident, witty, playful tone."

MODEL_NAME = "microsoft/DialoGPT-small"

tokenizer = None
model = None

def load_model():
    global tokenizer, model
    if tokenizer is None or model is None:
        print("⏳ Loading model...")
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME,
            padding_side="left"
        )
        model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
        model.eval()
        print("✅ Model loaded")

# ========= AI GENERATION (RUNS IN BACKGROUND THREAD) =========
def generate_reply(user_text: str) -> str:
    # 🔥 BEHAVIOR PREFIX + EXAMPLE (THIS IS THE MAGIC)
    prompt = (
        f"{SYSTEM_PROMPT}\n"
        "Adam replies in short Hinglish sentences.\n"
        "Tone is playful, confident, and friendly.\n\n"
        "User: kya haal hai?\n"
        "Adam: Mast bhai 😄 bol kya scene hai?\n\n"
        f"User: {user_text}\n"
        "Adam:"
    )

    input_ids = tokenizer.encode(prompt + tokenizer.eos_token, return_tensors="pt")

    output_ids = model.generate(
        input_ids,
        max_new_tokens=60,
        do_sample=True,
        temperature=0.8,
        top_p=0.9,
        pad_token_id=tokenizer.eos_token_id
    )

    reply = tokenizer.decode(
        output_ids[0][input_ids.shape[-1]:],
        skip_special_tokens=True
    )

    return reply.strip() or "Haan bhai 🙂"

# ========= DISCORD SETUP =========
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    load_model()
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name="Chatting 💬")
    )
    print(f"🤖 Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Reply only when mentioned
    if bot.user not in message.mentions:
        return

    user_text = message.content.replace(f"<@{bot.user.id}>", "").strip()
    if not user_text:
        await message.channel.send("Bol bhai 🙂")
        return

    loop = asyncio.get_running_loop()
    reply = await loop.run_in_executor(None, generate_reply, user_text)

    await message.channel.send(reply)

bot.run(os.environ["DISCORD_BOT_TOKEN"])
