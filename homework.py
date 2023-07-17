import logging
import os
import time

from dotenv import load_dotenv
import requests
import telegram

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

PRACTICUM_TOKEN = os.getenv('TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN_BOT')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    message = '''Отсутствует обязательная переменная окружения: {variable}.
                Программа принудительно остановлена.'''

    if (PRACTICUM_TOKEN is None):
        logging.critical(message.format(variable='PRACTICUM_TOKEN'))
        raise SystemExit
    elif (TELEGRAM_TOKEN is None):
        logging.critical(message.format(variable='TELEGRAM_TOKEN'))
        raise SystemExit
    elif (TELEGRAM_CHAT_ID is None):
        logging.critical(message.format(variable='TELEGRAM_CHAT_ID'))
        raise SystemExit


def send_message(bot, message):
    """Отправка сообщениея в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
    except Exception:
        logging.error('Ошибка при отправке сообщения')
    else:
        logging.debug(f'Бот отправил сообщение "{message}"')


def get_api_answer(timestamp):
    """Отправляет запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=payload
        )
    except requests.exceptions.RequestException:
        logging.error('Сбой при запросе к эндпоинту')
        raise Exception
    if homework_statuses.status_code != 200:
        logging.error('API домашки возвращает код, отличный от 200')
        raise Exception
    else:
        return homework_statuses.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if (type(response) != dict):
        raise TypeError('Получен список вместо ожидаемого словаря')

    homeworks = response.get('homeworks')
    if (type(homeworks) != list):
        raise TypeError('Данные приходят не в виде списка')


def parse_status(homework):
    """Извлекает статус домашней работы."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        logging.error('В ответе API домашки нет ключа `homework_name`')

    status = homework['status']
    try:
        verdict = HOMEWORK_VERDICTS[status]
    except KeyError:
        logging.error('Неожиданный статус домашней работы в ответе API')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    status = ''
    status_error = ''

    while True:
        try:
            response = get_api_answer(timestamp - 5000000)
            check_response(response)
            homeworks = response.get('homeworks')
            message = parse_status(homeworks[0])
            if message != status:
                send_message(bot, message)
                status = message
            else:
                logging.debug('Нет новых обновлений')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if message != status_error:
                send_message(bot, message)
                status_error = message

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
