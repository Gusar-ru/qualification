import asyncio
import json
import os
import ssl
from typing import List, Dict, Optional
import aiohttp
from urllib.parse import urljoin, quote


class MatrixChatManager:
    """Менеджер для работы с Matrix API через прямые HTTP запросы"""
    
    def __init__(self, homeserver: str = "https://matrix.it-teacher.pro", verify_ssl: bool = False):
        """
        Инициализация менеджера Matrix
        
        Args:
            homeserver: URL Matrix сервера
            verify_ssl: Проверять ли SSL сертификат (False для серверов с самоподписанными сертификатами)
        """
        self.homeserver = homeserver.rstrip('/')
        self.verify_ssl = verify_ssl
        self.access_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.device_id: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить или создать HTTP сессию"""
        if self.session is None or self.session.closed:
            # Создаем SSL контекст
            if not self.verify_ssl:
                # Отключаем проверку SSL сертификата
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                connector = aiohttp.TCPConnector(ssl=ssl_context)
            else:
                connector = aiohttp.TCPConnector()
            
            self.session = aiohttp.ClientSession(connector=connector)
        return self.session

    async def _close_session(self):
        """Закрыть HTTP сессию"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Получить заголовки для запросов"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Matrix-Python-Client/1.0"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    async def login(self, username: str, password: str) -> bool:
        """Авторизация пользователя в Matrix"""
        try:
            session = await self._get_session()
            
            # Определяем тип логина (username или user_id)
            login_type = "m.id.user" if username.startswith("@") else "m.id.user"
            
            # Подготавливаем данные для логина
            login_data = {
                "type": "m.login.password",
                "identifier": {
                    "type": login_type,
                    "user": username.split(":")[0].lstrip("@") if ":" in username else username
                },
                "password": password
            }
            
            # URL для логина
            login_url = urljoin(self.homeserver, "/_matrix/client/v3/login")
            
            async with session.post(login_url, json=login_data, headers=self._get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data.get("access_token")
                    self.user_id = data.get("user_id")
                    self.device_id = data.get("device_id")
                    
                    print(f"✅ Успешный вход пользователя: {self.user_id}")
                    return True
                else:
                    error_data = await response.json()
                    error_msg = error_data.get("error", f"HTTP {response.status}")
                    print(f"❌ Ошибка авторизации: {error_msg}")
                    return False
                    
        except Exception as e:
            print(f"❌ Ошибка при входе: {str(e)}")
            return False
    
    async def sync(self, timeout: int = 30000) -> Optional[Dict]:
        """Синхронизация с сервером для получения актуальных данных"""
        if not self.access_token:
            print("❌ Не авторизован. Сначала выполните вход.")
            return None
        
        try:
            session = await self._get_session()
            sync_url = urljoin(self.homeserver, "/_matrix/client/v3/sync")
            
            params = {
                "timeout": timeout,
                "full_state": "false"
            }
            
            async with session.get(sync_url, params=params, headers=self._get_headers()) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_data = await response.json()
                    print(f"❌ Ошибка синхронизации: {error_data.get('error', response.status)}")
                    return None
        except Exception as e:
            print(f"❌ Ошибка при синхронизации: {str(e)}")
            return None
    
    async def get_room_info(self, room_id: str) -> Optional[Dict]:
        """Получить информацию о комнате"""
        if not self.access_token:
            return None
        
        try:
            session = await self._get_session()
            # URL для получения состояния комнаты
            room_url = urljoin(self.homeserver, f"/_matrix/client/v3/rooms/{quote(room_id)}/state")
            
            async with session.get(room_url, headers=self._get_headers()) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            print(f"❌ Ошибка при получении информации о комнате {room_id}: {str(e)}")
        
        return None
    
    async def get_room_members(self, room_id: str) -> List[str]:
        """Получить список участников комнаты"""
        if not self.access_token:
            return []
        
        try:
            session = await self._get_session()
            members_url = urljoin(self.homeserver, f"/_matrix/client/v3/rooms/{quote(room_id)}/members")
            
            async with session.get(members_url, headers=self._get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    members = []
                    for member in data.get("chunk", []):
                        display_name = member.get("content", {}).get("displayname")
                        user_id = member.get("state_key", "")
                        members.append(display_name if display_name else user_id)
                    return members
        except Exception as e:
            print(f"❌ Ошибка при получении участников комнаты {room_id}: {str(e)}")
        
        return []
    
    async def get_user_chats(self) -> List[Dict]:
        """Получение списка чатов/комнат пользователя"""
        if not self.access_token:
            print("❌ Не авторизован. Сначала выполните вход.")
            return []
        
        try:
            # Синхронизация для получения актуальных данных
            sync_data = await self.sync(timeout=30000)
            
            if not sync_data:
                return []
            
            rooms = []
            joined_rooms = sync_data.get("rooms", {}).get("join", {})
            
            for room_id, room_data in joined_rooms.items():
                # Получаем информацию о комнате из состояния
                state_events = room_data.get("state", {}).get("events", [])
                
                # Извлекаем информацию о комнате
                room_name = "Без названия"
                room_topic = "Нет описания"
                room_alias = "Нет алиаса"
                is_encrypted = False
                member_count = 0
                
                for event in state_events:
                    event_type = event.get("type")
                    content = event.get("content", {})
                    
                    if event_type == "m.room.name":
                        room_name = content.get("name", room_name)
                    elif event_type == "m.room.topic":
                        room_topic = content.get("topic", room_topic)
                    elif event_type == "m.room.canonical_alias":
                        room_alias = content.get("alias", room_alias)
                    elif event_type == "m.room.encryption":
                        is_encrypted = True
                    elif event_type == "m.room.member":
                        member_count += 1
                
                # Получаем последнее сообщение из timeline
                timeline_events = room_data.get("timeline", {}).get("events", [])
                last_message = "Нет сообщений"
                
                for event in reversed(timeline_events):
                    if event.get("type") == "m.room.message":
                        content = event.get("content", {})
                        if "body" in content:
                            body = content["body"]
                            last_message = body[:100] + "..." if len(body) > 100 else body
                            break
                
                # Получаем участников комнаты
                members = await self.get_room_members(room_id)
                members_preview = members[:10] if members else []
                
                room_info = {
                    'room_id': room_id,
                    'name': room_name,
                    'canonical_alias': room_alias,
                    'member_count': len(members) if members else member_count,
                    'is_encrypted': is_encrypted,
                    'topic': room_topic,
                    'last_message': last_message,
                    'members': members_preview
                }
                rooms.append(room_info)
            
            return rooms
            
        except Exception as e:
            print(f"❌ Ошибка при получении чатов: {str(e)}")
            return []
    
    async def logout(self):
        """Выход из системы"""
        if not self.access_token:
            return
        
        try:
            session = await self._get_session()
            logout_url = urljoin(self.homeserver, "/_matrix/client/v3/logout")
            
            async with session.post(logout_url, headers=self._get_headers()) as response:
                if response.status == 200:
                    print("✅ Выход выполнен успешно")
                else:
                    print("⚠️ Не удалось выполнить выход, но сессия будет закрыта")
        except Exception as e:
            print(f"⚠️ Ошибка при выходе: {str(e)}")
        finally:
            self.access_token = None
            self.user_id = None
            self.device_id = None
            await self._close_session()
    
    def display_chats(self, chats: List[Dict]):
        """Красивый вывод списка чатов"""
        if not chats:
            print("📭 У вас нет активных чатов")
            return
        
        print(f"\n📋 ВАШИ ЧАТЫ ({len(chats)}):")
        print("=" * 80)
        
        for i, chat in enumerate(chats, 1):
            print(f"\n{i}. {chat['name']}")
            print(f"   ID: {chat['room_id']}")
            print(f"   Алиас: {chat['canonical_alias']}")
            print(f"   Участников: {chat['member_count']}")
            print(f"   Зашифрован: {'✅' if chat['is_encrypted'] else '❌'}")
            print(f"   Описание: {chat['topic']}")
            print(f"   Последнее сообщение: {chat['last_message']}")
            
            if chat['members']:
                members_preview = ", ".join(chat['members'])
                print(f"   Участники: {members_preview}{'...' if len(chat['members']) >= 10 else ''}")
            
            print("-" * 80)


async def main():
    """Основная функция"""
    print("🔐 ПОДКЛЮЧЕНИЕ К MATRIX СЕРВЕРУ")
    print("=" * 50)
    
    # Предупреждение о SSL (если отключена проверка)
    print("⚠️  ВНИМАНИЕ: Проверка SSL сертификата отключена для работы с сервером.")
    print("   Это безопасно только для доверенных серверов.\n")
    
    # Ввод данных пользователя
    username = input("Введите логин (например @user:matrix.org или user): ").strip()
    password = input("Введите пароль: ").strip()
    
    # Создаем менеджер чатов (verify_ssl=False по умолчанию для серверов с самоподписанными сертификатами)
    chat_manager = MatrixChatManager("https://matrix.it-teacher.pro", verify_ssl=False)
    
    try:
        # Выполняем вход
        print("\n🔄 Выполняется вход...")
        login_success = await chat_manager.login(username, password)
        
        if not login_success:
            print("❌ Не удалось войти в систему. Проверьте логин и пароль.")
            return
        
        # Получаем список чатов
        print("\n🔄 Загрузка списка чатов...")
        chats = await chat_manager.get_user_chats()
        
        # Выводим результат
        chat_manager.display_chats(chats)
        
        # Сохраняем в файл (опционально)
        if chats:
            with open('matrix_chats.json', 'w', encoding='utf-8') as f:
                json.dump(chats, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Список чатов сохранен в файл: matrix_chats.json")
        
    finally:
        # Выход из системы
        await chat_manager.logout()


if __name__ == "__main__":
    asyncio.run(main())
