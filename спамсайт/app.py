from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from pyrogram import Client, errors
import asyncio
import nest_asyncio
import os
import uuid
import time
from datetime import datetime, timedelta
import threading
from functools import wraps
import queue
import json
import hashlib
import sqlite3
import random
import string
import re
from werkzeug.security import generate_password_hash, check_password_hash

# Применяем nest_asyncio
nest_asyncio.apply()

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_TYPE'] = 'filesystem'

# API данные
API_ID = 30032542
API_HASH = "ce646da1307fb452305d49f9bb8751ca"

# Папки для данных
DATA_DIR = "data"
USERS_DIR = os.path.join(DATA_DIR, "users")
SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")
TEMP_DIR = os.path.join(DATA_DIR, "temp")
CODES_DIR = "codes"  # Папка с файлами кодов

for dir_path in [DATA_DIR, USERS_DIR, SESSIONS_DIR, TEMP_DIR, CODES_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

# Соответствие типов кодов и количества дней
CODE_TYPES = {
    'day': {'days': 1, 'description': 'Подписка на 1 день', 'price': 39},
    'week': {'days': 7, 'description': 'Подписка на неделю', 'price': 179},
    'month': {'days': 30, 'description': 'Подписка на месяц', 'price': 499},
    'year': {'days': 365, 'description': 'Подписка на год', 'price': 1999},
    'forever': {'days': 9999, 'description': 'Пожизненная подписка', 'price': 2499}
}

# Стартовые коды (будут добавлены при первом запуске)
INITIAL_CODES = {
    'day': [
        '9F99-1104-3319-7105',
        'day-6d30-4a5b-b13d-88c7',
        'day-9b95-d782-576e-40b6',
        'day-3480-1c58-7b69-52c7',
        'day-3480-1c58-7b69-234f',
        'day-0fe6-5912-3213-0814',
        'day-2570-5f93-257c-6718',
        'day-3727-455e-1e52-9576',
        'day-64a1-c006-f999-6242',
        'day-9286-ae49-485b-40f9',
        'day-8de8-c55a-5a46-49d4',
        'day-6ee8-d163-4281-38a0'
    ],
    'week': [
        'A7F3-K9Q2-X4LM-8P1D',
        'B6ZT-4KDP-M2Q8-R7XA',
        'C9L2-W5QX-7FDE-3K8T',
        'D4RM-N8Q1-Z6KP-5XLT',
        'E7XA-3MQL-K9P2-W6RD',
        'week-F2KD-8QRM-4XZT-L7PA',
        'week-G5QX-R2LM-9D7K-A4ZT',
        'week-H8KP-6QTX-M3RD-2LFA',
        'week-J3LM-7XQA-5KDP-R9ZT',
        'week-K9RD-4QXM-L2PA-8FZT',
        'week-L6XA-Q8ZT-3KRM-5DP2',
        'week-M2QT-9LFA-R7KD-X4PZ',
        'week-N7KP-3RDX-Q6LM-8AZT',
        'week-P4ZT-8QRM-2KLA-7XDF',
        'week-Q8LM-5RZT-K3PA-9DX2',
        'week-R1XA-7KDP-4QZT-6LFM',
        'week-S6QK-2ZTA-R8LM-4DPX',
        'week-T9PA-3LMX-7QKD-5RZT',
        'week-U5ZT-6KLM-Q2RD-8XPA',
        'week-V8RD-4QPA-9ZTK-2LMX'
    ],
    'month': [
        'A8F3-K2Q9-X4LM-7P1D',
        'B6ZT-5KDP-M3Q8-R9XA',
        'C4L2-W7QX-8FDE-3K6T',
        'D9RM-N2Q1-Z5KP-7XLT',
        'E3XA-6MQL-K8P2-W4RD',
        'F7KD-9QRM-4XZT-L2PA',
        'G5QX-R8LM-1D7K-A4ZT',
        'H2KP-6QTX-M9RD-3LFA',
        'J3LM-7XQA-5KDP-R8ZT',
        'K8RD-4QXM-L2PA-6FZT',
        'L6XA-Q9ZT-3KRM-5DP2',
        'M2QT-7LFA-R4KD-X8PZ',
        'month-N7KP-3RDX-Q6LM-9AZT',
        'month-P4ZT-8QRM-2KLA-5XDF',
        'month-Q8LM-5RZT-K3PA-9DX2',
        'month-R1XA-7KDP-4QZT-6LFM',
        'month-S6QK-2ZTA-R8LM-3DPX',
        'month-T9PA-3LMX-7QKD-5RZT',
        'month-U5ZT-6KLM-Q2RD-8XPA',
        'month-V8RD-4QPA-9ZTK-2LMX'
    ],
    'year': [
        'A7KD-4QXM-9LZT-2PRA',
        'B3LM-8QZT-5KDP-R6XA',
        'C9RD-2XPA-Q7LM-4ZTK',
        'D5ZT-7KLM-3QPA-8RDX',
        'E8QX-4LMP-6KZT-1RDA',
        'F2PA-9LMX-7QKD-5RZT',
        'year-G6ZT-3KLM-Q8RD-4PXA',
        'year-H1RD-7QZT-2LMX-9KPA',
        'year-J4LM-6QPA-8ZTK-3RDX',
        'year-K9ZT-5LMX-1QKD-7RPA',
        'year-L3QX-8RDA-6KZT-4LMP',
        'year-M7RD-2QZT-9LPA-5KXM',
        'year-N6ZT-4KPA-8LMX-3QRD',
        'year-P2LM-9QZT-7KDX-5RPA',
        'year-Q5ZT-3LMX-8KPA-1QRD',
        'year-R8LM-4QZT-6KPA-2DXR',
        'year-S7QX-1LMP-9KZT-4RDA',
        'year-T3ZT-8LMX-5KPA-6QRD',
        'year-U6LM-2QZT-7KPA-9RDX',
        'year-V4ZT-5LMX-3KPA-8QRD'
    ],
    'forever': [
        'A9XZ-4KLM-7QPA-2RDT',
        'B6QT-3LMX-8KPA-5RZD',
        'C2LM-9QZT-4KPA-7RDX',
        'D7PA-5LMX-3QZT-8KRD',
        'E4QX-6LMP-2KZT-9RDA',
        'F8ZT-1LMX-7KPA-4QRD',
        'forever-G3LM-8QZT-6KPA-2RDX',
        'forever-H9PA-4LMX-5KZT-7QRD',
        'forever-J6ZT-3LMX-9KPA-1QRD',
        'forever-K2LM-7QZT-8KPA-4RDX',
        'forever-L5PA-9LMX-3KZT-6QRD',
        'forever-M8ZT-4LMX-1KPA-7QRD',
        'forever-N7LM-2QZT-6KPA-9RDX',
        'forever-P3ZT-5LMX-8KPA-4QRD',
        'forever-Q6LM-1QZT-9KPA-7RDX',
        'forever-R4PA-8LMX-2KZT-5QRD',
        'forever-S9ZT-6LMX-4KPA-3QRD',
        'forever-T2LM-7QZT-5KPA-8RDX',
        'forever-U5ZT-3LMX-9KPA-6QRD',
        'forever-V8LM-4QZT-1KPA-7RDX'
    ]
}

# База данных пользователей и подписок
def init_db():
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
    c = conn.cursor()
    
    # Проверяем существующие колонки в таблице users
    c.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in c.fetchall()]
    
    # Если таблицы нет, создаем с новыми колонками
    if not columns:
        c.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                subscription_type TEXT DEFAULT 'none',
                subscription_end TIMESTAMP,
                can_send_messages BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        # Добавляем недостающие колонки
        if 'subscription_type' not in columns:
            c.execute('ALTER TABLE users ADD COLUMN subscription_type TEXT DEFAULT "none"')
        if 'subscription_end' not in columns:
            c.execute('ALTER TABLE users ADD COLUMN subscription_end TIMESTAMP')
        if 'can_send_messages' not in columns:
            c.execute('ALTER TABLE users ADD COLUMN can_send_messages BOOLEAN DEFAULT 0')
    
    # Таблица для кодов подписок
    c.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            duration_days INTEGER NOT NULL,
            description TEXT,
            price INTEGER DEFAULT 0,
            is_used BOOLEAN DEFAULT 0,
            used_by INTEGER,
            used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (used_by) REFERENCES users (id)
        )
    ''')
    
    # Таблица для Telegram сессий
    c.execute('''
        CREATE TABLE IF NOT EXISTS telegram_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            phone TEXT NOT NULL,
            session_string TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, phone)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Хранилища данных
