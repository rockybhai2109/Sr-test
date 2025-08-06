# ---------------------------------------------------
# File Name: get_func.py
# Description: A Pyrogram bot for downloading files from Telegram channels or groups 
#              and uploading them back to Telegram.
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# Telegram: https://t.me/team_spy_pro
# YouTube: https://youtube.com/@dev_gagan
# Created: 2025-01-11
# Last Modified: 2025-02-01
# Version: 2.0.5
# License: MIT License
# Improved logic handles
# ---------------------------------------------------

import asyncio
import time
import gc
import os
import re
from typing import Callable
from devgagan import app
import aiofiles
from devgagan import sex as gf
from telethon.tl.types import DocumentAttributeVideo, Message
from telethon.sessions import StringSession
import pymongo
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid
from pyrogram.enums import MessageMediaType, ParseMode
from devgagan.core.func import *
from pyrogram.errors import RPCError
from pyrogram.types import Message
from config import MONGO_DB as MONGODB_CONNECTION_STRING, LOG_GROUP, OWNER_ID, STRING, API_ID, API_HASH
from devgagan.core.mongo import db as odb
from telethon import TelegramClient, events, Button
from devgagantools import fast_upload
from datetime import datetime
import asyncio
import unicodedata
from datetime import datetime
from pyrogram.enums import ParseMode
from telethon.tl.types import DocumentAttributeVideo
import random

# Clean filename helper


def clean_filename(text):
    if not text:
        return "file"

    # Normalize to separate combined accents
    text = unicodedata.normalize("NFKC", text)

    # Remove emojis and unwanted symbols (but keep letters from all scripts)
    text = ''.join(
        char for char in text
        if not unicodedata.category(char).startswith('S')  # Symbols (includes emojis)
        and not unicodedata.category(char).startswith('C')  # Control characters, etc.
        and not unicodedata.category(char).startswith('P')  # Punctuation
        or char in ['.', '-']  # Keep only period and dash
    )

    # Replace any remaining underscores, spaces, or dashes with a single space
    text = re.sub(r'[_\s\-]+', ' ', text)

    # Final strip
    return text.strip()



def thumbnail(sender):
    path = os.path.join(THUMBNAIL_DIR, f"{sender}.jpg")
    return path if os.path.exists(path) else None



THUMBNAIL_DIR = "./thumbnails"
os.makedirs(THUMBNAIL_DIR, exist_ok=True)

# MongoDB database name and collection name
DB_NAME = "smart_users"
COLLECTION_NAME = "super_user"

VIDEO_EXTENSIONS = ['mp4', 'mov', 'avi', 'mkv', 'flv', 'wmv', 'webm', 'mpg', 'mpeg', '3gp', 'ts', 'm4v', 'f4v', 'vob']
DOCUMENT_EXTENSIONS = ['pdf', 'docs']

mongo_app = pymongo.MongoClient(MONGODB_CONNECTION_STRING)
db = mongo_app[DB_NAME]
collection = db[COLLECTION_NAME]

if STRING:
    from devgagan import pro
    print("App imported")
else:
    pro = None
    print("STRING is not available. 'app' is set to None.")
    
async def fetch_upload_method(user_id):
    """Fetch the user's preferred upload method."""
    user_data = collection.find_one({"user_id": user_id})
    return user_data.get("upload_method", "Pyrogram") if user_data else "Pyrogram"


def format_caption_to_html(caption: str) -> str:
    if not caption:
        return None

    caption = re.sub(r"^> (.*)", r"<blockquote>\1</blockquote>", caption, flags=re.MULTILINE)
    caption = re.sub(r"```(.*?)```", r"<pre>\1</pre>", caption, flags=re.DOTALL)
    caption = re.sub(r"`(.*?)`", r"<code>\1</code>", caption)
    caption = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", caption)
    caption = re.sub(r"\*(.*?)\*", r"<b>\1</b>", caption)
    caption = re.sub(r"__(.*?)__", r"<i>\1</i>", caption)
    caption = re.sub(r"_(.*?)_", r"<i>\1</i>", caption)
    caption = re.sub(r"~~(.*?)~~", r"<s>\1</s>", caption)
    caption = re.sub(r"\|\|(.*?)\|\|", r"<details>\1</details>", caption)
    caption = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2">\1</a>', caption)
    
    return caption.strip()

    

from pyrogram.enums import ParseMode
from datetime import datetime
from telethon.tl.types import DocumentAttributeVideo
import os, gc, time, asyncio

# Unified log_upload
async def log_upload(user_id, file_type, file_msg, upload_method, duration=None, file_name=None):
    try:
        user = await app.get_users(user_id)
        bot = await app.get_me()

        # Keep mention format exactly like you want
        user_mention = user.mention if user else "User"

        bot_name = f"{bot.first_name} (@{bot.username})" if bot else "Unknown Bot"
        display_text = file_msg.caption or file_name or "No caption/filename"
        clean_text = (display_text[:1000] + '...') if len(display_text) > 1000 else display_text

        text = (
            f"{clean_text}\n\n"
            f"📁 **log info:**\n"
            f"👤 **User:** {user_mention}\n"
            f"🆔 **User ID:** `{user_id}`\n"
        )

        text += f"🤖 **Saved by:** {bot_name}"

        await file_msg.copy(LOG_GROUP, caption=text)

    except Exception as e:
        await app.send_message(LOG_GROUP, f"❌ Log Error: `{e}`")


