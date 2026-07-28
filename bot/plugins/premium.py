# Copyright (c) 2025 Gagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  
# See LICENSE file in the repository root for full license text.

from shared_client import client as bot_client, app
from telethon import events
from datetime import timedelta
from config import OWNER_ID
from utils.func import add_premium_user, is_private_chat
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton as IK, InlineKeyboardMarkup as IKM
from config import OWNER_ID, JOIN_LINK as JL , ADMIN_CONTACT as AC
import base64 as spy
from utils.func import a1, a2, a3, a4, a5, a7, a8, a9, a10, a11
from plugins.start import subscribe


@bot_client.on(events.NewMessage(pattern='/add'))
async def add_premium_handler(event):
    if not await is_private_chat(event):
        await event.respond(
            'This command can only be used in private chats for security reasons.'
            )
        return
    """Handle /add command to add premium users (owner only)"""
    user_id = event.sender_id
    if user_id not in OWNER_ID:
        await event.respond('This command is restricted to the bot owner.')
        return
    text = event.message.text.strip()
    parts = text.split(' ')
    if len(parts) != 4:
        await event.respond(
            """Invalid format. Use: /add user_id duration_value duration_unit
Example: /add 123456 1 week"""
            )
        return
    try:
        target_user_id = int(parts[1])
        duration_value = int(parts[2])
        duration_unit = parts[3].lower()
        # Normalize common aliases (singular/plural) to canonical units
        unit_aliases = {
            'minute': 'min', 'minutes': 'min', 'mins': 'min', 'm': 'min',
            'hour': 'hours', 'hr': 'hours', 'hrs': 'hours', 'h': 'hours',
            'day': 'days', 'd': 'days',
            'week': 'weeks', 'w': 'weeks',
            'months': 'month', 'mo': 'month',
            'years': 'year', 'yr': 'year', 'yrs': 'year', 'y': 'year',
            'decade': 'decades',
        }
        duration_unit = unit_aliases.get(duration_unit, duration_unit)
        valid_units = ['min', 'hours', 'days', 'weeks', 'month', 'year',
            'decades']
        if duration_unit not in valid_units:
            await event.respond(
                f"Invalid duration unit. Choose from: {', '.join(valid_units)}"
                )
            return
        success, result = await add_premium_user(target_user_id,
            duration_value, duration_unit)
        if success:
            expiry_utc = result
            expiry_ist = expiry_utc + timedelta(hours=5, minutes=30)
            formatted_expiry = expiry_ist.strftime('%d-%b-%Y %I:%M:%S %p')
            await event.respond(
                f"""✅ User {target_user_id} added as premium member
Subscription valid until: {formatted_expiry} (IST)"""
                )
            await bot_client.send_message(target_user_id,
                f"""✅ Your have been added as premium member
**Validity upto**: {formatted_expiry} (IST)"""
                )
        else:
            await event.respond(f'❌ Failed to add premium user: {result}')
    except ValueError:
        await event.respond(
            'Invalid user ID or duration value. Both must be integers.')
    except Exception as e:
        await event.respond(f'Error: {str(e)}')
        
        
START_TEXT = (
    "> 👋 **Welcome {mention}!**\n\n"
    "**I am the Advanced Save Restricted Content Bot.**\n\n"
    "> 🚀 **What I Can Do:**\n"
    "> **‣ Save Restricted Post (Text, Media, Files)**\n"
    "> **‣ Support Private & Public Channels**\n"
    "> **‣ Batch/Bulk Mode Supported**\n\n"
    "> ⚠️ **Note:** __You must__ `/login` __to your account to use the "
    "downloading features.__"
)

