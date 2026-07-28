# Copyright (c) 2025 devgagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  
# See LICENSE file in the repository root for full license text.

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import BadRequest, SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired, MessageNotModified
from pyrogram.enums import ParseMode
import logging
import os
import asyncio
from config import API_HASH, API_ID
from shared_client import app as bot
from utils.func import save_user_session, get_user_data, remove_user_session, save_user_bot, remove_user_bot
from utils.encrypt import ecs, dcs
from plugins.batch import UB, UC
from utils.custom_filters import login_in_progress, set_user_step, get_user_step
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
model = "v3saver Team SPY"

STEP_PHONE = 1
STEP_CODE = 2
STEP_PASSWORD = 3
login_cache = {}

PHONE_TIMEOUT = 180   # 3 minutes to send phone
CODE_TIMEOUT = 300    # 5 minutes to send OTP
PW_TIMEOUT = 300      # 5 minutes to send 2FA password
MAX_ATTEMPTS = 3

DIVIDER = "━━━━━━━━━━━━━━━━━━━━"

CANCEL_TEXT = (
    "❌ <b>Login cancelled. All data cleared.</b>\n\n"
    "Send <b>/login</b> to start again."
)


def _phone_prompt() -> str:
    return (
        f"{DIVIDER}\n\n"
        "📱 <b>Send your phone number</b>\n\n"
        "Include country code, e.g. <code>+12345678900</code>\n\n"
        f"⏱ You have <b>3 minutes</b> to send it.\n"
        "Send /cancellogin to stop."
    )


def _otp_prompt(attempts_left: int) -> str:
    return (
        f"{DIVIDER}\n\n"
        "📩 <b>OTP Sent!</b>\n\n"
        "Open your Telegram app and check the code.\n\n"
        "⚠️ <b>Never send OTP directly as one number.</b>\n"
        "Always add spaces between digits.\n\n"
        "✅ <code>12 345</code>\n"
        "✅ <code>1 2 3 4 5</code>\n"
        "❌ <code>12345</code>\n\n"
        f"⏱ Expires in <b>5 minutes</b> · <b>{attempts_left} attempt(s) left</b>\n"
        "Send /cancellogin to stop."
    )


def _password_prompt(hint: str, attempts_left: int) -> str:
    hint_line = f"Hint: <code>{hint}</code>\n\n" if hint else ""
    return (
        f"{DIVIDER}\n\n"
        "🔒 <b>Your account requires a password.</b>\n\n"
        f"{hint_line}"
        f"⏱ <b>5 minutes</b> to enter. Max <b>{attempts_left}</b> attempts.\n\n"
        "Send /cancellogin to cancel."
    )


SUCCESS_TEXT = (
    "✅ <b>Login Successful!</b>\n\n\n"
    "Your account is now connected.\n"
    "You can save restricted content.\n\n"
    "Use /check to verify your session anytime."
)


async def _cleanup(user_id: int, cancel_timeout: bool = True):
    entry = login_cache.get(user_id)
    if not entry:
        set_user_step(user_id, None)
        return
    if cancel_timeout:
        task = entry.get('timeout_task')
        if task and not task.done():
            task.cancel()
    tc = entry.get('temp_client')
    if tc:
        try:
            await tc.disconnect()
        except Exception:
            pass
    login_cache.pop(user_id, None)
    set_user_step(user_id, None)


async def _timeout_watchdog(user_id: int, token: object, seconds: int):
    try:
        await asyncio.sleep(seconds)
    except asyncio.CancelledError:
        return
    entry = login_cache.get(user_id)
    if not entry or entry.get('token') is not token:
        return
    status_msg = entry.get('status_msg')
    await _cleanup(user_id, cancel_timeout=False)
    if status_msg:
        await edit_message_safely(status_msg, CANCEL_TEXT)


