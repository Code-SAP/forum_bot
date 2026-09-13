# -*- coding: utf-8 -*-
"""Сервис для работы с форумом"""

import re
import logging
from typing import Optional, Dict, Any, Tuple

from arizona_forum_async import ArizonaAPI

from config import config

logger = logging.getLogger(__name__)

THREAD_URL_RE = re.compile(
    r"(?:https?://)?(?:[\w.-]+\.)?arizona-rp\.com/threads/(?:[^/\s?#]+\.)?(\d+)",
    re.IGNORECASE,
)


class ForumService:
    """Сервис для взаимодействия с форумом"""
    
    def __init__(self):
        self._api: Optional[ArizonaAPI] = None
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        return self._connected and self._api is not None
    
    async def connect(self) -> bool:
        """Подключение к форуму"""
        try:
            cookies = {k: v for k, v in config.FORUM_COOKIES.items() if v}
            
            if not cookies.get("xf_user") or not cookies.get("xf_session"):
                logger.error("❌ Отсутствуют куки форума")
                return False
            
            self._api = ArizonaAPI(config.FORUM_USER_AGENT, cookies)
            await self._api.connect()
            self._connected = True
            logger.info("✅ Форум подключён")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к форуму: {e}")
            self._connected = False
            return False
    
    async def close(self):
        """Закрытие соединения"""
        if self._api:
            try:
                await self._api.close()
            except Exception as e:
                logger.warning(f"Ошибка при закрытии: {e}")
            self._api = None
        self._connected = False
    
    @staticmethod
    def extract_thread_id(text: str) -> Optional[int]:
        """Извлечение ID темы из URL или текста"""
        if not text:
            return None
        
        text = text.strip()
        
        # Прямой ID
        if text.isdigit():
            return int(text)
        
        # URL с названием.123456
        match = THREAD_URL_RE.search(text)
        if match:
            return int(match.group(1))
        
        # /threads/123456
        match = re.search(r"/threads/(\d+)", text)
        if match:
            return int(match.group(1))
        
        return None
    
    async def get_thread_info(self, thread_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о теме"""
        if not self._api:
            return None
    
        try:
            thread = await self._api.get_thread(thread_id)
            if not thread:
                return None
        
            # Получаем категорию (может быть ID или объект)
            category = await thread.get_category()
            category_id = None
            category_name = "Неизвестно"
        
            if category:
                # Если category — это число (ID)
                if isinstance(category, int):
                    category_id = category
                    # Пробуем получить название категории
                    cat_obj = await self._api.get_category(category)
                    if cat_obj:
                        category_name = getattr(cat_obj, "title", "Неизвестно")
                else:
                    # Если category — объект
                    category_id = getattr(category, "id", None)
                    category_name = getattr(category, "title", "Неизвестно")
        
            return {
                "id": thread_id,
                "title": getattr(thread, "title", "Без названия"),
                "is_closed": getattr(thread, "is_closed", False),
                "is_sticky": getattr(thread, "is_sticky", False),
                "author": getattr(thread.creator, "username", "Неизвестно") if thread.creator else "Неизвестно",
                "author_id": getattr(thread.creator, "id", None) if thread.creator else None,
                "created_date": getattr(thread, "create_date", None),
                "forum_id": category_id,
                "forum_name": category_name,
            }
        except Exception as e:
            logger.error(f"Ошибка получения темы {thread_id}: {e}")
            return None

    async def set_thread_open(self, thread_id: int, opened: bool) -> Tuple[bool, str]:
        """Открыть/закрыть тему"""
        if not self._api:
            return False, "Форум не подключён"
        
        try:
            thread = await self._api.get_thread(thread_id)
            if not thread:
                return False, "Тема не найдена"
            
            resp = await thread.edit_info(
                opened=opened,
                sticky=getattr(thread, "is_sticky", False),
                title=getattr(thread, "title", "")
            )
            
            if resp and resp.status == 200:
                status = "открыта" if opened else "закрыта"
                return True, f"Тема {status}"
            return False, "Ошибка при изменении статуса"
            
        except Exception as e:
            logger.error(f"Ошибка set_thread_open {thread_id}: {e}")
            return False, str(e)
    
    async def set_thread_sticky(self, thread_id: int, sticky: bool) -> Tuple[bool, str]:
        """Закрепить/открепить тему"""
        if not self._api:
            return False, "Форум не подключён"
        
        try:
            thread = await self._api.get_thread(thread_id)
            if not thread:
                return False, "Тема не найдена"
            
            resp = await thread.edit_info(
                sticky=sticky,
                opened=not getattr(thread, "is_closed", False),
                title=getattr(thread, "title", "")
            )
            
            if resp and resp.status == 200:
                status = "закреплена" if sticky else "откреплена"
                return True, f"Тема {status}"
            return False, "Ошибка при изменении статуса"
            
        except Exception as e:
            logger.error(f"Ошибка set_thread_sticky {thread_id}: {e}")
            return False, str(e)
    
    async def edit_thread_title(self, thread_id: int, new_title: str) -> Tuple[bool, str]:
        """Изменение названия темы"""
        if not self._api:
            return False, "Форум не подключён"
        
        new_title = new_title.strip()
        if len(new_title) < 3:
            return False, "Название слишком короткое (минимум 3 символа)"
        
        try:
            thread = await self._api.get_thread(thread_id)
            if not thread:
                return False, "Тема не найдена"
            
            resp = await thread.edit_info(
                title=new_title,
                opened=not getattr(thread, "is_closed", False),
                sticky=getattr(thread, "is_sticky", False)
            )
            
            if resp and resp.status == 200:
                return True, f"Название изменено на: {new_title}"
            return False, "Ошибка при изменении названия"
            
        except Exception as e:
            logger.error(f"Ошибка edit_thread_title {thread_id}: {e}")
            return False, str(e)
    
    async def delete_thread(self, thread_id: int) -> Tuple[bool, str]:
        """Удаление темы"""
        if not self._api:
            return False, "Форум не подключён"
        
        try:
            thread = await self._api.get_thread(thread_id)
            if not thread:
                return False, "Тема не найдена"
            
            if hasattr(thread, "delete"):
                resp = await thread.delete()
                if resp and resp.status == 200:
                    return True, "Тема удалена"
            
            return False, "Удаление не поддерживается"
            
        except Exception as e:
            logger.error(f"Ошибка delete_thread {thread_id}: {e}")
            return False, str(e)
    
    async def check_access(self, thread_id: int, user_id: int, is_admin: bool) -> Tuple[bool, str]:
        """Проверка доступа к теме"""
        if is_admin:
            return True, ""
        
        info = await self.get_thread_info(thread_id)
        if not info:
            return False, "Тема не найдена или нет доступа"
        
        if info["forum_id"] == config.JUDGE_FORUM_ID:
            return True, ""
        
        return False, f"⛔ Судьи могут работать только в разделе судебных исков (ID: {config.JUDGE_FORUM_ID})"
    
    async def debug_get_threads(self, category_id: int, page: int = 1):
        """Отладочный метод для просмотра структуры данных"""
        if not self._api:
            return None
        
        try:
            category = await self._api.get_category(category_id)
            if not category:
                return None
            
            result = await category.get_threads(page=page)
            
            # Выводим структуру в лог
            logger.info(f"Тип результата: {type(result)}")
            
            if isinstance(result, dict):
                logger.info(f"Ключи словаря: {list(result.keys())}")
                for key in result.keys():
                    value = result[key]
                    logger.info(f"  {key}: {type(value)} - {len(value) if hasattr(value, '__len__') else 'N/A'}")
            
            return result
        except Exception as e:
            logger.error(f"Debug error: {e}")
            return None