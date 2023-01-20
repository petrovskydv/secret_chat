import logging
import time
import tkinter as tk
from datetime import datetime
from enum import Enum
from tkinter import messagebox

from sender import authorise, submit_message
from utils.tools import get_connection, read_message, UnknownToken

watchdog_logger = logging.getLogger('watchdog')


async def read_msgs(host, port, messages_queue, saving_queue, status_updates_queue, watchdog_queue):
    async with get_connection(host, port) as connection:
        status_updates_queue.put_nowait(ReadConnectionStateChanged.ESTABLISHED)
        reader, writer = connection

        while message := await reader.readline():
            text = f'[{datetime.now().strftime("%d.%m.%y %H:%M")}]: {message.strip().decode()}'
            messages_queue.put_nowait(text)
            saving_queue.put_nowait(text)
            await add_watchdog_record(watchdog_queue, 'New message in chat')


async def send_msgs(host, port, token, queue, status_updates_queue, watchdog_queue):
    async with get_connection(host, port) as connection:
        status_updates_queue.put_nowait(SendingConnectionStateChanged.ESTABLISHED)
        reader, writer = connection
        await read_message(reader)

        try:
            await add_watchdog_record(watchdog_queue, 'Prompt before auth')
            nickname = await authorise(reader, writer, token)
            await add_watchdog_record(watchdog_queue, 'Authorization done')
            status_updates_queue.put_nowait(NicknameReceived(nickname))
        except UnknownToken:
            messagebox.showinfo("Неверный токен", 'Проверьте токен. сервер его не узнал.')
            raise tk.TclError

        while True:
            message = await queue.get()
            await submit_message(writer, message)
            await add_watchdog_record(watchdog_queue, 'Message sent')


async def add_watchdog_record(watchdog_queue, text):
    watchdog_text = f'[{int(time.time())}] Connection is alive. {text}'
    watchdog_queue.put_nowait(watchdog_text)


async def watch_for_connection(watchdog_queue):
    while True:
        message = await watchdog_queue.get()
        watchdog_logger.debug(message)


class ReadConnectionStateChanged(Enum):
    INITIATED = 'устанавливаем соединение'
    ESTABLISHED = 'соединение установлено'
    CLOSED = 'соединение закрыто'

    def __str__(self):
        return str(self.value)


class SendingConnectionStateChanged(Enum):
    INITIATED = 'устанавливаем соединение'
    ESTABLISHED = 'соединение установлено'
    CLOSED = 'соединение закрыто'

    def __str__(self):
        return str(self.value)


class NicknameReceived:
    def __init__(self, nickname):
        self.nickname = nickname
