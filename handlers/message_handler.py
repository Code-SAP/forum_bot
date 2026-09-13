# -*- coding: utf-8 -*-
"""Основной обработчик сообщений"""

import logging
import time
from typing import Dict, Any

from vk_api.bot_longpoll import VkBotEvent
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from database.users_db import is_admin, is_judge, get_role_chat
from config import config
from utils.helpers import clean_username

logger = logging.getLogger(__name__)


class MessageHandler:
    """Обработчик входящих сообщений"""
    
    DUPLICATE_TIMEOUT = 10
    
    def __init__(self, bot):
        self.bot = bot
        self.processed_events: Dict[str, float] = {}
    
    async def handle(self, event: VkBotEvent):
        """Обработка сообщения"""
        message = event.object.message
        message_id = message.get("id", 0)
        peer_id = message["peer_id"]
        user_id = message["from_id"]
        text = message.get("text", "").strip()
        
        # Игнорируем сообщения от бота
        if user_id < 0:
            return
        
        # Проверка на дубли
        if self._is_duplicate(message_id, peer_id, text):
            return
        
        # Проверка прав
        if not await self._check_permissions(user_id, peer_id):
            return
        
        user_display = self.bot.get_user_display(user_id)
        
        # Обработка ожидающих состояний
        if user_id in self.bot.user_data:
            if await self._handle_waiting_state(user_id, peer_id, text, user_display):
                return
        
        # Обработка callback payload
        if "payload" in message:
            import json
            try:
                payload = json.loads(message["payload"])
                await self.bot.callback_handler.handle(peer_id, user_id, payload, user_display, message.get("conversation_message_id"))
            except:
                pass
            return
        
        # Обработка команд
        if not text:
            return
        
        # /notif команды
        if text.startswith("/notif"):
            await self._handle_notify_commands(peer_id, user_id, text, user_display)
            return
        
        # /reg команды (регистрация бесед)
        if text.startswith(("/regcourt", "/regadmin")):
            await self._handle_register_chat(peer_id, user_id, text, user_display)
            return
        
        # ! команды
        if not text.startswith("!"):
            return
        
        parts = text.split()
        command = parts[0].lower()
        
        await self._handle_command(peer_id, user_id, command, parts, user_display)
    
    def _is_duplicate(self, message_id: int, peer_id: int, text: str) -> bool:
        """Проверка на дублирование сообщения"""
        unique_key = f"{message_id}_{peer_id}_{text[:10]}"
        current_time = time.time()
        
        if unique_key in self.processed_events:
            if current_time - self.processed_events[unique_key] < self.DUPLICATE_TIMEOUT:
                logger.debug(f"Дубль: {unique_key}")
                return True
        
        self.processed_events[unique_key] = current_time
        
        # Очистка старых ключей
        old_keys = [k for k, ts in self.processed_events.items() if current_time - ts > 60]
        for k in old_keys:
            del self.processed_events[k]
        
        return False
    
    async def _check_permissions(self, user_id: int, peer_id: int) -> bool:
        """Проверка прав пользователя"""
        from database.users_db import check_admin, check_judge, get_chat
        
        # Админы имеют полный доступ
        if check_admin(user_id):
            return True
        
        # Судьи работают только в зарегистрированной беседе
        if check_judge(user_id):
            judge_chat = get_chat("judge")
            if judge_chat and peer_id == judge_chat:
                return True
            if peer_id < 2000000000:
                return True  # Личные сообщения
            self.bot.send_message(peer_id, "⛔ Эта команда работает только в беседе судей")
            return False
        
        # Обычные пользователи не имеют доступа к командам
        if peer_id < 2000000000:
            return True  # Личные сообщения разрешены
        
        return False
    
    async def _handle_waiting_state(self, user_id: int, peer_id: int, text: str, user_display: str) -> bool:
        """Обработка ожидающих состояний"""
        data = self.bot.user_data[user_id]
        action = data.get("action")
        
        # Отмена
        if text.lower() in ["отмена", "cancel", "-"]:
            self.bot.send_message(peer_id, "❌ Действие отменено")
            del self.bot.user_data[user_id]
            return True
        
        # Ожидание названия для темы
        if action == "awaiting_thread_title":
            await self.bot.thread_handler.process_title_change(user_id, peer_id, text, user_display)
            del self.bot.user_data[user_id]
            return True
        
        # Ожидание причины удаления
        if action == "awaiting_delete_reason":
            await self.bot.thread_handler.process_delete_thread(user_id, peer_id, text, user_display)
            del self.bot.user_data[user_id]
            return True
        
        return False
    
    async def _handle_notify_commands(self, peer_id: int, user_id: int, text: str, user_display: str):
        """Обработка команд /notif"""
        from handlers.judge_commands import JudgeCommands
        judge_cmd = JudgeCommands(self.bot)
        
        parts = text.split()
        
        if len(parts) >= 2 and parts[1] == "status":
            await judge_cmd.show_my_notifications(peer_id, user_id, user_display)
        elif len(parts) >= 2 and parts[1] == "all":
            await judge_cmd.show_all_notifications(peer_id, user_id, user_display)
        elif len(parts) >= 2 and parts[1] == "del" and len(parts) >= 3 and parts[2].isdigit():
            await judge_cmd.delete_notification(peer_id, user_id, int(parts[2]), user_display)
        else:
            await judge_cmd.send_notification(peer_id, user_id, text, user_display)
    
    async def _handle_register_chat(self, peer_id: int, user_id: int, text: str, user_display: str):
        """Регистрация беседы"""
        if not is_admin(user_id):
            self.bot.send_message(peer_id, "⛔ Только администраторы могут регистрировать беседы")
            return
        
        if peer_id < 2000000000:
            self.bot.send_message(peer_id, "❌ Эта команда работает только в беседах")
            return
        
        if text.startswith("/regcourt"):
            role = "judge"
            role_name = "Судей"
        elif text.startswith("/regadmin"):
            role = "admin"
            role_name = "Администрации"
        else:
            return
        
        from database.database import save_role_chat
        save_role_chat(role, peer_id, user_id)
        
        self.bot.send_message(peer_id, f"✅ Беседа зарегистрирована как беседа {role_name}")
        
        await self.bot.logger.log_action(
            "register_chat",
            user_display,
            f"peer_id={peer_id}",
            f"Зарегистрирована как {role_name}",
            source_peer_id=peer_id
        )
    
    async def _handle_command(self, peer_id: int, user_id: int, command: str, parts: list, user_display: str):
        """Обработка команд"""
        
        # Помощь
        if command == "!help":
            await self._show_help(peer_id)
            return
        
        # Получить ID чата
        if command == "!getid":
            chat_id = peer_id - 2000000000 if peer_id >= 2000000000 else peer_id
            self.bot.send_message(peer_id, f"📌 ID: {chat_id}\nPeer ID: {peer_id}")
            return
        
        # Статистика
        if command == "!иски":
            days = 7
            if len(parts) >= 2 and parts[1].isdigit():
                days = int(parts[1])
            await self.bot.stats_handler.get_court_stats(peer_id, user_display, days)
            return
        
        # Перезапуск
        if command == "!reboot":
            if not is_admin(user_id):
                self.bot.send_message(peer_id, "⛔ Только администраторы могут перезапускать бота")
                return
            
            kb = VkKeyboard(inline=True)
            kb.add_button("✅ Да", VkKeyboardColor.NEGATIVE, payload={"cmd": "confirm_reboot", "user_id": user_id})
            kb.add_button("❌ Нет", VkKeyboardColor.POSITIVE, payload={"cmd": "cancel_reboot"})
            self.bot.send_message(peer_id, "⚠️ Подтвердите перезапуск бота:", kb)
            return
        
        # Информация о теме
        if command == "!info":
            if len(parts) < 2:
                self.bot.send_message(peer_id, "❌ Укажите ссылку на тему")
                return
            
            thread_id = self.bot.forum.extract_thread_id(parts[1])
            if not thread_id:
                self.bot.send_message(peer_id, "❌ Не удалось распознать ID темы")
                return
            
            await self.bot.thread_handler.show_info(peer_id, user_id, thread_id, user_display)
            return
        
        # Редактирование темы
        if command == "!edit":
            if len(parts) < 2:
                self.bot.send_message(peer_id, "❌ Укажите ссылку на тему")
                return
            
            thread_id = self.bot.forum.extract_thread_id(parts[1])
            if not thread_id:
                self.bot.send_message(peer_id, "❌ Не удалось распознать ID темы")
                return
            
            await self.bot.thread_handler.show_edit_menu(peer_id, user_id, thread_id, user_display)
            return
        
        # Админ-команды
        if command in ["!addadmin", "!deladmin", "!admins", "!addjudge", "!deljudge", "!judges", "!deluser"]:
            if not is_admin(user_id):
                self.bot.send_message(peer_id, "⛔ Только администраторы могут использовать эту команду")
                return
            
            await self.bot.admin_handler.handle(peer_id, user_id, command, parts, user_display)
            return
    
    async def _show_help(self, peer_id: int):
        """Показать справку"""
        help_text = """
╔══════════════════════════════════╗
║        🤖 ПОМОЩЬ ПО БОТУ         ║
╚══════════════════════════════════╝

📌 ОСНОВНЫЕ КОМАНДЫ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
!help          — показать эту справку
!getid         — получить ID текущего чата
!info [ссылка] — информация о теме
!edit [ссылка] — управление темой
!иски [дни]    — статистика судебных исков

⚖️ КОМАНДЫ СУДЕЙ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/notif Ник Текст        — отправить повестку
/notif status           — статус ваших повесток
/notif all              — все повестки (админы)
/notif del ID           — удалить повестку

👑 АДМИН-КОМАНДЫ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
!addjudge @user [заметка]  — добавить судью
!deljudge @user            — удалить судью
!judges                    — список судей
!addadmin @user [заметка]  — добавить админа
!deladmin @user            — удалить админа
!admins                    — список админов
!deluser @user             — удалить пользователя
!reboot                    — перезапустить бота

📌 РЕГИСТРАЦИЯ БЕСЕД
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/regcourt   — зарегистрировать беседу судей
/regadmin   — зарегистрировать беседу админов
        """
        self.bot.send_message(peer_id, help_text)