# Upload handler
async def upload_media(sender, target_chat_id, file, caption, edit, topic_id):
    try:
        upload_method = await fetch_upload_method(sender)
        metadata = video_metadata(file)
        width, height, duration = metadata['width'], metadata['height'], metadata['duration']
        thumb_path = await screenshot(file, duration, sender)

        ext = file.split('.')[-1].lower()
        raw_name = os.path.basename(file)
        clean_name = clean_filename(os.path.splitext(raw_name)[0])
        file_name = f"{clean_name}.{ext}"

        video_formats = {'mp4', 'mkv', 'avi', 'mov'}
        image_formats = {'jpg', 'png', 'jpeg'}

        # ✅ Generate cleaned caption for user post
        caption = format_caption(caption, sender, custom_caption=None)

        # ✅ Generate log caption separately
        user = await app.get_users(sender)
        bot = await app.get_me()
        user_mention = user.mention if user else "User"
        bot_name = f"{bot.first_name} (@{bot.username})" if bot else "Bot"

        display_text = caption or file_name or "No caption/filename"
        clean_text = (display_text[:1000] + '...') if len(display_text) > 1000 else display_text

        log_caption = (            
            f"📁 **log info:**\n"
            f"👤 **User:** {user_mention}\n"
            f"🆔 **User ID:** `{sender}`\n"
            f"🤖 **Saved by:** {bot_name}"
        )

        # ────── Pyrogram Upload ──────
        if upload_method == "Pyrogram":
            if ext in video_formats:
                # Send to user
                dm = await app.send_video(
                    chat_id=target_chat_id,
                    video=file,
                    caption=caption,
                    height=height,
                    width=width,
                    duration=duration,
                    thumb=thumb_path,
                    reply_to_message_id=topic_id,
                    parse_mode=ParseMode.MARKDOWN,
                    progress=progress_bar,
                    progress_args=("╔══━⚡️Uploading...⚡️━══╗\n", edit, time.time())
                )

                # Send to log group (no caption)
                log_file_msg = await app.send_video(
                    LOG_GROUP,
                    caption=caption,
                    video=file,
                    height=height,
                    width=width,
                    duration=duration,
                    thumb=thumb_path,
                    has_spoiler=True,
                    parse_mode=ParseMode.MARKDOWN
                )

            elif ext in image_formats:
                dm = await app.send_photo(
                    chat_id=target_chat_id,
                    photo=file,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    progress=progress_bar,
                    reply_to_message_id=topic_id,
                    progress_args=("╔══━⚡️Uploading...⚡️━══╗\n", edit, time.time())
                )

                log_file_msg = await app.send_photo(
                    LOG_GROUP,
                    caption=caption,
                    photo=file,
                    has_spoiler=True,
                    parse_mode=ParseMode.MARKDOWN
                )

            else:
                dm = await app.send_document(
                    chat_id=target_chat_id,
                    document=file,
                    caption=caption,
                    thumb=thumb_path,
                    reply_to_message_id=topic_id,
                    parse_mode=ParseMode.MARKDOWN,
                    progress=progress_bar,
                    progress_args=("╔══━⚡️Uploading...⚡️━══╗\n", edit, time.time())
                )
                await asyncio.sleep(2)
                log_file_msg = await app.send_document(
                    LOG_GROUP,
                    caption=caption,
                    document=file,
                    thumb=thumb_path,
                    parse_mode=ParseMode.MARKDOWN
                )

            # ✅ Send log info separately as reply to log file
            await app.send_message(
                LOG_GROUP,
                text=log_caption,
                reply_to_message_id=log_file_msg.id,
                parse_mode=ParseMode.MARKDOWN
            )


        # ────── Telethon Upload ──────
        elif upload_method == "Telethon":
            await edit.delete()
            progress_message = await gf.send_message(sender, "**__Uploading...__**")
            caption_html = await format_caption_to_html(caption)

            uploaded = await fast_upload(
                gf, file,
                reply=progress_message,
                name=file_name,
                progress_bar_function=lambda done, total: progress_callback(done, total, sender)
            )
            await progress_message.delete()

            attributes = [
                DocumentAttributeVideo(duration=duration, w=width, h=height, supports_streaming=True)
            ] if ext in video_formats else []

            bot = await app.get_me()
            bot_name = f"{bot.first_name} (@{bot.username})" if bot else "Bot"

            log_caption = (
                f"📁 **File Name:** {file_name}\n\n"
                f"📤 **Upload Info**\n"
                f"👤 **User:** [{sender}](tg://user?id={sender})\n"
                f"🆔 **User ID:** `{sender}`\n"
                f"🗂️ **Type:** `{ext.upper()}`\n"

            )

            await gf.send_file(
                target_chat_id,
                uploaded,
                caption=caption_html,
                attributes=attributes,
                reply_to=topic_id,
                thumb_path = thumbnail(sender) or await screenshot(file, duration, sender)
            )

            await gf.send_file(
                LOG_GROUP,
                uploaded,
                caption=log_caption,
                attributes=attributes,
                thumb_path = thumbnail(sender) or await screenshot(file, duration, sender)
            )

    except Exception as e:
        await app.send_message(LOG_GROUP, f"❌ **Upload Failed:** `{str(e)}`")
        print(f"Error during media upload: {e}")

    finally:
    # Only delete if it was not from saved thumbnail
        if thumb_path and os.path.exists(thumb_path) and not thumb_path.startswith(THUMBNAIL_DIR):
            os.remove(thumb_path)
        gc.collect()