temp_storage = {}  # {phone: {'client': client, 'user_id': user_id, ...}}
flood_wait_storage = {}  # {phone: wait_until}
spam_tasks = {}  # {task_id: {'user_id': user_id, 'queue': queue, ...}}
spam_queues = {}  # {user_id: queue}

# Глобальный цикл событий
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

def async_handler(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        return loop.run_until_complete(f(*args, **kwargs))
    return wrapped

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Требуется авторизация', 'redirect': '/login'})
        return f(*args, **kwargs)
    return decorated_function

def can_send_messages_required(f):
    """Декоратор для проверки права на отправку сообщений"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Требуется авторизация'})
        
        conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
        c = conn.cursor()
        c.execute('SELECT can_send_messages, subscription_type, subscription_end FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'})
        
        can_send, sub_type, sub_end = user
        
        # Проверяем, не истекла ли подписка
        if sub_end and sub_type != 'forever':
            try:
                end_date = datetime.fromisoformat(sub_end) if isinstance(sub_end, str) else datetime.fromtimestamp(float(sub_end))
                if datetime.now() > end_date:
                    # Обновляем права
                    conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
                    c = conn.cursor()
                    c.execute('UPDATE users SET can_send_messages = 0 WHERE id = ?', (user_id,))
                    conn.commit()
                    conn.close()
                    return jsonify({'success': False, 'error': 'Срок подписки истек'})
            except:
                pass
        
        if not can_send:
            return jsonify({'success': False, 'error': 'Требуется подписка для отправки сообщений'})
        
        return f(*args, **kwargs)
    return decorated_function

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С КОДАМИ ==========

def add_initial_codes():
    """Добавляет стартовые коды в базу данных"""
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
    c = conn.cursor()
    
    added = 0
    skipped = 0
    
    print("\n" + "="*60)
    print("ДОБАВЛЕНИЕ СТАРТОВЫХ КОДОВ")
    print("="*60)
    
    for code_type, codes in INITIAL_CODES.items():
        days = CODE_TYPES[code_type]['days']
        description = CODE_TYPES[code_type]['description']
        price = CODE_TYPES[code_type]['price']
        
        print(f"\n📁 Тип: {code_type} ({description})")
        
        for code in codes:
            try:
                # Проверяем, есть ли уже такой код в базе
                c.execute('SELECT id FROM subscriptions WHERE code = ?', (code,))
                if c.fetchone():
                    print(f"   ⏭️ Код {code} уже существует")
                    skipped += 1
                    continue
                
                # Добавляем код
                c.execute('''
                    INSERT INTO subscriptions (code, duration_days, description, price, is_used)
                    VALUES (?, ?, ?, ?, 0)
                ''', (code, days, description, price))
                added += 1
                print(f"   ✅ Добавлен код: {code}")
                
            except Exception as e:
                print(f"   ❌ Ошибка при добавлении кода {code}: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n" + "="*60)
    print(f"📊 ИТОГ:")
    print(f"   ✅ Добавлено новых кодов: {added}")
    print(f"   ⏭️ Пропущено (уже есть): {skipped}")
    print("="*60)
    
    return added

def validate_code_format(code, code_type):
    """Проверяет формат кода"""
    pattern = rf"^{code_type}-[A-Z0-9]{{4}}-[A-Z0-9]{{4}}-[A-Z0-9]{{4}}-[A-Z0-9]{{4}}$"
    return re.match(pattern, code, re.IGNORECASE) is not None

def load_codes_from_file(file_path, code_type):
    """Загружает коды из файла"""
    codes = []
    if not os.path.exists(file_path):
        return codes
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            # Пропускаем пустые строки и комментарии
            if not line or line.startswith('#'):
                continue
            
            # Проверяем формат
            if validate_code_format(line, code_type):
                codes.append(line.upper())
            else:
                print(f"⚠️ Строка {line_num} в {file_path} имеет неверный формат: {line}")
    
    return codes

def load_all_codes_from_files():
    """Загружает все коды из всех файлов в базу данных"""
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
    c = conn.cursor()
    
    total_added = 0
    total_found = 0
    
    print("\n" + "="*60)
    print("ЗАГРУЗКА КОДОВ ИЗ ФАЙЛОВ")
    print("="*60)
    
    for code_type, info in CODE_TYPES.items():
        file_path = os.path.join(CODES_DIR, f"{code_type}.txt")
        print(f"\n📁 Проверка файла: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"   📄 Файл не найден, создаем пустой файл")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# Коды для {info['description']}\n")
                f.write(f"# Формат: {code_type}-XXXX-XXXX-XXXX-XXXX\n\n")
            continue
        
        # Показываем размер файла
        file_size = os.path.getsize(file_path)
        print(f"   📊 Размер файла: {file_size} байт")
        
        codes = load_codes_from_file(file_path, code_type)
        print(f"   📊 Найдено кодов в файле: {len(codes)}")
        total_found += len(codes)
        
        for code in codes:
            try:
                # Проверяем, есть ли уже такой код в базе
                c.execute('SELECT id FROM subscriptions WHERE code = ?', (code,))
                if c.fetchone():
                    print(f"   ⏭️ Код {code} уже существует в базе")
                    continue
                
                # Добавляем код
                c.execute('''
                    INSERT INTO subscriptions (code, duration_days, description, price, is_used)
                    VALUES (?, ?, ?, ?, 0)
                ''', (code, info['days'], info['description'], info['price']))
                total_added += 1
                print(f"   ✅ Добавлен код: {code}")
                
            except Exception as e:
                print(f"   ❌ Ошибка при добавлении кода {code}: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n" + "="*60)
    print(f"📊 ИТОГ ЗАГРУЗКИ ИЗ ФАЙЛОВ:")
    print(f"   📁 Найдено в файлах: {total_found}")
    print(f"   ✅ Добавлено новых: {total_added}")
    print("="*60)
    
    return total_added

def sync_codes_with_files():
    """Синхронизирует файлы с базой данных (удаляет использованные коды из файлов)"""
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
    c = conn.cursor()
    
    # Получаем все использованные коды
    c.execute('SELECT code FROM subscriptions WHERE is_used = 1')
    used_codes = [row[0] for row in c.fetchall()]
    
    conn.close()
    
    if not used_codes:
        return 0
    
    total_removed = 0
    
    for code_type in CODE_TYPES:
        file_path = os.path.join(CODES_DIR, f"{code_type}.txt")
        if not os.path.exists(file_path):
            continue
        
        # Читаем файл
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Фильтруем использованные коды
        new_lines = []
        removed = 0
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                new_lines.append(line)
                continue
            
            # Проверяем, не использован ли код
            if any(code in line_stripped for code in used_codes):
                removed += 1
                continue  # Пропускаем использованный код
            
            new_lines.append(line)
        
        # Записываем обратно
        if removed > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            total_removed += removed
            print(f"✅ Из файла {file_path} удалено {removed} использованных кодов")
    
    return total_removed

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ПОДПИСКАМИ ==========

def generate_subscription_code(duration_days, description=None, price=0):
    """Генерирует уникальный код подписки"""
    # Определяем префикс по количеству дней
    if duration_days >= 9999:
        prefix = 'FOREVER'
    elif duration_days >= 365:
        prefix = 'YEAR'
    elif duration_days >= 30:
        prefix = 'MONTH'
    elif duration_days >= 7:
        prefix = 'WEEK'
    else:
        prefix = 'DAY'
    
    # Генерируем уникальный код
    while True:
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
        code = f"{prefix}-{random_part[:4]}-{random_part[4:8]}-{random_part[8:12]}-{random_part[12:16]}"
        
        conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
        c = conn.cursor()
        c.execute('SELECT id FROM subscriptions WHERE code = ?', (code,))
        exists = c.fetchone()
        conn.close()
        
        if not exists:
            return code

def activate_subscription(user_id, code):
    """Активирует подписку для пользователя"""
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
    c = conn.cursor()
    
    try:
        # Проверяем код
        c.execute('''
            SELECT id, duration_days FROM subscriptions 
            WHERE code = ? AND is_used = 0
        ''', (code,))
        sub = c.fetchone()
        
        if not sub:
            return {'success': False, 'error': 'Недействительный или уже использованный код'}
        
        sub_id, duration_days = sub
        
        # Получаем текущую подписку пользователя
        c.execute('SELECT subscription_type, subscription_end FROM users WHERE id = ?', (user_id,))
        current = c.fetchone()
        
        # Вычисляем новую дату окончания
        now = datetime.now()
        
        if duration_days >= 9999:  # Навсегда
            new_end = None
            sub_type = 'forever'
            can_send = True
        else:
            if current and current[1]:
                try:
                    current_end = datetime.fromisoformat(current[1]) if isinstance(current[1], str) else datetime.fromtimestamp(float(current[1]))
                    if current_end > now:
                        new_end = current_end + timedelta(days=duration_days)
                    else:
                        new_end = now + timedelta(days=duration_days)
                except:
                    new_end = now + timedelta(days=duration_days)
            else:
                new_end = now + timedelta(days=duration_days)
            
            # Определяем тип подписки
            if duration_days <= 7:
                sub_type = 'week'
            elif duration_days <= 30:
                sub_type = 'month'
            elif duration_days <= 365:
                sub_type = 'year'
            else:
                sub_type = 'extended'
            
            can_send = True
        
        # Обновляем пользователя
        c.execute('''
            UPDATE users 
            SET subscription_type = ?, subscription_end = ?, can_send_messages = ?
            WHERE id = ?
        ''', (sub_type, new_end.isoformat() if new_end else None, can_send, user_id))
        
        # Отмечаем код как использованный
        c.execute('''
            UPDATE subscriptions 
            SET is_used = 1, used_by = ?, used_at = ?
            WHERE id = ?
        ''', (user_id, now.isoformat(), sub_id))
        
        conn.commit()
        
        # Синхронизируем файлы с базой (удаляем использованный код из файла)
        sync_codes_with_files()
        
        return {
            'success': True, 
            'message': f'Подписка активирована на {duration_days} дней',
            'end_date': new_end.isoformat() if new_end else 'forever'
        }
        
    except Exception as e:
        print(f"Ошибка активации подписки: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        conn.close()

def get_user_subscription(user_id):
    """Получает информацию о подписке пользователя"""
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT subscription_type, subscription_end, can_send_messages FROM users WHERE id = ?
        ''', (user_id,))
        result = c.fetchone()
        
        if result:
            sub_type, sub_end, can_send = result
            if sub_type == 'forever':
                return {
                    'type': 'forever', 
                    'days_left': -1, 
                    'active': True,
                    'can_send': True,
                    'end_date': 'навсегда'
                }
            elif sub_end:
                try:
                    end_date = datetime.fromisoformat(sub_end) if isinstance(sub_end, str) else datetime.fromtimestamp(float(sub_end))
                    days_left = (end_date - datetime.now()).days
                    return {
                        'type': sub_type, 
                        'days_left': max(0, days_left), 
                        'active': days_left > 0,
                        'can_send': can_send and days_left > 0,
                        'end_date': end_date.strftime('%d.%m.%Y')
                    }
                except:
                    return {
                        'type': 'none', 
                        'days_left': 0, 
                        'active': False,
                        'can_send': False,
                        'end_date': 'ошибка формата'
                    }
        
        return {
            'type': 'none', 
            'days_left': 0, 
            'active': False,
            'can_send': False,
            'end_date': 'отсутствует'
        }
    except Exception as e:
        print(f"Ошибка получения подписки: {e}")
        return {
            'type': 'none', 
            'days_left': 0, 
            'active': False,
            'can_send': False,
            'end_date': 'ошибка'
        }
    finally:
        conn.close()

# ========== МАРШРУТЫ ДЛЯ ПОДПИСОК ==========

@app.route('/subscription')
def subscription_page():
    """Страница подписок"""
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('subscription.html')

@app.route('/api/subscription/status', methods=['GET'])
@login_required
def subscription_status():
    """Получить статус подписки пользователя"""
    user_id = session['user_id']
    sub_info = get_user_subscription(user_id)
    return jsonify({'success': True, 'subscription': sub_info})

@app.route('/api/subscription/activate', methods=['POST'])
@login_required
def activate_subscription_route():
    """Активировать подписку по коду"""
    user_id = session['user_id']
    data = request.json
    code = data.get('code', '').upper().strip()
    
    if not code:
        return jsonify({'success': False, 'error': 'Введите код'})
    
    result = activate_subscription(user_id, code)
    return jsonify(result)

@app.route('/api/subscription/deactivate', methods=['POST'])
@login_required
def deactivate_subscription():
    """Деактивировать подписку пользователя (с подтверждением пароля)"""
    user_id = session['user_id']
    data = request.json
    password = data.get('password')
    
    if not password:
        return jsonify({'success': False, 'error': 'Введите пароль'})
    
    # Получаем данные пользователя
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
    c = conn.cursor()
    c.execute('SELECT password_hash FROM users WHERE id = ?', (user_id,))
    result = c.fetchone()
    
    if not result:
        conn.close()
        return jsonify({'success': False, 'error': 'Пользователь не найден'})
    
    password_hash = result[0]
    
    # Проверяем пароль
    if not check_password_hash(password_hash, password):
        conn.close()
        return jsonify({'success': False, 'error': 'Неверный пароль'})
    
    # Деактивируем подписку
    c.execute('''
        UPDATE users 
        SET subscription_type = 'none', 
            subscription_end = NULL, 
            can_send_messages = 0 
        WHERE id = ?
    ''', (user_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True, 
        'message': 'Подписка успешно деактивирована'
    })

# ========== МАРШРУТЫ ДЛЯ АВТОРИЗАЦИИ ==========

@app.route('/')
def index():
    """Главная страница"""
    if 'user_id' in session:
        return render_template('index.html')
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    """Страница входа"""
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/register')
def register_page():
    """Страница регистрации"""
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Регистрация нового пользователя"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Заполните все поля'})
    
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Пароль должен быть минимум 6 символов'})
    
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
    c = conn.cursor()
    
    try:
        password_hash = generate_password_hash(password)
        c.execute('''
            INSERT INTO users (username, password_hash, subscription_type, subscription_end, can_send_messages)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, password_hash, 'none', None, False))
        conn.commit()
        
        return jsonify({'success': True, 'message': 'Регистрация успешна'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Имя пользователя уже занято'})
    finally:
        conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Вход пользователя"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Заполните все поля'})
    
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
    c = conn.cursor()
    
    c.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    
    if user and check_password_hash(user[1], password):
        session['user_id'] = user[0]
        session['username'] = username
        session.permanent = True
        return jsonify({'success': True, 'message': 'Вход выполнен'})
    else:
        return jsonify({'success': False, 'error': 'Неверное имя или пароль'})

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Выход пользователя"""
    session.clear()
    return jsonify({'success': True})

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    """Проверка авторизации"""
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'username': session.get('username')
        })
    return jsonify({'authenticated': False})

