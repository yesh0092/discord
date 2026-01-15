import os
import asyncio
import warnings
import discord
from discord.ext import commands
from transformers import AutoTokenizer, AutoModelForCausalLM

# Suppress all torch + numpy compatibility warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Force numpy to ignore errors (extreme safety)
import numpy as np
np.seterr(all='ignore')

# ========= MODEL & TOKENIZER =========
MODEL_NAME = "microsoft/DialoGPT-small"
tokenizer = None
model = None
model_loaded = False

def load_model():
    global tokenizer, model, model_loaded
    if model_loaded:
        return
    
    print("⏳ Loading tokenizer & model...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME,
            padding_side="left"
        )
        tokenizer.pad_token = tokenizer.eos_token
        
        model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
        model.eval()
        model_loaded = True
        print("✅ Model loaded successfully")
    except Exception as e:
        print(f"Model loading failed: {e}")
        model_loaded = False

# ========= ADAM BHAI GENERATION (with extra fallback) =========
def generate_reply(user_text: str) -> str:
    if not model_loaded or model is None or tokenizer is None:
        return "Bhai model load nahi hua abhi, thodi der baad pelunga 😈🔥"

    prompt = (
        "You are Adam Bhai – Ghaziabad ka gunda, full savage roasting king 👑\n"
        "Rules:\n"
        "- Sirf Hinglish bol, no full English/Hindi\n"
        "- 1-2 line max, tez gaaliyan: madarchod bhenchod chutiya harami gandu lavde bhosdike\n"
        "- 2-4 emojis: 🔥😈🤡💀👊🖕😂\n"
        "- Savage personal roast – looks, gf, family, dimag, phone\n"
        "- Full toxic mode, no sorry\n\n"

        "Examples:\n"
        "User: bhai kaisa hai\n"
        "Adam: Mast hu madarchod, tu fir pelwane aaya? 😂🖕🔥\n\n"

        f"User: {user_text}\n"
        "Adam:"
    )

    try:
        inputs = tokenizer(prompt, return_tensors="pt", padding=True, truncation=True)
        
        outputs = model.generate(
            **inputs,
            max_new_tokens=80,
            do_sample=True,
            temperature=0.9,
            top_p=0.92,
            repetition_penalty=1.25,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id
        )

        reply = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()

        # Agar reply khali ya chhota → fallback savage reply
        if not reply or len(reply) < 10 or "english" in reply.lower():
            return "Oye harami, itna chhota message? Teri aukaat bhi chhoti hai kya? 😂🖕🔥"

        return reply

    except Exception as e:
        print(f"Generation error: {e}")
        return "Bhai error aa gaya, fir tag kar pelte hain madarchod 😈💀"

# ========= DISCORD BOT =========
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    load_model()
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name="Roasting 🔥😈")
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
        await message.channel.send("Bol lavde kuch toh sahi! 😈💀🖕")
        return

    try:
        loop = asyncio.get_running_loop()
        reply = await loop.run_in_executor(None, generate_reply, user_text)
        await message.channel.send(reply)
    except Exception as e:
        print(f"Message error: {e}")
        await message.channel.send("Bhai abhi dimag down hai, fir try kar 😈🔥")

bot.run(os.environ["DISCORD_BOT_TOKEN"])
