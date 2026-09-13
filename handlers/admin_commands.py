# -*- coding: utf-8 -*-
"""Административные команды"""

import logging
from datetime import datetime
from typing import List

from database.database import (
    add_admin, add_judge, remove_user_by_username,
    get_all_admins, get_all_judges, get_username_by_vk_id,
    get_vk_id_by_username, set_admin, set_judge
)
from database.users_db import check_admin, add_allowed_user
from utils.helpers import clean_username

logger = logging.getLogger(__name__)


class AdminCommandHandler:
    """Обработчик админ-команд"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def handle(self, peer_id: int, user_id: int, command: str, parts: List[str], admin_display: str):
        """Обработка админ-команд"""
        
        # Список судей
        if command == "!judges" or command == "!court":
            await self._show_judges(peer_id)
            return
        
        # Список админов
        if command == "!admins":
            await self._show_admins(peer_id)
            return
        
        # Добавление судьи
        if command == "!addjudge" or command == "!addcourt":
            await self._add_judge(peer_id, user_id, parts, admin_display)
            return
        
        # Удаление судьи
        if command == "!deljudge":
            await self._remove_judge(peer_id, parts, admin_display)
            return
        
        # Добавление админа
        if command == "!addadmin":
            await self._add_admin(peer_id, user_id, parts, admin_display)
            return
        
        # Удаление админа
        if command == "!deladmin":
            await self._remove_admin(peer_id, parts, admin_display)
            return
        
        # Удаление пользователя
        if command == "!deluser":
            await self._remove_user(peer_id, parts, admin_display)
            return
    
    async def _show_judges(self, peer_id: int):
        """Показать список судей"""
        judges = get_all_judges()
        
        if not judges:
            self.bot.send_message(peer_id, "📭 Список судей пуст")
            return
        
        text = "⚖️ **Список судей**\n━━━━━━━━━━━━━━━━━━\n"
        
        for row in judges:
            # row: (vk_id, username, added_date, last_used, note)
            vk_id = row[0]
            username = row[1]
            note = row[4] if len(row) > 4 else ""
            
            display = self._format_user_link(vk_id, username)
            note_str = f" — {note}" if note else ""
            text += f"• {display}{note_str}\n"
        
        self.bot.send_message(peer_id, text[:4000])
    
    async def _show_admins(self, peer_id: int):
        """Показать список админов"""
        admins = get_all_admins()
        
        if not admins:
            self.bot.send_message(peer_id, "📭 Список администраторов пуст")
            return
        
        text = "👑 **Список администраторов**\n━━━━━━━━━━━━━━━━━━\n"
        
        for row in admins:
            # row: (vk_id, username, note)
            vk_id = row[0]
            username = row[1]
            note = row[2] if len(row) > 2 else ""
            
            display = self._format_user_link(vk_id, username)
            note_str = f" — {note}" if note else ""
            text += f"• {display}{note_str}\n"
        
        self.bot.send_message(peer_id, text[:4000])
    
    async def _add_judge(self, peer_id: int, admin_id: int, parts: List[str], admin_display: str):
        """Добавление судьи"""
        if len(parts) < 2:
            self.bot.send_message(peer_id, "❌ Укажите пользователя. Пример: !addjudge @username [заметка]")
            return
        
        target = parts[1]
        note = " ".join(parts[2:]) if len(parts) > 2 else f"Судья с {datetime.now().strftime('%d.%m.%Y')}"
        
        # Поиск пользователя в VK
        user_data = await self._resolve_vk_user(target)
        if not user_data:
            self.bot.send_message(peer_id, f"❌ Пользователь {target} не найден")
            return
        
        vk_id, username, full_name = user_data
        
        # Добавляем через существующую функцию add_judge
        add_judge(vk_id, username, note)
        
        display = self._format_user_link(vk_id, username, full_name)
        self.bot.send_message(peer_id, f"⚖️ {display} теперь судья\n📝 {note}")
        
        await self.bot.logger.log_action(
            "add_judge", admin_display, f"{full_name} (@{username})", 
            f"Заметка: {note}", source_peer_id=peer_id
        )
    
    async def _remove_judge(self, peer_id: int, parts: List[str], admin_display: str):
        """Удаление судьи"""
        if len(parts) < 2:
            self.bot.send_message(peer_id, "❌ Укажите пользователя. Пример: !deljudge @username")
            return
        
        target = parts[1]
        clean = clean_username(target)
        
        vk_id = get_vk_id_by_username(clean)
        if not vk_id:
            self.bot.send_message(peer_id, f"❌ Пользователь {target} не найден в БД")
            return
        
        set_judge(vk_id, False, "")
        username = get_username_by_vk_id(vk_id) or clean
        display = self._format_user_link(vk_id, username)
        
        self.bot.send_message(peer_id, f"❌ {display} больше не судья")
        
        await self.bot.logger.log_action(
            "remove_judge", admin_display, f"@{username}", "Роль снята", source_peer_id=peer_id
        )
    
    async def _add_admin(self, peer_id: int, admin_id: int, parts: List[str], admin_display: str):
        """Добавление администратора"""
        if len(parts) < 2:
            self.bot.send_message(peer_id, "❌ Укажите пользователя. Пример: !addadmin @username [заметка]")
            return
        
        target = parts[1]
        note = " ".join(parts[2:]) if len(parts) > 2 else f"Админ с {datetime.now().strftime('%d.%m.%Y')}"
        
        user_data = await self._resolve_vk_user(target)
        if not user_data:
            self.bot.send_message(peer_id, f"❌ Пользователь {target} не найден")
            return
        
        vk_id, username, full_name = user_data
        
        # Добавляем через существующую функцию add_admin
        add_admin(vk_id, username, note)
        
        display = self._format_user_link(vk_id, username, full_name)
        self.bot.send_message(peer_id, f"👑 {display} теперь администратор\n📝 {note}")
        
        await self.bot.logger.log_action(
            "add_admin", admin_display, f"{full_name} (@{username})", 
            f"Заметка: {note}", source_peer_id=peer_id
        )
    
    async def _remove_admin(self, peer_id: int, parts: List[str], admin_display: str):
        """Удаление администратора"""
        if len(parts) < 2:
            self.bot.send_message(peer_id, "❌ Укажите пользователя. Пример: !deladmin @username")
            return
        
        target = parts[1]
        clean = clean_username(target)
        
        vk_id = get_vk_id_by_username(clean)
        if not vk_id:
            self.bot.send_message(peer_id, f"❌ Пользователь {target} не найден в БД")
            return
        
        # Нельзя удалить самого себя
        if vk_id == admin_display:
            self.bot.send_message(peer_id, "❌ Вы не можете удалить сами себя")
            return
        
        set_admin(vk_id, False, "")
        username = get_username_by_vk_id(vk_id) or clean
        display = self._format_user_link(vk_id, username)
        
        self.bot.send_message(peer_id, f"❌ {display} больше не администратор")
        
        await self.bot.logger.log_action(
            "remove_admin", admin_display, f"@{username}", "Роль снята", source_peer_id=peer_id
        )
    
    async def _remove_user(self, peer_id: int, parts: List[str], admin_display: str):
        """Полное удаление пользователя из БД"""
        if len(parts) < 2:
            self.bot.send_message(peer_id, "❌ Укажите пользователя. Пример: !deluser @username")
            return
        
        target = parts[1]
        clean = clean_username(target)
        
        # Проверяем, существует ли пользователь
        vk_id = get_vk_id_by_username(clean)
        if not vk_id:
            self.bot.send_message(peer_id, f"❌ Пользователь {target} не найден в БД")
            return
        
        username = get_username_by_vk_id(vk_id) or clean
        
        # Удаляем через существующую функцию
        remove_user_by_username(clean)
        
        display = self._format_user_link(vk_id, username)
        self.bot.send_message(peer_id, f"🗑 {display} удалён из базы данных")
        
        await self.bot.logger.log_action(
            "remove_user", admin_display, f"@{username}", "Пользователь удалён", source_peer_id=peer_id
        )
    
    async def _resolve_vk_user(self, target: str) -> tuple:
        """Поиск пользователя в VK"""
        clean = clean_username(target)
        
        try:
            users = self.bot.vk.users.get(user_ids=clean, fields="screen_name")
            if not users and clean.isdigit():
                users = self.bot.vk.users.get(user_ids=int(clean), fields="screen_name")
            
            if not users:
                return None
            
            user = users[0]
            vk_id = user["id"]
            username = user.get("screen_name", str(vk_id))
            full_name = f"{user['first_name']} {user['last_name']}"
            
            return (vk_id, username, full_name)
        except Exception as e:
            logger.error(f"Ошибка поиска пользователя {target}: {e}")
            return None
    
    def _format_user_link(self, vk_id: int, username: str, full_name: str = None) -> str:
        """Форматирование ссылки на пользователя"""
        if full_name:
            return f"[id{vk_id}|{full_name}] (@{username})"
        return f"[id{vk_id}|@{username}]"