# ========== МАРШРУТЫ ДЛЯ ТЕЛЕГРАМ ==========

@app.route('/api/telegram/status', methods=['GET'])
@login_required
def telegram_status():
    """Проверка статуса Telegram авторизации"""
    user_id = session['user_id']
    active_session = load_active_telegram_session(user_id)
    
    if active_session:
        return jsonify({
            'authenticated': True,
            'phone': active_session['phone']
        })
    return jsonify({'authenticated': False})

@app.route('/api/user/sessions', methods=['GET'])
@login_required
def get_user_sessions():
    """Получить список всех Telegram сессий пользователя"""
    user_id = session['user_id']
    sessions = get_user_telegram_sessions(user_id)
    return jsonify({'success': True, 'sessions': sessions})

@app.route('/api/user/sessions/activate', methods=['POST'])
@login_required
def activate_session():
    """Активировать конкретную Telegram сессию"""
    user_id = session['user_id']
    data = request.json
    phone = data.get('phone')
    
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
    c = conn.cursor()
    try:
        c.execute('UPDATE telegram_sessions SET is_active = 0 WHERE user_id = ?', (user_id,))
        c.execute('''UPDATE telegram_sessions SET is_active = 1, last_used = ? 
                    WHERE user_id = ? AND phone = ?''', 
                 (datetime.now().isoformat(), user_id, phone))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()

