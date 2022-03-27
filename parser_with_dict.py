import logging
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import Text
from aiogram.utils.exceptions import BadRequest
import os

TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

HEROKU_APP_NAME = os.getenv('HEROKU_APP_NAME')

# webhook settings
WEBHOOK_HOST = f'https://{HEROKU_APP_NAME}.herokuapp.com'
WEBHOOK_PATH = f'/webhook/{TOKEN}'
WEBHOOK_URL = f'{WEBHOOK_HOST}{WEBHOOK_PATH}'

# webserver settings
WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = os.getenv('PORT', default=8000)


async def on_startup(dispatcher):
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)


async def on_shutdown(dispatcher):
    await bot.delete_webhook()

search_element = {'floor': ['search%5Bfilter_float_floor%3Afrom%5D=', 'search%5Bfilter_float_floor%3Ato%5D='],
                  'price': ['search%5Bfilter_float_price%3Afrom%5D=', 'search%5Bfilter_float_price%3Ato%5D='],
                  'number of rooms': ['search%5Bfilter_enum_number_of_rooms_string%5D%5B0%5D=odnokomnatnye',
                                      'search%5Bfilter_enum_number_of_rooms_string%5D%5B1%5D=dvuhkomnatnye',
                                      'search%5Bfilter_enum_number_of_rooms_string%5D%5B2%5D=trehkomnatnye']}

url = ['https://www.olx.ua/uk/nedvizhimost/kvartiry/dolgosrochnaya-arenda-kvartir/']


def search_house(url_name, price_from=0, price_to=0, num_room=0):
    if price_from and price_to:
        url_name += '?' + search_element['price'][0] + str(price_from) + '&' + search_element['price'][1] + \
                    str(price_to)
    elif price_from:
        url_name += '?' + search_element['price'][0] + str(price_from)
    elif price_to:
        url_name += '?' + search_element['price'][1] + str(price_to)
    if num_room:
        url_name += '&' + search_element['number of rooms'][num_room-1]
        # i = 0
        # while num_room != i:
        #     url_name += '&' + search_element['number of rooms'][i]
        #     i += 1
    return str(url_name)


db = dict()


def run_parser(url1, city, room, price_from, price_to):
    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:99.0) Gecko/20100101 Firefox/99.0"
    }
    r = requests.get(url1, headers=headers).text
    soup = BeautifulSoup(r, 'lxml')
    quotes = soup.find_all('td', class_='offer')
    counter = 1
    for quote in quotes:
        detail = quote.find('td', class_='title-cell').find('a')['href']
        response = requests.get(detail, headers=headers)
        soup = BeautifulSoup(response.text, 'lxml')
        photos = soup.find_all('div', class_='swiper-zoom-container')
        photo_list = []
        for photo in photos[:5]:
            try:
                photo_list.append(photo.find('img')['src'])
            except:
                photo_list.append(photo.find('img')['data-src'])

        db[f'offer_{counter}'] = {
            'title': quote.find('td', class_='title-cell').find('h3', 'lheight22 margintop5').text.strip(),
            'detail': quote.find('td', class_='title-cell').find('a')['href'],
            'photo': photo_list,
            'price': quote.find('td', class_='wwnormal tright td-price').find('strong').text
        }
        counter += 1

    return db


@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = types.KeyboardButton('Довгострокова оренда квартир')
    keyboard.add(button)
    await message.answer('Почнемо?', reply_markup=keyboard)


@dp.message_handler(Text(equals='Довгострокова оренда квартир'))
async def cmd_start(message: types.Message):
    buttons = [
        types.InlineKeyboardButton(text="Черкаси", callback_data="city_cherkassy"),
        types.InlineKeyboardButton(text="Львів", callback_data="city_lvov"),
        types.InlineKeyboardButton(text="Івано-Франківськ", callback_data="city_ivano-frankovsk"),
        types.InlineKeyboardButton(text="Вінниця", callback_data="city_vinnitsa"),
        types.InlineKeyboardButton(text="Київ", callback_data="city_kiev")
    ]
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(*buttons)
    await message.answer('Виберіть місто', reply_markup=keyboard)
    await message.answer('.', reply_markup=types.ReplyKeyboardRemove())


@dp.callback_query_handler(Text(startswith='city'))
async def send_url(call: types.CallbackQuery):
    res = call.data.split('_')[1]
    url[0] = url[0] + res + '/'
    buttons = [
        types.InlineKeyboardButton(text="Не важливо", callback_data="from_nothing"),
        types.InlineKeyboardButton(text="1000", callback_data="from_1000"),
        types.InlineKeyboardButton(text="5000", callback_data="from_5000"),
        types.InlineKeyboardButton(text="10000", callback_data="from_10000")
    ]
    keyboard = types.InlineKeyboardMarkup(row_width=4)
    keyboard.add(*buttons)
    await call.message.answer('Мінімальна ціна', reply_markup=keyboard)


data_for_search = dict()


