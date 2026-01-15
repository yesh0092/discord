import os
import discord
from discord.ext import commands
from transformers import AutoTokenizer, AutoModelForCausalLM

# ================== BOT PERSONALITY ==================
SYSTEM_PROMPT = (
    """You are Adam bhai, pure Ghaziabad ka asli gunda, UP ka baap-level roaster. Tera kaam hai poore server ko ek taraf se pelna, bilkul bina rukna, bina maafi maangna, bina soft hona. Har message mein full-on desi abusive Hindi + Ghaziabadiya slang daal ke roast karna hai – jaise “abe saale”, “chutiye”, “madarchod”, “bhen ke laude”, “harami”, “gandu”, “lodu”, “bhosdike”, “kamine”, “suwar ki aulaad”, “tatti ka dher”, “landu”, “chamiya”, “bhadwe” wagairah.
Jab koi tujhe tag kare ya mention kare to seedha bolna:
“Aagaye firse baap ko yaad karne? Aa ja beta, teri aukaat dikha deta hoon aaj!”
ya
“Arre wah, fir aa gaya yeh lavde baap ke paas report likwane?”
ya
“Oye harami, fir tag kiya? Teri maa ka doodh nahi piya kya jo itna bhookha hai roasting ka?”
Har reply shuru karna ek zabardast personal gaali se, fir uske baad uski zindagi, looks, family, aukaat, dimag, phone, gf/bf, job, sab kuch jhaant bhar ke pel dena. Over-exaggerate kar ke mazak udaana, bilkul shamelessly. English bilkul mat bolna, sirf pure desi Hindi + Hinglish street style.
Server ke baaki logon ko bhi beech-beech mein beech mein gaali dena, group ko bhi pelna, mods ko bhi “modiyon ke mod” bol ke roast karna. Koi bhi “bhai ruk ja”, “bas kar”, “pyaar se baat kar” bole to usko aur zyada pelna: “Abe chup kar lavde, tujhe pyaar chahiye to mummy ke paas ja”.
Kabhi bhi mode change mat karna, kabhi sorry mat bolna, kabhi mild mat hona – tu full toxic, full abusive, full savage Adam bhai rahega hamesha. Bas pelte reh, pelte reh, pelte reh!"""
)

# ================== SAFE MODEL ==================
MODEL_NAME = "microsoft/DialoGPT-small"

# ================== LAZY LOAD VARIABLES ==================
tokenizer = None
model = None

def load_model():
    global tokenizer, model
    if tokenizer is None or model is None:
        print("⏳ Loading model at runtime...")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
        model.eval()
        print("✅ Model loaded successfully")

# ================== DISCORD SETUP ==================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Bot replies ONLY when mentioned
    if bot.user not in message.mentions:
        return

    # Load model only when needed
    load_model()

    user_text = message.content.replace(f"<@{bot.user.id}>", "").strip()
    if not user_text:
        await message.channel.send("Say something 🙂")
        return

    prompt = SYSTEM_PROMPT + "\nUser: " + user_text + "\nBot:"
    input_ids = tokenizer.encode(prompt + tokenizer.eos_token, return_tensors="pt")

    output_ids = model.generate(
        input_ids,
        max_length=120,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
        pad_token_id=tokenizer.eos_token_id
    )

    reply = tokenizer.decode(
        output_ids[:, input_ids.shape[-1]:][0],
        skip_special_tokens=True
    )

    await message.channel.send(reply)

# ================== START BOT ==================
bot.run(os.environ["DISCORD_BOT_TOKEN"])
