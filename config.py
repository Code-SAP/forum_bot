# -*- coding: utf-8 -*-
"""Конфигурация бота"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Класс конфигурации"""
    
    # ВК
    VK_GROUP_ID = int(os.getenv('VK_GROUP_ID'))

    VK_GROUP_TOKEN = os.getenv('VK_GROUP_TOKEN')
    VK_USER_TOKEN = os.getenv('VK_USER_TOKEN')

    # Форум
    FORUM_USER_AGENT = os.getenv('FORUM_USER_AGENT')
    FORUM_COOKIES = {
        'xf_user': os.getenv('FORUM_XF_USER'),
        'xf_session': os.getenv('FORUM_XF_SESSION'),
        'xf_tfa_trust': os.getenv('FORUM_XF_TFA_TRUST')
    }

    # Главный администратор (твой ID и username ВК)
    MAIN_ADMIN_ID = int(os.getenv('MAIN_ADMIN_ID', 0))
    MAIN_ADMIN_USERNAME = os.getenv('MAIN_ADMIN_USERNAME', '')

    # Беседа для логов
    LOG_CHAT_ID = int(os.getenv('LOG_CHAT_ID', 0))

    # Беседа техов
    TECH_CHAT_ID = 2000000007

    # ID бесед для автоматического снятия ролей
    LEADER_CHAT_ID = None
    JUDGE_CHAT_ID = None
    ATTORNEY_CHAT_ID = None
    ADMIN_CHAT_ID = None

    JUDGE_FORUM_ID = 3419
    SERVER_LABEL = "Arizona №26 [Faraway]"

    # Ограничения
    MAX_NOTIFY_PER_MINUTE = 5
    MAX_THREAD_PAGES = 50

config = Config()

