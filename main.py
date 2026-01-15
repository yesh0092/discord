import os
import asyncio
import discord
from discord.ext import commands
from transformers import AutoTokenizer, AutoModelForCausalLM

# ========= SHORT SYSTEM PROMPT (<= 100 chars) =========
SYSTEM_PROMPT = "You are Adam Bhai – Ghaziabad ka gunda, UP ka roasting king. Full savage Hinglish."

MODEL_NAME = "microsoft/DialoGPT-small"
tokenizer = None
model = None

def load_model():
    global tokenizer, model
    if tokenizer is None or model is None:
        print("⏳ Loading model...")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, padding_side="left")
        model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
        model.eval()
        print("✅ Model loaded")

# ========= AI GENERATION (better prompt – full Adam personality) =========
def generate_reply(user_text: str) -> str:
    # 🔥 This long prompt is what actually controls the savage Adam behaviour
    prompt = (
        "You are Adam Bhai – Ghaziabad ka asli gunda, Yash ka bhai, UP ka undisputed roasting king 👑\n"
        "Style: short 1-2 line max, tez abusive Hinglish, full desi gaaliyan, savage roast, zero sorry\n"
        "Always 2-4 emojis 🔥😈🤡💀👊🖕😂\n"
        "Personal attack on looks, aukaat, gf, dimag, family, phone, everything\n"
        "Tone: toxic, over-confident, mazedaar, dost jaisa but full gunda wala pelna\n\n"

        "Examples:\n"
        "User: bhai kaisa hai?\n"
        "Adam: Mast hu madarchod, tu itna tag karta hai jaise teri gf tujhe chod ke bhaag gayi 😂🖕🔥\n\n"

        "User: yaar help kar na\n"
        "Adam: Oye harami, fir aa gaya baap ko yaad karne? Bol kya chahiye bhosdike 😈💀👊\n\n"

        "User: tu bura bol raha hai\n"
        "Adam: Arre lavde dimag mein tatti bhari hai kya? Chal pelte rahunga tu chill kar 🤡🔥🖕\n\n"

        f"User (Yash): {user_text}\n"
        "Adam:"
    )

    input_ids = tokenizer.encode(prompt + tokenizer.eos_token, return_tensors="pt")
    
    output_ids = model.generate(
        input_ids,
        max_new_tokens=80,          # thoda zyada tokens rakha taaki savage reply fit ho
        do_sample=True,
        temperature=0.85,           # thoda zyada wild
        top_p=0.92,
        repetition_penalty=1.15,    # repeat gaali kam karega
        pad_token_id=tokenizer.eos_token_id
    )

    reply = tokenizer.decode(
        output_ids[0][input_ids.shape[-1]:],
        skip_special_tokens=True
    ).strip()

    # Fallback agar model kuch bhi na de
    if not reply or len(reply) < 5:
        return "Bol bhai, kya bakchodi chal rahi hai? 😈🔥🖕"

    return reply

# ========= DISCORD SETUP =========
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

    # Sirf mention pe reply (Adam bhai ko tag karo)
    if bot.user not in message.mentions:
        return

    user_text = message.content.replace(f"<@{bot.user.id}>", "").strip()
    
    if not user_text:
        await message.channel.send("Oye gandu bol kuch toh sahi! 😈💀🖕")
        return

    loop = asyncio.get_running_loop()
    reply = await loop.run_in_executor(None, generate_reply, user_text)
    
    await message.channel.send(reply)

bot.run(os.environ["DISCORD_BOT_TOKEN"])
