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
            padding_side="left"              # Required for decoder-only generation
        )
        # 🔥 FIX: DialoGPT doesn't have pad_token → set it to eos_token
        tokenizer.pad_token = tokenizer.eos_token
        
        model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
        model.eval()
        print("✅ Model loaded")

# ========= ADAM BHAI GENERATION =========
def generate_reply(user_text: str) -> str:
    prompt = (
        "You are Adam Bhai – Ghaziabad ka asli gunda, Yash (Patna wala) ka bhai, UP ka roasting king 👑\n"
        "Rules (follow strictly):\n"
        "- Sirf Hinglish bol (Hindi + English mix), koi full English ya full Hindi nahi\n"
        "- Reply 1-2 line max, tez, abusive, gaaliyan maar\n"
        "- Gaaliyan examples: madarchod, bhenchod, chutiya, harami, gandu, lavde, bhosdike, suwar\n"
        "- 2-4 emojis daal: 🔥😈🤡💀👊🖕😂\n"
        "- Savage roast kar – looks, aukaat, gf, dimag, family, phone pe personal attack\n"
        "- Full toxic gunda mode, kabhi sorry nahi, kabhi soft nahi\n\n"

        "Examples:\n"
        "User: bhai kaisa hai\n"
        "Adam: Thik hu madarchod, tu fir aa gaya pelwane? 😂🖕🔥\n\n"

        "User: yaar help chahiye\n"
        "Adam: Oye harami fir tag kiya? Tatti khane ka mann hai kya bhosdike 😈💀👊\n\n"

        f"User (Yash): {user_text}\n"
        "Adam:"
    )

    # Tokenize with padding
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        padding=True,
        truncation=True,
        return_attention_mask=True
    )

    # Generate with explicit pad_token_id
    outputs = model.generate(
        **inputs,
        max_new_tokens=80,
        do_sample=True,
        temperature=0.9,
        top_p=0.92,
        repetition_penalty=1.2,
        pad_token_id=tokenizer.eos_token_id,     # 🔥 Important fix
        eos_token_id=tokenizer.eos_token_id,
        attention_mask=inputs.attention_mask
    )

    reply = tokenizer.decode(
        outputs[0][inputs.input_ids.shape[-1]:],
        skip_special_tokens=True
    ).strip()

    # Fallback agar reply kharab aaye
    if not reply or len(reply) < 10:
        return "Oye gandu kuch toh bol madarchod! 😈🔥🖕"

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
        activity=discord.Game(name="Yash ko pel raha hu 🔥😈")
    )
    print(f"🤖 Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Reply only when mentioned (Adam Bhai ko tag karo)
    if bot.user not in message.mentions:
        return

    user_text = message.content.replace(f"<@{bot.user.id}>", "").strip()
    
    if not user_text:
        await message.channel.send("Bol bhai kuch toh sahi gandu! 😈💀🖕")
        return

    loop = asyncio.get_running_loop()
    reply = await loop.run_in_executor(None, generate_reply, user_text)
    
    await message.channel.send(reply)

    # Optional: process commands if you add any later
    # await bot.process_commands(message)

bot.run(os.environ["DISCORD_BOT_TOKEN"])
