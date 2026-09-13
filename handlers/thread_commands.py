# -*- coding: utf-8 -*-
"""Команды для работы с темами форума"""

import logging
from typing import Optional

from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from database.users_db import is_admin, is_judge
from config import config

logger = logging.getLogger(__name__)


class ThreadCommandHandler:
    """Обработчик команд для работы с темами"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def show_info(self, peer_id: int, user_id: int, thread_id: int, user_display: str):
        """Показать информацию о теме"""
        is_user_admin = is_admin(user_id)
        
        # Проверка доступа
        can_access, error = await self.bot.forum.check_access(thread_id, user_id, is_user_admin)
        if not can_access:
            self.bot.send_message(peer_id, error)
            return
        
        info = await self.bot.forum.get_thread_info(thread_id)
        if not info:
            self.bot.send_message(peer_id, f"❌ Тема {thread_id} не найдена")
            return
        
        status_emoji = "🔒" if info["is_closed"] else "🔓"
        pin_emoji = "📌" if info["is_sticky"] else "📍"
        status_text = "Закрыта" if info["is_closed"] else "Открыта"
        
        text = (
            f"{status_emoji} **{info['title']}** {pin_emoji}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: {thread_id}\n"
            f"{status_emoji} Статус: {status_text}\n"
            f"👤 Автор: {info['author']}\n"
            f"📂 Раздел: {info['forum_name']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        if is_user_admin:
            text += "👇 Выберите действие:"
            keyboard = self._create_admin_keyboard(thread_id, user_id)
        else:
            keyboard = None
        
        self.bot.send_message(peer_id, text, keyboard)
        
        await self.bot.logger.log_action(
            "thread_info", user_display, f"Тема {thread_id}", info['title'][:50],
            source_peer_id=peer_id
        )
    
    async def show_edit_menu(self, peer_id: int, user_id: int, thread_id: int, user_display: str):
        """Показать меню редактирования темы"""
        is_user_admin = is_admin(user_id)
        
        # Проверка доступа
        can_access, error = await self.bot.forum.check_access(thread_id, user_id, is_user_admin)
        if not can_access:
            self.bot.send_message(peer_id, error)
            return
        
        info = await self.bot.forum.get_thread_info(thread_id)
        if not info:
            self.bot.send_message(peer_id, f"❌ Тема {thread_id} не найдена")
            return
        
        keyboard = self._create_action_keyboard(thread_id, user_id, is_user_admin)
        
        self.bot.send_message(
            peer_id,
            f"🛠 Управление темой\n━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 {info['title']}\n🆔 {thread_id}\n━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👇 Выберите действие:",
            keyboard
        )
    
    async def process_callback(self, peer_id: int, user_id: int, payload: dict, user_display: str):
        """Обработка callback от кнопок тем"""
        cmd = payload.get("cmd")
        thread_id = payload.get("thread_id")
        
        if not thread_id:
            return
        
        is_user_admin = is_admin(user_id)
        
        # Проверка доступа
        can_access, error = await self.bot.forum.check_access(thread_id, user_id, is_user_admin)
        if not can_access:
            self.bot.send_message(peer_id, error)
            return
        
        # Открыть/закрыть
        if cmd == "toggle_open_close":
            info = await self.bot.forum.get_thread_info(thread_id)
            if not info:
                self.bot.send_message(peer_id, "❌ Тема не найдена")
                return
            
            success, msg = await self.bot.forum.set_thread_open(thread_id, info["is_closed"])
            self.bot.send_message(peer_id, f"🔧 {msg}")
            
            await self.bot.logger.log_action(
                "toggle_thread", user_display, f"Тема {thread_id}", msg, source_peer_id=peer_id
            )
        
        # Закрепить/открепить
        elif cmd == "pin":
            success, msg = await self.bot.forum.set_thread_sticky(thread_id, True)
            self.bot.send_message(peer_id, f"📌 {msg}")
        
        elif cmd == "unpin":
            success, msg = await self.bot.forum.set_thread_sticky(thread_id, False)
            self.bot.send_message(peer_id, f"📍 {msg}")
        
        # Изменить название
        elif cmd == "edit_title" and is_user_admin:
            self.bot.user_data[user_id] = {
                "action": "awaiting_thread_title",
                "thread_id": thread_id
            }
            self.bot.send_message(peer_id, "📝 Введите новое название темы (или 'отмена'):")
        
        # Удалить тему
        elif cmd == "delete_thread" and is_user_admin:
            keyboard = VkKeyboard(inline=True)
            keyboard.add_button("✅ Да, удалить", VkKeyboardColor.NEGATIVE,
                               payload={"cmd": "confirm_delete", "thread_id": thread_id})
            keyboard.add_button("❌ Нет", VkKeyboardColor.POSITIVE,
                               payload={"cmd": "cancel_delete"})
            self.bot.send_message(
                peer_id,
                f"⚠️ **Удаление темы {thread_id}**\n"
                f"Тема будет удалена без возможности восстановления!\n"
                f"Укажите причину удаления:",
                keyboard
            )
            self.bot.user_data[user_id] = {
                "action": "awaiting_delete_reason",
                "thread_id": thread_id
            }
        
        # Обновить информацию
        elif cmd == "refresh_info":
            await self.show_info(peer_id, user_id, thread_id, user_display)
    
    async def process_title_change(self, user_id: int, peer_id: int, new_title: str, user_display: str):
        """Обработка изменения названия темы"""
        data = self.bot.user_data.get(user_id, {})
        thread_id = data.get("thread_id")
        
        if not thread_id:
            return
        
        success, msg = await self.bot.forum.edit_thread_title(thread_id, new_title)
        self.bot.send_message(peer_id, f"✏️ {msg}")
        
        await self.bot.logger.log_action(
            "edit_title", user_display, f"Тема {thread_id}", new_title[:50], source_peer_id=peer_id
        )
    
    async def process_delete_thread(self, user_id: int, peer_id: int, reason: str, user_display: str):
        """Обработка удаления темы"""
        data = self.bot.user_data.get(user_id, {})
        thread_id = data.get("thread_id")
        
        if not thread_id:
            return
        
        success, msg = await self.bot.forum.delete_thread(thread_id)
        self.bot.send_message(peer_id, f"🗑 {msg}")
        
        await self.bot.logger.log_action(
            "delete_thread", user_display, f"Тема {thread_id}", f"Причина: {reason}", source_peer_id=peer_id
        )
    
    def _create_action_keyboard(self, thread_id: int, user_id: int, is_admin: bool) -> VkKeyboard:
        """Создание клавиатуры для управления темой"""
        keyboard = VkKeyboard(inline=True)
        
        # Базовые кнопки
        keyboard.add_button("🔒 Закрыть/Открыть", VkKeyboardColor.PRIMARY,
                           payload={"cmd": "toggle_open_close", "thread_id": thread_id})
        
        keyboard.add_button("📌 Закрепить", VkKeyboardColor.PRIMARY,
                           payload={"cmd": "pin", "thread_id": thread_id})
        
        keyboard.add_line()
        keyboard.add_button("📍 Открепить", VkKeyboardColor.SECONDARY,
                           payload={"cmd": "unpin", "thread_id": thread_id})
        
        keyboard.add_button("🔄 Обновить", VkKeyboardColor.SECONDARY,
                           payload={"cmd": "refresh_info", "thread_id": thread_id})
        
        # Админские кнопки
        if is_admin:
            keyboard.add_line()
            keyboard.add_button("✏️ Изменить название", VkKeyboardColor.PRIMARY,
                               payload={"cmd": "edit_title", "thread_id": thread_id})
            keyboard.add_button("🗑 Удалить", VkKeyboardColor.NEGATIVE,
                               payload={"cmd": "delete_thread", "thread_id": thread_id})
        
        return keyboard
    
    def _create_admin_keyboard(self, thread_id: int, user_id: int) -> VkKeyboard:
        """Создание полной клавиатуры для админов"""
        return self._create_action_keyboard(thread_id, user_id, True)