@app.route('/api/user/sessions/delete', methods=['POST'])
@login_required
def delete_session():
    """Удалить Telegram сессию"""
    user_id = session['user_id']
    data = request.json
    phone = data.get('phone')
    
    if delete_telegram_session(user_id, phone):
        return jsonify({'success': True, 'message': 'Сессия удалена'})
    return jsonify({'success': False, 'error': 'Ошибка удаления'})

@app.route('/api/auth/send-code', methods=['POST'])
@login_required
@async_handler
async def send_code():
    """Отправка кода подтверждения в Telegram"""
    user_id = session['user_id']
    data = request.json
    phone = data.get('phone')
    
    if not phone:
        return jsonify({'success': False, 'error': 'Телефон не указан'})
    
    phone = ''.join(filter(lambda x: x.isdigit() or x == '+', phone))
    
    # Проверяем, есть ли уже сохраненная сессия
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
    c = conn.cursor()
    c.execute('SELECT session_string FROM telegram_sessions WHERE user_id = ? AND phone = ?', 
              (user_id, phone))
    saved_session = c.fetchone()
    conn.close()
    
    if saved_session:
        try:
            client = Client(
                f"user_{user_id}_check",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=saved_session[0],
                in_memory=True
            )
            await client.start()
            await client.stop()
            
            conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
            c = conn.cursor()
            c.execute('''UPDATE telegram_sessions SET is_active = 1, last_used = ? 
                        WHERE user_id = ? AND phone = ?''',
                     (datetime.now().isoformat(), user_id, phone))
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'already_authorized': True})
        except:
            delete_telegram_session(user_id, phone)
    
    flood_seconds = check_flood_wait(phone)
    if flood_seconds:
        return jsonify({'success': False, 'error': f'Подождите {flood_seconds}с', 'flood_wait': flood_seconds})
    
    try:
        session_id = str(uuid.uuid4())
        client = Client(
            f"user_{user_id}_temp_{session_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True,
            workdir=TEMP_DIR
        )
        
        await client.connect()
        
        try:
            sent_code = await client.send_code(phone)
            temp_storage[phone] = {
                'client': client,
                'phone_code_hash': sent_code.phone_code_hash,
                'session_id': session_id,
                'user_id': user_id
            }
            return jsonify({'success': True})
            
        except errors.FloodWait as e:
            wait_seconds = e.value if hasattr(e, 'value') else 60
            flood_wait_storage[phone] = datetime.now() + timedelta(seconds=wait_seconds)
            await client.disconnect()
            return jsonify({'success': False, 'error': f'Подождите {wait_seconds}с', 'flood_wait': wait_seconds})
        except Exception as e:
            await client.disconnect()
            return jsonify({'success': False, 'error': str(e)})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/auth/verify-code', methods=['POST'])