async def get_msg(userbot, sender, edit_id, msg_link, i, message):
    try:
        # Sanitize the message link
        msg_link = msg_link.split("?single")[0]
        chat, msg_id = None, None
        saved_channel_ids = load_saved_channel_ids()
        size_limit = 2 * 1024 * 1024 * 1024  # 1.99 GB size limit
        file = ''
        edit = ''
        # Extract chat and message ID for valid Telegram links
        if 't.me/c/' in msg_link or 't.me/b/' in msg_link:
            parts = msg_link.split("/")
            if 't.me/b/' in msg_link:
                chat = parts[-2]
                msg_id = int(parts[-1]) + i # fixed bot problem 
            else:
                chat = int('-100' + parts[parts.index('c') + 1])
                msg_id = int(parts[-1]) + i

            if chat in saved_channel_ids:
                await app.edit_message_text(
                    message.chat.id, edit_id,
                    "This channel is protected by **__CHOSEN ONE ⚝__💀**.\Kya Be... Hamara Hi Content Nikalega 🌝 Kahi Or Try Kar 😘"
                )
                return
            
        elif '/s/' in msg_link: # fixed story typo
            edit = await app.edit_message_text(sender, edit_id, "Story Link Dictected...")
            if userbot is None:
                await edit.edit("Login in bot save stories...")     
                return
            parts = msg_link.split("/")
            chat = parts[3]
            
            if chat.isdigit():   # this is for channel stories
                chat = f"-100{chat}"
            
            msg_id = int(parts[-1])
            await download_user_stories(userbot, chat, msg_id, edit, sender)
            await edit.delete(2)
            return
        
        else:
            edit = await app.edit_message_text(sender, edit_id, "Public link detected...🌝")
            chat = msg_link.split("t.me/")[1].split("/")[0]
            msg_id = int(msg_link.split("/")[-1])
            await copy_message_with_chat_id(app, userbot, sender, chat, msg_id, edit)
            await edit.delete(2)
            return
            
        # Fetch the target message
        msg = await userbot.get_messages(chat, msg_id)
        if not msg or msg.service or msg.empty:
            return

        target_chat_id = user_chat_ids.get(message.chat.id, message.chat.id)
        topic_id = None
        if '/' in str(target_chat_id):
            target_chat_id, topic_id = map(int, target_chat_id.split('/', 1))

        # Handle different message types
        if msg.media == MessageMediaType.WEB_PAGE_PREVIEW:
            await clone_message(app, msg, target_chat_id, topic_id, edit_id, LOG_GROUP)
            return

        if msg.text:
            await clone_text_message(app, msg, target_chat_id, topic_id, edit_id, LOG_GROUP)
            return

        if msg.sticker:
            await handle_sticker(app, msg, target_chat_id, topic_id, edit_id, LOG_GROUP)
            return

        
        # Handle file media (photo, document, video)
        file_size = get_message_file_size(msg)

        # if file_size and file_size > size_limit and pro is None:
        #     await app.edit_message_text(sender, edit_id, "**❌ 4GB Uploader not found**")
        #     return

        file_name = await get_media_filename(msg)
        edit = await app.edit_message_text(sender, edit_id, "**>Downloading...Darling 😉**")

        # Download media
        file = await userbot.download_media(
            msg,
            file_name=file_name,            
            progress_args=("╔══━⚡️ Downloading ⚡️━══╗\n", edit, time.time()),
            progress=progress_bar
        )
        
        caption = await get_final_caption(msg, sender)

        # Rename file
        file = await rename_file(file, sender)
        if msg.audio:
            result = await app.send_audio(target_chat_id, file, caption=caption, reply_to_message_id=topic_id)
            await result.copy(LOG_GROUP)
            await edit.delete(1)
            return
        
        if msg.voice:
            result = await app.send_voice(target_chat_id, file, reply_to_message_id=topic_id)
            await result.copy(LOG_GROUP)
            await edit.delete(1)
            return

        if msg.photo:
            result = await app.send_photo(target_chat_id, file, caption=caption, reply_to_message_id=topic_id)
            await result.copy(LOG_GROUP)
            await edit.delete(1)
            return

        # Upload media
        # await edit.edit("**Checking file...**")
        if file_size > size_limit and (free_check == 1 or pro is None):
            await edit.delete()
            await split_and_upload_file(app, sender, target_chat_id, file, caption, topic_id)
            return
        elif file_size > size_limit:
            await handle_large_file(file, sender, edit, caption)
        else:
            await upload_media(sender, target_chat_id, file, caption, edit, topic_id)

    except (ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid):
        await app.edit_message_text(sender, edit_id, "🌚 First do /login & then send me the Link again send /guide for more help")
    except Exception as e:
        # await app.edit_message_text(sender, edit_id, f"Failed to save: `{msg_link}`\n\nError: {str(e)}")
        print(f"Error: {e}")
    finally:
        # Clean up
        if file and os.path.exists(file):
            os.remove(file)
        if edit:
            await edit.delete(1)
        
async def clone_message(app, msg, target_chat_id, topic_id, edit_id, log_group):
    edit = await app.edit_message_text(target_chat_id, edit_id, "Cloning...")
    devgaganin = await app.send_message(target_chat_id, msg.text.markdown, reply_to_message_id=topic_id)
    await devgaganin.copy(log_group)
    await edit.delete()

async def clone_text_message(app, msg, target_chat_id, topic_id, edit_id, log_group):
    edit = await app.edit_message_text(target_chat_id, edit_id, "Cloning text message...")
    devgaganin = await app.send_message(target_chat_id, msg.text.markdown, reply_to_message_id=topic_id)
    await devgaganin.copy(log_group)
    await edit.delete()


async def handle_sticker(app, msg, target_chat_id, topic_id, edit_id, log_group):
    edit = await app.edit_message_text(target_chat_id, edit_id, "Handling sticker...")
    result = await app.send_sticker(target_chat_id, msg.sticker.file_id, reply_to_message_id=topic_id)
    await result.copy(log_group)
    await edit.delete()




async def get_media_filename(msg):
    if msg.document:
        return msg.document.file_name or "Document_By_@Src_pro_bot.txt"
    if msg.video:
        return msg.video.file_name or "Video_By_@Src_pro_bot.mp4"
    if msg.audio:
        return msg.audio.file_name or "Audio_By_@Src_pro_bot.mp3"
    if msg.photo:
        return "Image_By_@Src_pro_bot.jpg"
    return "File_By_@Src_pro_bot.dat"



def get_message_file_size(msg):
    if msg.document:
        return msg.document.file_size
    if msg.photo:
        return msg.photo.file_size
    if msg.video:
        return msg.video.file_size
    return 1



async def get_final_caption(msg, sender):
    # Get original caption in markdown if available
    original_caption = msg.caption.markdown if msg.caption else ""
    
    # Add custom caption if present
    custom_caption = get_user_caption_preference(sender)
    final_caption = f"{original_caption}\n\n{custom_caption}" if custom_caption else original_caption

    # Replace @mentions with @Real_Pirates
    final_caption = re.sub(r'@\w+', '@II_LevelUP_II', final_caption)

    # Replace all links with your channel link
    final_caption = re.sub(r'https?://\S+|www\.\S+', 'https://t.me/II_Way_to_Success_II', final_caption)

    # Perform additional replacements from user-defined rules
    replacements = load_replacement_words(sender)
    for word, replace_word in replacements.items():
        final_caption = final_caption.replace(word, replace_word)

    return final_caption.strip() if final_caption else None



async def download_user_stories(userbot, chat_id, msg_id, edit, sender):
    try:
        # Fetch the story using the provided chat ID and message ID
        story = await userbot.get_stories(chat_id, msg_id)
        if not story:
            await edit.edit("No story available for this user.")
            return  
        if not story.media:
            await edit.edit("The story doesn't contain any media.")
            return
        await edit.edit("Downloading Story...")
        file_path = await userbot.download_media(story)
        print(f"Story downloaded: {file_path}")
        # Send the downloaded story based on its type
        if story.media:
            await edit.edit("Uploading Story...")
            if story.media == MessageMediaType.VIDEO:
                await app.send_video(sender, file_path)
            elif story.media == MessageMediaType.DOCUMENT:
                await app.send_document(sender, file_path)
            elif story.media == MessageMediaType.PHOTO:
                await app.send_photo(sender, file_path)
        if file_path and os.path.exists(file_path):
            os.remove(file_path)  
        await edit.edit("Story processed successfully.")
    except RPCError as e:
        print(f"Failed to fetch story: {e}")
        await edit.edit(f"Error: {e}")
        
