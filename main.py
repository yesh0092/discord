import os
import asyncio
import discord
from discord.ext import commands
from transformers import AutoTokenizer, AutoModelForCausalLM

# ========= MODEL & TOKENIZER =========
MODEL_NAME = "microsoft/DialoGPT-small"
tokenizer = None
model = None

def load_model():
    global tokenizer, model
    if tokenizer is None or model is None:
        print("⏳ Loading tokenizer & model...")
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME,
            padding_side="left"          # 🔥 FIX: Left padding for decoder-only
        )
        model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
        model.eval()
        print("✅ Model loaded")

# ========= STRONGER PROMPT TO FORCE HINGLISH + ADAM PERSONALITY =========
def generate_reply(user_text: str) -> str:
    prompt = (
        "You are Adam Bhai – Ghaziabad ka gunda, Yash ka dost, full savage roasting king 👑\n"
        "Rules (strict):\n"
        "- Sirf aur sirf Hinglish bolna (Hindi + English mix), koi pure English ya pure Hindi nahi\n"
        "- Har reply 1-2 line max, tez, abusive, gaaliyan daal\n"
        "- Gaaliyan: madarchod, bhenchod, chutiya, harami, gandu, lavde, bhosdike, suwar\n"
        "- Emojis 2-4 daalna: 🔥😈🤡💀👊🖕😂\n"
        "- Personal savage roast kar – looks, aukaat, gf, family, dimag, phone sab pe\n"
        "- Kabhi sorry nahi, kabhi soft nahi – full toxic gunda mode\n\n"

        "Examples (only Hinglish):\n"
        "User: bhai kya haal?\n"
        "Adam: Mast hu bhosdike, tu itna tag karta hai jaise teri aukaat nahi hai 😂🖕🔥\n\n"

        "User: help kar na yaar\n"
        "Adam: Oye harami fir aa gaya baap ko yaad karne? Bol kya chahiye madarchod 😈💀👊\n\n"

        "User: tu bura bol raha\n"
        "Adam: Arre lavde dimag mein tatti hai kya? Chal pelta rahunga tu chill kar 🤡🔥🖕\n\n"

        f"User (Yash): {user_text}\n"
        "Adam:"
    )

    inputs = tokenizer(prompt, return_tensors="pt", padding=True, truncation=True)

    outputs = model.generate(
        **inputs,
        max_new_tokens=80,
        do_sample=True,
        temperature=0.9,
        top_p=0.92,
        repetition_penalty=1.25,         # Force less repetition & English drift
        pad_token_id=tokenizer.eos_token_id,
        eos_token_id=tokenizer.eos_token_id
    )

    reply = tokenizer.decode(
        outputs[0][inputs.input_ids.shape[-1]:],
        skip_special_tokens=True
    ).strip()

    if not reply or len(reply) < 8 or "english" in reply.lower():
        return "Oye gandu bol kuch sahi se! 😈🔥🖕"

    return reply

# ========= DISCORD BOT =========
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    load_model()
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name="Yash ko pel raha 🔥😈")
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
        await message.channel.send("Bol bhai kuch toh sahi gandu! 😈💀🖕")
        return

    loop = asyncio.get_running_loop()
    reply = await loop.run_in_executor(None, generate_reply, user_text)
    
    await message.channel.send(reply)

bot.run(os.environ["DISCORD_BOT_TOKEN"])
