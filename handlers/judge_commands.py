# -*- coding: utf-8 -*-
"""Команды судей (повестки)"""

import logging
from datetime import datetime

from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from database.database import (
    add_notification, get_notification, get_judge_notifications,
    get_all_notifications, update_notification_status, delete_notification,
    get_role_chat
)
from database.users_db import check_admin
from utils.helpers import truncate_text

logger = logging.getLogger(__name__)


class JudgeCommands:
    """Обработчик команд судей"""
    
    MAX_MESSAGE_LEN = 1000
    
    def __init__(self, bot):
        self.bot = bot
    
    async def send_notification(self, peer_id: int, user_id: int, text: str, user_display: str):
        """Отправка повестки"""
        admin_chat = get_role_chat("admin")
        judge_chat = get_role_chat("judge")
        
        if not admin_chat:
            self.bot.send_message(peer_id, "❌ Беседа администрации не зарегистрирована. Используйте /regadmin")
            return
        
        if not judge_chat:
            self.bot.send_message(peer_id, "❌ Беседа судей не зарегистрирована. Используйте /regcourt")
            return
        
        # Проверяем, что команда в беседе судей
        if peer_id != judge_chat:
            self.bot.send_message(peer_id, "⛔ Команда /notif работает только в беседе судей")
            return
        
        # Парсим команду
        command_text = text[6:].strip()
        if not command_text:
            self.bot.send_message(peer_id, "❌ Формат: /notif Nick_Name Текст сообщения")
            return
        
        parts = command_text.split(maxsplit=1)
        if len(parts) < 2:
            self.bot.send_message(peer_id, "❌ Формат: /notif Nick_Name Текст сообщения")
            return
        
        target_nickname = parts[0]
        message_text = parts[1]
        
        if len(message_text) > self.MAX_MESSAGE_LEN:
            self.bot.send_message(peer_id, f"❌ Текст не должен превышать {self.MAX_MESSAGE_LEN} символов")
            return
        
        # Сохраняем в БД
        notification_id = add_notification(user_id, peer_id, user_display, target_nickname, message_text)
        
        # Отправляем админам
        keyboard = self._create_notify_keyboard(notification_id)
        
        admin_message = (
            f"📢 НОВАЯ ПОВЕСТКА #{notification_id}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👨‍⚖️ Судья: {user_display}\n"
            f"👤 Ответчик: {target_nickname}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 {message_text}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ Для обработки используйте кнопки ниже"
        )
        
        self.bot.send_message(admin_chat, admin_message, keyboard)
        self.bot.send_message(peer_id, f"✅ Повестка #{notification_id} отправлена администрации")
        
        await self.bot.logger.log_action(
            "notify_sent", user_display, f"Повестка #{notification_id}", 
            f"Ответчик: {target_nickname}", source_peer_id=peer_id
        )
    
    async def show_my_notifications(self, peer_id: int, user_id: int, user_display: str):
        """Показать свои повестки"""
        notifications = get_judge_notifications(user_id, limit=10)
        
        if not notifications:
            self.bot.send_message(peer_id, "📭 У вас нет отправленных повесток")
            return
        
        text = "📋 ВАШИ ПОСЛЕДНИЕ ПОВЕСТКИ\n━━━━━━━━━━━━━━━━━━\n\n"
        
        for n in notifications:
            status_emoji = self._get_status_emoji(n["status"])
            text += f"{status_emoji} **#{n['id']}** — {n['target_nickname']}\n"
            text += f"   📝 {truncate_text(n['message'], 50)}\n"
            text += f"   📅 {n['created_at'][:16]}\n\n"
        
        self.bot.send_message(peer_id, text[:4000])
    
    async def show_all_notifications(self, peer_id: int, user_id: int, user_display: str):
        """Показать все повестки (только для админов)"""
        if not check_admin(user_id):
            self.bot.send_message(peer_id, "⛔ Только администраторы могут просматривать все повестки")
            return
        
        notifications = get_all_notifications(limit=50)
        
        if not notifications:
            self.bot.send_message(peer_id, "📭 Нет отправленных повесток")
            return
        
        # Статистика
        pending = sum(1 for n in notifications if n["status"] == "pending")
        accepted = sum(1 for n in notifications if n["status"] == "accepted")
        rejected = sum(1 for n in notifications if n["status"] == "rejected")
        
        text = (
            f"📋 ВСЕ ПОВЕСТКИ** (последние 50)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Статистика: ⏳{pending} | ✅{accepted} | ❌{rejected}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        
        for n in notifications:
            status_emoji = self._get_status_emoji(n["status"])
            status_text = self._get_status_text(n["status"])
            
            text += f"{status_emoji} #{n['id']} {status_text}\n"
            text += f"   👨‍⚖️ {n['judge_name']} → {n['target_nickname']}\n"
            text += f"   📝 {truncate_text(n['message'], 35)}\n"
            
            if n["status"] == "rejected" and n.get("reject_reason"):
                text += f"   ❌ Причина: {truncate_text(n['reject_reason'], 30)}\n"
            
            text += "\n"
        
        # Разбиваем на части если длинное
        for part in self._split_text(text, 4000):
            self.bot.send_message(peer_id, part)
    
    async def delete_notification(self, peer_id: int, user_id: int, notify_id: int, user_display: str):
        """Удаление повестки"""
        notification = get_notification(notify_id)
        
        if not notification:
            self.bot.send_message(peer_id, f"❌ Повестка #{notify_id} не найдена")
            return
        
        # Только автор или админ
        if notification["judge_id"] != user_id and not check_admin(user_id):
            self.bot.send_message(peer_id, "⛔ Вы можете удалять только свои повестки")
            return
        
        delete_notification(notify_id)
        self.bot.send_message(peer_id, f"✅ Повестка #{notify_id} удалена")
        
        await self.bot.logger.log_action(
            "notify_deleted", user_display, f"Повестка #{notify_id}", 
            "Удалена", source_peer_id=peer_id
        )
    
    async def process_callback(self, peer_id: int, user_id: int, payload: dict, user_display: str):
        """Обработка callback от кнопок повесток"""
        cmd = payload.get("cmd")
        notify_id = payload.get("notification_id")
        
        if not notify_id:
            return
        
        # Только админы могут обрабатывать
        if not check_admin(user_id):
            self.bot.send_message(peer_id, "⛔ Только администраторы могут обрабатывать повестки")
            return
        
        notification = get_notification(notify_id)
        if not notification:
            self.bot.send_message(peer_id, f"❌ Повестка #{notify_id} не найдена")
            return
        
        if notification["status"] != "pending":
            self.bot.send_message(peer_id, f"⚠️ Повестка уже {notification['status']}")
            return
        
        if cmd == "accept_notify":
            update_notification_status(notify_id, "accepted", user_id, user_display)
            
            # Уведомляем судью
            judge_msg = (
                f"✅ Повестка #{notify_id} ПРИНЯТА\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 Ответчик: {notification['target_nickname']}\n"
                f"✅ Принял: {user_display}\n"
                f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
            if notification.get("judge_peer_id"):
                self.bot.send_message(notification["judge_peer_id"], judge_msg)
            
            self.bot.send_message(peer_id, f"✅ Повестка #{notify_id} принята")
            
            await self.bot.logger.log_action(
                "notify_accepted", user_display, f"Повестка #{notify_id}",
                f"Судья: {notification['judge_name']}", source_peer_id=peer_id
            )
        
        elif cmd == "reject_notify":
            # Сохраняем состояние для ввода причины
            self.bot.user_data[user_id] = {
                "action": "awaiting_reject_reason",
                "notify_id": notify_id,
                "notification": notification
            }
            self.bot.send_message(peer_id, "📝 Введите причину отказа (одним сообщением):")
    
    async def process_reject_reason(self, user_id: int, peer_id: int, reason: str, user_display: str) -> bool:
        """Обработка причины отказа"""
        data = self.bot.user_data.get(user_id)
        if not data or data.get("action") != "awaiting_reject_reason":
            return False
        
        notify_id = data["notify_id"]
        notification = data["notification"]
        
        update_notification_status(notify_id, "rejected", user_id, user_display, reason)
        
        # Уведомляем судью
        judge_msg = (
            f"❌ Повестка #{notify_id} ОТКЛОНЕНА\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 Ответчик: {notification['target_nickname']}\n"
            f"❌ Отклонил: {user_display}\n"
            f"📌 Причина: {reason}\n"
            f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        if notification.get("judge_peer_id"):
            self.bot.send_message(notification["judge_peer_id"], judge_msg)
        
        self.bot.send_message(peer_id, f"❌ Повестка #{notify_id} отклонена\nПричина: {reason}")
        
        await self.bot.logger.log_action(
            "notify_rejected", user_display, f"Повестка #{notify_id}",
            f"Причина: {reason}", source_peer_id=peer_id
        )
        
        del self.bot.user_data[user_id]
        return True
    
    def _create_notify_keyboard(self, notify_id: int) -> VkKeyboard:
        """Создание клавиатуры для повестки"""
        keyboard = VkKeyboard(inline=True)
        keyboard.add_button("✅ Принять", VkKeyboardColor.POSITIVE,
                           payload={"cmd": "accept_notify", "notification_id": notify_id})
        keyboard.add_button("❌ Отклонить", VkKeyboardColor.NEGATIVE,
                           payload={"cmd": "reject_notify", "notification_id": notify_id})
        return keyboard
    
    def _get_status_emoji(self, status: str) -> str:
        return {"pending": "⏳", "accepted": "✅", "rejected": "❌"}.get(status, "❓")
    
    def _get_status_text(self, status: str) -> str:
        return {"pending": "ожидает", "accepted": "принята", "rejected": "отклонена"}.get(status, status)
    
    def _split_text(self, text: str, max_len: int) -> list:
        """Разбиение длинного текста"""
        if len(text) <= max_len:
            return [text]
        
        parts = []
        while text:
            if len(text) <= max_len:
                parts.append(text)
                break
            split_at = text.rfind('\n', 0, max_len)
            if split_at == -1:
                split_at = max_len
            parts.append(text[:split_at])
            text = text[split_at:]
        return parts