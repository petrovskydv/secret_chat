import asyncio
import logging
import time
from asyncio import Event
from datetime import datetime
from enum import Enum

from anyio import create_task_group, TASK_STATUS_IGNORED, get_cancelled_exc_class, ExceptionGroup
from async_timeout import timeout

from messenger.connection import get_connection, reconnect
from messenger.messages import read_message, submit_message
from messenger.auth_tools import UnknownToken, authorise

watchdog_logger = logging.getLogger('watchdog')
TIMEOUT_IN_SECONDS = 5


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
                        text = f'[{datetime.now().strftime("%d.%m.%y %H:%M:%S")}]: {message.strip().decode()}'
                        messages_queue.put_nowait(text)
                        saving_queue.put_nowait(text)
                        await add_watchdog_alive(watchdog_queue, 'New message in chat')
                except asyncio.TimeoutError:
                    if cm.expired:
                        await add_watchdog_elapsed(watchdog_queue, TIMEOUT_IN_SECONDS, source='read')
    except get_cancelled_exc_class():
        status_updates_queue.put_nowait(ReadConnectionStateChanged.CLOSED)
        raise


async def send_msgs(host, port, token, sending_queue, status_updates_queue, watchdog_queue, token_error_event: Event,
                    task_status=TASK_STATUS_IGNORED):
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
                token_error_event.set()

            async with create_task_group() as tg:
                await tg.start(send_msg_from_queue, writer, sending_queue, watchdog_queue)
                await tg.start(send_watchdog_msg, writer, watchdog_queue)

    except get_cancelled_exc_class():
        status_updates_queue.put_nowait(SendingConnectionStateChanged.CLOSED)
        status_updates_queue.put_nowait(NicknameReceived('неизвестно'))
        raise


async def send_msg_from_queue(writer, sending_queue, watchdog_queue, task_status=TASK_STATUS_IGNORED):
    task_status.started()
    while message := await sending_queue.get():
        try:
            async with timeout(TIMEOUT_IN_SECONDS) as cm:
                await submit_message(writer, message)
                await add_watchdog_alive(watchdog_queue, 'Message sent')
        except asyncio.TimeoutError:
            if cm.expired:
                await add_watchdog_elapsed(watchdog_queue, TIMEOUT_IN_SECONDS, source='send')


async def send_watchdog_msg(writer, watchdog_queue, task_status=TASK_STATUS_IGNORED):
    task_status.started()
    while True:
        try:
            async with timeout(TIMEOUT_IN_SECONDS) as cm:
                await submit_message(writer, '')
                await add_watchdog_alive(watchdog_queue, 'Watchdog message sent')
        except asyncio.TimeoutError:
            if cm.expired:
                await add_watchdog_elapsed(watchdog_queue, TIMEOUT_IN_SECONDS, source='WD')
        await asyncio.sleep(1)


async def add_watchdog_alive(watchdog_queue, text):
    watchdog_text = f'[{int(time.time())}] Connection is alive. {text}'
    watchdog_queue.put_nowait(watchdog_text)


async def add_watchdog_elapsed(watchdog_queue, seconds, source):
    watchdog_text = f'[{int(time.time())}] {seconds}s timeout is elapsed from {source}'
    watchdog_queue.put_nowait(watchdog_text)


async def watch_for_connection(watchdog_queue, task_status=TASK_STATUS_IGNORED):
    task_status.started()
    while True:
        message = await watchdog_queue.get()
        watchdog_logger.debug(message)
        if 'timeout is elapsed' in message:
            raise ConnectionError


@reconnect(exceptions=(ConnectionError, ExceptionGroup, OSError), logger=watchdog_logger)
async def handle_connection(host, port, sender_port, token, messages_queue, sending_queue, saving_queue,
                            status_updates_queue, token_error_event, task_status=TASK_STATUS_IGNORED):
    watchdog_queue = asyncio.Queue()
    try:
        async with create_task_group() as tg:
            await tg.start(send_msgs, host, sender_port, token, sending_queue, status_updates_queue, watchdog_queue,
                           token_error_event)
            await tg.start(read_msgs, host, port, messages_queue, saving_queue, status_updates_queue, watchdog_queue)
            await tg.start(watch_for_connection, watchdog_queue)
    except ExceptionGroup as e:
        raise ConnectionError
