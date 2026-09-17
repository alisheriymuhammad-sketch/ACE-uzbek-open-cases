
import logging
import random
import sqlite3
import asyncio

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import FSInputFile

# ⚠️ TOKENNI SHU YERGA YOZING
API_TOKEN = '8641408841:AAHT54ySJRPnhENy5S5j9gVuP7Zu3dck4KA'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ══════════════════════════════════════════
# 🗄️  DATABASE
# ══════════════════════════════════════════
conn = sqlite3.connect('cs2_bot.db')
cur  = conn.cursor()

cur.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        user_id      INTEGER PRIMARY KEY,
        username     TEXT,
        full_name    TEXT,
        balance      INTEGER DEFAULT 1000,
        keys         INTEGER DEFAULT 3,
        referred_by  INTEGER DEFAULT 0,
        referrals    INTEGER DEFAULT 0,
        opened_cases INTEGER DEFAULT 0,
        total_won    INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS inventory (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id  INTEGER,
        item     TEXT,
        rarity   TEXT,
        price    INTEGER,
        date     TEXT DEFAULT (datetime('now','localtime'))
    );
''')
conn.commit()

# ══════════════════════════════════════════
# 🎁  CASE ITEMS
# ══════════════════════════════════════════
CASES = {
    "pistol": {
        "name":  "🔫 Pistol Case",
        "price": 50,
        "emoji": "🔫",
        "items": [
            {"name": "Glock-18 | Water Elemental",     "rarity": "Mil-Spec",   "price": 30,   "chance": 40},
            {"name": "P250 | Gunsmoke",                "rarity": "Mil-Spec",   "price": 25,   "chance": 30},
            {"name": "USP-S | Caiman",                 "rarity": "Restricted", "price": 120,  "chance": 15},
            {"name": "Desert Eagle | Cobalt Disruption","rarity": "Restricted","price": 200,  "chance": 10},
            {"name": "P2000 | Fire Elemental",         "rarity": "Classified", "price": 800,  "chance": 4},
            {"name": "Glock-18 | Fade ★ StatTrak",    "rarity": "Covert",     "price": 5000, "chance": 1},
        ]
    },
    "rifle": {
        "name":  "🎯 Rifle Case",
        "price": 150,
        "emoji": "🎯",
        "items": [
            {"name": "AK-47 | Slate",                  "rarity": "Mil-Spec",   "price": 80,    "chance": 38},
            {"name": "M4A4 | Faded Zebra",             "rarity": "Mil-Spec",   "price": 60,    "chance": 28},
            {"name": "AK-47 | Redline",                "rarity": "Restricted", "price": 300,   "chance": 15},
            {"name": "M4A1-S | Hyper Beast",           "rarity": "Classified", "price": 900,   "chance": 10},
            {"name": "AK-47 | Fire Serpent",           "rarity": "Classified", "price": 2500,  "chance": 6},
            {"name": "M4A4 | Howl ★",                  "rarity": "Covert",     "price": 25000, "chance": 2},
            {"name": "AK-47 | Case Hardened ★ StatTrak","rarity":"Covert",     "price": 40000, "chance": 1},
        ]
    },
    "knife": {
        "name":  "🔪 Knife Case",
        "price": 500,
        "emoji": "🔪",
        "items": [
            {"name": "Falchion Knife | Fade",          "rarity": "Covert",  "price": 8000,  "chance": 30},
            {"name": "Gut Knife | Marble Fade",        "rarity": "Covert",  "price": 12000, "chance": 25},
            {"name": "Flip Knife | Tiger Tooth",       "rarity": "Covert",  "price": 18000, "chance": 20},
            {"name": "Bowie Knife | Doppler",          "rarity": "Covert",  "price": 22000, "chance": 15},
            {"name": "Karambit | Fade",                "rarity": "Covert",  "price": 50000, "chance": 7},
            {"name": "Butterfly Knife | Doppler ★",   "rarity": "Covert",  "price": 80000, "chance": 2},
            {"name": "Karambit | Case Hardened ★ ST", "rarity": "Covert",  "price":150000, "chance": 1},
        ]
    }
}

RARITY_COLOR = {
    "Mil-Spec":  "🔵",
    "Restricted":"🟣",
    "Classified":"🩷",
    "Covert":    "🔴",
}

RARITY_ANIM = {
    "Mil-Spec":  ["⬜","⬜","🔵","⬜","⬜"],
    "Restricted":["⬜","🟣","🟣","⬜","⬜"],
    "Classified":["🩷","🩷","🩷","⬜","⬜"],
    "Covert":    ["🔴","🔴","🔴","🔴","🔴"],
}

# ══════════════════════════════════════════
# 🛠️  HELPERS
# ══════════════════════════════════════════
def db_get(user_id: int, name: str = "Noma'lum", username: str = ""):
    cur.execute("SELECT balance, keys, opened_cases, total_won, referrals FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO users (user_id, username, full_name) VALUES (?,?,?)",
            (user_id, username, name)
        )
        conn.commit()
        return 1000, 3, 0, 0, 0
    return row

def db_update(user_id: int, balance_delta: int = 0, keys_delta: int = 0,
              cases_delta: int = 0, won_delta: int = 0):
    cur.execute(
        "UPDATE users SET "
        "  balance      = MAX(0, balance      + ?), "
        "  keys         = MAX(0, keys         + ?), "
        "  opened_cases = opened_cases + ?, "
        "  total_won    = total_won    + ? "
        "WHERE user_id = ?",
        (balance_delta, keys_delta, cases_delta, won_delta, user_id)
    )
    conn.commit()

def spin(case_key: str) -> dict:
    items   = CASES[case_key]["items"]
    weights = [i["chance"] for i in items]
    return random.choices(items, weights=weights, k=1)[0]

def price_fmt(p: int) -> str:
    return f"{p:,}".replace(",", " ")

# ══════════════════════════════════════════
# ⌨️  KEYBOARDS
# ══════════════════════════════════════════
def main_kb():
    b = ReplyKeyboardBuilder()
    b.add(types.KeyboardButton(text="🎁 Qutilar"))
    b.add(types.KeyboardButton(text="🎒 Inventar"))
    b.add(types.KeyboardButton(text="👤 Profil"))
    b.add(types.KeyboardButton(text="🏆 Top Players"))
    b.add(types.KeyboardButton(text="👥 Referral"))
    b.add(types.KeyboardButton(text="💰 Magazin"))
    b.adjust(2, 2, 2)
    return b.as_markup(resize_keyboard=True)

def cases_kb():
    b = InlineKeyboardBuilder()
    for key, case in CASES.items():
        b.add(types.InlineKeyboardButton(
            text=f"{case['emoji']} {case['name']}  |  {case['price']} 🪙",
            callback_data=f"case_info:{key}"
        ))
    b.adjust(1)
    return b.as_markup()

def case_action_kb(case_key: str):
    b = InlineKeyboardBuilder()
    b.add(types.InlineKeyboardButton(text="🔑 Kalit bilan och (1 🔑)",  callback_data=f"open_key:{case_key}"))
    b.add(types.InlineKeyboardButton(text="🪙 Koin bilan och",          callback_data=f"open_coin:{case_key}"))
    b.add(types.InlineKeyboardButton(text="🔁 5x Birdan och",           callback_data=f"open_5x:{case_key}"))
    b.add(types.InlineKeyboardButton(text="◀️ Orqaga",                  callback_data="back_cases"))
    b.adjust(1, 1, 1, 1)
    return b.as_markup()

def shop_kb():
    b = InlineKeyboardBuilder()
    b.add(types.InlineKeyboardButton(text="🔑 1 Kalit  — 200 🪙",  callback_data="buy_key:1"))
    b.add(types.InlineKeyboardButton(text="🔑 5 Kalit  — 900 🪙",  callback_data="buy_key:5"))
    b.add(types.InlineKeyboardButton(text="🔑 10 Kalit — 1700 🪙", callback_data="buy_key:10"))
    b.adjust(1)
    return b.as_markup()

# ══════════════════════════════════════════
# 📨  HANDLERS — asosiy menu
# ══════════════════════════════════════════
@dp.message(Command("start"))
async def cmd_start(msg: types.Message):
    args = msg.text.split()
    ref  = int(args[1]) if len(args) > 1 and args[1].isdigit() else 0

    uid  = msg.from_user.id
    name = msg.from_user.full_name
    uname= msg.from_user.username or ""

    cur.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
    exists = cur.fetchone()
    db_get(uid, name, uname)

    if not exists and ref and ref != uid:
        cur.execute("UPDATE users SET balance=balance+200, referrals=referrals+1 WHERE user_id=?", (ref,))
        cur.execute("UPDATE users SET balance=balance+100, referred_by=?         WHERE user_id=?", (ref, uid))
        conn.commit()
        try:
            await bot.send_message(ref,
                "🎉 Yangi do'stingiz botga qo'shildi!\n"
                "Siz *+200 🪙* bonus oldingiz!", parse_mode="Markdown")
        except Exception:
            pass

    await msg.answer(
        "╔══════════════════════╗\n"
        "║   🔫  CS2 CASE BOT   ║\n"
        "╚══════════════════════╝\n\n"
        "Salom, *" + name + "*! 👋\n\n"
        "🪙 Boshlang'ich balans: *1000 🪙*\n"
        "🔑 Bepul kalitlar: *3 🔑*\n\n"
        "Qutilarni oching va CS2 skinlari yutib oling!",
        parse_mode="Markdown",
        reply_markup=main_kb()
    )

@dp.message(F.text == "👤 Profil")
async def profile(msg: types.Message):
    uid = msg.from_user.id
    bal, keys, opened, won, refs = db_get(uid, msg.from_user.full_name)

    await msg.answer(
        "╔═══════════════════════╗\n"
        "║      👤  PROFIL       ║\n"
        "╚═══════════════════════╝\n\n"
        f"👤 Ism: *{msg.from_user.full_name}*\n"
        f"🆔 ID: `{uid}`\n\n"
        "──────────────────────\n"
        f"🪙 Balans:        *{price_fmt(bal)} 🪙*\n"
        f"🔑 Kalitlar:      *{keys} 🔑*\n"
        "──────────────────────\n"
        f"📦 Ochilgan:      *{opened} ta*\n"
        f"💰 Jami yutildi:  *{price_fmt(won)} 🪙*\n"
        f"👥 Referrallar:   *{refs} kishi*",
        parse_mode="Markdown"
    )

@dp.message(F.text == "🎁 Qutilar")
async def show_cases(msg: types.Message):
    await msg.answer(
        "╔═══════════════════════╗\n"
        "║     🎁  QUTILAR       ║\n"
        "╚═══════════════════════╝\n\n"
        "Qutini tanlang va skinlar yutib oling! 🎯",
        reply_markup=cases_kb()
    )

@dp.message(F.text == "💰 Magazin")
async def show_shop(msg: types.Message):
    await msg.answer(
        "╔══════════════════════╗\n"
        "║     💰  MAGAZIN      ║\n"
        "╚══════════════════════╝\n\n"
        "🔑 *Kalitlar narxi:*",
        parse_mode="Markdown",
        reply_markup=shop_kb()
    )

@dp.message(F.text == "👥 Referral")
async def show_referral(msg: types.Message):
    uid     = msg.from_user.id
    me      = await bot.get_me()
    link    = f"https://t.me/{me.username}?start={uid}"
    _, _, _, _, refs = db_get(uid)

    await msg.answer(
        "╔══════════════════════╗\n"
        "║    👥  REFERRAL      ║\n"
        "╚══════════════════════╝\n\n"
        "Do'stlaringizni taklif qiling:\n\n"
        f"🔗 Havola: `{link}`\n\n"
        "🎁 *Bonus tizimi:*\n"
        "• Siz: *+200 🪙* har do'st uchun\n"
        "• Do'stingiz: *+100 🪙* bonus\n\n"
        f"📊 Hozirgi referrallar: *{refs} kishi*",
        parse_mode="Markdown"
    )

@dp.message(F.text == "🏆 Top Players")
async def show_top(msg: types.Message):
    cur.execute(
        "SELECT full_name, opened_cases, total_won FROM users "
        "ORDER BY total_won DESC LIMIT 10"
    )
    rows = cur.fetchall()
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    lines  = []
    for i, (name, opened, won) in enumerate(rows):
        lines.append(
            f"{medals[i]} *{name}*\n"
            f"   📦 {opened} ta | 💰 {price_fmt(won)} 🪙"
        )
    text = (
        "╔══════════════════════╗\n"
        "║   🏆  TOP PLAYERS    ║\n"
        "╚══════════════════════╝\n\n"
    ) + ("\n\n".join(lines) if lines else "Hali hech kim yo'q!")
    await msg.answer(text, parse_mode="Markdown")

@dp.message(F.text == "🎒 Inventar")
async def show_inventory(msg: types.Message):
    uid = msg.from_user.id
    cur.execute(
        "SELECT item, rarity, price, date FROM inventory "
        "WHERE user_id=? ORDER BY id DESC LIMIT 15",
        (uid,)
    )
    rows = cur.fetchall()
    if not rows:
        await msg.answer("🎒 Inventaringiz bo'sh.\nQutilarni oching!")
        return

    lines = []
    for item, rarity, price, date in rows:
        em = RARITY_COLOR.get(rarity,"⚪")
        lines.append(f"{em} *{item}*\n   💰 {price_fmt(price)} 🪙  •  {rarity}")

    await msg.answer(
        "╔══════════════════════╗\n"
        "║    🎒  INVENTAR      ║\n"
        "╚══════════════════════╝\n\n" +
        "\n\n".join(lines),
        parse_mode="Markdown"
    )

# ══════════════════════════════════════════
# 📨  CALLBACKS — case ko'rish
# ══════════════════════════════════════════
@dp.callback_query(F.data.startswith("case_info:"))
async def case_info(call: types.CallbackQuery):
    key  = call.data.split(":")[1]
    case = CASES[key]

    lines = []
    for it in case["items"]:
        em = RARITY_COLOR.get(it["rarity"],"⚪")
        lines.append(f"{em} {it['name']}  —  *{price_fmt(it['price'])} 🪙*  ({it['chance']}%)")

    await call.message.edit_text(
        f"╔══════════════════════╗\n"
        f"║  {case['emoji']}  {case['name']:^18}║\n"
        f"╚══════════════════════╝\n\n"
        f"💵 Narxi: *{case['price']} 🪙* yoki *1 🔑*\n\n"
        "📋 *Tarkib:*\n" + "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=case_action_kb(key)
    )
    await call.answer()

@dp.callback_query(F.data == "back_cases")
async def back_cases(call: types.CallbackQuery):
    await call.message.edit_text(
        "╔═══════════════════════╗\n"
        "║     🎁  QUTILAR       ║\n"
        "╚═══════════════════════╝\n\n"
        "Qutini tanlang:",
        reply_markup=cases_kb()
    )
    await call.answer()

# ══════════════════════════════════════════
# 🎰  ANIMATION + OPEN LOGIC
# ══════════════════════════════════════════
async def do_open(call: types.CallbackQuery, case_key: str, count: int = 1):
    uid  = call.from_user.id
    case = CASES[case_key]
    bal, keys, opened, won, refs = db_get(uid)
    total_cost = case["price"] * count

    if bal < total_cost:
        await call.answer(
            f"❌ Pul yetarli emas!\nKerak: {total_cost} 🪙 | Sizda: {bal} 🪙",
            show_alert=True
        )
        return

    await call.answer()
    db_update(uid, balance_delta=-total_cost, cases_delta=count)

    # --- animatsiya ---
    frames = [
        "🎰  |  ⬜⬜⬜⬜⬜  |  Aylanyapti...",
        "🎰  |  🔵⬜⬜⬜⬜  |  Aylanyapti...",
        "🎰  |  🔵🟣⬜⬜⬜  |  Aylanyapti...",
        "🎰  |  🔵🟣🩷⬜⬜  |  Sekinlayapti...",
        "🎰  |  🔵🟣🩷🔴⬜  |  Sekinlayapti...",
    ]
    anim_msg = await call.message.edit_text(frames[0])
    for f in frames[1:]:
        await asyncio.sleep(0.5)
        try:
            await anim_msg.edit_text(f)
        except Exception:
            pass

    # --- natija ---
    results = [spin(case_key) for _ in range(count)]
    total_prize = sum(r["price"] for r in results)
    db_update(uid, balance_delta=0, won_delta=total_prize)

    # inventory'ga yozish
    for r in results:
        cur.execute(
            "INSERT INTO inventory (user_id, item, rarity, price) VALUES (?,?,?,?)",
            (uid, r["name"], r["rarity"], r["price"])
        )
    conn.commit()

    if count == 1:
        r  = results[0]
        em = RARITY_COLOR.get(r["rarity"],"⚪")
        bars = RARITY_ANIM.get(r["rarity"], ["⬜"]*5)
        bar  = "".join(bars)
        text = (
            f"╔══════════════════════╗\n"
            f"║   🎉  YUTILDI!       ║\n"
            f"╚══════════════════════╝\n\n"
            f"🎰  |  {bar}  |  STOP!\n\n"
            f"{em} *{r['name']}*\n"
            f"📊 Nadir: _{r['rarity']}_\n"
            f"💰 Qiymati: *{price_fmt(r['price'])} 🪙*"
        )
    else:
        lines = []
        for r in results:
            em = RARITY_COLOR.get(r["rarity"],"⚪")
            lines.append(f"{em} *{r['name']}*  —  {price_fmt(r['price'])} 🪙")
        text = (
            f"╔══════════════════════╗\n"
            f"║  🎉  5x NATIJALAR    ║\n"
            f"╚══════════════════════╝\n\n"
            + "\n".join(lines) +
            f"\n\n💰 Jami yutildi: *{price_fmt(total_prize)} 🪙*"
        )

    b = InlineKeyboardBuilder()
    b.add(types.InlineKeyboardButton(text="🔄 Yana och", callback_data=f"open_coin:{case_key}"))
    b.add(types.InlineKeyboardButton(text="◀️ Qutilar",  callback_data="back_cases"))
    b.adjust(2)

    try:
        await anim_msg.edit_text(text, parse_mode="Markdown", reply_markup=b.as_markup())
    except Exception:
        await call.message.answer(text, parse_mode="Markdown", reply_markup=b.as_markup())


@dp.callback_query(F.data.startswith("open_coin:"))
async def open_coin(call: types.CallbackQuery):
    await do_open(call, call.data.split(":")[1], count=1)

@dp.callback_query(F.data.startswith("open_5x:"))
async def open_5x(call: types.CallbackQuery):
    await do_open(call, call.data.split(":")[1], count=5)

@dp.callback_query(F.data.startswith("open_key:"))
async def open_key(call: types.CallbackQuery):
    uid  = call.from_user.id
    key  = call.data.split(":")[1]
    bal, keys, *_ = db_get(uid)

    if keys < 1:
        await call.answer("❌ Kalitingiz yo'q!\nMagazindan sotib oling.", show_alert=True)
        return

    db_update(uid, keys_delta=-1)
    await do_open(call, key, count=1)

# ══════════════════════════════════════════
# 🛒  SHOP CALLBACKS
# ══════════════════════════════════════════
@dp.callback_query(F.data.startswith("buy_key:"))
async def buy_key(call: types.CallbackQuery):
    uid   = call.from_user.id
    count = int(call.data.split(":")[1])
    price = {1: 200, 5: 900, 10: 1700}[count]
    bal, *_ = db_get(uid)

    if bal < price:
        await call.answer(f"❌ Pul yetarli emas! Kerak: {price} 🪙", show_alert=True)
        return

    db_update(uid, balance_delta=-price, keys_delta=count)
    await call.answer(f"✅ {count} ta kalit sotib olindi!", show_alert=True)

    # balansni yangilash
    bal2, keys2, *_ = db_get(uid)
    try:
        await call.message.edit_text(
            "╔══════════════════════╗\n"
            "║     💰  MAGAZIN      ║\n"
            "╚══════════════════════╝\n\n"
            f"✅ Sotib olindi: *{count} 🔑*\n\n"
            f"💳 Qolgan balans: *{price_fmt(bal2)} 🪙*\n"
            f"🔑 Kalitlar: *{keys2}*\n\n"
            "Yana kalitlar:",
            parse_mode="Markdown",
            reply_markup=shop_kb()
        )
    except Exception:
        pass

# ══════════════════════════════════════════
# 🚀  RUN
# ══════════════════════════════════════════
async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    logging.info("🚀 CS2 Bot ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")