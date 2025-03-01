from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputFile, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime
import logging
import os
import json
from dotenv import load_dotenv
import asyncio
import uuid
from flask import Flask, request, jsonify
from aiogram import Router

# Загрузка переменных окружения
load_dotenv()

# Инициализация бота и диспетчера
API_TOKEN = '5037002755:AAH0SdUBgoGG27O3Gm6BS31cOKE286e3Oqo'
ADMIN_ID = '2122584931'

# URL вашего веб-приложения
WEBAPP_URL = "https://gademoffshit.github.io/telegram-shop-bot/"

# ID администратора
ADMIN_ID = 2122584931

# Словари для хранения данных
orders_data = {}
pending_orders = {}
admin_referral_stats = {}
admin_ref_usernames = {}

# Состояния
class PaymentStates(StatesGroup):
    waiting_for_receipt = State()

# Создаем бота, диспетчер и роутер
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# Регистрируем роутер в диспетчере
dp.include_router(router)

# Создаем папку для квитанций если её нет
if not os.path.exists('receipts'):
    os.makedirs('receipts')

def get_main_keyboard():
    """Создаем основную клавиатуру"""
    buttons = [
        [{"text": "🛍 Перейти в магазин", "web_app": {"url": WEBAPP_URL}}],
        [{"text": "❓ Помощь", "callback_data": "help"}],
        [{"text": "ℹ️ О нас", "callback_data": "about_us"}]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_payment_keyboard():
    """Создаем клавиатуру для выбора способа оплаты"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплата картой", callback_data="pay_card")],
        [InlineKeyboardButton(text="🔙 Вернуться назад", callback_data="back_to_main")]
    ])
    return keyboard

def get_admin_keyboard():
    """Создание клавиатуры админ-панели"""
    buttons = [
        [
            {"text": "Все заказы", "callback_data": "all_orders"},
            {"text": "Ожидают оплаты", "callback_data": "waiting_orders"}
        ],
        [
            {"text": "Оплаченные", "callback_data": "paid_orders"},
            {"text": "Отправленные", "callback_data": "shipped_orders"}
        ]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_order_keyboard(order_id: str):
    """Создание клавиатуры для конкретного заказа"""
    buttons = [
        [
            {"text": "✅ Принять", "callback_data": f"accept_{order_id}"},
            {"text": "❌ Отклонить", "callback_data": f"reject_{order_id}"}
        ],
        [{"text": "🔙 Назад", "callback_data": "back_to_orders"}]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def generate_order_id():
    """Функция для генерации уникального номера заказа"""
    return str(uuid.uuid4())

def create_order(user_id, order_data):
    """Функция для создания заказа"""
    # Проверяем, что order_data имеет нужную структуру
    required_fields = ['name', 'phone', 'email', 'telegram', 'address', 'items', 'total']
    if not all(field in order_data for field in required_fields):
        raise ValueError("order_data is missing required fields")

    order_id = str(uuid.uuid4())[:8]  # Используем только первые 8 символов для краткости
    order = {
        'order_id': order_id,
        'user_id': user_id,
        'order_data': order_data,
        'status': 'Ожидает оплаты',
        'details': order_data  # Сохраняем полные детали заказа
    }
    orders_data[order_id] = order
    return order_id

def send_order_confirmation_to_user(user_id, order_id):
    """Функция для отправки сообщения пользователю"""
    message = f"✅ Благодарим за заказ!\n\nМы получили подтверждение оплаты и скоро отправим ваш заказ.\nОжидайте сообщения с номером отслеживания.\nВаш номер заказа: {order_id}"
    bot.send_message(chat_id=user_id, text=message)

# Основные обработчики
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в наш магазин!\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if str(message.from_user.id) == str(ADMIN_ID):
        await message.answer(
            "🔐 Панель администратора",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer("⛔️ У вас нет доступа к панели администратора")

@router.callback_query(lambda c: c.data == "help")
async def process_help(callback: types.CallbackQuery):
    help_text = (
        "🛍 <b>Как сделать заказ:</b>\n\n"
        "1. Нажмите кнопку 'Перейти в магазин'\n"
        "2. Выберите товары\n"
        "3. Добавьте их в корзину\n"
        "4. Оформите заказ\n"
        "5. Выберите способ оплаты\n"
        "6. Загрузите квитанцию\n\n"
        "❓ Есть вопросы? Пишите: @odnorazki_wrot"
    )
    await callback.message.edit_text(
        help_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "about_us")
async def process_about(callback: types.CallbackQuery):
    about_text = (
        "🏪 <b>О нашем магазине</b>\n\n"
        "Мы предлагаем широкий ассортимент товаров высокого качества.\n\n"
        "✅ Быстрая доставка\n"
        "✅ Надежная упаковка\n"
        "✅ Гарантия качества\n"
        "✅ Поддержка 24/7\n\n"
        "📞 Контакты: @odnorazki_wro"
    )
    await callback.message.edit_text(
        about_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "confirm_order")
async def process_confirm_order(callback: types.CallbackQuery):
    """Обработчик подтверждения заказа"""
    try:
        # Получаем текст сообщения с заказом
        message_text = callback.message.text
        
        # Отправляем сообщение админу
        admin_message = f"🆕 Новый подтвержденный заказ!\n\n{message_text}"
        
        try:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                parse_mode="HTML"
            )
            print(f"Сообщение успешно отправлено админу")
        except Exception as e:
            print(f"Ошибка отправки сообщения админу: {e}")
            
        # Генерируем уникальный номер заказа
        order_id = str(uuid.uuid4())[:8]
            
        # Отправляем подтверждение пользователю и предлагаем выбрать способ оплаты
        await callback.message.edit_text(
            f"{message_text}\n\n"
            f"✅ Заказ #{order_id} подтвержден!\n\n"
            "Выберите способ оплаты:",
            reply_markup=get_payment_keyboard(),
            parse_mode="HTML"
        )
        
        # Отправляем уведомление о успешном подтверждении
        await callback.answer("✅ Заказ подтвержден! Выберите способ оплаты")
        
    except Exception as e:
        print(f"Ошибка в process_confirm_order: {e}")
        await callback.answer("Произошла ошибка при подтверждении заказа. Попробуйте еще раз.")

@router.callback_query(lambda c: c.data.startswith("pay_"))
async def process_payment(callback: types.CallbackQuery):
    """Обработчик выбора способа оплаты"""
    payment_method = callback.data.split("_")[1]
    
    if payment_method == "card":
        payment_info = (
            "💳 Оплата картой:\n\n"
            "Номер карты: (Сбер) 2202206784083664\n"
            "Получатель: Александр Т\n\n"
            "После оплаты нажмите кнопку 'Я оплатил' и прикрепите скриншот чека."
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data="payment_done")],
        [InlineKeyboardButton(text="🔙 Назад к выбору оплаты", callback_data="back_to_payment")]
    ])
    
    await callback.message.edit_text(
        payment_info,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "payment_done")
async def process_payment_confirmation(callback: types.CallbackQuery):
    """Обработчик подтверждения оплаты"""
    # Запрашиваем квитанцию
    await callback.message.edit_text(
        "❗️ Для подтверждения оплаты необходимо прикрепить квитанцию.\n\n"
        "📎 Пожалуйста, отправьте фото или файл квитанции об оплате.\n"
        "✅ Поддерживаемые форматы: jpg, png, pdf",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [{"text": "📤 Отправить квитанцию", "callback_data": "send_receipt"}],
            [{"text": "◀️ Назад к способам оплаты", "callback_data": "back_to_payment"}]
        ])
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "back_to_payment")
async def back_to_payment(callback: types.CallbackQuery):
    """Обработчик кнопки возврата к выбору способа оплаты"""
    await callback.message.edit_text(
        "Выберите способ оплаты:",
        reply_markup=get_payment_keyboard()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "operator_chat")
async def operator_chat(callback: types.CallbackQuery):
    """Обработчик кнопки чата с оператором"""
    await callback.message.answer(
        "Наш оператор скоро свяжется с вами.\n"
        "Пожалуйста, опишите ваш вопрос."
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "help")
async def help_handler(callback: types.CallbackQuery):
    """Обработчик кнопки помощи"""
    help_text = (
        "🛍 Как сделать заказ:\n"
        "1. Нажмите 'Перейти в магазин'\n"
        "2. Выберите товары\n"
        "3. Добавьте их в корзину\n"
        "4. Оформите заказ\n\n"
        "❓ Есть вопросы? Используйте 'Чат с оператором'"
    )
    await callback.message.answer(help_text)
    await callback.answer()

@router.callback_query(lambda c: c.data == "about_us")
async def send_about_us(callback: types.CallbackQuery):
    about_text = (
        "Новостной канал @shopneverepeat\n\n"
        "Мы – проверенный магазин электронных сигарет, ридинов для подов и аксессуаров. "
        "Уже 3,5 года на рынке, за этот период мы обработали более 3000 заказов и получили "
        "более 1500 реальных отзывов от довольных клиентов.\n\n"
        "Чему обирают нас?\n\n"
        "✅ Быстрая доставка – отправляем заказы в другие города с доставкой за 1-2 дня.\n"
        "Есть сомнения? Напишите менеджеру и получите видеофиксацию вашего заказа!\n"
        "✅ Оперативная поддержка – отвечаем в течение 10-15 минут.\n"
        "✅ Гибкая система скидок – постоянные клиенты получают выгодные предложения.\n"
        "✅ Оптовая торговля – работаем с крупными заказами.\n\n"
        "Наша цель – предоставить качественный сервис и лучший выбор продукции для вейпинга. "
        "Присоединяйтесь к Vape Room и убедитесь сами!"
    )
    
    buttons = [[{"text": "🛍 Сделать заказ", "web_app": {"url": WEBAPP_URL}}]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.answer(about_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(lambda c: c.data == "main_menu")
async def process_main_menu(callback: types.CallbackQuery):
    """Обработчик возврата в главное меню"""
    try:
        await callback.message.delete()
    except Exception as e:
        print(f"Error deleting message: {e}")

    await callback.message.answer(
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data in ["all_orders", "waiting_orders", "paid_orders", "shipped_orders"])
async def process_order_filter(callback: types.CallbackQuery):
    """Обработчик фильтрации заказов"""
    try:
        await callback.message.delete()
    except Exception as e:
        print(f"Error deleting message: {e}")

    status_map = {
        "all_orders": None,  # None означает все заказы
        "waiting_orders": "Ожидает оплаты",
        "paid_orders": "Оплачен",
        "shipped_orders": "Отправлен"
    }
    
    selected_status = status_map.get(callback.data)
    title = "Все заказы" if callback.data == "all_orders" else f"Заказы: {selected_status}"
    orders_list = f"📋 {title}:\n\n"
    
    buttons = []
    
    # Фильтруем заказы
    filtered_orders = {
        order_id: order for order_id, order in orders_data.items()
        if (selected_status is None or order['status'] == selected_status)
        and order['status'] != 'Отклонен'  # Не показываем отклоненные заказы
    }
    
    for order_id, order in filtered_orders.items():
        button_text = f"Заказ #{order_id} - {order['status']}"
        buttons.append([{"text": button_text, "callback_data": f"view_order_{order_id}"}])
    
    buttons.append([
        {"text": "🔄 Обновить", "callback_data": callback.data},
        {"text": "🔙 Назад", "callback_data": "main_menu"}
    ])
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    
    if not filtered_orders:
        orders_list += "Нет активных заказов"
    
    await callback.message.answer(orders_list, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith('view_order_'))
async def process_view_order(callback: types.CallbackQuery):
    """Обработчик просмотра деталей заказа"""
    try:
        await callback.message.delete()
    except Exception as e:
        print(f"Error deleting message: {e}")

    order_id = callback.data.replace('view_order_', '')
    order = orders_data.get(order_id)
    
    if order:
        # Форматируем детали заказа
        details = order['details']
        formatted_details = (
            f"📦 Заказ #{order_id}\n\n"
            f"Статус: {order['status']}\n"
            f"Пользователь: {order['user_id']}\n\n"
            f"Имя: {details['name']}\n"
            f"Телефон: {details['phone']}\n"
            f"Email: {details['email']}\n"
            f"Telegram: @{details['telegram']}\n"
            f"Адреса доставки: {details['address']}\n\n"
            f"Товары: {', '.join(item['name'] for item in details['items'])}\n"
            f"Сумма: {details['total']} zł\n"
        )
        
        await callback.message.answer(
            formatted_details,
            reply_markup=get_order_keyboard(order_id)
        )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith(('accept_', 'reject_')))
async def process_order_action(callback: types.CallbackQuery):
    """Обработчик принятия/отклонения заказа"""
    try:
        await callback.message.delete()
    except Exception as e:
        print(f"Error deleting message: {e}")

    action, order_id = callback.data.split('_')
    order = orders_data.get(order_id)
    
    if order:
        if action == 'accept':
            order['status'] = 'Принят'
            await bot.send_message(
                chat_id=order['user_id'],
                text=f"✅ Ваш заказ #{order_id} принят и будет обработан!"
            )
        else:
            order['status'] = 'Отклонен'
            await bot.send_message(
                chat_id=order['user_id'],
                text=f"❌ Ваш заказ #{order_id} был отклонен."
            )
        
        buttons = [[
            {"text": "🔙 К списку заказов", "callback_data": "all_orders"},
            {"text": "🏠 В главное меню", "callback_data": "main_menu"}
        ]]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.answer(
            f"Заказ #{order_id} {order['status'].lower()}",
            reply_markup=keyboard
        )
    await callback.answer()

@router.callback_query(lambda c: c.data == 'send_receipt')
async def request_receipt(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(PaymentStates.waiting_for_receipt)
    await callback_query.message.edit_text(
        "📄 Пожалуйста, отправьте фото или файл квитанции об оплате.\n"
        "❗️ Поддерживаемые форматы: jpg, png, pdf\n\n"
        "Для отмены нажмите /cancel"
    )

@router.message(lambda message: message.content_type in ['document', 'photo'], PaymentStates.waiting_for_receipt)
async def handle_receipt(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    try:
        # Создаем папку для пользователя если её нет
        user_folder = f'receipts/{user_id}'
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)
        
        # Генерируем имя файла
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if message.document:
            # Проверяем расширение файла
            file_ext = os.path.splitext(message.document.file_name)[1].lower()
            if file_ext not in ['.jpg', '.jpeg', '.png', '.pdf']:
                await message.reply(
                    "❌ Неподдерживаемый формат файла.\n"
                    "Пожалуйста, отправьте файл в формате jpg, png или pdf."
                )
                return
            
            # Сохраняем документ
            file_id = message.document.file_id
            file = await bot.get_file(file_id)
            file_path = f"{user_folder}/{timestamp}{file_ext}"
            await bot.download_file(file.file_path, file_path)
            
        elif message.photo:
            # Берем фото максимального размера
            photo = message.photo[-1]
            file_id = photo.file_id
            file = await bot.get_file(file_id)
            file_path = f"{user_folder}/{timestamp}.jpg"
            await bot.download_file(file.file_path, file_path)
        
        # Отправляем уведомление администратору
        admin_message = (
            f"📥 Получена новая квитанция об оплате\n\n"
            f"👤 От пользователя: {message.from_user.username or message.from_user.id}\n"
            f"🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )
        
        # Создаем клавиатуру для админа
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_payment_{user_id}"),
            types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_payment_{user_id}")
        ]])
        
        # Пересылаем файл админу
        if message.document:
            await bot.send_document(ADMIN_ID, message.document.file_id, caption=admin_message, reply_markup=keyboard)
        else:
            await bot.send_photo(ADMIN_ID, photo.file_id, caption=admin_message, reply_markup=keyboard)
        
        # Отправляем подтверждение пользователю
        await message.reply(
            "✅ Квитанция успешно отправлена!\n"
            "Ожидайте подтверждения от администратора.\n\n"
            "После проверки вы получите уведомление о статусе оплаты."
        )
        
        await state.clear()
        
    except Exception as e:
        logging.error(f"Error handling receipt: {e}")
        await message.reply(
            "❌ Произошла ошибка при обработке файла.\n"
            "Пожалуйста, попробуйте еще раз или обратитесь к администратору."
        )
        await state.clear()

@router.callback_query(lambda c: c.data.startswith('approve_payment_'))
async def approve_payment(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split('_')[2])
    
    photo = FSInputFile("images/buyer.jpg")
    await bot.send_photo(
        user_id,
        photo=photo,
        caption=(
            "✅ Ваш платеж подтвержден!\n"
            "Теперь вам нужно написать в личные сообщения @neverepeatmanager свой основной ник в роблоксе(смотри гайд-картинку)"
        )
    )
    
    await callback_query.message.edit_caption(
        callback_query.message.caption + "\n\n✅ Платеж подтвержден",
        reply_markup=None
    )

@router.callback_query(lambda c: c.data.startswith('reject_payment_'))
async def reject_payment(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split('_')[2])
    
    await bot.send_message(
        user_id,
        "❌ Ваш платеж отклонен.\n"
        "Пожалуйста, проверьте правильность оплаты и отправьте квитанцию повторно."
    )
    
    await callback_query.message.edit_caption(
        callback_query.message.caption + "\n\n❌ Платеж отклонен",
        reply_markup=None
    )

@router.message(lambda message: True)
async def handle_order(message: types.Message):
    try:
        data = json.loads(message.text)
        customer_info = data['customerInfo']
        items = data['items']
        total = data['total']

        # Формируем сообщение для админа
        admin_message = "🛍 Новый заказ!\n\n"
        admin_message += f"👤 Покупатель:\n"
        admin_message += f"Имя: {customer_info['name']}\n\n"
        
        admin_message += "🛒 Товары:\n"
        for item in items:
            admin_message += f"- {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽\n"
        
        admin_message += f"\n💰 Итого: {total}₽"

        # Отправляем сообщение админу
        await bot.send_message(ADMIN_ID, admin_message)

        # Формируем сообщение для клиента
        client_message = "✅ Ваш заказ принят!\n\n"
        client_message += "📦 Состав заказа:\n"
        for item in items:
            client_message += f"- {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽\n"
        
        client_message += f"\n💰 Сумма заказа: {total}₽\n\n"
        client_message += "Мы свяжемся с вами в ближайшее время!"

        # Отправляем сообщение клиенту
        await bot.reply_to(message, client_message)

    except Exception as e:
        print(f"Error processing order: {e}")
        await bot.reply_to(message, "Произошла ошибка при обработке заказа. Пожалуйста, попробуйте позже.")

app = Flask(__name__)

@app.route('/create-order', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        items = data.get('items', [])
        total = data.get('total', 0)
        
        # Здесь можно добавить логику сохранения заказа в базу данных
        # и отправку уведомления администратору
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

async def main():
    # Удаляем вебхук перед запуском бота
    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