async def copy_message_with_chat_id(app, userbot, sender, chat_id, message_id, edit):
    target_chat_id = user_chat_ids.get(sender, sender)
    file = None
    result = None
    size_limit = 2 * 1024 * 1024 * 1024  # 2 GB size limit

    try:
        msg = await app.get_messages(chat_id, message_id)
        custom_caption = get_user_caption_preference(sender)
        final_caption = format_caption(msg.caption or '', sender, custom_caption)

        # Parse target_chat_id and topic_id
        topic_id = None
        if '/' in str(target_chat_id):
            target_chat_id, topic_id = map(int, target_chat_id.split('/', 1))

        # Handle different media types
        if msg.media:
            result = await send_media_message(app, target_chat_id, msg, final_caption, topic_id)
            return
        elif msg.text:
            result = await app.copy_message(target_chat_id, chat_id, message_id, reply_to_message_id=topic_id)
            return

        # Fallback if result is None
        if result is None:
            await edit.edit("Trying if it is a group...")
            chat_id = (await userbot.get_chat(f"@{chat_id}")).id
            msg = await userbot.get_messages(chat_id, message_id)

            if not msg or msg.service or msg.empty:
                return

            if msg.text:
                await app.send_message(target_chat_id, msg.text.markdown, reply_to_message_id=topic_id)
                return

            final_caption = format_caption(msg.caption.markdown if msg.caption else "", sender, custom_caption)
            file = await userbot.download_media(
                msg,
                progress=progress_bar,
                progress_args=("╭─────────────────────╮\n│      **__Downloading__...**\n├─────────────────────", edit, time.time())
            )
            file = await rename_file(file, sender)

            if msg.photo:
                result = await app.send_photo(target_chat_id, file, caption=final_caption, reply_to_message_id=topic_id)
            elif msg.video or msg.document:
                freecheck = await chk_user(chat_id, sender)
                if file_size > size_limit and (freecheck == 1 or pro is None):
                    await edit.delete()
                    await split_and_upload_file(app, sender, target_chat_id, file, caption, topic_id)
                    return       
                elif file_size > size_limit:
                    await handle_large_file(file, sender, edit, final_caption)
                    return
                await upload_media(sender, target_chat_id, file, final_caption, edit, topic_id)
            elif msg.audio:
                result = await app.send_audio(target_chat_id, file, caption=final_caption, reply_to_message_id=topic_id)
            elif msg.voice:
                result = await app.send_voice(target_chat_id, file, reply_to_message_id=topic_id)
            elif msg.sticker:
                result = await app.send_sticker(target_chat_id, msg.sticker.file_id, reply_to_message_id=topic_id)
            else:
                await edit.edit("Unsupported media type.")

    except Exception as e:
        print(f"Error : {e}")
        pass
        #error_message = f"Error occurred while processing message: {str(e)}"
        # await app.send_message(sender, error_message)
        # await app.send_message(sender, f"Make Bot admin in your Channel - {target_chat_id} and restart the process after /cancel")

    finally:
        if file and os.path.exists(file):
            os.remove(file)

async def send_media_message(app, target_chat_id, msg, caption, topic_id):
    try:
        file_name = None

        # Try to get file name if available
        if msg.document and msg.document.file_name:
            file_name = msg.document.file_name
        elif msg.video and msg.video.file_name:
            file_name = msg.video.file_name

        # If no caption, but file name exists, use it
        if not caption and file_name:
            caption = f"> 🗃️ **{file_name}**"
        elif caption and file_name:
            # Add blockquote formatting
            caption = re.sub(
                r'https?://t\.me/[^\s]+|https?://telegram\.me/[^\s]+',
                'https://t.me/+7R-7p7jVoz9mM2M1',
                caption
            )
            caption = "\n".join([f"> {line}" for line in caption.strip().splitlines()])
            caption = f">🗃️ **{file_name}**\n\n{caption}"
        elif caption:
            caption = "\n".join([f"> {line}" for line in caption.strip().splitlines()])
        else:
            caption = ">II_LevelUP_II"

        # Send the message with the right method
        if msg.video:
            return await app.send_video(
                target_chat_id,
                msg.video.file_id,
                caption=caption,
                reply_to_message_id=topic_id,
                
            )

        if msg.document:
            return await app.send_document(
                target_chat_id,
                msg.document.file_id,
                caption=caption,
                reply_to_message_id=topic_id,
                
            )

        if msg.photo:
            return await app.send_photo(
                target_chat_id,
                msg.photo.file_id,
                caption=caption,
                reply_to_message_id=topic_id,
                
            )

    except Exception as e:
        print(f"Error while sending media: {e}")
        return await app.send_message(target_chat_id, f"❌ Failed to send media.\n\nError: `{e}`")



#CUSTOM_EMOJIS = ["🍁", "🍀", "👑", "✨", "🦋", "🌟", "💖"]

def replace_fancy_and_emoji(text: str) -> str:
    """
    Remove fancy Unicode characters (like 𝐀–𝒁, 𓆩𓆪, etc.)
    Replace emojis (symbols) with our custom emoji set.
    """
    result = []
    for char in text:
        code = ord(char)

        # Skip fancy styled alphabets (Mathematical, etc.)
        if (0x1D400 <= code <= 0x1D7FF) or (0x13000 <= code <= 0x1342F):
            continue

        # Replace emojis or symbolic characters
        if unicodedata.category(char) == "So" or char in ['️', '‍', '\u200d']:
            result.append(random.choice(CUSTOM_EMOJIS))
        else:
            result.append(char)

    return ''.join(result)