def _arm_timeout(user_id: int, seconds: int):
    entry = login_cache.get(user_id)
    if not entry:
        return
    old = entry.get('timeout_task')
    if old and not old.done():
        old.cancel()
    token = object()
    entry['token'] = token
    entry['timeout_task'] = asyncio.create_task(
        _timeout_watchdog(user_id, token, seconds)
    )


@bot.on_message(filters.command('login'))
async def login_command(client, message):
    user_id = message.from_user.id
    # Reset any prior state cleanly
    if user_id in login_cache:
        await _cleanup(user_id)
    set_user_step(user_id, STEP_PHONE)
    try:
        await message.delete()
    except Exception:
        pass
    status_msg = await message.reply(_phone_prompt(), parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    login_cache[user_id] = {'status_msg': status_msg}
    _arm_timeout(user_id, PHONE_TIMEOUT)
    
    
@bot.on_message(filters.command("setbot"))
async def set_bot_token(C, m):
    user_id = m.from_user.id
    args = m.text.split(" ", 1)
    if user_id in UB:
        try:
            await UB[user_id].stop()
            if UB.get(user_id, None):
                del UB[user_id]  # Remove from dictionary
                
            try:
                if os.path.exists(f"user_{user_id}.session"):
                    os.remove(f"user_{user_id}.session")
            except Exception:
                pass
            
            print(f"Stopped and removed old bot for user {user_id}")
        except Exception as e:
            print(f"Error stopping old bot for user {user_id}: {e}")
            del UB[user_id]  # Remove from dictionary

    if len(args) < 2:
        await m.reply_text("⚠️ Please provide a bot token. Usage: `/setbot token`", quote=True)
        return

    bot_token = args[1].strip()
    saved = await save_user_bot(user_id, bot_token)
    if saved:
        await m.reply_text("✅ Bot token saved successfully.", quote=True)
    else:
        await m.reply_text("❌ Bot token could not be saved because MongoDB is not connected. Fix Atlas Network Access first.", quote=True)
    
    
@bot.on_message(filters.command("rembot"))
async def rem_bot_token(C, m):
    user_id = m.from_user.id
    if user_id in UB:
        try:
            await UB[user_id].stop()
            
            if UB.get(user_id, None):
                del UB[user_id]  # Remove from dictionary # Remove from dictionary
            print(f"Stopped and removed old bot for user {user_id}")
            try:
                if os.path.exists(f"user_{user_id}.session"):
                    os.remove(f"user_{user_id}.session")
            except Exception:
                pass
        except Exception as e:
            print(f"Error stopping old bot for user {user_id}: {e}")
            if UB.get(user_id, None):
                del UB[user_id]  # Remove from dictionary  # Remove from dictionary
            try:
                if os.path.exists(f"user_{user_id}.session"):
                    os.remove(f"user_{user_id}.session")
            except Exception:
                pass
    await remove_user_bot(user_id)
    await m.reply_text("✅ Bot token removed successfully.", quote=True)

    
@bot.on_message(login_in_progress & filters.text & filters.private & ~filters.command([
    'start', 'batch', 'cancel', 'login', 'logout', 'stop', 'set', 'pay',
    'redeem', 'gencode', 'generate', 'keyinfo', 'encrypt', 'decrypt', 'keys', 'setbot', 'rembot', 'cancellogin', 'check']))
async def handle_login_steps(client, message):
    user_id = message.from_user.id
    text = message.text.strip()
    step = get_user_step(user_id)
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f'Could not delete message: {e}')
    entry = login_cache.get(user_id) or {}
    status_msg = entry.get('status_msg')
    if not status_msg:
        status_msg = await message.reply('Processing...')
        login_cache.setdefault(user_id, {})['status_msg'] = status_msg
    try:
        if step == STEP_PHONE:
            if not text.startswith('+'):
                await edit_message_safely(status_msg,
                    '❌ Please provide a valid phone number starting with +')
                return
            await edit_message_safely(status_msg, '⏳ Sending OTP...')
            temp_client = Client(f'temp_{user_id}', api_id=API_ID, api_hash
                =API_HASH, device_model=model, in_memory=True)
            try:
                await temp_client.connect()
                sent_code = await temp_client.send_code(text)
                login_cache[user_id]['phone'] = text
                login_cache[user_id]['phone_code_hash'
                    ] = sent_code.phone_code_hash
                login_cache[user_id]['temp_client'] = temp_client
                login_cache[user_id]['otp_attempts'] = MAX_ATTEMPTS
                set_user_step(user_id, STEP_CODE)
                await edit_message_safely(status_msg, _otp_prompt(MAX_ATTEMPTS))
                _arm_timeout(user_id, CODE_TIMEOUT)
            except BadRequest as e:
                await edit_message_safely(status_msg,
                    f"""❌ Error: {str(e)}
Please try again with /login.""")
                await temp_client.disconnect()
                await _cleanup(user_id)
        elif step == STEP_CODE:
            # Enforce: user MUST separate digits with spaces
            if ' ' not in text:
                login_cache[user_id]['otp_attempts'] = login_cache[user_id].get('otp_attempts', MAX_ATTEMPTS) - 1
                left = login_cache[user_id]['otp_attempts']
                if left <= 0:
                    await _cleanup(user_id)
                    await edit_message_safely(status_msg, CANCEL_TEXT)
                    return
                await edit_message_safely(status_msg, _otp_prompt(left))
                return
            code = text.replace(' ', '')
            if not code.isdigit() or len(code) != 5:
                login_cache[user_id]['otp_attempts'] = login_cache[user_id].get('otp_attempts', MAX_ATTEMPTS) - 1
                left = login_cache[user_id]['otp_attempts']
                if left <= 0:
                    await _cleanup(user_id)
                    await edit_message_safely(status_msg, CANCEL_TEXT)
                    return
                await edit_message_safely(status_msg, _otp_prompt(left))
                return
            phone = login_cache[user_id]['phone']
            phone_code_hash = login_cache[user_id]['phone_code_hash']
            temp_client = login_cache[user_id]['temp_client']
            try:
                await edit_message_safely(status_msg, '🔄 Verifying code...')
                await temp_client.sign_in(phone, phone_code_hash, code)
                session_string = await temp_client.export_session_string()
                encrypted_session = ecs(session_string)
                saved = await save_user_session(user_id, encrypted_session)
                await _cleanup(user_id)
                if saved:
                    await edit_message_safely(status_msg, SUCCESS_TEXT)
                else:
                    await edit_message_safely(status_msg,
                        """❌ Login verified, but session was not saved because MongoDB is not connected. Fix Atlas Network Access first."""
                        )
            except SessionPasswordNeeded:
                # fetch hint
                hint = ''
                try:
                    hint = await temp_client.get_password_hint() or ''
                except Exception as e:
                    logger.warning(f'get_password_hint failed: {e}')
                login_cache[user_id]['pw_attempts'] = MAX_ATTEMPTS
                set_user_step(user_id, STEP_PASSWORD)
                await edit_message_safely(status_msg, _password_prompt(hint, MAX_ATTEMPTS))
                _arm_timeout(user_id, PW_TIMEOUT)
            except (PhoneCodeInvalid, PhoneCodeExpired) as e:
                login_cache[user_id]['otp_attempts'] = login_cache[user_id].get('otp_attempts', MAX_ATTEMPTS) - 1
                left = login_cache[user_id]['otp_attempts']
                if left <= 0:
                    await _cleanup(user_id)
                    await edit_message_safely(status_msg, CANCEL_TEXT)
                    return
                await edit_message_safely(status_msg, _otp_prompt(left))
        elif step == STEP_PASSWORD:
            temp_client = login_cache[user_id]['temp_client']
            try:
                await edit_message_safely(status_msg, '🔄 Verifying password...'
                    )
                await temp_client.check_password(text)
                session_string = await temp_client.export_session_string()
                encrypted_session = ecs(session_string)
                saved = await save_user_session(user_id, encrypted_session)
                await _cleanup(user_id)
                if saved:
                    await edit_message_safely(status_msg, SUCCESS_TEXT)
                else:
                    await edit_message_safely(status_msg,
                        """❌ Login verified, but session was not saved because MongoDB is not connected. Fix Atlas Network Access first."""
                        )
            except BadRequest as e:
                login_cache[user_id]['pw_attempts'] = login_cache[user_id].get('pw_attempts', MAX_ATTEMPTS) - 1
                left = login_cache[user_id]['pw_attempts']
                if left <= 0:
                    await _cleanup(user_id)
                    await edit_message_safely(status_msg, CANCEL_TEXT)
                    return
                hint = ''
                try:
                    hint = await temp_client.get_password_hint() or ''
                except Exception:
                    pass
                await edit_message_safely(status_msg, _password_prompt(hint, left))
    except Exception as e:
        logger.error(f'Error in login flow: {str(e)}')
        await edit_message_safely(status_msg,
            f"""❌ An error occurred: {str(e)}
Please try again with /login.""")
        await _cleanup(user_id)