@login_required
@async_handler
async def verify_code():
    """Проверка кода подтверждения"""
    user_id = session['user_id']
    data = request.json
    phone = data.get('phone')
    code = data.get('code')
    
    if not phone or not code:
        return jsonify({'success': False, 'error': 'Телефон или код не указаны'})
    
    phone = ''.join(filter(lambda x: x.isdigit() or x == '+', phone))
    
    flood_seconds = check_flood_wait(phone)
    if flood_seconds:
        return jsonify({'success': False, 'error': f'Подождите {flood_seconds}с', 'flood_wait': flood_seconds})
    
    try:
        client_data = temp_storage.get(phone)
        if not client_data or client_data.get('user_id') != user_id:
            return jsonify({'success': False, 'error': 'Сессия не найдена'})
        
        client = client_data['client']
        phone_code_hash = client_data['phone_code_hash']
        
        try:
            await client.sign_in(phone, phone_code_hash, code)
            session_string = await client.export_session_string()
            
            # Сохраняем сессию в БД
            save_telegram_session(user_id, phone, session_string)
            
            await client.disconnect()
            
            if phone in temp_storage:
                del temp_storage[phone]
            if phone in flood_wait_storage:
                del flood_wait_storage[phone]
            
            return jsonify({'success': True})
            
        except errors.SessionPasswordNeeded:
            return jsonify({'success': False, 'need_password': True})
        except errors.FloodWait as e:
            wait_seconds = e.value if hasattr(e, 'value') else 60
            flood_wait_storage[phone] = datetime.now() + timedelta(seconds=wait_seconds)
            return jsonify({'success': False, 'error': f'Подождите {wait_seconds}с', 'flood_wait': wait_seconds})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/auth/check-password', methods=['POST'])
@login_required
@async_handler
async def check_password():
    """Проверка пароля 2FA"""
    user_id = session['user_id']
    data = request.json
    phone = data.get('phone')
    password = data.get('password')
    
    if not phone or not password:
        return jsonify({'success': False, 'error': 'Телефон или пароль не указаны'})
    
    phone = ''.join(filter(lambda x: x.isdigit() or x == '+', phone))
    
    flood_seconds = check_flood_wait(phone)
    if flood_seconds:
        return jsonify({'success': False, 'error': f'Подождите {flood_seconds}с', 'flood_wait': flood_seconds})
    
    try:
        client_data = temp_storage.get(phone)
        if not client_data or client_data.get('user_id') != user_id:
            return jsonify({'success': False, 'error': 'Сессия не найдена'})
        
        client = client_data['client']
        
        try:
            await client.check_password(password)
            session_string = await client.export_session_string()
            
            # Сохраняем сессию в БД
            save_telegram_session(user_id, phone, session_string)
            
            await client.disconnect()
            
            if phone in temp_storage:
                del temp_storage[phone]
            if phone in flood_wait_storage:
                del flood_wait_storage[phone]
            
            return jsonify({'success': True})
            
        except errors.FloodWait as e:
            wait_seconds = e.value if hasattr(e, 'value') else 60
            flood_wait_storage[phone] = datetime.now() + timedelta(seconds=wait_seconds)
            return jsonify({'success': False, 'error': f'Подождите {wait_seconds}с', 'flood_wait': wait_seconds})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ========== МАРШРУТЫ ДЛЯ РАССЫЛКИ ==========