def format_caption(original_caption, sender, custom_caption):
    delete_words = load_delete_words(sender)
    replacements = load_replacement_words(sender)

    if not original_caption:
        original_caption = ""

    # ✅ Clean fancy characters and replace emojis
    #original_caption = replace_fancy_and_emoji(original_caption)

    # ✅ Remove all hashtags like #Movie
    original_caption = re.sub(r'#\S+', '', original_caption)

    # ✅ Replace @mentions
    original_caption = re.sub(r'@\w+', '@Chosen_Onex', original_caption)

    # ✅ Replace telegram links
    original_caption = re.sub(
        r'https?://(t\.me|telegram\.me)/[^\s]+',
        'https://t.me/+7R-7p7jVoz9mM2M1',
        original_caption
    )

    # ✅ Replace "Extracted By" with custom credit    
    original_caption = re.sub(
        r'(📩)?\s*(Extracted[\s_]*By)\s*[:➤>–\-]*\s*.*',
        r'Xᴛʀᴀᴄᴛᴇᴅ ʙʏ:Sᴛꪮʟᴇɴ Hᴀᴘᴘɪɴᴇss',
        original_caption,
        flags=re.IGNORECASE
    )
    original_caption = re.sub(
        r'(📥)?\s*[ᴇe][xхх][ᴛt][ʀr][ᴀa][ᴄc][ᴛt][ᴇe][ᴅd]\s*[ʙb][ʏy]\s*[:➤>–\-]*\s*.*',
        r'Xᴛʀᴀᴄᴛᴇᴅ ʙʏ:Sᴛꪮʟᴇɴ Hᴀᴘᴘɪɴᴇss',
        original_caption,
        flags=re.IGNORECASE
    )

   
    original_caption = re.sub(
        r'(📩|📥)?\s*[\W_]*[eᴇ𝑬𝐄𝓔𝙀𝔈][x𝘅𝑿𝐱𝓧𝙭𝔵][t𝘁𝑻𝐭𝓣𝙩𝔗][rʀ𝑹𝐫𝓡𝙧𝔯][aᴀ𝑨𝐚𝓐𝙖𝔄][cᴄ𝑪𝐜𝓒𝙘𝔠][t𝘁𝑻𝐭𝓣𝙩𝔗][eᴇ𝑬𝐞𝓔𝙀𝔈][dᴅ𝑫𝐝𝓓𝙙𝔇]\s*'
        r'[bʙ𝐁𝑩𝓑𝙱𝔅][yʏ𝐘𝑌𝓨𝙔𝔜]\s*[:➤>–\-]*\s*.*',
        r'𖣐 𝗫𝘁𝗿𝗮𝗰𝘁𝗲𝗱 𝗕𝘆: 𝗖𝗛𝗢𝗦𝗘𝗡 𝗢𝗡𝗘 ⚝',
        original_caption,
        flags=re.IGNORECASE
    )


    # ✅ Replace "Downloaded By" with bot handle

    original_caption = re.sub(
        r'(?:📥)?\s*(Downloaded[\s_]*By)\s*[:➤>–\-]*\s*.*',
        r'Xᴛʀᴀᴄᴛᴇᴅ ʙʏ:Sᴛꪮʟᴇɴ Hᴀᴘᴘɪɴᴇss',
        original_caption,
        flags=re.IGNORECASE
    )

    
    original_caption = re.sub(
        r'(⏫)?\s*<u>?\s*(Uploaded[\s_]*By)\s*[➤:>–\-]*\s*[^<\n]+</u>?',
        r'Uploaded By ➤ Sᴛꪮʟᴇɴ Hᴀᴘᴘɪɴᴇss',
        original_caption,
        flags=re.IGNORECASE
        )
    original_caption = re.sub(
        r'^.*[ＥE][ＲR]{2}.*[⁹9]{2,}.*[⁺+]?.*$',
        r'Xᴛʀᴀᴄᴛᴇᴅ ʙʏ:Sᴛꪮʟᴇɴ Hᴀᴘᴘɪɴᴇss',
        original_caption,
        flags=re.IGNORECASE | re.MULTILINE
    )


    # 🔁 Delete unwanted words
    for word in delete_words:
        original_caption = original_caption.replace(word, ' ')

    # 🔁 Replace mapped words
    for old, new in replacements.items():
        original_caption = original_caption.replace(old, new)

    # ✅ Symbol replacements
    original_caption = original_caption.replace("[", "〔").replace("]", "〕")
    original_caption = original_caption.replace("(", "「").replace(")", "」")
    original_caption = original_caption.replace("📕", "📙")
    original_caption = original_caption.replace("📚", "⭐")
    original_caption = original_caption.replace("📌", "💠")

    # ✅ Append custom caption if exists
    if custom_caption:
        return f"{original_caption}\n\n__**{custom_caption}**__"
    return original_caption

# ------------------------ Button Mode Editz FOR SETTINGS ----------------------------

# Define a dictionary to store user chat IDs
user_chat_ids = {}

def load_user_data(user_id, key, default_value=None):
    try:
        user_data = collection.find_one({"_id": user_id})
        return user_data.get(key, default_value) if user_data else default_value
    except Exception as e:
     
        print(f"Error loading {key}: {e}")
        return default_value

def load_saved_channel_ids():
    saved_channel_ids = set()
    try:
        # Retrieve channel IDs from MongoDB collection
        for channel_doc in collection.find({"channel_id": {"$exists": True}}):
            saved_channel_ids.add(channel_doc["channel_id"])
    except Exception as e:
        print(f"Error loading saved channel IDs: {e}")
    return saved_channel_ids

def save_user_data(user_id, key, value):
    try:
        collection.update_one(
            {"_id": user_id},
            {"$set": {key: value}},
            upsert=True
        )
    except Exception as e:
        print(f"Error saving {key}: {e}")


# Delete and replacement word functions
load_delete_words = lambda user_id: set(load_user_data(user_id, "delete_words", []))
save_delete_words = lambda user_id, words: save_user_data(user_id, "delete_words", list(words))

load_replacement_words = lambda user_id: load_user_data(user_id, "replacement_words", {})
save_replacement_words = lambda user_id, replacements: save_user_data(user_id, "replacement_words", replacements)

# User session functions
def load_user_session(user_id):
    return load_user_data(user_id, "session")

# Upload preference functions
set_dupload = lambda user_id, value: save_user_data(user_id, "dupload", value)
get_dupload = lambda user_id: load_user_data(user_id, "dupload", False)

# User preferences storage
user_rename_preferences = {}
user_caption_preferences = {}

# Rename and caption preference functions
async def set_rename_command(user_id, custom_rename_tag):
    user_rename_preferences[str(user_id)] = custom_rename_tag

get_user_rename_preference = lambda user_id: user_rename_preferences.get(str(user_id), '@II_LevelUP_II')

async def set_caption_command(user_id, custom_caption):
    user_caption_preferences[str(user_id)] = custom_caption

get_user_caption_preference = lambda user_id: user_caption_preferences.get(str(user_id), '')

# Initialize the dictionary to store user sessions

sessions = {}
m = None
SET_PIC = "settings.jpg"
MESS = "Customize settings ..."

@gf.on(events.NewMessage(incoming=True, pattern='/settings'))
async def settings_command(event):
    user_id = event.sender_id
    await send_settings_message(event.chat_id, user_id)

async def send_settings_message(chat_id, user_id):
    buttons = [
        [Button.inline("💀 Forward to Chat", b'setchat'), Button.inline("✏️ Set Rename Tag", b'setrename')],
        [Button.inline("🔆 Set Caption", b'setcaption'), Button.inline("💠 Replace Words", b'setreplacement')],
        [Button.inline("‼️ Remove Words 🗑️", b'delete')],
        [Button.inline("🖼️ Set Thumbnail", b'setthumb'), Button.inline("🧲 Remove Thumbnail", b'remthumb')],
        [Button.inline("📤 Upload Method", b'uploadmethod'), Button.inline("⛔ Logout", b'logout')],
        [Button.inline("♻️ Reset All Settings ☢️", b'reset')],
        [Button.url("💞 Contact Owner 🦋", "https://t.me/Chosen_Onex_bot")]
    ]
    
    await gf.send_file(
        chat_id,
        file=SET_PIC,
        caption=MESS,
        buttons=buttons
    )


