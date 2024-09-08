
import requests
import xml.etree.ElementTree as ET
import asyncio
from datetime import datetime
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, CallbackContext
import os

# Вставь сюда свой токен бота
TELEGRAM_TOKEN = '7184238540:AAHCW50sy8BouE3erbX2yNj3d-nKYBPydmE'
# Вставь сюда ID чата, куда бот будет отправлять сообщения
CHAT_ID = '1047092792'
# URL для проверки
URL = 'https://ubilling.net.ua/aerialalerts/?xml=true'
# Путь к видеофайлам
ALERT_VIDEO_PATH = '1.mp4'
ALL_CLEAR_VIDEO_PATH = '2.mp4'

def parse_alertnow(xml_data):
    try:
        root = ET.fromstring(xml_data)
        state23_elements = root.findall('.//state23')
        for state in state23_elements:
            alertnow = state.find('alertnow').text
            if alertnow is not None:
                return alertnow == 'true'
    except ET.ParseError:
        return False
    return False

def get_current_time():
    return datetime.now().strftime('%H:%M:%S')

def file_exists(file_path):
    return os.path.isfile(file_path)

async def fetch_data_with_retries(url, retries=3, timeout=10):
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Ошибка запроса (попытка {attempt + 1}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2)  # Ожидание перед повторной попыткой
            else:
                raise

async def check_alert(context: CallbackContext):
    try:
        xml_data = await fetch_data_with_retries(URL)
        alert_now = parse_alertnow(xml_data)
        
        if 'last_alert' not in context.chat_data:
            context.chat_data['last_alert'] = False
        
        current_alert = context.chat_data['last_alert']

        if alert_now and not current_alert:
            current_time = get_current_time()
            await context.bot.send_message(chat_id=CHAT_ID, text=f"🔴 {current_time} Повітряна тривога в Чернігівській області!")
            if file_exists(ALERT_VIDEO_PATH):
                with open(ALERT_VIDEO_PATH, 'rb') as f:
                    await context.bot.send_video(chat_id=CHAT_ID, video=InputFile(f, filename='1.mp4'))
            else:
                await context.bot.send_message(chat_id=CHAT_ID, text="Не удалось найти файл тревоги.")
            context.chat_data['last_alert'] = True
        elif not alert_now and current_alert:
            current_time = get_current_time()
            await context.bot.send_message(chat_id=CHAT_ID, text=f"🟢 {current_time} Відбій тривоги в Чернігівській області!")
            if file_exists(ALL_CLEAR_VIDEO_PATH):
                with open(ALL_CLEAR_VIDEO_PATH, 'rb') as f:
                    await context.bot.send_video(chat_id=CHAT_ID, video=InputFile(f, filename='2.mp4'))
            else:
                await context.bot.send_message(chat_id=CHAT_ID, text="Не удалось найти файл отбой.")
            context.chat_data['last_alert'] = False

        # Отладочные сообщения
        print(f"Current alert: {alert_now}, Last alert: {current_alert}")
    except Exception as e:
        print(f"Ошибка при проверке тревоги: {e}")

async def send_current_status(update: Update, context: CallbackContext):
    try:
        xml_data = await fetch_data_with_retries(URL)
        alert_now = parse_alertnow(xml_data)
        current_time = get_current_time()
        if alert_now:
            await update.message.reply_text(f"🔴 {current_time} Повітряна тривога в Чернігівській області!")
            if file_exists(ALERT_VIDEO_PATH):
                with open(ALERT_VIDEO_PATH, 'rb') as f:
                    await update.message.reply_video(video=InputFile(f, filename='1.mp4'))
            else:
                await update.message.reply_text("Не удалось найти файл тревоги.")
        else:
            await update.message.reply_text(f"🟢 {current_time} Відбій тривоги в Чернігівській області!")
            if file_exists(ALL_CLEAR_VIDEO_PATH):
                with open(ALL_CLEAR_VIDEO_PATH, 'rb') as f:
                    await update.message.reply_video(video=InputFile(f, filename='2.mp4'))
            else:
                await update.message.reply_text("Не удалось найти файл отбой.")
    except Exception as e:
        print(f"Ошибка при отправке статуса: {e}")
        await update.message.reply_text("Не удалось проверить текущий статус тревоги.")

async def start(update: Update, context: CallbackContext):
    await send_current_status(update, context)
    # Запускаем проверку тревоги через asyncio
    context.application.create_task(periodic_check(context))

async def periodic_check(context: CallbackContext):
    while True:
        await check_alert(context)
        await asyncio.sleep(10)  # Проверяем каждые 10 секунд

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler('start', start))

    application.run_polling()

if __name__ == '__main__':
    main()
