import os
import asyncio
import discord
from discord.ext import commands
from transformers import AutoTokenizer, AutoModelForCausalLM

# ================= PROMPT (KEEP SHORT) =================
SYSTEM_PROMPT = "Tu Adam bhai Ghaziabad ka gunda hai🔥 Server ki maa-behen ek taraf se pel! Short Hinglish roast, tag pe: \"Aa gaya firse baap ko yaad? 😈\" Heavy gaali maar!"

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

# ================= AI GENERATION (BLOCKING → THREAD) =================
def generate_reply(prompt: str) -> str:
    input_ids = tokenizer.encode(prompt + tokenizer.eos_token, return_tensors="pt")

    output_ids = model.generate(
        input_ids,
        max_new_tokens=60,   # keep small for CPU
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

# ================= DISCORD SETUP =================
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

    if bot.user not in message.mentions:
        return

    user_text = message.content.replace(f"<@{bot.user.id}>", "").strip()
    if not user_text:
        await message.channel.send("Bol bhai 🙂")
        return

    prompt = SYSTEM_PROMPT + " " + user_text

    # 🔥 RUN AI IN BACKGROUND THREAD (FIX)
    loop = asyncio.get_running_loop()
    reply = await loop.run_in_executor(None, generate_reply, prompt)

    await message.channel.send(reply)

bot.run(os.environ["DISCORD_BOT_TOKEN"])
