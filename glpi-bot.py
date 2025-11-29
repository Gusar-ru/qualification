import requests
import json
from typing import Dict, Optional

def init_glpi_session(base_url, app_token, user_token):
    """
    Инициализация сессии GLPI
    """
    try:
        url = f"{base_url}/apirest.php/initSession"
        headers = {
            'Content-Type': 'application/json',
            'App-Token': app_token,
            'Authorization': f"user_token {user_token}"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            session_token = data.get('session_token')
            print("✅ Сессия GLPI успешно инициализирована")
            return session_token
        else:
            print(f"❌ Ошибка инициализации сессии: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка при инициализации сессии: {e}")
        return None

def kill_glpi_session(base_url, app_token, session_token):
    """
    Завершение сессии GLPI
    """
    try:
        url = f"{base_url}/apirest.php/killSession"
        headers = {
            'App-Token': app_token,
            'Session-Token': session_token
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            print("✅ Сессия GLPI успешно завершена")
            return True
        else:
            print(f"❌ Ошибка завершения сессии: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при завершении сессии: {e}")
        return False

def create_ticket(base_url: str, app_token: str, session_token: str, ticket_data: Dict) -> Optional[Dict]:
    """
    Создание новой заявки в GLPI
    
    Args:
        base_url: URL GLPI сервера
        app_token: Токен приложения
        session_token: Токен сессии
        ticket_data: Данные для создания заявки
    
    Returns:
        Созданная заявка или None в случае ошибки
    
    Пример ticket_data:
    {
        "name": "Проблема с принтером",
        "content": "Принтер в отделе бухгалтерии не печатает",
        "itilcategories_id": 1,  # ID категории
        "type": 1,  # Тип: 1 - Инцидент, 2 - Запрос
        "urgency": 3,  # Срочность: 1-5
        "impact": 2,  # Влияние: 1-5
        "priority": 3,  # Приоритет: 1-5
        "entities_id": 0,  # ID организации
        "users_id_recipient": 2  # ID пользователя-заявителя
    }
    """
    try:
        url = f"{base_url}/apirest.php/Ticket"
        headers = {
            'App-Token': app_token,
            'Session-Token': session_token,
            'Content-Type': 'application/json'
        }
        
        # Обязательные поля
        required_fields = ['name', 'content']
        for field in required_fields:
            if field not in ticket_data:
                print(f"❌ Отсутствует обязательное поле: {field}")
                return None
        
        # Отправка запроса
        response = requests.post(url, headers=headers, json=ticket_data)
        
        if response.status_code == 201:
            created_ticket = response.json()
            ticket_id = created_ticket.get('id')
            print(f"✅ Заявка успешно создана! ID: {ticket_id}")
            return created_ticket
        else:
            print(f"❌ Ошибка создания заявки: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка при создании заявки: {e}")
        return None

def create_ticket_simple(base_url: str, app_token: str, session_token: str, 
                        title: str, description: str, category_id: int = 0, 
                        priority: int = 3, ticket_type: int = 1) -> Optional[Dict]:
    """
    Упрощенная версия создания заявки
    
    Args:
        title: Заголовок заявки
        description: Описание проблемы
        category_id: ID категории (0 - без категории)
        priority: Приоритет (1-5)
        ticket_type: Тип заявки (1 - Инцидент, 2 - Запрос)
    """
    ticket_data = {
        "name": title,
        "content": description,
        "type": ticket_type,
        "priority": priority,
        "itilcategories_id": category_id,
        "_users_id_requester": 0,  # Текущий пользователь
    }
    
    return create_ticket(base_url, app_token, session_token, ticket_data)

def get_categories(base_url: str, app_token: str, session_token: str) -> list:
    """
    Получение списка категорий для заявок
    """
    try:
        url = f"{base_url}/apirest.php/ITILCategory"
        headers = {
            'App-Token': app_token,
            'Session-Token': session_token
        }
        params = {
            'range': '0-100',
            'order': 'ASC',
            'sort': 'name'
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            categories = response.json()
            print(f"✅ Получено {len(categories)} категорий")
            return categories
        else:
            print(f"❌ Ошибка получения категорий: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Ошибка при получении категорий: {e}")
        return []

def display_categories(categories: list):
    """
    Отображение списка категорий
    """
    if not categories:
        print("📭 Категории не найдены")
        return
    
    print(f"\n{'='*60}")
    print(f"{'ID':<6} {'Название категории':<40} {'Полный путь':<20}")
    print(f"{'='*60}")
    
    for category in categories:
        cat_id = category.get('id', 'N/A')
        name = category.get('name', 'Без названия')[:38]
        complete_name = category.get('completename', '')[:18]
        
        print(f"{cat_id:<6} {name:<40} {complete_name:<20}")

def get_tickets(base_url, app_token, session_token, limit=10):
    """
    Получение списка заявок из GLPI
    """
    try:
        url = f"{base_url}/apirest.php/Ticket"
        headers = {
            'App-Token': app_token,
            'Session-Token': session_token
        }
        params = {
            'range': f"0-{limit-1}",
            'order': 'DESC',
            'sort': 'id'
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            tickets = response.json()
            print(f"✅ Получено {len(tickets)} заявок")
            return tickets
        else:
            print(f"❌ Ошибка получения заявок: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Ошибка при получении заявок: {e}")
        return []

def display_tickets_simple(tickets):
    """
    Простое отображение заявок
    """
    if not tickets:
        print("📭 Заявки не найдены")
        return
    
    status_map = {
        1: "📝 Новая", 2: "🔄 В работе", 3: "✅ Решена",
        4: "👍 Утверждена", 5: "🧪 Тестирование", 6: "🔒 Закрыта"
    }
    
    priority_map = {
        1: "🟢 Низкий", 2: "🟡 Средний", 3: "🟠 Высокий",
        4: "🔴 Очень высокий", 5: "💀 Критический"
    }
    
    type_map = {
        1: "🛠️ Инцидент", 2: "❓ Запрос"
    }
    
    print(f"\n{'='*120}")
    print(f"{'ID':<6} {'Тип':<12} {'Статус':<15} {'Приоритет':<15} {'Заголовок':<40} {'Создана':<20}")
    print(f"{'='*120}")
    
    for ticket in tickets:
        ticket_id = ticket.get('id', 'N/A')
        name = ticket.get('name', 'Без названия')[:38]
        status_id = ticket.get('status', 1)
        priority_id = ticket.get('priority', 1)
        type_id = ticket.get('type', 1)
        date_creation = ticket.get('date_creation', '')[:19]
        
        status = status_map.get(status_id, "❓ Неизвестно")
        priority = priority_map.get(priority_id, "⚪ Не указан")
        ticket_type = type_map.get(type_id, "❓ Неизвестно")
        
        print(f"{ticket_id:<6} {ticket_type:<12} {status:<15} {priority:<15} {name:<40} {date_creation:<20}")

def main():
    """
    Основная функция с демонстрацией создания заявки
    """
    # КОНФИГУРАЦИЯ - ЗАМЕНИТЕ НА ВАШИ ДАННЫЕ
    CONFIG = {
        'base_url': 'https://help.it-teacher.pro',
        'app_token': 'FOnIW0T8On2WEx5Ud9VKgHmvnk82kMaVKOnJxrS9',
        'user_token': 'h4umAudep3iKzMOeennsR3y45h34O5sfUPkh0Wbh'
    }
    
    print("🚀 Запуск GLPI API клиента с функцией создания заявок")
    print("=" * 60)
    
    # Инициализация сессии
    session_token = init_glpi_session(
        CONFIG['base_url'],
        CONFIG['app_token'], 
        CONFIG['user_token']
    )
    
    if not session_token:
        print("❌ Не удалось инициализировать сессию. Проверьте настройки.")
        return
    
    try:
        # 1. Получение категорий
        print("\n1. 📂 ПОЛУЧЕНИЕ КАТЕГОРИЙ:")
        categories = get_categories(
            CONFIG['base_url'],
            CONFIG['app_token'],
            session_token
        )
        display_categories(categories)
        
        # 2. Создание тестовой заявки
        print("\n2. 📝 СОЗДАНИЕ ТЕСТОВОЙ ЗАЯВКИ:")
        
        # Пример данных для заявки
        ticket_data = {
            "name": "Тестовая заявка из API",
            "content": "Это тестовая заявка, созданная через Python API клиент.\n\nОписание проблемы: тестирование функционала создания заявок.",
            "type": 1,  # Инцидент
            "priority": 3,  # Высокий приоритет
            "urgency": 2,  # Средняя срочность
            "impact": 2,  # Среднее влияние
            "itilcategories_id": 0,  # Без категории (можно указать ID из списка выше)
            "requesttypes_id": 1,  # Тип запроса
        }
        
        created_ticket = create_ticket(
            CONFIG['base_url'],
            CONFIG['app_token'],
            session_token,
            ticket_data
        )
        
        # 3. Создание заявки через упрощенную функцию
        print("\n3. 📝 СОЗДАНИЕ ЗАЯВКИ (УПРОЩЕННАЯ ВЕРСИЯ):")
        
        simple_ticket = create_ticket_simple(
            CONFIG['base_url'],
            CONFIG['app_token'],
            session_token,
            title="Проблема с доступом к сети",
            description="Не могу подключиться к корпоративной сети Wi-Fi.\n\nДетали:\n- Локация: 3 этаж\n- Устройство: ноутбук Dell\n- Время возникновения: 10:00",
            priority=2,  # Средний приоритет
            ticket_type=1  # Инцидент
        )
        
        # 4. Показать созданные заявки
        print("\n4. 📨 ПОСЛЕДНИЕ ЗАЯВКИ (включая созданные):")
        tickets = get_tickets(
            CONFIG['base_url'],
            CONFIG['app_token'],
            session_token, 
            limit=10
        )
        display_tickets_simple(tickets)
        
        # 5. Пример создания заявки с выбором категории
        if categories:
            print("\n5. 📝 СОЗДАНИЕ ЗАЯВКИ С КАТЕГОРИЕЙ:")
            
            # Берем первую категорию из списка
            first_category_id = categories[0].get('id', 0)
            
            category_ticket = create_ticket_simple(
                CONFIG['base_url'],
                CONFIG['app_token'],
                session_token,
                title="Заявка с категорией",
                description=f"Эта заявка создана с категорией ID: {first_category_id}",
                category_id=first_category_id,
                priority=2
            )
       
    finally:
        # Завершение сессии
        kill_glpi_session(
            #CONFIG['base_url'],
            #CONFIG['app_token'],
            #session_token
            )


def interactive_create_ticket():
    """
    Интерактивное создание заявки через консоль
    """
    CONFIG = {
        'base_url': 'https://your-glpi-instance.com',
        'app_token': 'your_app_token_here',
        'user_token': 'your_user_token_here'
    }
    
    session_token = init_glpi_session(**CONFIG)
    if not session_token:
        return
    
    try:
        print("\n🎯 ИНТЕРАКТИВНОЕ СОЗДАНИЕ ЗАЯВКИ")
        print("=" * 40)
        
        # Запрос данных у пользователя
        title = input("Введите заголовок заявки: ").strip()
        if not title:
            print("❌ Заголовок не может быть пустым!")
            return
        
        description = input("Введите описание проблемы: ").strip()
        if not description:
            print("❌ Описание не может быть пустым!")
            return
        
        print("\nВыберите приоритет:")
        print("1 - 🟢 Низкий")
        print("2 - 🟡 Средний") 
        print("3 - 🟠 Высокий")
        print("4 - 🔴 Очень высокий")
        print("5 - 💀 Критический")
        
        priority_input = input("Приоритет (1-5, по умолчанию 3): ").strip()
        priority = int(priority_input) if priority_input.isdigit() and 1 <= int(priority_input) <= 5 else 3
        
        print("\nВыберите тип заявки:")
        print("1 - 🛠️ Инцидент (проблема)")
        print("2 - ❓ Запрос (вопрос, услуга)")
        
        type_input = input("Тип (1-2, по умолчанию 1): ").strip()
        ticket_type = int(type_input) if type_input.isdigit() and int(type_input) in [1, 2] else 1
        
        # Создание заявки
        result = create_ticket_simple(
            CONFIG['base_url'],
            CONFIG['app_token'],
            session_token,
            title=title,
            description=description,
            priority=priority,
            ticket_type=ticket_type
        )
        
        if result:
            print(f"\n🎉 Заявка успешно создана! ID: {result.get('id')}")
        else:
            print("\n❌ Не удалось создать заявку")
            
    finally:
        kill_glpi_session(CONFIG['base_url'], CONFIG['app_token'], session_token)

if __name__ == "__main__":
    print("GLPI API Client - Create Ticket Example")
    print("=" * 50)
    print("Доступные функции:")
    print("1. main() - Демонстрация всех возможностей")
    print("2. interactive_create_ticket() - Интерактивное создание заявки\n")
    
    # Запуск основного примера
    main()
    
    # Или интерактивное создание заявки
    # interactive_create_ticket()