@app.route('/api/chats', methods=['GET'])
@login_required
@async_handler
async def get_chats():
    """Получение списка чатов"""
    user_id = session['user_id']
    active_session = load_active_telegram_session(user_id)
    
    if not active_session:
        return jsonify({'success': False, 'error': 'Не авторизован в Telegram'})
    
    try:
        client = Client(
            f"user_{user_id}_chats",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=active_session['session_string'],
            in_memory=True
        )
        
        await client.start()
        
        try:
            chats = []
            async for dialog in client.get_dialogs(limit=200):
                chat = dialog.chat
                chat_type = str(chat.type).split('.')[-1]
                
                if chat_type == 'CHANNEL' and hasattr(chat, 'username') and chat.username:
                    chat_id = f"@{chat.username}"
                else:
                    chat_id = str(chat.id)
                
                chat_info = {
                    'id': chat_id,
                    'name': get_chat_name(chat),
                    'type': chat_type,
                    'unread': dialog.unread_messages_count
                }
                chats.append(chat_info)
            
            chats.sort(key=lambda x: (x['type'], x['name'].lower()))
            
            await client.stop()
            return jsonify({'success': True, 'chats': chats})
            
        except errors.FloodWait as e:
            await client.stop()
            wait_seconds = e.value if hasattr(e, 'value') else 60
            return jsonify({'success': False, 'error': f'Подождите {wait_seconds}с', 'flood_wait': wait_seconds})
        except Exception as e:
            await client.stop()
            return jsonify({'success': False, 'error': str(e)})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/spam/start', methods=['POST'])
@login_required
@can_send_messages_required
@async_handler
async def start_spam():
    """Запуск бесконечной рассылки"""
    user_id = session['user_id']
    active_session = load_active_telegram_session(user_id)
    
    if not active_session:
        return jsonify({'success': False, 'error': 'Не авторизован в Telegram'})
    
    data = request.json
    message = data.get('message')
    chat_ids = data.get('chat_ids', [])
    interval = data.get('interval', 5)
    
    if not message:
        return jsonify({'success': False, 'error': 'Введите текст сообщения'})
    
    if not chat_ids:
        return jsonify({'success': False, 'error': 'Выберите хотя бы один чат'})
    
    if interval < 1:
        interval = 1
    
    # Создаем очередь для остановки
    stop_queue = queue.Queue()
    spam_queues[user_id] = stop_queue
    
    # Запускаем задачу в отдельном потоке
    task_id = str(uuid.uuid4())
    
    def spam_worker():
        worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(worker_loop)
        try:
            worker_loop.run_until_complete(spam_task_loop(
                active_session['session_string'], message, chat_ids, interval, 
                stop_queue, task_id, user_id
            ))
        finally:
            worker_loop.close()
    
    thread = threading.Thread(target=spam_worker, daemon=True)
    thread.start()
    
    spam_tasks[task_id] = {
        'thread': thread,
        'queue': stop_queue,
        'start_time': datetime.now(),
        'chats_count': len(chat_ids),
        'interval': interval,
        'status': 'running',
        'sent_count': 0,
        'failed_count': 0,
        'cycles': 0,
        'user_id': user_id
    }
    
    print(f"🚀 Запущена рассылка task_id={task_id} для user_id={user_id} в {len(chat_ids)} чатов")
    
    return jsonify({
        'success': True, 
        'task_id': task_id,
        'message': f'Бесконечная рассылка запущена в {len(chat_ids)} чатов с интервалом {interval}с'
    })

async def spam_task_loop(session_string, message, chat_ids, interval, stop_queue, task_id, user_id):
    """Бесконечный цикл рассылки"""
    client = None
    try:
        client = Client(
            f"spam_user_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=session_string,
            in_memory=True
        )
        
        await client.start()
        cycle = 0
        should_stop = False
        
        print(f"🚀 Запущена рассылка task_id={task_id} для user_id={user_id}")
        
        while not should_stop:
            # Проверяем сигнал остановки в начале каждой итерации
            if not stop_queue.empty():
                try:
                    stop_queue.get_nowait()
                    print(f"⏹️ Получен сигнал остановки для task_id={task_id} (начало цикла)")
                    should_stop = True
                    break
                except queue.Empty:
                    pass
            
            cycle += 1
            spam_tasks[task_id]['cycles'] = cycle
            spam_tasks[task_id]['status'] = f'running_cycle_{cycle}'
            print(f"🔄 Цикл {cycle} для task_id={task_id}")
            
            # Отправляем сообщения во все выбранные чаты
            for i, chat_id in enumerate(chat_ids):
                # Проверяем остановку перед каждым сообщением
                if not stop_queue.empty():
                    try:
                        stop_queue.get_nowait()
                        print(f"⏹️ Остановка во время цикла {cycle} перед отправкой в {chat_id}")
                        should_stop = True
                        break
                    except queue.Empty:
                        pass
                
                if should_stop:
                    break
                
                try:
                    if chat_id.startswith('@'):
                        await client.send_message(chat_id, message)
                    else:
                        chat_id_int = int(chat_id)
                        await client.send_message(chat_id_int, message)
                    
                    spam_tasks[task_id]['sent_count'] += 1
                    print(f"   ✅ Отправлено в {chat_id} (всего: {spam_tasks[task_id]['sent_count']})")
                    
                except errors.FloodWait as e:
                    wait_seconds = e.value if hasattr(e, 'value') else 60
                    spam_tasks[task_id]['failed_count'] += 1
                    spam_tasks[task_id]['status'] = f'flood_wait_{wait_seconds}s'
                    print(f"   ⚠️ Flood wait {wait_seconds}с для {chat_id}")
                    
                    # Ждем указанное время с проверкой остановки
                    for _ in range(wait_seconds):
                        if not stop_queue.empty():
                            try:
                                stop_queue.get_nowait()
                                should_stop = True
                                break
                            except queue.Empty:
                                pass
                        if should_stop:
                            break
                        await asyncio.sleep(1)
                    
                    if should_stop:
                        break
                        
                except Exception as e:
                    spam_tasks[task_id]['failed_count'] += 1
                    print(f"   ❌ Ошибка отправки в чат {chat_id}: {e}")
                
                # Небольшая задержка между сообщениями в одном цикле
                await asyncio.sleep(1)
            
            if should_stop:
                break
            
            # Ждем указанный интервал перед следующим циклом
            spam_tasks[task_id]['status'] = f'waiting_{interval}s'
            print(f"⏳ Ожидание {interval}с перед следующим циклом")
            
            for _ in range(interval):
                if not stop_queue.empty():
                    try:
                        stop_queue.get_nowait()
                        should_stop = True
                        break
                    except queue.Empty:
                        pass
                if should_stop:
                    break
                await asyncio.sleep(1)
        
        if should_stop:
            spam_tasks[task_id]['status'] = 'stopped'
            print(f"⏹️ Рассылка task_id={task_id} остановлена")
        else:
            spam_tasks[task_id]['status'] = 'completed'
            print(f"✅ Рассылка task_id={task_id} завершена")
        
    except Exception as e:
        spam_tasks[task_id]['status'] = f'error: {str(e)}'
        print(f"❌ Ошибка в рассылке task_id={task_id}: {e}")
    finally:
        if client:
            try:
                await client.stop()
                print(f"👋 Клиент остановлен для task_id={task_id}")
            except:
                pass

