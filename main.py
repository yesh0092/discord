import os
import discord
from discord.ext import commands
from transformers import AutoTokenizer, AutoModelForCausalLM

# ================== IMPORTANT ==================
# KEEP THIS PROMPT SHORT (see rules below)
SYSTEM_PROMPT = "You are Adam bhai, Ghaziabad ka savage roaster 🔥 One-sided heavy roast poore server ko! Short Hinglish + emojis. Light abuses (chutiye, harami, lavde). Tag pe: "Aa gaya firse baap ko yaad? 😈" Fun but brutal!"

MODEL_NAME = "microsoft/DialoGPT-small"

tokenizer = None
model = None

def load_model():
    global tokenizer, model
    if tokenizer is None or model is None:
        print("⏳ Loading model at runtime...")
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME,
            padding_side="left"   # FIX for decoder-only models
        )
        model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
        model.eval()
        print("✅ Model loaded")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name="Chatting 💬")
    )
    print(f"🤖 Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # BOT REPLIES ONLY WHEN MENTIONED
    if bot.user not in message.mentions:
        return

    load_model()

    user_text = message.content.replace(f"<@{bot.user.id}>", "").strip()
    if not user_text:
        await message.channel.send("Bol bhai 🙂")
        return

    # DialoGPT works best with SHORT context
    input_text = SYSTEM_PROMPT + " " + user_text + tokenizer.eos_token

    input_ids = tokenizer.encode(input_text, return_tensors="pt")

    output_ids = model.generate(
        input_ids,
        max_new_tokens=80,          # ✅ CORRECT
        do_sample=True,
        temperature=0.8,
        top_p=0.9,
        pad_token_id=tokenizer.eos_token_id
    )

    reply = tokenizer.decode(
        output_ids[0][input_ids.shape[-1]:],
        skip_special_tokens=True
    )

    if reply.strip() == "":
        reply = "Haan bhai, bol 🙂"

    await message.channel.send(reply)

bot.run(os.environ["DISCORD_BOT_TOKEN"])
