# -*- coding: utf-8 -*-
"""Обработчик callback-кнопок"""

import logging
import asyncio
import sys
import os

from vk_api.keyboard import VkKeyboard

logger = logging.getLogger(__name__)


class CallbackHandler:
    """Обработчик нажатий на кнопки"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def handle(self, peer_id: int, user_id: int, payload: dict, user_display: str, cmid: int = None):
        """Обработка callback"""
        cmd = payload.get("cmd")
        
        # Повестки
        if cmd in ["accept_notify", "reject_notify"]:
            await self.bot.judge_commands.process_callback(peer_id, user_id, payload, user_display)
            if cmid:
                await self.bot.safe_edit(peer_id, "✅ Обработано", conversation_message_id=cmid)
            return
        
        # Кнопки тем
        if cmd in ["toggle_open_close", "pin", "unpin", "edit_title", "delete_thread", "refresh_info", "confirm_delete", "cancel_delete"]:
            if cmd == "confirm_delete":
                # Уже обрабатывается в thread_commands
                pass
            elif cmd == "cancel_delete":
                if user_id in self.bot.user_data:
                    del self.bot.user_data[user_id]
                self.bot.send_message(peer_id, "❌ Удаление отменено")
                if cmid:
                    await self.bot.safe_edit(peer_id, "❌ Отменено", conversation_message_id=cmid)
                return
            else:
                await self.bot.thread_handler.process_callback(peer_id, user_id, payload, user_display)
                if cmid and cmd not in ["edit_title", "delete_thread"]:
                    await self.bot.safe_edit(peer_id, "✅ Выполнено", conversation_message_id=cmid)
            return
        
        # Перезапуск
        if cmd == "confirm_reboot":
            from database.users_db import is_admin
            
            if not is_admin(user_id):
                self.bot.send_message(peer_id, "⛔ Только администраторы могут перезапускать бота")
                return
            
            if payload.get("user_id") != user_id:
                self.bot.send_message(peer_id, "⛔ Это не ваша команда")
                return
            
            if cmid:
                await self.bot.safe_edit(peer_id, "🔄 Перезапуск...", conversation_message_id=cmid)
            
            await self.bot.logger.log_action(
                "bot_reboot", user_display, "Бот", "Перезапуск по команде", source_peer_id=peer_id
            )
            
            # Закрываем соединения
            await self.bot.forum.close()
            
            # Перезапуск
            os.execv(sys.executable, [sys.executable] + sys.argv)
        
        elif cmd == "cancel_reboot":
            if cmid:
                await self.bot.safe_edit(peer_id, "❌ Перезапуск отменён", conversation_message_id=cmid)