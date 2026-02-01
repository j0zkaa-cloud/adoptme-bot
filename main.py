# -*- coding: utf-8 -*-
import discord
from discord.ext import commands, tasks
import json
import asyncio
from playwright.async_api import async_playwright
import os
import datetime
import re
from flask import Flask
from threading import Thread

# ==============================================================================
# ⚙️ ULTRA STABLE EDITION (RENDER FIX)
# ==============================================================================
print("⏳ [SYSTEM] Starting Bot (Memory Optimized)...")

# 👇 SEM VLOŽ TOKEN 👇
TOKEN = "MTQ2NTQ1MzI0NDQzOTMzNTAyNQ.GLl1sv.fsb39JgJYus0X2J3gezgHJvCxnrcaBU4YBOGEQ"

if TOKEN == "SEM_VLOZ_TVUJ_TOKEN" or TOKEN == "":
    print("⛔ [ERROR] Missing Token!")
    exit()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# --- WEB SERVER (KEEP ALIVE) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is alive!"

def run():
    # Důležité: Použijeme port, který nám dá Render, nebo 8080 jako zálohu
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

DATA_FILE = "values_database.json"
DASHBOARD_FILE = "dashboard_config.json"

CATEGORIES = [
    {"name": "Pets", "url": "https://amvgg.com/values/pets"},
    {"name": "Pet Wear", "url": "https://amvgg.com/values/petwear"},
    {"name": "Vehicles", "url": "https://amvgg.com/values/vehicles"},
    {"name": "Food", "url": "https://amvgg.com/values/food"},
]

# --- LOGIKA ---
def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)
    except: pass

def load_data():
    if not os.path.exists(DATA_FILE): return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)

def parse_price(price_str):
    try: return float(re.sub(r'[^\d.]', '', price_str))
    except: return 0.0

def calculate_demand(html):
    stars = re.findall(r'[★]', html)
    count = len(stars)
    if count >= 3: return "3/3"
    if count == 2: return "2/3"
    if count == 1: return "1/3"
    return "0/3"

# --- DASHBOARD ---
class DashboardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⚡ Refresh Now", style=discord.ButtonStyle.green, custom_id="refresh_btn_render")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚀 **Update Queued!**", ephemeral=True)
        asyncio.create_task(scrape_and_update())

def save_dashboard_config(channel_id, message_id):
    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump({"channel_id": channel_id, "message_id": message_id}, f)

def load_dashboard_config():
    if not os.path.exists(DASHBOARD_FILE): return None
    with open(DASHBOARD_FILE, "r", encoding="utf-8") as f: return json.load(f)

async def update_dashboard_ui(data):
    config = load_dashboard_config()
    if not config or not data: return
    
    pets = [i for i in data.values() if i['category'] == 'Pets']
    pets_sorted = sorted(pets, key=lambda x: parse_price(x['price']), reverse=True)
    top_15 = pets_sorted[:15]
    
    embed = discord.Embed(title="🏆 MARKET LEADERBOARD", color=0x5865F2)
    embed.description = f"**Last Update:** `{datetime.datetime.now().strftime('%H:%M')}`\n*Top 15 Highest Value Pets*"
    embed.set_thumbnail(url="https://amvgg.com/favicon.ico")

    table_text = ""
    for i, item in enumerate(top_15, 1):
        name = item['original_name'][:18] + ".." if len(item['original_name']) > 20 else item['original_name']
        table_text += f"`#{i}` **{name}**\n└ 💎 `{item['price']}` | 📊 `{item['demand']}`\n"

    embed.add_field(name="🔥 High Value Items", value=table_text, inline=False)
    embed.set_footer(text=f"Total Database Items: {len(data)}")

    try:
        channel = bot.get_channel(config['channel_id'])
        if channel:
            msg = await channel.fetch_message(config['message_id'])
            await msg.edit(content="", embed=embed, view=DashboardView())
    except: pass

# --- SCRAPER (OPTIMIZED FOR RENDER) ---
async def scrape_and_update():
    print("\n🚀 [SCRAPER] Scanning...")
    new_data = {}
    async with async_playwright() as p:
        # PŘIDÁNY ARGUMENTY PROTI PÁDŮM (Memory Crash Fix)
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'] 
        )
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        # Blokace obrázků pro úsporu paměti
        await page.route("**/*", lambda route: route.abort() 
            if route.request.resource_type in ["image", "media"] 
            else route.continue_())

        for cat in CATEGORIES:
            try:
                await page.goto(cat['url'], timeout=60000, wait_until="domcontentloaded")
                try: 
                    await page.wait_for_timeout(500)
                    btn = page.get_by_text("Agree", exact=True).first
                    if await btn.is_visible(): await btn.click()
                except: pass

                scrolls = 15 if cat['name'] == "Pets" else 5
                for _ in range(scrolls):
                    await page.mouse.wheel(0, 3000)
                    await page.wait_for_timeout(300)

                cards = await page.locator("div:has(h2):has-text('Value')").all()
                for card in cards:
                    try:
                        html = await card.inner_html()
                        title = await card.locator("h2").inner_text()
                        price = await card.locator("xpath=.//span[contains(text(), 'Value')]/following-sibling::span").inner_text()
                        demand = calculate_demand(html)

                        new_data[title.lower().strip()] = {
                            "price": price.strip(), "demand": demand,
                            "category": cat['name'], "original_name": title.strip(),
                            "last_update": datetime.datetime.now().strftime("%Y-%m-%d")
                        }
                    except: continue
            except Exception as e: print(f"   ❌ Error: {e}")
        await browser.close()
    
    if len(new_data) > 0:
        save_data(new_data)
        await update_dashboard_ui(new_data)
    return new_data

# --- COMMANDS ---
@tasks.loop(hours=6)
async def auto_update(): await scrape_and_update()

@bot.event
async def on_ready():
    print(f"🤖 Bot {bot.user} ONLINE.")
    bot.add_view(DashboardView())
    if not auto_update.is_running(): auto_update.start()
    
    # Odložený start stahování o 30s, aby se stihl nastartovat webserver
    if not load_data():
        print("⚡ Empty DB. Waiting 30s before first scrape...")
        await asyncio.sleep(30)
        asyncio.create_task(scrape_and_update())

@bot.command(name="setup_dashboard")
async def setup(ctx):
    if not ctx.author.guild_permissions.administrator: return
    msg = await ctx.send(embed=discord.Embed(title="📊 Initializing...", color=0x95a5a6))
    save_dashboard_config(ctx.channel.id, msg.id)
    await ctx.send("✅ Ready!", delete_after=5)

@bot.command(name="value")
async def val(ctx, *, q: str):
    data = load_data()
    if not data:
        await ctx.send("⏳ Booting up... Data will be available in ~2 mins.")
        return
    match = [i for k, i in data.items() if q.lower() in k]
    if match:
        match.sort(key=lambda x: len(x['original_name']))
        top = match[0]
        embed = discord.Embed(title=top['original_name'], color=0x2ECC71)
        embed.add_field(name="💎 Value", value=f"**{top['price']}**", inline=True)
        embed.add_field(name="📊 Demand", value=f"`{top['demand']}`", inline=True)
        embed.add_field(name="📂 Category", value=top['category'], inline=True)
        await ctx.send(embed=embed)
    else: await ctx.send(f"❌ '{q}' not found.")

if __name__ == "__main__":
    try:
        keep_alive()
        bot.run(TOKEN)
    except Exception as e: print(f"CRITICAL: {e}")