async def edit_message_safely(message, text):
    """Helper function to edit message and handle errors"""
    try:
        from pyrogram.enums import ParseMode
        await message.edit(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except MessageNotModified:
        pass
    except Exception as e:
        logger.error(f'Error editing message: {e}')
        
@bot.on_message(filters.command(['cancel', 'cancellogin']))
async def cancel_command(client, message):
    user_id = message.from_user.id
    try:
        await message.delete()
    except Exception:
        pass
    if get_user_step(user_id):
        status_msg = login_cache.get(user_id, {}).get('status_msg')
        await _cleanup(user_id)
        if status_msg:
            await edit_message_safely(status_msg, CANCEL_TEXT)
        else:
            temp_msg = await message.reply(CANCEL_TEXT, parse_mode=ParseMode.HTML)
            await temp_msg.delete(5)
    else:
        temp_msg = await message.reply('No active login process to cancel.')
        await temp_msg.delete(5)
        
@bot.on_message(filters.command('logout'))
async def logout_command(client, message):
    user_id = message.from_user.id
    await message.delete()
    status_msg = await message.reply('🔄 Processing logout request...')
    try:
        session_data = await get_user_data(user_id)
        
        if not session_data or 'session_string' not in session_data:
            await edit_message_safely(status_msg,
                '❌ No active session found for your account.')
            return
        encss = session_data['session_string']
        session_string = dcs(encss)
        temp_client = Client(f'temp_logout_{user_id}', api_id=API_ID,
            api_hash=API_HASH, session_string=session_string)
        try:
            await temp_client.connect()
            await temp_client.log_out()
            await edit_message_safely(status_msg,
                '✅ Telegram session terminated successfully. Removing from database...'
                )
        except Exception as e:
            logger.error(f'Error terminating session: {str(e)}')
            await edit_message_safely(status_msg,
                f"""⚠️ Error terminating Telegram session: {str(e)}
Still removing from database..."""
                )
        finally:
            await temp_client.disconnect()
        await remove_user_session(user_id)
        await edit_message_safely(status_msg,
            '✅ Logged out successfully!!')
        try:
            if os.path.exists(f"{user_id}_client.session"):
                os.remove(f"{user_id}_client.session")
        except Exception:
            pass
        if UC.get(user_id, None):
            del UC[user_id]
    except Exception as e:
        logger.error(f'Error in logout command: {str(e)}')
        try:
            await remove_user_session(user_id)
        except Exception:
            pass
        if UC.get(user_id, None):
            del UC[user_id]
        await edit_message_safely(status_msg,
            f'❌ An error occurred during logout: {str(e)}')
        try:
            if os.path.exists(f"{user_id}_client.session"):
                os.remove(f"{user_id}_client.session")
        except Exception:
            pass

