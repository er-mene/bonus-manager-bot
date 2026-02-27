import os
from dotenv import load_dotenv
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.formatting import Text, Bold
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InputFile
import asyncpg

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
USER = os.getenv("POSTGRES_USER")
PASSWORD = os.getenv("POSTGRES_PASSWORD")
DATABASE = os.getenv("POSTGRES_DB")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")

bot = Bot(TOKEN)
dp = Dispatcher()


async def get_main_menu(user_name):
    conn = await asyncpg.connect(user=USER,
                                password=PASSWORD,
                                database=DATABASE,
                                host=DB_HOST,
                                port=DB_PORT)

    num_promos = await conn.fetchval('SELECT COUNT(*) FROM promotion WHERE active = true')
    
    caption = Text(Bold(f"Ciao {user_name}!\nBenvenuto/a sul bot ufficiale di Bonus Hustlin 🤑\n\n") +
                   "Attualmente sono attive " + Bold(f"{num_promos}") + " promozioni\n\n" +
                   "👇 " + Bold("Accedi subito alla lista!\n\n"))

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📋 Lista Promozioni", callback_data="list_promotions")],
        [types.InlineKeyboardButton(text="🆘 Assistenza", url="https://t.me/ErMenee")],
        [types.InlineKeyboardButton(text="🔗 Canale Bonus Hustlin", url="https://t.me/bonushustlin")]
    ])

    return caption, keyboard


async def get_db_connection():
    conn = await asyncpg.connect(user=USER,
                                password=PASSWORD,
                                database=DATABASE,
                                host=DB_HOST,
                                port=DB_PORT)
    return conn


async def get_promo_header(promo_name):
    conn = await get_db_connection()
    row = await conn.fetchrow('''SELECT bonus_txt, end_date, deposit_txt, timing_text, kyc, max_slots, phisical_card, fees
                                 FROM promotion WHERE platform = $1''', promo_name)
    
    bonus_txt = row['bonus_txt']
    end_date_txt = row['end_date'].strftime('%d/%m/%Y')
    deposit_txt = row['deposit_txt']
    timing_txt = row['timing_text']
    kyc = "si" if row['kyc'] else "no"
    max_slots = row['max_slots']
    max_slots_txt = Bold("👥 Limite inviti: ") + max_slots + "\n" if max_slots else ""
    has_phisical_card = "💳 Carta fisica obbligatoria" if row['phisical_card'] else ""
    fees = row['fees']
    fees_txt = Bold("📤 Commissioni: ") + fees + "\n" if fees else ""

    header = (  Bold("💸 Bonus: ") + bonus_txt + "\n" +
                Bold("📥 Deposito: ") + deposit_txt + "\n" +
                Bold("🗓 Scadenza: ") + end_date_txt + "\n" +
                Bold("⏱ Tempistiche: ") + timing_txt + "\n" +
                Bold("🆔 Verifica documenti: ") + kyc + "\n" +
                max_slots_txt +
                Bold(has_phisical_card) +
                fees_txt )
    
    return header


def num_to_emoji(num):
    emoji_numbers = {
        '0': '0️⃣',
        '1': '1️⃣',
        '2': '2️⃣',
        '3': '3️⃣',
        '4': '4️⃣',
        '5': '5️⃣',
        '6': '6️⃣',
        '7': '7️⃣',
        '8': '8️⃣',
        '9': '9️⃣'
    }
    return ''.join(emoji_numbers.get(digit, digit) for digit in str(num))


@dp.callback_query(F.data == "list_promotions")
async def list_callback_handler(callback_query: types.CallbackQuery):
    await callback_query.answer() #interrupt loading notification
    print(f"📋 Lista promozioni richiesta da {callback_query.from_user.id} - {callback_query.from_user.full_name}")

    #fetch promotions from database
    conn = await get_db_connection()
    rows = await conn.fetch('''SELECT platform
                               FROM promotion WHERE active = true
                               ORDER BY deposit_min, bonus_min''')
    
    total_sum = await conn.fetchval('SELECT SUM(bonus_min) FROM promotion WHERE active = true')
    
    #format list
    builder = InlineKeyboardBuilder()
    promos = []

    i = 1
    for row in rows:
        name = row['platform']
        header = await get_promo_header(name)
        n_emoji = num_to_emoji(i)
        promos.append(Text(Bold(f"{n_emoji} {name.upper()}\n"), header, "\n\n"))
        builder.button(text=f"{n_emoji}", callback_data=f"promo_{name.lower()}")
        i += 1

    builder.adjust(5)
    builder.row(types.InlineKeyboardButton(text="🔙 Torna al menu principale", callback_data="main_menu"))

    caption = Text( Bold(f"📋 PROMOZIONI ATTIVE 📋\n\n\n"), 
                    *promos, 
                    Bold(f"📈 Guadagno potenziale complessivo: {total_sum}€\n\n",
                    "Premi il numero corrispondente alla promozione desiderata per ottenere la guida!"))

    try: await callback_query.message.edit_text(**caption.as_kwargs(), reply_markup=builder.as_markup())
    except: 
        await callback_query.message.delete()
        await callback_query.message.answer(**caption.as_kwargs(), reply_markup=builder.as_markup())


@dp.callback_query(F.data.startswith("promo_"))
async def promo_callback_handler(callback_query: types.CallbackQuery):
    await callback_query.answer() #interrupt loading notification
    conn = await get_db_connection()
    promo_name = callback_query.data.split("promo_")[1]
    row = await conn.fetchrow('SELECT guide, photo_id FROM promotion WHERE platform = $1', promo_name)
    header = await get_promo_header(promo_name)
    caption = Text(Bold(f"💰 {promo_name.upper()}\n\n"), header, "\n\n", row['guide'])
    photo = row['photo_id']
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="↩️ Torna alla lista", callback_data="list_promotions")],
        [types.InlineKeyboardButton(text="🆘 Assistenza", url="https://t.me/ErMenee")],
    ])
    media = types.InputMediaPhoto(media=photo, **caption.as_caption_kwargs())
    await callback_query.message.edit_media(media=media, reply_markup=keyboard)


@dp.callback_query(F.data == "main_menu")
async def menu_callback_handler(callback_query: types.CallbackQuery):
    await callback_query.answer() #interrupt loading notification
    caption, keyboard = await get_main_menu(callback_query.from_user.full_name)
    await callback_query.message.edit_text(**caption.as_kwargs(), reply_markup=keyboard)


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    print(f"📩 Nuovo utente: {message.from_user.id} - {message.from_user.full_name}")
    caption, keyboard = await get_main_menu(message.from_user.full_name)
    await message.answer(**caption.as_kwargs(), reply_markup=keyboard)


async def main() -> None:
    print("🤖 Bot avviato. In attesa di messaggi...")
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())