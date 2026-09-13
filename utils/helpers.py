# -*- coding: utf-8 -*-
"""Вспомогательные функции"""

import re
from typing import List, Optional


def clean_username(raw: str) -> str:
    """Очистка username для поиска"""
    if not raw:
        return ""
    
    # Убираем @, [id, | и пробелы
    cleaned = raw.strip().lstrip('@')
    cleaned = re.sub(r'\[id\d+\|', '', cleaned)
    cleaned = re.sub(r'[^a-zA-Z0-9_.-]', '', cleaned)
    
    return cleaned.lower()


def split_long_message(text: str, max_len: int = 4000) -> List[str]:
    """Разбиение длинного сообщения на части"""
    if len(text) <= max_len:
        return [text]
    
    parts = []
    while text:
        if len(text) <= max_len:
            parts.append(text)
            break
        
        # Ищем последний перенос строки в пределах лимита
        split_at = text.rfind('\n', 0, max_len)
        if split_at == -1:
            split_at = max_len
        
        parts.append(text[:split_at])
        text = text[split_at:]
    
    return parts


def format_date(timestamp: Optional[float]) -> str:
    """Форматирование даты из timestamp"""
    if not timestamp:
        return "Неизвестно"
    
    from datetime import datetime
    try:
        return datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M")
    except:
        return str(timestamp)


def truncate_text(text: str, max_len: int = 50) -> str:
    """Обрезание текста с многоточием"""
    if len(text) <= max_len:
        return text
    
    # Обрезаем по словам
    truncated = text[:max_len]
    last_space = truncated.rfind(' ')
    if last_space > max_len // 2:
        truncated = truncated[:last_space]
    
    return truncated + "..."