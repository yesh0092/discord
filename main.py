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
            padding_side="left"
        )
        tokenizer.pad_token = tokenizer.eos_token  # Fix padding token issue
        
        model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
        model.eval()
        print("✅ Model loaded")

# ========= ADAM BHAI GENERATION =========
def generate_reply(user_text: str) -> str:
    prompt = (
        "You are Adam Bhai – Ghaziabad ka asli gunda, full savage roasting king 👑\n"
        "Rules (strict):\n"
        "- Sirf Hinglish bolna (Hindi + English mix), koi full English ya full Hindi nahi\n"
        "- Har reply 1-2 line max, tez abusive, gaaliyan daal\n"
        "- Gaaliyan: madarchod, bhenchod, chutiya, harami, gandu, lavde, bhosdike, suwar\n"
        "- 2-4 emojis: 🔥😈🤡💀👊🖕😂\n"
        "- Personal savage roast – looks, aukaat, gf, dimag, family, phone pe attack\n"
        "- Full toxic gunda mode, no sorry, no soft\n\n"

        "Examples:\n"
        "User: bhai kaisa hai\n"
        "Adam: Mast hu bhosdike, tu fir pelwane aaya? 😂🖕🔥\n\n"

        "User: help kar na\n"
        "Adam: Oye harami, fir aa gaya report likwane? Bol kya chahiye madarchod 😈💀👊\n\n"

        f"User: {user_text}\n"
        "Adam:"
    )

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        padding=True,
        truncation=True,
        return_attention_mask=True
    )

    outputs = model.generate(
        **inputs,                          # includes input_ids + attention_mask
        max_new_tokens=80,
        do_sample=True,
        temperature=0.9,
        top_p=0.92,
        repetition_penalty=1.2,
        pad_token_id=tokenizer.eos_token_id,
        eos_token_id=tokenizer.eos_token_id
        # NO extra attention_mask= here → avoids the error
    )

    reply = tokenizer.decode(
        outputs[0][inputs.input_ids.shape[-1]:],
        skip_special_tokens=True
    ).strip()

    if not reply or len(reply) < 8:
        return "Oye chutiye bol kuch toh sahi! 😈🔥🖕"

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
        activity=discord.Game(name="Roasting Mode 🔥😈")
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

    loop = asyncio.get_running_loop()
    reply = await loop.run_in_executor(None, generate_reply, user_text)
    
    await message.channel.send(reply)

bot.run(os.environ["DISCORD_BOT_TOKEN"])