@app.route('/api/spam/stop', methods=['POST'])
@login_required
def stop_spam():
    """Остановка рассылки"""
    user_id = session['user_id']
    data = request.json
    task_id = data.get('task_id')
    
    print(f"🔴 Попытка остановки спама: user_id={user_id}, task_id={task_id}")
    
    # Проверяем по user_id в spam_queues
    if user_id in spam_queues:
        print(f"   ✅ Найдена очередь для user_id={user_id}, отправляем сигнал stop")
        spam_queues[user_id].put('stop')
        
        # Также обновляем статус задачи если есть task_id
        if task_id and task_id in spam_tasks:
            spam_tasks[task_id]['status'] = 'stopping'
            print(f"   ✅ Статус задачи {task_id} обновлен на 'stopping'")
        
        return jsonify({'success': True, 'message': 'Рассылка останавливается...'})
    
    # Если не нашли по user_id, пробуем по task_id
    if task_id and task_id in spam_tasks:
        task = spam_tasks[task_id]
        if task['user_id'] == user_id:
            print(f"   ✅ Найдена задача по task_id={task_id}, отправляем сигнал stop")
            if 'queue' in task:
                task['queue'].put('stop')
            task['status'] = 'stopping'
            return jsonify({'success': True, 'message': 'Рассылка останавливается...'})
    
    print(f"   ❌ Не найдена активная рассылка для user_id={user_id}")
    return jsonify({'success': False, 'error': 'Нет активной рассылки'})

@app.route('/api/spam/status', methods=['GET'])
@login_required
def spam_status():
    """Получение статуса рассылки"""
    user_id = session['user_id']
    task_id = request.args.get('task_id')
    
    print(f"📊 Запрос статуса: user_id={user_id}, task_id={task_id}")
    
    # Если есть task_id, ищем по нему
    if task_id and task_id in spam_tasks:
        task = spam_tasks[task_id]
        if task['user_id'] == user_id:
            print(f"   ✅ Найдена задача {task_id}, статус: {task['status']}")
            return jsonify({
                'success': True,
                'status': task['status'],
                'sent': task['sent_count'],
                'failed': task['failed_count'],
                'total': task['chats_count'],
                'cycles': task['cycles'],
                'interval': task['interval']
            })
    
    # Если нет task_id, ищем активную задачу для пользователя
    for tid, task in spam_tasks.items():
        if task['user_id'] == user_id and task['status'] not in ['stopped', 'completed']:
            print(f"   ✅ Найдена активная задача {tid} для пользователя")
            return jsonify({
                'success': True,
                'task_id': tid,
                'status': task['status'],
                'sent': task['sent_count'],
                'failed': task['failed_count'],
                'total': task['chats_count'],
                'cycles': task['cycles'],
                'interval': task['interval']
            })
    
    print(f"   ❌ Активных задач не найдено для user_id={user_id}")
    return jsonify({'success': False, 'status': 'no_active_task'})

@app.route('/api/telegram/logout', methods=['POST'])
@login_required
def telegram_logout():
    """Выход из Telegram"""
    user_id = session['user_id']
    data = request.json
    phone = data.get('phone')
    
    if delete_telegram_session(user_id, phone):
        return jsonify({'success': True, 'message': 'Выход из Telegram выполнен'})
    return jsonify({'success': False, 'error': 'Ошибка выхода'})

# ========== АДМИН МАРШРУТЫ ==========

@app.route('/admin/codes')
def admin_codes_page():
    """Страница управления кодами (только для админа)"""
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    # Простая проверка на админа
    if session.get('username') not in ['admin', 'Administrator']:
        return "Доступ запрещен", 403
    
    return render_template('admin_codes.html')

@app.route('/api/admin/codes/load', methods=['POST'])
def admin_load_codes():
    """Загрузить коды из файлов (только для админа)"""
    if session.get('username') not in ['admin', 'Administrator']:
        return jsonify({'success': False, 'error': 'Доступ запрещен'})
    
    added = load_all_codes_from_files()
    return jsonify({'success': True, 'message': f'Загружено {added} новых кодов'})

@app.route('/api/admin/codes/sync', methods=['POST'])
def admin_sync_codes():
    """Синхронизировать файлы с базой (только для админа)"""
    if session.get('username') not in ['admin', 'Administrator']:
        return jsonify({'success': False, 'error': 'Доступ запрещен'})
    
    removed = sync_codes_with_files()
    return jsonify({'success': True, 'message': f'Удалено {removed} использованных кодов из файлов'})

