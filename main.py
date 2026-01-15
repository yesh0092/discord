import os
import asyncio
import warnings
import discord
from discord.ext import commands
from transformers import AutoTokenizer, AutoModelForCausalLM

# Suppress annoying NumPy + torch compatibility warning (common in some envs)
warnings.filterwarnings("ignore", category=UserWarning, module="torch.storage")

# ========= MODEL & TOKENIZER (global + load once) =========
MODEL_NAME = "microsoft/DialoGPT-small"
tokenizer = None
model = None
model_loaded = False

def load_model():
    global tokenizer, model, model_loaded
    if model_loaded:
        return
    
    print("⏳ Loading tokenizer & model (one time only)...")
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

# ========= ADAM BHAI REPLY GENERATOR =========
def generate_reply(user_text: str) -> str:
    if not model_loaded or model is None or tokenizer is None:
        return "Bhai abhi model load nahi hua, thodi der baad pelunga 😈🔥"

    prompt = (
        "You are Adam Bhai – Ghaziabad ka gunda, full savage roasting king 👑\n"
        "Rules (follow 100%):\n"
        "- Sirf Hinglish bol (Hindi + English mix), no full English, no full Hindi\n"
        "- Reply 1-2 line max, tez, abusive, gaaliyan daal\n"
        "- Gaaliyan: madarchod, bhenchod, chutiya, harami, gandu, lavde, bhosdike\n"
        "- 2-4 emojis daal: 🔥😈🤡💀👊🖕😂\n"
        "- Personal savage roast kar – looks, aukaat, gf, dimag, family, phone\n"
        "- Full toxic gunda mode, never sorry, never soft\n\n"

        "Examples:\n"
        "User: bhai kaisa hai\n"
        "Adam: Thik hu madarchod, tu fir pelwane aaya? 😂🖕🔥\n\n"

        "User: help chahiye\n"
        "Adam: Oye harami fir aa gaya? Bol kya chahiye bhosdike 😈💀👊\n\n"

        f"User: {user_text}\n"
        "Adam:"
    )

    try:
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            return_attention_mask=True
        )

        outputs = model.generate(
            **inputs,
            max_new_tokens=80,
            do_sample=True,
            temperature=0.9,
            top_p=0.92,
            repetition_penalty=1.2,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id
        )

        reply = tokenizer.decode(
            outputs[0][inputs.input_ids.shape[-1]:],
            skip_special_tokens=True
        ).strip()

        if not reply or len(reply) < 8:
            return "Oye chutiye kuch toh bol sahi se! 😈🔥🖕"

        return reply

    except Exception as e:
        print(f"Generation error: {e}")
        return "Bhai error aa gaya, fir try kar madarchod 😈💀"

# ========= DISCORD BOT =========
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    load_model()  # Load only once when bot starts
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
        await message.channel.send("Bol gandu kuch toh sahi! 😈💀🖕")
        return

    loop = asyncio.get_running_loop()
    reply = await loop.run_in_executor(None, generate_reply, user_text)
    
    await message.channel.send(reply)

bot.run(os.environ["DISCORD_BOT_TOKEN"])