pending_photos = {}

@gf.on(events.CallbackQuery)
async def callback_query_handler(event):
    user_id = event.sender_id
    data = event.data.decode()  # Decode bytes to string

    if data == 'setchat':
        await event.respond(
            "🎯 **Set Your Channel or Group**\n\n"
            "🆔 **Send the Chat ID** where you want to forward all posts automatically. 🌝\n\n"
            "💡 *Tip:* Just **add me to that chat**, then send `/id` in the Channel/Group.\n"
            "**I'll automatically detect the Chat ID.**"
        )
        sessions[user_id] = 'setchat'
    
    elif data == 'setrename':
        await event.respond("✏️ Send the **rename tag** you want to set your custom name")
        sessions[user_id] = 'setrename'

    elif data == 'setcaption':
        await event.respond("📝 Send the **caption format** (you can include variables like {filename}, {size}):")
        sessions[user_id] = 'setcaption'

    elif data == 'setreplacement':
        await event.respond("🔄 Send replacement inside this ' '\n\n'oldword' 'newword'\n\n")
        sessions[user_id] = 'setreplacement'

    elif data == 'addsession':
        await event.respond("🔐 Send your **Pyrogram V2 session string**:\n\n*(We recommend not sharing this publicly)*")
        sessions[user_id] = 'addsession'

    elif data == 'delete':
        await event.respond("🗑️ Send **words to delete** (separated by space) from the filename/caption:")
        sessions[user_id] = 'deleteword'

    elif data == 'logout':
        await odb.remove_session(user_id)
        user_data = await odb.get_data(user_id)
        if user_data and user_data.get("session") is None:
            await event.respond("✅ You have been **logged out** and your session was removed successfully.")
        else:
            await event.respond("⚠️ You are not logged in.")

    elif data == 'setthumb':
        pending_photos[user_id] = True
        await event.respond("📸 Send the **photo** you want to use as your custom thumbnail.")

    elif event.data == b'uploadmethod':
        # Retrieve the user's current upload method (default to Pyrogram)
        user_data = collection.find_one({'user_id': user_id})
        current_method = user_data.get('upload_method', 'Pyrogram') if user_data else 'Pyrogram'
        pyrogram_check = " ✅" if current_method == "Pyrogram" else ""
        telethon_check = " ✅" if current_method == "Telethon" else ""

        # Display the buttons for selecting the upload method
        buttons = [
            [Button.inline(f"II_LevelUP_II v1 ⚡{pyrogram_check}", b'pyrogram')],
            [Button.inline(f"⚠️ Coming soon V2 {telethon_check}", b'telethon')]
        ]
        await event.edit("Choose your preferred upload method:\n\n__**Note:** **II_LevelUP_II v2 ⚡**, built on Telethon(base), by @II_LevelUP_II still in beta.__", buttons=buttons)

    elif event.data == b'pyrogram':
        save_user_upload_method(user_id, "Pyrogram")
        await event.edit("Upload method set to **Pyrogram** ✅")

    elif event.data == b'telethon':
        save_user_upload_method(user_id, "Telethon")
        await event.edit("Upload method set to **II_LevelUP_II V2 ⚡ \n\n Use V1 V2 is just Testing purpose**")        
        
    elif event.data == b'reset':
        try:
            user_id_str = str(user_id)
            
            collection.update_one(
                {"_id": user_id},
                {"$unset": {
                    "delete_words": "",
                    "replacement_words": "",
                    "watermark_text": "",
                    "duration_limit": ""
                }}
            )
            
            collection.update_one(
                {"user_id": user_id},
                {"$unset": {
                    "delete_words": "",
                    "replacement_words": "",
                    "watermark_text": "",
                    "duration_limit": ""
                }}
            )            
            user_chat_ids.pop(user_id, None)
            user_rename_preferences.pop(user_id_str, None)
            user_caption_preferences.pop(user_id_str, None)
            thumbnail_path = f"{user_id}.jpg"
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
            await event.respond("✅ Reset successfully, to logout click /logout")
        except Exception as e:
            await event.respond(f"Error clearing delete list: {e}")
    
    elif event.data == b'remthumb':
        try:
            os.remove(f'{user_id}.jpg')
            await event.respond('Thumbnail removed successfully!')
        except FileNotFoundError:
            await event.respond("No thumbnail found to remove.")
    

@gf.on(events.NewMessage(func=lambda e: e.sender_id in pending_photos))
async def save_thumbnail(event):
    user_id = event.sender_id  # Use event.sender_id as user_id

    if event.photo:
        temp_path = await event.download_media()
        if os.path.exists(f'{user_id}.jpg'):
            os.remove(f'{user_id}.jpg')
        os.rename(temp_path, f'./{user_id}.jpg')
        await event.respond('Thumbnail saved successfully!')

    else:
        await event.respond('Please send a photo... Retry')

    # Remove user from pending photos dictionary in both cases
    pending_photos.pop(user_id, None)

def save_user_upload_method(user_id, method):
    # Save or update the user's preferred upload method
    collection.update_one(
        {'user_id': user_id},  # Query
        {'$set': {'upload_method': method}},  # Update
        upsert=True  # Create a new document if one doesn't exist
    )

@gf.on(events.NewMessage)
async def handle_user_input(event):
    user_id = event.sender_id
    if user_id in sessions:
        session_type = sessions[user_id]

        if session_type == 'setchat':
            try:
                chat_id = event.text
                user_chat_ids[user_id] = chat_id
                await event.respond("Chat ID set successfully! ✅ Now i will Forward All Content in That Chat")
            except ValueError:
                await event.respond("Invalid chat ID! Send valid chat id starting with -100xxxxxxxx")
                
        elif session_type == 'setrename':
            custom_rename_tag = event.text
            await set_rename_command(user_id, custom_rename_tag)
            await event.respond(f"😉 Your Custom rename tag set to: {custom_rename_tag} 🌝")
        
        elif session_type == 'setcaption':
            custom_caption = event.text
            await set_caption_command(user_id, custom_caption)
            await event.respond(f"Custom caption set to: {custom_caption}")

        elif session_type == 'setreplacement':
            match = re.match(r"'(.+)' '(.+)'", event.text)
            if not match:
                await event.respond("Usage: 'Oldword(S)' 'ReplaceWord'\n\n **Example:** 'apple' 'banana'")
            else:
                word, replace_word = match.groups()
                delete_words = load_delete_words(user_id)
                if word in delete_words:
                    await event.respond(f"The word '{word}' is in the delete set and cannot be replaced.")
                else:
                    replacements = load_replacement_words(user_id)
                    replacements[word] = replace_word
                    save_replacement_words(user_id, replacements)
                    await event.respond(f"⇆ Replacement saved ⇆ \n\n 🌚 {word} ≫ {replace_word} 🌝")

        elif session_type == 'addsession':
            session_string = event.text
            await odb.set_session(user_id, session_string)
            await event.respond("✅ Session string added successfully!")
                
        elif session_type == 'deleteword':
            words_to_delete = event.message.text.split()
            delete_words = load_delete_words(user_id)
            delete_words.update(words_to_delete)
            save_delete_words(user_id, delete_words)
            await event.respond(f"🗑️ Words added to delete list: {', '.join(words_to_delete)}")
               
            
        del sessions[user_id]
    
