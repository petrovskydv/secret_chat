# Подключаемся к чату

Скрипт может подключиться к чату и сохрантяь историю переписки. Так же можно зарегистрироваться в чате и писать сообщения.

## Установка

- Скачайте код
- Установите зависимости командой 

```
pip install -r requirements.txt
```

## Запуск

### Сохранение истории переписки
```shell
python listener.py
```
По умолчанию все сообщения сохраняются в файл `history.txt` в корне проекта.

Для получения справки по аргументам запуска
```shell
python listener.py -h
```

### Написать сообщение в чат

Чтобы написать первое сообщение, надо запустить скрипт с ключем --username и именем пользователя. Скрипт зарегистрирует пользователя с переданным именем и отправит сообщение.

Пример запуска:
```shell
python sender.py --username estuser "текст сообщения"
```

После регистрации ключ --username можно не указывать.
```shell
python sender.py "текст сообщения"
```
Для получения справки по аргументам запуска
```shell
python sender.py -h
```
## Цели проекта

Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте [Devman](https://dvmn.org).