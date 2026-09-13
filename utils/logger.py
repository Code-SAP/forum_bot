# -*- coding: utf-8 -*-
"""Логирование действий"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class ActionLogger:
    """Логирование действий в VK чат и файл"""
    
    def __init__(self, vk_api, log_chat_id: Optional[int] = None):
        self.vk = vk_api
        self.log_chat_id = log_chat_id
    
    async def log_action(
        self,
        action_type: str,
        user_name: str,
        target: str,
        details: str,
        source_peer_id: Optional[int] = None
    ):
        """Логирование действия"""
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        log_message = (
            f"[{timestamp}] {action_type}\n"
            f"👤 {user_name}\n"
            f"🎯 {target}\n"
            f"📝 {details}"
        )
        
        # Лог в файл
        logger.info(f"ACTION: {action_type} | {user_name} | {target} | {details}")
        
        # Лог в VK чат
        if self.log_chat_id:
            try:
                self.vk.messages.send(
                    peer_id=self.log_chat_id,
                    message=log_message[:4000],
                    random_id=self._get_random_id()
                )
            except Exception as e:
                logger.error(f"Ошибка отправки лога в чат: {e}")
    
    def _get_random_id(self) -> int:
        import random
        return random.randint(1, 2**63)