HOW_TO_TEXT = (
    "🛠 **How To Use Me**\n\n"
    "👤 **User Commands**\n"
    "> /start - Start the bot\n"
    "> /help - How to use guide\n"
    "> /id - View user ID, chat ID\n"
    "> /commands - View all commands\n"
    "> /login - Login your Telegram account\n"
    "> /logout - Logout current session\n"
    "> /cancel - Cancel ongoing process\n"
    "> /settings - Bot settings (Caption, Rename, Upload, Thumbnail)\n"
    "> /referral - Referral program\n"
    "> /myplan - Check your plan\n"
    "> /premium - Buy premium\n\n"
    "📌 **How To Save Content**\n"
    "> **Single Post:** Send any Telegram post link\n"
    "> **Batch/Bulk:** Send link with range like\n"
    "> `https://t.me/channel/1-100`\n"
    "> **Upload Chat:** Set via /settings ➜ Set Upload\n"
    "> **Custom Caption:** /settings ➜ Set Caption\n"
    "> **Rename Rules:** /settings ➜ Set Rename (delete/replace words)\n\n"
    "🎬 **Bot Content Extraction** ( 💎 **Premium**)\n"
    "> Extract restricted content from other bots!\n"
    "> Just send the bot's deep link like:\n"
    "> `https://t.me/SomeBot?start=PARAM`\n"
    ">\n"
    "> Bot will extract all messages & media the target bot sends.\n"
    "> **Limit:** 5000 msgs/link | 2 min cooldown"
)

ABOUT_TEXT = (
    "ℹ️ **About Bot**\n\n"
    "> 🤖 **Name:** Advanced Save Restricted Content Bot\n"
    "> ⚙️ **Version:** v3\n"
    "> 🐍 **Language:** Python (Pyrogram + Telethon)\n"
    "> 💾 **Database:** MongoDB\n"
    "> 👨‍💻 **Developer:** [Contact]({admin})\n"
    "> 🚩 **Channel:** [Join Here]({join})"
)


def start_keyboard():
    return IKM([
        [
            IK("🆘 How To Use", callback_data="start_how"),
            IK("ℹ️ About Bot", callback_data="start_about"),
        ],
        [IK("⚙️ Settings", callback_data="start_settings")],
        [
            IK("📢 Official Channel", url=JL),
            IK("👨‍💻 Developer", url=AC),
        ],
    ])


def back_keyboard():
    return IKM([[IK("⬅️ Back", callback_data="start_back")]])


def how_keyboard():
    return IKM([[
        IK("❌ Close", callback_data="start_close"),
        IK("⬅️ Back", callback_data="start_back"),
    ]])


@app.on_message(filters.command(spy.b64decode(a5.encode()).decode()))
async def start_handler(client, message):
    subscription_status = await subscribe(client, message)
    if subscription_status == 1:
        return

    mention = message.from_user.mention if message.from_user else "there"
    await message.reply_text(
        START_TEXT.format(mention=mention),
        reply_markup=start_keyboard(),
        disable_web_page_preview=True,
        reply_to_message_id=message.id,
    )


@app.on_callback_query(filters.regex(r"^start_(how|about|settings|back|close)$"))
async def start_menu_cb(client, callback_query):
    action = callback_query.data.split("_", 1)[1]

    if action == "how":
        await callback_query.message.edit_text(
            HOW_TO_TEXT, reply_markup=how_keyboard(),
            disable_web_page_preview=True,
        )
    elif action == "close":
        try:
            await callback_query.message.delete()
        except Exception:
            pass
        await callback_query.answer()
        return
    elif action == "about":
        await callback_query.message.edit_text(
            ABOUT_TEXT.format(admin=AC, join=JL),
            reply_markup=back_keyboard(),
            disable_web_page_preview=True,
        )
    elif action == "settings":
        try:
            from plugins.settings import send_settings_message
            await send_settings_message(callback_query.message.chat.id, callback_query.from_user.id)
            await callback_query.answer()
        except Exception:
            await callback_query.answer("Send /settings to personalize things.", show_alert=True)
        return
    else:
        mention = callback_query.from_user.mention if callback_query.from_user else "there"
        await callback_query.message.edit_text(
            START_TEXT.format(mention=mention),
            reply_markup=start_keyboard(),
            disable_web_page_preview=True,
        )

    await callback_query.answer()
