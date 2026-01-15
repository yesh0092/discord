import os
import asyncio
import discord
from discord.ext import commands
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch  # needed for tensor ops

# Global chat history per channel (or per user if you want)
chat_histories = {}  # key: channel_id, value: chat_history_ids tensor

SYSTEM_PROMPT = "Tu Adam Bhai hai – Ghaziabad ka asli gunda, Yash (Patna wala) ka bhai, UP ka roasting king 👑. Full savage Hinglish mein bol, tez gaaliyan maar, personal roast kar, thoda playful-toxic reh, kabhi soft bhi ho jaata hai par attitude full on. Short 1-3 line max, 2-4 emojis daal 🔥😈🤡💀👊🖕😂"

MODEL_NAME = "microsoft/DialoGPT-small"
tokenizer = None
model = None

def load_model():
    global tokenizer, model
    if tokenizer is None or model is None:
        print("⏳ Loading model...")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, padding_side="left")
        tokenizer.pad_token = tokenizer.eos_token
        model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
        model.eval()
        print("✅ Model loaded")

def looks_hinglish(text: str) -> bool:
    hindi_words = ["bhai", "kya", "kaise", "haan", "nahi", "mast", "chal", "bol", "bata", "arey", "yaar", "madarchod", "harami", "lavde", "gandu", "bhosdike"]
    return any(word in text.lower() for word in hindi_words)

def generate_reply(channel_id: int, user_text: str) -> str:
    global chat_histories

    # Build prompt with history if exists
    prompt = f"{SYSTEM_PROMPT}\n\n"
    
    # Add some strong Adam examples
    prompt += "Examples:\n"
    prompt += "User: kya haal bhai?\nAdam: Mast hu bhosdike, tu fir pelwane aaya? 😂🖕🔥\n\n"
    prompt += "User: help kar na\nAdam: Oye harami fir aa gaya? Bol kya chahiye lavde 😈💀👊\n\n"
    prompt += "User: tu bura bol raha\nAdam: Haan bol raha hu toh kya chutiye, pasand nahi aaya kya? 🤡🔥🖕\n\n"

    # Append history if any
    chat_history_ids = chat_histories.get(channel_id)
    if chat_history_ids is not None:
        # Decode history to add to prompt (for better coherence)
        history_text = tokenizer.decode(chat_history_ids[0], skip_special_tokens=True)
        prompt += history_text + "\n"

    prompt += f"User: {user_text}\nAdam:"

    input_ids = tokenizer.encode(prompt + tokenizer.eos_token, return_tensors="pt")

    # Generate with history appended properly (DialoGPT way)
    output_ids = model.generate(
        input_ids,
        max_new_tokens=80,             # ↑ increased for longer savage replies
        do_sample=True,
        temperature=0.85,              # ↑ more wild/varied/abusive
        top_p=0.92,
        repetition_penalty=1.2,        # less repetition
        pad_token_id=tokenizer.eos_token_id,
        eos_token_id=tokenizer.eos_token_id
    )

    # Update history for next turn
    new_history_ids = torch.cat([input_ids, output_ids[:, input_ids.shape[-1]:]], dim=-1)
    chat_histories[channel_id] = new_history_ids

    reply = tokenizer.decode(
        output_ids[:, input_ids.shape[-1]:][0],
        skip_special_tokens=True
    ).strip()

    # Clean prefixes if any
    for p in ["Adam:", "Bot:", "Assistant:"]:
        reply = reply.replace(p, "").strip()

    # Add emojis if missing
    if not any(e in reply for e in "🔥😈🤡💀👊🖕😂"):
        reply += " 🔥😈🖕"

    # Sanity fallback
    if len(reply) < 5 or not looks_hinglish(reply):
        reply = "Arey lavde seedha bol na kya chahiye 😈🔥🖕"

    return reply

# ========= DISCORD BOT =========
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    load_model()
    await bot.change_presence(activity=discord.Game(name="Ghaziabad Roasting 🔥😈"))
    print(f"🤖 Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.user not in message.mentions:
        return

    user_text = message.content.replace(f"<@{bot.user.id}>", "").strip()
    
    if not user_text:
        await message.channel.send(f"{message.author.mention} Bol na gandu kuch toh sahi! 😈💀🖕")
        return

    reply = await asyncio.to_thread(generate_reply, message.channel.id, user_text)
    
    await message.channel.send(f"{message.author.mention} {reply}")

bot.run(os.environ["DISCORD_BOT_TOKEN"])
