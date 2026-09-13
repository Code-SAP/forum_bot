# main.py - обновлённая версия с подключением всех обработчиков

import asyncio
import logging
import sys
import os

from vk_api import VkApi
from vk_api.bot_longpoll import VkBotLongPoll

from config import config
from database.database import init_db
from services.forum_service import ForumService
from handlers.message_handler import MessageHandler
from handlers.callback_handler import CallbackHandler
from handlers.admin_commands import AdminCommandHandler
from handlers.judge_commands import JudgeCommands
from handlers.thread_commands import ThreadCommandHandler
from handlers.stats_commands import StatsCommandHandler
from utils.logger import ActionLogger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ],
)
logger = logging.getLogger(__name__)


class ForumBot:
    """Главный класс бота"""
    
    def __init__(self):
        logger.info("🚀 Инициализация бота...")
        
        # VK API
        self.vk_session = VkApi(token=config.VK_GROUP_TOKEN)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, config.VK_GROUP_ID)
        
        # Сервисы
        self.forum = ForumService()
        self.logger = ActionLogger(self.vk, config.LOG_CHAT_ID)
        
        # Обработчики
        self.admin_handler = AdminCommandHandler(self)
        self.judge_commands = JudgeCommands(self)
        self.thread_handler = ThreadCommandHandler(self)
        self.stats_handler = StatsCommandHandler(self)
        self.callback_handler = CallbackHandler(self)
        self.message_handler = MessageHandler(self)
        
        # Состояния
        self.user_data = {}
        
        logger.info("✅ Бот инициализирован")
    
    def send_message(self, peer_id: int, message: str, keyboard=None) -> int:
        """Отправка сообщения"""
        try:
            params = {
                "peer_id": peer_id,
                "message": message[:4000],
                "random_id": self._get_random_id(),
            }
            if keyboard:
                params["keyboard"] = keyboard.get_keyboard()
            return self.vk.messages.send(**params)
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
            return 0
    
    async def safe_edit(self, peer_id: int, new_text: str, conversation_message_id: int = None, remove_keyboard: bool = True) -> bool:
        """Безопасное редактирование"""
        try:
            params = {"peer_id": peer_id, "message": new_text}
            if conversation_message_id:
                params["conversation_message_id"] = conversation_message_id
            if remove_keyboard:
                params["keyboard"] = '{"buttons":[],"inline":true}'
            self.vk.messages.edit(**params)
            await asyncio.sleep(0.2)
            return True
        except Exception as e:
            logger.error(f"Ошибка редактирования: {e}")
            return False
    
    def _get_random_id(self) -> int:
        import random
        return random.randint(1, 2**63)
    
    def get_user_display(self, user_id: int) -> str:
        """Получение отображения пользователя"""
        try:
            info = self.vk.users.get(user_ids=user_id)[0]
            first = info.get("first_name", "")
            last = info.get("last_name", "")
            screen = info.get("screen_name", "")
            name = f"{first} {last}".strip()
            if screen:
                return f"{name} (@{screen})"
            return name or f"id{user_id}"
        except:
            return f"id{user_id}"
    
    async def run(self):
        """Запуск бота"""
        logger.info("=" * 50)
        logger.info("🤖 ЗАПУСК БОТА")
        logger.info("=" * 50)
        
        # Подключение к форуму
        if not await self.forum.connect():
            logger.error("❌ Не удалось подключиться к форуму")
            await asyncio.sleep(60)
            return
        
        logger.info("👂 Бот запущен и ожидает сообщения...")
        
        while True:
            try:
                for event in self.longpoll.listen():
                    if event.type.value == 4:  # MESSAGE_NEW
                        await self.message_handler.handle(event)
            except Exception as e:
                logger.error(f"Ошибка: {e}", exc_info=True)
                await asyncio.sleep(10)


def main():
    """Точка входа"""
    init_db()
    bot = ForumBot()
    
    while True:
        try:
            asyncio.run(bot.run())
        except KeyboardInterrupt:
            logger.info("🛑 Бот остановлен")
            break
        except Exception as e:
            logger.error(f"💥 Критическая ошибка: {e}", exc_info=True)
            import time
            time.sleep(30)


if __name__ == "__main__":
    main()