# Command to store channel IDs
@gf.on(events.NewMessage(incoming=True, pattern='/lock'))
async def lock_command_handler(event):
    if event.sender_id not in OWNER_ID:
        return await event.respond("You are not authorized to use this command.😘 its only for my owner")
    
    # Extract the channel ID from the command
    try:
        channel_id = int(event.text.split(' ')[1])
    except (ValueError, IndexError):
        return await event.respond("Invalid /lock command. Use /lock CHANNEL_ID.")
    
    # Save the channel ID to the MongoDB database
    try:
        # Insert the channel ID into the collection
        collection.insert_one({"channel_id": channel_id})
        await event.respond(f"Channel ID {channel_id} locked successfully.")
    except Exception as e:
        await event.respond(f"Error occurred while locking channel ID: {str(e)}")


async def handle_large_file(file, sender, edit, caption):
    if pro is None:
        await edit.edit('**__ ❌ 4GB trigger not found__**')
        os.remove(file)
        gc.collect()
        return
    
    dm = None
    
    print("4GB connector found.")
    await edit.edit('**__ ✅ 4GB trigger connected...__**\n\n')
    
    target_chat_id = user_chat_ids.get(sender, sender)
    file_extension = str(file).split('.')[-1].lower()
    metadata = video_metadata(file)
    duration = metadata['duration']
    width = metadata['width']
    height = metadata['height']
    
    thumb_path = await screenshot(file, duration, sender)
    try:
        if file_extension in VIDEO_EXTENSIONS:
            dm = await pro.send_video(
                LOG_GROUP,
                video=file,
                caption=caption,
                thumb=thumb_path,
                height=height,
                width=width,
                duration=duration,
                progress=progress_bar,
                progress_args=(
                    "╭─────────────────────╮\n│       **__4GB Uploader__ ⚡**\n├─────────────────────",
                    edit,
                    time.time()
                )
            )
        else:
            # Send as document
            dm = await pro.send_document(
                LOG_GROUP,
                document=file,
                caption=caption,
                thumb=thumb_path,
                progress=progress_bar,
                progress_args=(
                    "╭─────────────────────╮\n│      **__4GB Uploader ⚡__**\n├─────────────────────",
                    edit,
                    time.time()
                )
            )

        from_chat = dm.chat.id
        msg_id = dm.id
        freecheck = 0
        if freecheck == 1:
            reply_markup = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("💎 Get Premium to Forward", url="https://t.me/GeniusJunctionX")]
                ]
            )
            await app.copy_message(
                target_chat_id,
                from_chat,
                msg_id,
                protect_content=True,
                reply_markup=reply_markup
            )
        else:
            # Simple copy without protect_content or reply_markup
            await app.copy_message(
                target_chat_id,
                from_chat,
                msg_id
            )
            
    except Exception as e:
        print(f"Error while sending file: {e}")

    finally:
        await edit.delete()
        os.remove(file)
        gc.collect()
        return


def strip_unicode_junk(text: str) -> str:
    """Remove stylized junk but preserve Indian language text and matras like ી િ ુ ે ા ૂ ૌ."""
    clean = []
    for char in text:
        codepoint = ord(char)
        name = unicodedata.name(char, "")

        # ✅ Preserve Gujarati & Indian scripts including matras
        if (
            0x0900 <= codepoint <= 0x097F or  # Devanagari
            0x0A80 <= codepoint <= 0x0AFF or  # Gujarati
            0x0980 <= codepoint <= 0x09FF or  # Bengali
            0x0B80 <= codepoint <= 0x0BFF or  # Tamil
            0x0C00 <= codepoint <= 0x0C7F or  # Telugu
            0x0C80 <= codepoint <= 0x0CFF or  # Kannada
            0x0D00 <= codepoint <= 0x0D7F     # Malayalam
        ):
            clean.append(char)
            continue

        # ✅ Preserve basic Latin and digits
        if (
            0x0020 <= codepoint <= 0x007E or
            0x00A0 <= codepoint <= 0x00FF
        ):
            if any(x in name for x in [
                'BOLD', 'ITALIC', 'SCRIPT', 'FRAKTUR', 'DOUBLE-STRUCK', 'CIRCLED', 'TAG'
            ]):
                continue
            clean.append(char)
            continue

        # ✅ Allow some safe symbols
        if char in (' ', '.', '-', '_', '(', ')', '[', ']'):
            clean.append(char)

    result = ''.join(clean)

    # 🧼 Normalize spacing (convert multiple dashes/underscores/spaces)
    result = re.sub(r'[ \-_]+', ' ', result)

    return result.strip()


# ✅ Clean rename function with junk filter
async def rename_file(file, sender, caption=None):
    delete_words = load_delete_words(sender)
    replacements = load_replacement_words(sender)
    custom_rename_tag = get_user_rename_preference(sender)

    # Split filename into name + extension
    base_name, ext = os.path.splitext(file)
    ext = ext if ext and len(ext) <= 6 else ".mp4"
    original_base = os.path.basename(base_name)

    # Use caption if filename is empty/generic
    if not original_base.strip() or original_base.lower() in ['untitled', 'noname', 'video', 'image']:
        if caption:
            # Take first 50 words of caption as filename
            words = caption.split()[:50]
            base_name = ' '.join(words)
        else:
            # Fallback to timestamp if no caption
            base_name = f"file_{int(time.time())}"
    else:
        base_name = original_base

    # Clean the base name
    base_name = os.path.basename(base_name)

    # Apply text transformations
    base_name = re.sub(r'@\w+', '⚝ @Chosen_Onex', base_name)  # Replace mentions
    for word in delete_words:
        base_name = base_name.replace(word, "")  # Remove banned words
    for word, replace_word in replacements.items():
        base_name = base_name.replace(word, replace_word)  # Apply word replacements

    # Clean Unicode while preserving spaces and basic punctuation
    base_name = strip_unicode_junk(base_name)

    # Final filename assembly
    new_file_name = f"{base_name.strip()} {custom_rename_tag}{ext}".strip()
    
    # Ensure filename isn't empty after processing
    if not os.path.splitext(new_file_name)[0]:
        new_file_name = f"document_{int(time.time())}{ext}"

    # Perform the rename
    await asyncio.to_thread(os.rename, file, new_file_name)
    return new_file_name


