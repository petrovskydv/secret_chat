import asyncio
import logging
import tkinter as tk
from asyncio import Event

import configargparse
from anyio import create_task_group, TASK_STATUS_IGNORED

from messenger.tools import register


class TkAppClosed(Exception):
    pass


def process_login(event: Event):
    event.set()


async def register_user(host, port, input_field, event: Event, task_status=TASK_STATUS_IGNORED):
    while True:
        await event.wait()
        username = input_field.get()
        await register(host, port, username)
        event.clear()


async def update_tk(root_frame, interval=1 / 120, task_status=TASK_STATUS_IGNORED):
    task_status.started()
    while True:
        try:
            root_frame.update()
        except tk.TclError:
            # if application has been destroyed/closed
            raise TkAppClosed()
        await asyncio.sleep(interval)


async def draw(host, port):
    root = tk.Tk()

    root.title('Регистрация в чате Майнкрафтера')

    root_frame = tk.Frame()
    root_frame.pack(fill='both', expand=True)

    input_frame = tk.Frame(root_frame)
    input_frame.pack(side='bottom', fill=tk.X)

    title = tk.Label(input_frame, text='Введите логин')
    title.pack(side='left')

    input_field = tk.Entry(input_frame)
    input_field.pack(side='left', fill=tk.X, expand=True)

    is_button_pressed = asyncio.Event()

    send_button = tk.Button(input_frame)
    send_button['text'] = 'Зарегистрировать'
    send_button['command'] = lambda: process_login(is_button_pressed)
    send_button.pack(side='left')

    async with create_task_group() as tg:
        await tg.start(update_tk, root_frame)
        await tg.start(register_user, host, port, input_field, is_button_pressed)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

    parser = configargparse.ArgParser(
        default_config_files=['settings/settings.ini'],
        ignore_unknown_config_file_keys=True,
        description='Listener for dvmn chat',
    )
    parser.add_argument('-c', '--config', is_config_file=True, help='config file path')
    parser.add_argument('--host', required=True, help='chat server url')
    parser.add_argument('--sender_port', required=True, help='chat server port')
    args = parser.parse_args()
    asyncio.run(draw(args.host, args.sender_port))