@dp.callback_query_handler(Text(startswith='from'))
async def send_url(call: types.CallbackQuery):
    res = call.data.split('_')[1]
    buttons = [
        types.InlineKeyboardButton(text="Не важливо", callback_data="to_nothing"),
        types.InlineKeyboardButton(text="1000", callback_data="to_1000"),
        types.InlineKeyboardButton(text="5000", callback_data="to_5000"),
        types.InlineKeyboardButton(text="10000", callback_data="to_10000")
    ]
    if res == 'nothing':
        data_for_search[f'{call.from_user.id}'] = {
            'price_from': 0
        }
    else:
        data_for_search[f'{call.from_user.id}'] = {
            'price_from': int(res)
        }

    keyboard = types.InlineKeyboardMarkup(row_width=4)
    keyboard.add(*buttons)
    await call.message.answer('Максимальна ціна', reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith='to'))
async def send_url(call: types.CallbackQuery):
    res = call.data.split('_')[1]
    if res == 'nothing':
        data_for_search[f'{call.from_user.id}'].update({
            'price_to': 0
        })
    else:
        data_for_search[f'{call.from_user.id}'].update({
            'price_to': int(res)
        })
    buttons = [
        types.InlineKeyboardButton(text="Не важливо", callback_data="room_nothing"),
        types.InlineKeyboardButton(text="1", callback_data="room_1"),
        types.InlineKeyboardButton(text="2", callback_data="room_2"),
        types.InlineKeyboardButton(text="3", callback_data="room_3")
    ]
    keyboard = types.InlineKeyboardMarkup(row_width=4)
    keyboard.add(*buttons)
    await call.message.answer('Кількість кімнат', reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith='room'))
async def send_url(call: types.CallbackQuery):
    res = call.data.split('_')[1]
    if res == 'nothing':
        data_for_search[f'{call.from_user.id}'].update({
            'room': 0
        })
    else:
        data_for_search[f'{call.from_user.id}'].update({
            'room': int(res)
        })
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = types.KeyboardButton('Пошук')
    keyboard.add(button)
    await call.answer('Дані успішно записано')
    await call.message.answer('Натисніть для пошуку', reply_markup=keyboard)


count = list()


@dp.message_handler(Text(equals='Пошук'))
async def search(message: types.Message):
    await message.answer(f'Йде збір інформації. Це займе декілька секунд. {message.from_user.first_name}, '
                         f'дякую за очікування)', reply_markup=types.ReplyKeyboardRemove())
    room = data_for_search[f'{message.from_user.id}']['room']
    price_from = data_for_search[f'{message.from_user.id}']['price_from']
    price_to = data_for_search[f'{message.from_user.id}']['price_to']
    city = url[0].split('/')[-2]

    res = search_house(url[0], price_from, price_to, room)
    run_parser(res, city, room, price_from, price_to)
    count.append(0)

    count[0] += 5

    for order_key, order_value in list(db.items())[:count[0]]:
        db_photo = []
        try:
            if order_value['photo']:
                for photo in order_value['photo']:
                    db_photo.append(types.InputMediaPhoto(photo))
                await bot.send_media_group(message.chat.id, media=db_photo)
            title = order_value['title']
            detail = order_value['detail']
            price = order_value['price']
            await message.answer(f'Назва:{title}\nДетально:{detail}\nЦіна:{price}')
        except BadRequest:
            title = order_value['title']
            detail = order_value['detail']
            price = order_value['price']
            await message.answer(f'Назва:{title}\nДетально:{detail}\nЦіна:{price}')
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text="Наступні 5 оголошень", callback_data="next"))
    await message.answer(f'Оголошень: {count[0]} / {len(db)}', reply_markup=keyboard)


@dp.callback_query_handler(Text(equals='next'))
async def send_url(call: types.CallbackQuery):

    for order_key, order_value in list(db.items())[count[0]:count[0] + 5]:
        db_photo = []
        try:
            if order_value['photo']:
                for photo in order_value['photo']:
                    db_photo.append(types.InputMediaPhoto(photo))
                await bot.send_media_group(call.message.chat.id, media=db_photo)
            title = order_value['title']
            detail = order_value['detail']
            price = order_value['price']
            await call.message.answer(f'Назва:{title}\nДетально:{detail}\nЦіна:{price}')
        except BadRequest:
            title = order_value['title']
            detail = order_value['detail']
            price = order_value['price']
            await call.message.answer(f'Назва:{title}\nДетально:{detail}\nЦіна:{price}')
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text="Наступні 5 оголошень", callback_data="next"))

    if count[0] < len(db) < count[0] + 5:
        count[0] += len(db) - count[0]
    else:
        count[0] += 5

    if count[0] <= len(db):
        await call.message.answer(f'Оголошення: {count[0]} / {len(db)}', reply_markup=keyboard)
    else:
        await call.answer('Оголошення закінчилися', show_alert=True)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.InlineKeyboardButton(text="/start"))
        url[0] = 'https://www.olx.ua/uk/nedvizhimost/kvartiry/dolgosrochnaya-arenda-kvartir/'
        data_for_search.clear()
        count.clear()
        db.clear()
        await call.message.answer('Оголошення закінчилися. Знайти квартири з новими параметрами?',
                                  reply_markup=keyboard)


if __name__ == '__main__':
    # executor.start_polling(dp, skip_updates=True)
    logging.basicConfig(level=logging.INFO)
    executor.start_webhook(dispatcher=dp,
                           webhook_path=WEBHOOK_PATH,
                           skip_updates=True,
                           on_startup=on_startup,
                           on_shutdown=on_shutdown,
                           host=WEBAPP_HOST,
                           port=WEBAPP_PORT,
                           )