def progress_callback(done, total, user_id):
    # Check if this user already has progress tracking
    if user_id not in user_progress:
        user_progress[user_id] = {
            'previous_done': 0,
            'previous_time': time.time()
        }
    
    # Retrieve the user's tracking data
    user_data = user_progress[user_id]
    
    # Calculate the percentage of progress
    percent = (done / total) * 100
    
    # Format the progress bar
    completed_blocks = int(percent // 10)
    remaining_blocks = 10 - completed_blocks
    progress_bar = "♦" * completed_blocks + "◇" * remaining_blocks
    
    # Convert done and total to MB for easier reading
    done_mb = done / (1024 * 1024)  # Convert bytes to MB
    total_mb = total / (1024 * 1024)
    
    # Calculate the upload speed (in bytes per second)
    speed = done - user_data['previous_done']
    elapsed_time = time.time() - user_data['previous_time']
    
    if elapsed_time > 0:
        speed_bps = speed / elapsed_time  # Speed in bytes per second
        speed_mbps = (speed_bps * 8) / (1024 * 1024)  # Speed in Mbps
    else:
        speed_mbps = 0
    
    # Estimated time remaining (in seconds)
    if speed_bps > 0:
        remaining_time = (total - done) / speed_bps
    else:
        remaining_time = 0
    
    # Convert remaining time to minutes
    remaining_time_min = remaining_time / 60
    
    # Format the final output as needed
    final = (
        f"╭──────────────────╮\n"
        f"│     **__II_LevelUP_II ⚡ Uploader__**       \n"
        f"├──────────\n"
        f"│ {progress_bar}\n\n"
        f"│ **__Progress:__** {percent:.2f}%\n"
        f"│ **__Done:__** {done_mb:.2f} MB / {total_mb:.2f} MB\n"
        f"│ **__Speed:__** {speed_mbps:.2f} Mbps\n"
        f"│ **__ETA:__** {remaining_time_min:.2f} min\n"
        f"╰──────────────────╯\n\n"
        f"**__Pwrd by CHOSEN ONE ⚝__**"
    )
    
    # Update tracking variables for the user
    user_data['previous_done'] = done
    user_data['previous_time'] = time.time()
    
    return final


def dl_progress_callback(done, total, user_id):
    # Check if this user already has progress tracking
    if user_id not in user_progress:
        user_progress[user_id] = {
            'previous_done': 0,
            'previous_time': time.time()
        }
    
    # Retrieve the user's tracking data
    user_data = user_progress[user_id]
    
    # Calculate the percentage of progress
    percent = (done / total) * 100
    
    # Format the progress bar
    completed_blocks = int(percent // 10)
    remaining_blocks = 10 - completed_blocks
    progress_bar = "♦" * completed_blocks + "◇" * remaining_blocks
    
    # Convert done and total to MB for easier reading
    done_mb = done / (1024 * 1024)  # Convert bytes to MB
    total_mb = total / (1024 * 1024)
    
    # Calculate the upload speed (in bytes per second)
    speed = done - user_data['previous_done']
    elapsed_time = time.time() - user_data['previous_time']
    
    if elapsed_time > 0:
        speed_bps = speed / elapsed_time  # Speed in bytes per second
        speed_mbps = (speed_bps * 8) / (1024 * 1024)  # Speed in Mbps
    else:
        speed_mbps = 0
    
    # Estimated time remaining (in seconds)
    if speed_bps > 0:
        remaining_time = (total - done) / speed_bps
    else:
        remaining_time = 0
    
    # Convert remaining time to minutes
    remaining_time_min = remaining_time / 60
    
    # Format the final output as needed
    final = (
        f"╭──────────────────╮\n"
        f"│     **__II_LevelUP_II ⚡ Downloader__**       \n"
        f"├──────────\n"
        f"│ {progress_bar}\n\n"
        f"│ **__Progress:__** {percent:.2f}%\n"
        f"│ **__Done:__** {done_mb:.2f} MB / {total_mb:.2f} MB\n"
        f"│ **__Speed:__** {speed_mbps:.2f} Mbps\n"
        f"│ **__ETA:__** {remaining_time_min:.2f} min\n"
        f"╰──────────────────╯\n\n"
        f"**__Pwrd by CHOSEN ONE ⚝__**"
    )
    
    # Update tracking variables for the user
    user_data['previous_done'] = done
    user_data['previous_time'] = time.time()
    
    return final

# split function .... ?( to handle gareeb bot coder jo string n lga paaye)

async def split_and_upload_file(app, sender, target_chat_id, file_path, caption, topic_id):
    if not os.path.exists(file_path):
        await app.send_message(sender, "❌ File not found!")
        return

    file_size = os.path.getsize(file_path)
    start = await app.send_message(sender, f"ℹ️ File size: {file_size / (1024 * 1024):.2f} MB")
    PART_SIZE =  1.9 * 1024 * 1024 * 1024

    part_number = 0
    async with aiofiles.open(file_path, mode="rb") as f:
        while True:
            chunk = await f.read(PART_SIZE)
            if not chunk:
                break

            # Create part filename
            base_name, file_ext = os.path.splitext(file_path)
            part_file = f"{base_name}.part{str(part_number).zfill(3)}{file_ext}"

            # Write part to file
            async with aiofiles.open(part_file, mode="wb") as part_f:
                await part_f.write(chunk)

            # Uploading part
            edit = await app.send_message(target_chat_id, f"⬆️ Uploading part {part_number + 1}...")
            part_caption = f"{caption} \n\n**Part : {part_number + 1}**"
            await app.send_document(target_chat_id, document=part_file, caption=part_caption, reply_to_message_id=topic_id,
                progress=progress_bar,
                progress_args=("╭─────────────────────╮\n│      **__Pyro Uploader__**\n├─────────────────────", edit, time.time())
            )
            await edit.delete()
            os.remove(part_file)  # Cleanup after upload

            part_number += 1

    await start.delete()
    os.remove(file_path)