@app.route('/api/admin/codes/list', methods=['GET'])
def admin_list_codes():
    """Получить список всех кодов (только для админа)"""
    if session.get('username') not in ['admin', 'Administrator']:
        return jsonify({'success': False, 'error': 'Доступ запрещен'})
    
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
    c = conn.cursor()
    c.execute('''
        SELECT s.id, s.code, s.duration_days, s.description, s.price, 
               s.is_used, s.used_by, u.username, s.created_at
        FROM subscriptions s
        LEFT JOIN users u ON s.used_by = u.id
        ORDER BY s.created_at DESC
    ''')
    
    codes = []
    for row in c.fetchall():
        codes.append({
            'id': row[0],
            'code': row[1],
            'days': row[2],
            'description': row[3],
            'price': row[4],
            'is_used': bool(row[5]),
            'used_by': row[6],
            'used_by_username': row[7] if row[7] else '-',
            'created_at': row[8]
        })
    
    conn.close()
    return jsonify({'success': True, 'codes': codes})

@app.route('/api/admin/codes/generate', methods=['POST'])
def admin_generate_code():
    """Сгенерировать новый код (только для админа)"""
    if session.get('username') not in ['admin', 'Administrator']:
        return jsonify({'success': False, 'error': 'Доступ запрещен'})
    
    data = request.json
    days = data.get('days', 30)
    price = data.get('price', 0)
    description = data.get('description', '')
    
    code = generate_subscription_code(days, description, price)
    
    return jsonify({
        'success': True,
        'code': code,
        'message': f'Код {code} успешно сгенерирован'
    })

@app.route('/api/admin/codes/delete', methods=['POST'])
def admin_delete_code():
    """Удалить код (только для админа)"""
    if session.get('username') not in ['admin', 'Administrator']:
        return jsonify({'success': False, 'error': 'Доступ запрещен'})
    
    data = request.json
    code_id = data.get('id')
    
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
    c = conn.cursor()
    c.execute('DELETE FROM subscriptions WHERE id = ?', (code_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Код удален'})

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def load_active_telegram_session(user_id):
    """Загрузить активную Telegram сессию пользователя"""
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
    c = conn.cursor()
    try:
        c.execute('''
            SELECT phone, session_string FROM telegram_sessions 
            WHERE user_id = ? AND is_active = 1
            ORDER BY last_used DESC LIMIT 1
        ''', (user_id,))
        result = c.fetchone()
        if result:
            return {'phone': result[0], 'session_string': result[1]}
        return None
    finally:
        conn.close()

def get_user_telegram_sessions(user_id):
    """Получить все Telegram сессии пользователя"""
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
    c = conn.cursor()
    try:
        c.execute('''
            SELECT phone, created_at, is_active FROM telegram_sessions 
            WHERE user_id = ?
            ORDER BY last_used DESC
        ''', (user_id,))
        sessions = []
        for row in c.fetchall():
            sessions.append({
                'phone': row[0],
                'created_at': row[1],
                'is_active': bool(row[2])
            })
        return sessions
    finally:
        conn.close()

def save_telegram_session(user_id, phone, session_string):
    """Сохранить Telegram сессию пользователя"""
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
    c = conn.cursor()
    try:
        # Сначала деактивируем все сессии для этого пользователя
        c.execute('UPDATE telegram_sessions SET is_active = 0 WHERE user_id = ?', (user_id,))
        
        # Сохраняем новую сессию
        c.execute('''
            INSERT INTO telegram_sessions (user_id, phone, session_string, is_active, last_used)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(user_id, phone) 
            DO UPDATE SET session_string = ?, is_active = 1, last_used = ?
        ''', (user_id, phone, session_string, datetime.now().isoformat(), session_string, datetime.now().isoformat()))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка сохранения сессии: {e}")
        return False
    finally:
        conn.close()

def delete_telegram_session(user_id, phone):
    """Удалить Telegram сессию пользователя"""
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'users.db'))
    c = conn.cursor()
    try:
        c.execute('DELETE FROM telegram_sessions WHERE user_id = ? AND phone = ?', 
                 (user_id, phone))
        conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка удаления сессии: {e}")
        return False
    finally:
        conn.close()

def get_chat_name(chat):
    """Получение имени чата"""
    if chat.title:
        return chat.title
    if chat.first_name:
        name = chat.first_name
        if chat.last_name:
            name += f" {chat.last_name}"
        return name
    if chat.username:
        return f"@{chat.username}"
    return "Без имени"

def check_flood_wait(phone):
    """Проверка flood wait"""
    if phone in flood_wait_storage:
        wait_until = flood_wait_storage[phone]
        if datetime.now() < wait_until:
            seconds = int((wait_until - datetime.now()).total_seconds())
            return seconds
        else:
            del flood_wait_storage[phone]
    return None

# ========== ЗАПУСК ПРИЛОЖЕНИЯ ==========

if __name__ == '__main__':
    # При запуске добавляем стартовые коды
    print("="*60)
    print("ЗАПУСК TELEGRAM SENDER")
    print("="*60)
    
    print("\n📁 Проверка папок...")
    for dir_path in [DATA_DIR, USERS_DIR, SESSIONS_DIR, TEMP_DIR, CODES_DIR]:
        if os.path.exists(dir_path):
            print(f"   ✅ {dir_path}")
    
    print("\n📦 Добавление стартовых кодов...")
    try:
        added = add_initial_codes()
        print(f"   ✅ Добавлено {added} новых кодов")
    except Exception as e:
        print(f"   ❌ Ошибка добавления кодов: {e}")
    
    print("\n📦 Загрузка кодов из файлов...")
    try:
        added_files = load_all_codes_from_files()
        print(f"   ✅ Загружено {added_files} новых кодов из файлов")
    except Exception as e:
        print(f"   ❌ Ошибка загрузки кодов из файлов: {e}")
    
    print("\n🚀 Сервер запускается...")
    print("   🌐 http://localhost:5000")
    print("   🌐 http://127.0.0.1:5000")
    print("\n" + "="*60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)