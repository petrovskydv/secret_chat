import asyncio
import logging
import time
import tkinter as tk
from datetime import datetime
from enum import Enum
from tkinter import messagebox

from anyio import create_task_group, TASK_STATUS_IGNORED, get_cancelled_exc_class
from async_timeout import timeout

from sender import authorise, submit_message
from utils.tools import get_connection, read_message, UnknownToken, reconnect

watchdog_logger = logging.getLogger('watchdog')
TIMEOUT_IN_SECONDS = 2


async def read_msgs(host, port, messages_queue, saving_queue, status_updates_queue, watchdog_queue,
                    task_status=TASK_STATUS_IGNORED):
    try:
        task_status.started()
        status_updates_queue.put_nowait(ReadConnectionStateChanged.INITIATED)
        async with get_connection(host, port) as connection:
            status_updates_queue.put_nowait(ReadConnectionStateChanged.ESTABLISHED)
            reader, writer = connection

            while True:
                try:
                    async with timeout(TIMEOUT_IN_SECONDS) as cm:
                        message = await reader.readline()
                        text = f'[{datetime.now().strftime("%d.%m.%y %H:%M")}]: {message.strip().decode()}'
                        messages_queue.put_nowait(text)
                        saving_queue.put_nowait(text)
                        await add_watchdog_alive(watchdog_queue, 'New message in chat')
                except asyncio.TimeoutError:
                    if cm.expired:
                        await add_watchdog_elapsed(watchdog_queue, TIMEOUT_IN_SECONDS)
    except get_cancelled_exc_class():
        status_updates_queue.put_nowait(ReadConnectionStateChanged.CLOSED)
        raise


async def send_msgs(host, port, token, queue, status_updates_queue, watchdog_queue, task_status=TASK_STATUS_IGNORED):
    try:
        task_status.started()
        status_updates_queue.put_nowait(SendingConnectionStateChanged.INITIATED)
        async with get_connection(host, port) as connection:
            status_updates_queue.put_nowait(SendingConnectionStateChanged.ESTABLISHED)
            reader, writer = connection
            await read_message(reader)

            try:
                await add_watchdog_alive(watchdog_queue, 'Prompt before auth')
                nickname = await authorise(reader, writer, token)
                await add_watchdog_alive(watchdog_queue, 'Authorization done')
                status_updates_queue.put_nowait(NicknameReceived(nickname))
            except UnknownToken:
                messagebox.showinfo("Неверный токен", 'Проверьте токен. сервер его не узнал.')
                raise tk.TclError

            while True:
                message = await queue.get()
                await submit_message(writer, message)
                await add_watchdog_alive(watchdog_queue, 'Message sent')

    except get_cancelled_exc_class():
        status_updates_queue.put_nowait(SendingConnectionStateChanged.CLOSED)
        status_updates_queue.put_nowait(NicknameReceived('неизвестно'))
        raise


async def add_watchdog_alive(watchdog_queue, text):
    watchdog_text = f'[{int(time.time())}] Connection is alive. {text}'
    watchdog_queue.put_nowait(watchdog_text)


async def add_watchdog_elapsed(watchdog_queue, seconds):
    watchdog_text = f'[{int(time.time())}] {seconds}s timeout is elapsed'
    watchdog_queue.put_nowait(watchdog_text)


async def watch_for_connection(watchdog_queue, task_status=TASK_STATUS_IGNORED):
    task_status.started()
    while True:
        message = await watchdog_queue.get()
        watchdog_logger.debug(message)
        if 'timeout is elapsed' in message:
            raise ConnectionError


@reconnect(exceptions=(ConnectionError,), logger=watchdog_logger)
async def handle_connection(host, port, sender_port, token, messages_queue, sending_queue, saving_queue,
                            status_updates_queue):
    watchdog_queue = asyncio.Queue()
    async with create_task_group() as tg:
        await tg.start(send_msgs, host, sender_port, token, sending_queue, status_updates_queue, watchdog_queue)
        await tg.start(read_msgs, host, port, messages_queue, saving_queue, status_updates_queue, watchdog_queue)
        await tg.start(watch_for_connection, watchdog_queue)


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
