# users_db.py
import logging
from database.database import (
    is_user_allowed,
    is_admin,
    is_user_allowed_by_username,
    is_admin_by_username,
    add_user,
    remove_user_by_username,
    get_all_users,
    get_username_by_vk_id,
    is_judge,
    get_all_judges,
    save_role_chat,
    get_role_chat,
    get_all_role_chats,
)

logger = logging.getLogger(__name__)


#   ПРОВЕРКИ ПРАВ
def check_admin(user_id):
    """Проверяет, является ли пользователь админом."""
    return is_admin(user_id)


def check_judge(user_id):
    """Проверяет, является ли пользователь судьёй."""
    return is_judge(user_id)


#   ПРОВЕРКИ ПО USERNAME
def is_user_allowed_by_name(username):
    return is_user_allowed_by_username(username)


def is_admin_by_name(username):
    return is_admin_by_username(username)


#   УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
def add_allowed_user(vk_id, username, added_by, note=""):
    return add_user(vk_id, username, added_by, note)


def remove_allowed_user(username):
    return remove_user_by_username(username)


def list_all_users():
    return get_all_users()


def get_username(user_id):
    return get_username_by_vk_id(user_id)


#   РОЛИ (ТОЛЬКО admin + judge)
def list_all_judges():
    return get_all_judges()


#   БЕСЕДЫ РОЛЕЙ
def save_chat(role, chat_id, registered_by=None):
    return save_role_chat(role, chat_id, registered_by)


def get_chat(role):
    return get_role_chat(role)


def get_all_chats():
    return get_all_role_chats()
