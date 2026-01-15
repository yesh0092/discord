import os
import asyncio
import discord
from discord.ext import commands
from transformers import AutoTokenizer, AutoModelForCausalLM
import re

# ========= SHORT SYSTEM PROMPT =========
SYSTEM_PROMPT = "Tu Adam Bhai hai – Ghaziabad ka gunda, Yash ka bhai, full savage Hinglish roasting king. Thoda abusive, thoda mazedaar, kabhi soft bhi ho jaata hai par gussa bhi dikha deta hai."

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
        tokenizer.pad_token = tokenizer.eos_token   # fix padding warning
        model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
        model.eval()
        print("✅ Model loaded")

# ========= CHECK IF TEXT LOOKS LIKE HINGLISH =========
def looks_hinglish(text: str) -> bool:
    hindi_words = [
        "bhai", "kya", "kaise", "haan", "nahi", "mast", "scene",
        "chal", "bolo", "bata", "theek", "arey", "yaar", "madarchod",
        "bhenchod", "harami", "lavde", "gandu", "bhosdike"
    ]
    text_lower = text.lower()
    return any(word in text_lower for word in hindi_words)

# ========= FAST + ADAM PERSONALITY GENERATION =========
def generate_reply(user_text: str) -> str:
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        "Examples (short, tez, thoda abusive par kabhi playful bhi):\n"
        "User: kya haal hai bhai?\n"
        "Adam: Thik-thak hu madarchod, tu itna pyaar se pooch raha hai aaj? 😂🔥\n\n"
        "User: tu kaun hai?\n"
        "Adam: Adam Bhai hu lavde, Ghaziabad se, tera baap banne aaya hu 😈🖕\n\n"
        "User: sorry bhai galti ho gayi\n"
        "Adam: Arre bhen ke laude sorry bol diya? Chal maaf kiya, agli baar dimag laga lena 🤡👊\n\n"
        "User: help chahiye yaar\n"
        "Adam: Bol na harami kya chahiye, seedha-seedha bata, time waste mat kar 😏💀\n\n"
        "User: tu bura bol raha hai\n"
        "Adam: Haan bol raha hu toh kya, tujhe pasand nahi aaya kya chutiye? 😂🔥\n\n"
        f"User: {user_text}\n"
        "Adam:"
    )

    input_ids = tokenizer.encode(prompt + tokenizer.eos_token, return_tensors="pt")
    
    output_ids = model.generate(
        input_ids,
        max_new_tokens=40,          # thoda zyada rakha taaki savage fit ho
        do_sample=True,
        temperature=0.75,           # medium randomness – not too wild, not too boring
        top_p=0.9,
        repetition_penalty=1.15,    # kam repeat gaaliyan
        pad_token_id=tokenizer.eos_token_id
    )

    reply = tokenizer.decode(
        output_ids[0][input_ids.shape[-1]:],
        skip_special_tokens=True
    ).strip()

    # Clean unwanted prefixes
    for prefix in ["User:", "Adam:", "Assistant:", "Bot:"]:
        if reply.startswith(prefix):
            reply = reply[len(prefix):].strip()

    # Add 2–4 emojis if missing (Adam style)
    emojis = " 🔥😈🤡💀👊🖕😂"
    if not any(e in reply for e in emojis):
        reply += " " + emojis[:4]

    # Sanity check – force Hinglish vibe
    if len(reply) > 140 or not looks_hinglish(reply):
        return "Arey lavde seedha bol na kya chahiye 😈🔥"

    return reply or "Haan bhai bol na kuch toh sahi 😏🖕"

# ========= DISCORD SETUP =========
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    load_model()
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name="Ghaziabad ka Gunda 🔥😈")
    )
    print(f"🤖 Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.user not in message.mentions:
        return

    user_text = message.content.replace(f"<@{bot.user.id}>", "").strip()
    
    if not user_text:
        await message.channel.send(f"{message.author.mention} bol na gandu kuch toh! 😈🖕")
        return

    loop = asyncio.get_running_loop()
    reply = await loop.run_in_executor(None, generate_reply, user_text)
    
    # Mention user + reply
    await message.channel.send(f"{message.author.mention} {reply}")

bot.run(os.environ["DISCORD_BOT_TOKEN"])
