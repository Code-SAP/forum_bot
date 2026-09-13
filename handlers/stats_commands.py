# -*- coding: utf-8 -*-
"""Команды статистики"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any

from config import config

logger = logging.getLogger(__name__)


class StatsCommandHandler:
    """Обработчик команд статистики"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def get_court_stats(self, peer_id: int, user_display: str, days: int = 7):
        """Получение статистики по судебным искам"""
        self.bot.send_message(peer_id, "⚙️ Загрузка статистики...")
        
        try:
            # Получаем категорию
            category = await self.bot.forum._api.get_category(config.JUDGE_FORUM_ID)
            if not category:
                self.bot.send_message(peer_id, "❌ Раздел судебных исков не найден")
                return
            
            # Собираем ID тем
            thread_ids = await self._collect_thread_ids(category, days)
            
            if not thread_ids:
                self.bot.send_message(peer_id, f"📭 За {days} дней нет исков")
                return
            
            # Получаем объекты тем по ID
            threads = await self._get_threads_by_ids(thread_ids)
            
            if not threads:
                self.bot.send_message(peer_id, "❌ Не удалось загрузить темы")
                return
            
            # Анализируем
            stats = await self._analyze_threads(threads)
            
            # Формируем отчёт
            report = self._format_report(stats, days)
            self.bot.send_message(peer_id, report)
            
            await self.bot.logger.log_action(
                "court_stats", user_display, f"Статистика за {days} дней",
                f"Тем: {stats['total']}, закрыто: {stats['closed']}",
                source_peer_id=peer_id
            )
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            self.bot.send_message(peer_id, f"❌ Ошибка: {str(e)[:100]}")
    
    async def _collect_thread_ids(self, category, days: int) -> List[int]:
        """Сбор ID тем за указанный период"""
        thread_ids = []
        min_timestamp = (datetime.now() - timedelta(days=days)).timestamp()
        
        page = 1
        max_pages = 50
        
        while page <= max_pages:
            try:
                result = await category.get_threads(page=page)
                
                if not result or not isinstance(result, dict):
                    break
                
                # Получаем ID из unpins (обычные темы)
                unpins = result.get("unpins", [])
                
                if not unpins:
                    break
                
                # Для каждого ID проверяем дату создания
                for thread_id in unpins:
                    try:
                        thread = await self.bot.forum._api.get_thread(thread_id)
                        if thread:
                            created = getattr(thread, "create_date", None)
                            if created and created >= min_timestamp:
                                thread_ids.append(thread_id)
                    except Exception as e:
                        logger.debug(f"Ошибка получения темы {thread_id}: {e}")
                        continue
                
                # Если на странице меньше 25 ID — это последняя страница
                if len(unpins) < 25:
                    break
                
                page += 1
                
            except Exception as e:
                logger.error(f"Ошибка на странице {page}: {e}")
                break
        
        logger.info(f"Собрано {len(thread_ids)} ID тем за {days} дней")
        return thread_ids
    
    async def _get_threads_by_ids(self, thread_ids: List[int]) -> List:
        """Получение объектов тем по ID (с ограничением параллельности)"""
        threads = []
        semaphore = asyncio.Semaphore(5)  # Ограничиваем количество параллельных запросов
        
        async def fetch_thread(thread_id: int):
            async with semaphore:
                try:
                    return await self.bot.forum._api.get_thread(thread_id)
                except Exception as e:
                    logger.debug(f"Ошибка загрузки темы {thread_id}: {e}")
                    return None
        
        # Загружаем все темы параллельно
        results = await asyncio.gather(*[fetch_thread(tid) for tid in thread_ids])
        
        # Фильтруем None
        threads = [t for t in results if t is not None]
        
        logger.info(f"Загружено {len(threads)} объектов тем")
        return threads
    
    async def _analyze_threads(self, threads: List) -> Dict[str, Any]:
        """Анализ тем"""
        total = len(threads)
        closed = 0
        opened = 0
        
        # Статистика по закрывающим
        closers: Dict[str, int] = {}
        
        for thread in threads:
            is_closed = getattr(thread, "is_closed", False)
            
            if is_closed:
                closed += 1
                
                # Пытаемся получить имя закрывшего (последний автор)
                closer = "Неизвестно"
                try:
                    # Получаем ID последнего поста
                    post_ids = await thread.get_posts()
                    if post_ids and len(post_ids) > 0:
                        last_post_id = post_ids[-1]
                        last_post = await self.bot.forum._api.get_post(last_post_id)
                        if last_post and hasattr(last_post, "creator"):
                            creator = last_post.creator
                            if creator and hasattr(creator, "username"):
                                closer = creator.username
                except Exception as e:
                    logger.debug(f"Не удалось получить автора последнего поста: {e}")
                
                closers[closer] = closers.get(closer, 0) + 1
            else:
                opened += 1
        
        return {
            "total": total,
            "closed": closed,
            "opened": opened,
            "closers": closers,
        }
    
    def _format_report(self, stats: Dict[str, Any], days: int) -> str:
        """Форматирование отчёта"""
        if stats["total"] == 0:
            return f"📭 За {days} дней нет исков"
        
        text = (
            f"🔱 Статистика за {days} дней | {config.SERVER_LABEL} 🔱\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📩 Всего исков: {stats['total']}\n"
            f"🔓 Открыто: {stats['opened']}\n"
            f"🔐 Закрыто: {stats['closed']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        if stats["closed"] > 0 and stats["closers"]:
            text += "\nКто закрывал иски:\n"
            sorted_closers = sorted(stats["closers"].items(), key=lambda x: x[1], reverse=True)
            
            num_emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
            for i, (name, count) in enumerate(sorted_closers[:10], 1):
                percentage = count / stats["closed"] * 100
                emoji = num_emoji[i-1] if i <= 9 else f"{i}."
                word = self._pluralize(count, "иск", "иска", "исков")
                text += f"{emoji} {name} — {count} {word} (~{percentage:.0f}%)\n"
        
        return text
    
    def _pluralize(self, n: int, one: str, few: str, many: str) -> str:
        """Склонение слов"""
        n = abs(n) % 100
        if 11 <= n <= 19:
            return many
        last_digit = n % 10
        if last_digit == 1:
            return one
        if 2 <= last_digit <= 4:
            return few
        return many