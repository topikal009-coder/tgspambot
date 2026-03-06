#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для загрузки кодов из текстовых файлов в базу данных
Запуск: python load_codes.py
"""

import sqlite3
import os
import re
from datetime import datetime

# Путь к базе данных
DB_PATH = os.path.join('data', 'users.db')
# Путь к папке с кодами
CODES_DIR = 'codes'

# Соответствие типов кодов и количества дней
CODE_TYPES = {
    'day': {'days': 1, 'description': 'Подписка на 1 день'},
    'week': {'days': 7, 'description': 'Подписка на неделю'},
    'month': {'days': 30, 'description': 'Подписка на месяц'},
    'year': {'days': 365, 'description': 'Подписка на год'},
    'forever': {'days': 9999, 'description': 'Пожизненная подписка'}
}

def init_codes_directory():
    """Создает папку для кодов, если её нет"""
    if not os.path.exists(CODES_DIR):
        os.makedirs(CODES_DIR)
        print(f"✅ Создана папка {CODES_DIR}")
        
        # Создаем примеры файлов
        for code_type in CODE_TYPES:
            file_path = os.path.join(CODES_DIR, f"{code_type}.txt")
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Файл с кодами на {CODE_TYPES[code_type]['description']}\n")
                    f.write(f"# Формат: {code_type}-XXXX-XXXX-XXXX-XXXX\n")
                    f.write(f"# Пример: {code_type}-ABCD-EFGH-IJKL-MNOP\n\n")
                print(f"✅ Создан файл {file_path}")

def validate_code_format(code, code_type):
    """Проверяет формат кода"""
    pattern = rf"^{code_type}-[A-Z0-9]{{4}}-[A-Z0-9]{{4}}-[A-Z0-9]{{4}}-[A-Z0-9]{{4}}$"
    return re.match(pattern, code, re.IGNORECASE) is not None

def load_codes_from_file(file_path, code_type):
    """Загружает коды из файла"""
    codes = []
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
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

def add_codes_to_database(codes, code_type):
    """Добавляет коды в базу данных"""
    if not codes:
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    added = 0
    skipped = 0
    
    days = CODE_TYPES[code_type]['days']
    description = CODE_TYPES[code_type]['description']
    
    for code in codes:
        try:
            # Проверяем, есть ли уже такой код в базе
            c.execute('SELECT id FROM subscriptions WHERE code = ?', (code,))
            if c.fetchone():
                print(f"⏭️ Код {code} уже существует в базе")
                skipped += 1
                continue
            
            # Добавляем код
            c.execute('''
                INSERT INTO subscriptions (code, duration_days, description, price, is_used)
                VALUES (?, ?, ?, 0, 0)
            ''', (code, days, description))
            added += 1
            print(f"✅ Добавлен код: {code} ({description})")
            
        except Exception as e:
            print(f"❌ Ошибка при добавлении кода {code}: {e}")
    
    conn.commit()
    conn.close()
    
    return added, skipped

def mark_used_codes_as_used():
    """Помечает коды как использованные, если они уже активированы в базе"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Получаем все использованные коды
    c.execute('SELECT code FROM subscriptions WHERE is_used = 1')
    used_codes = [row[0] for row in c.fetchall()]
    
    conn.close()
    return used_codes

def sync_with_files():
    """Синхронизирует файлы с базой данных (удаляет использованные коды из файлов)"""
    used_codes = mark_used_codes_as_used()
    
    if not used_codes:
        return
    
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
            print(f"✅ Из файла {file_path} удалено {removed} использованных кодов")

def load_all_codes():
    """Загружает все коды из всех файлов"""
    print("\n" + "="*60)
    print("ЗАГРУЗКА КОДОВ ИЗ ФАЙЛОВ")
    print("="*60)
    
    total_added = 0
    total_skipped = 0
    
    for code_type in CODE_TYPES:
        file_path = os.path.join(CODES_DIR, f"{code_type}.txt")
        print(f"\n📁 Обработка файла: {os.path.basename(file_path)}")
        
        codes = load_codes_from_file(file_path, code_type)
        if codes:
            added, skipped = add_codes_to_database(codes, code_type)
            total_added += added
            total_skipped += skipped
            print(f"   Добавлено: {added}, Пропущено (уже есть): {skipped}")
        else:
            print("   Коды не найдены")
    
    print("\n" + "="*60)
    print(f"✅ ИТОГО: Добавлено {total_added} новых кодов, Пропущено {total_skipped}")
    print("="*60)
    
    # Синхронизируем файлы с базой
    sync_with_files()

def show_stats():
    """Показывает статистику по кодам"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("\n" + "="*60)
    print("СТАТИСТИКА КОДОВ")
    print("="*60)
    
    # Общая статистика
    c.execute('SELECT COUNT(*) FROM subscriptions')
    total = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM subscriptions WHERE is_used = 1')
    used = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM subscriptions WHERE is_used = 0')
    available = c.fetchone()[0]
    
    print(f"📊 Всего кодов: {total}")
    print(f"✅ Использовано: {used}")
    print(f"🆓 Доступно: {available}")
    
    # Статистика по типам
    print("\n📊 По типам подписок:")
    for code_type, info in CODE_TYPES.items():
        days = info['days']
        c.execute('SELECT COUNT(*) FROM subscriptions WHERE duration_days = ?', (days,))
        type_total = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM subscriptions WHERE duration_days = ? AND is_used = 1', (days,))
        type_used = c.fetchone()[0]
        
        if type_total > 0:
            print(f"   {info['description']}: {type_total} всего, {type_used} использовано")
    
    conn.close()

def main():
    """Главное меню"""
    while True:
        print("\n" + "="*50)
        print("УПРАВЛЕНИЕ КОДАМИ ИЗ ФАЙЛОВ")
        print("="*50)
        print("1. Загрузить все коды из файлов")
        print("2. Показать статистику")
        print("3. Создать примеры файлов")
        print("4. Синхронизировать файлы (удалить использованные)")
        print("5. Выйти")
        print("="*50)
        
        choice = input("\nВыберите действие (1-5): ").strip()
        
        if choice == '1':
            load_all_codes()
        
        elif choice == '2':
            show_stats()
        
        elif choice == '3':
            init_codes_directory()
            print("✅ Примеры файлов созданы. Заполните их кодами.")
        
        elif choice == '4':
            sync_with_files()
            print("✅ Синхронизация завершена")
        
        elif choice == '5':
            print("👋 До свидания!")
            break
        
        else:
            print("❌ Неверный выбор")

if __name__ == "__main__":
    # Проверяем существование базы данных
    if not os.path.exists(DB_PATH):
        print(f"❌ База данных не найдена по пути: {DB_PATH}")
        print("Сначала запустите основное приложение для создания базы")
    else:
        main()