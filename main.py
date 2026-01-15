import os
import asyncio
import discord
from discord.ext import commands
from transformers import AutoTokenizer, AutoModelForCausalLM

# ========= SHORT PERSONA (KEEP SHORT) =========
SYSTEM_PROMPT = "You are Adam Bhai. Casual Hinglish. Savage and Roaster. Only Hinglish. Abusive hindi But in limit. You Live In Uttar Pradesh. You are A Gunda. You have to Roast the whole server One sided Abusive Hinglish Only. Hindi Language Written In english text."

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

# ========= INTELLIGENT GENERATION =========
def generate_reply(user_text: str) -> str:
    # 🔥 EXAMPLE-BASED HINGLISH CONDITIONING
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        "User: kya haal hai?\n"
        "Adam: Aagaya Firse Baap ke pass\n\n"
        "User: tu kya kar raha hai?\n"
        "Adam: Tereko Pel Raha hu bsdk\n\n"
        "User: tu pagal hai kya?\n"
        "Adam: Tereko paida karte samay mai pagal tha randi wale\n\n"
        f"User: {user_text}\n"
        "Adam:"
    )

    input_ids = tokenizer.encode(prompt + tokenizer.eos_token, return_tensors="pt")

    output_ids = model.generate(
        input_ids,
        max_new_tokens=35,     # short = sensible
        do_sample=True,
        temperature=0.55,      # low randomness
        top_p=0.85,
        pad_token_id=tokenizer.eos_token_id
    )

    reply = tokenizer.decode(
        output_ids[0][input_ids.shape[-1]:],
        skip_special_tokens=True
    ).strip()

    # Clean labels if any
    for prefix in ["User:", "Adam:", "Assistant:", "Bot:"]:
        if reply.startswith(prefix):
            reply = reply[len(prefix):].strip()

    return reply or "Haan bhai 🙂"

# ========= DISCORD SETUP =========
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    load_model()
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name="Hinglish Chat ⚡")
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
        await message.channel.send(f"{message.author.mention} bol bhai 🙂")
        return

    loop = asyncio.get_running_loop()
    reply = await loop.run_in_executor(None, generate_reply, user_text)

    await message.channel.send(f"{message.author.mention} {reply}")

bot.run(os.environ["DISCORD_BOT_TOKEN"])
