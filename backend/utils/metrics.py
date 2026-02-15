"""
Модуль для сбора метрик и статистики
"""
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import func
from backend.database.database import SessionLocal
from backend.database.models import User, Project, Generation, UserState

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Сборщик метрик для бота"""
    
    @staticmethod
    def get_user_stats() -> Dict[str, Any]:
        """
        Статистика по пользователям
        
        Returns:
            Словарь со статистикой
        """
        db = SessionLocal()
        try:
            total_users = db.query(User).count()
            active_users = db.query(User).filter(User.is_active).count()
            
            # Пользователи за последние 24 часа
            yesterday = datetime.utcnow() - timedelta(days=1)
            new_users_24h = db.query(User).filter(User.created_at >= yesterday).count()
            
            # Пользователи за последние 7 дней
            week_ago = datetime.utcnow() - timedelta(days=7)
            new_users_7d = db.query(User).filter(User.created_at >= week_ago).count()
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'new_users_24h': new_users_24h,
                'new_users_7d': new_users_7d
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}
        finally:
            db.close()
    
    @staticmethod
    def get_project_stats() -> Dict[str, Any]:
        """
        Статистика по проектам
        
        Returns:
            Словарь со статистикой
        """
        db = SessionLocal()
        try:
            total_projects = db.query(Project).count()
            completed_projects = db.query(Project).filter(Project.status == 'completed').count()
            failed_projects = db.query(Project).filter(Project.status == 'failed').count()
            pending_projects = db.query(Project).filter(Project.status == 'pending').count()
            
            # Проекты за последние 24 часа
            yesterday = datetime.utcnow() - timedelta(days=1)
            projects_24h = db.query(Project).filter(Project.created_at >= yesterday).count()
            
            # Проекты за последние 7 дней
            week_ago = datetime.utcnow() - timedelta(days=7)
            projects_7d = db.query(Project).filter(Project.created_at >= week_ago).count()
            
            # Среднее время генерации
            avg_generation_time = db.query(
                func.avg(Project.generation_time)
            ).filter(
                Project.generation_time.isnot(None),
                Project.status == 'completed'
            ).scalar()
            
            avg_time = round(avg_generation_time, 2) if avg_generation_time else 0
            
            return {
                'total_projects': total_projects,
                'completed': completed_projects,
                'failed': failed_projects,
                'pending': pending_projects,
                'projects_24h': projects_24h,
                'projects_7d': projects_7d,
                'avg_generation_time_sec': avg_time,
                'success_rate': round((completed_projects / total_projects * 100), 2) if total_projects > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error getting project stats: {e}")
            return {}
        finally:
            db.close()
    
    @staticmethod
    def get_generation_stats() -> Dict[str, Any]:
        """
        Статистика по генерациям
        
        Returns:
            Словарь со статистикой
        """
        db = SessionLocal()
        try:
            total_generations = db.query(Generation).count()
            successful_generations = db.query(Generation).filter(Generation.success).count()
            failed_generations = db.query(Generation).filter(Generation.success.is_(False)).count()
            
            # Генерации за последние 24 часа
            yesterday = datetime.utcnow() - timedelta(days=1)
            generations_24h = db.query(Generation).filter(Generation.created_at >= yesterday).count()
            
            # Среднее количество токенов
            avg_tokens = db.query(
                func.avg(Generation.tokens_used)
            ).filter(
                Generation.tokens_used.isnot(None)
            ).scalar()
            
            avg_tokens_value = round(avg_tokens, 0) if avg_tokens else 0
            
            # Общее количество токенов
            total_tokens = db.query(
                func.sum(Generation.tokens_used)
            ).filter(
                Generation.tokens_used.isnot(None)
            ).scalar()
            
            total_tokens_value = int(total_tokens) if total_tokens else 0
            
            return {
                'total_generations': total_generations,
                'successful': successful_generations,
                'failed': failed_generations,
                'generations_24h': generations_24h,
                'avg_tokens': avg_tokens_value,
                'total_tokens': total_tokens_value,
                'success_rate': round((successful_generations / total_generations * 100), 2) if total_generations > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error getting generation stats: {e}")
            return {}
        finally:
            db.close()
    
    @staticmethod
    def get_all_stats() -> Dict[str, Any]:
        """
        Полная статистика системы
        
        Returns:
            Словарь со всей статистикой
        """
        return {
            'users': MetricsCollector.get_user_stats(),
            'projects': MetricsCollector.get_project_stats(),
            'generations': MetricsCollector.get_generation_stats(),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def get_user_specific_stats(user_id: int) -> Dict[str, Any]:
        """
        Статистика для конкретного пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            Словарь со статистикой пользователя
        """
        db = SessionLocal()
        try:
            user_id_str = str(user_id)
            
            # Находим пользователя
            user = db.query(User).filter(User.telegram_id == user_id_str).first()
            if not user:
                return {'error': 'User not found'}
            
            # Проекты пользователя
            user_projects = db.query(Project).filter(Project.user_id == user.id).all()
            total_projects = len(user_projects)
            completed = len([p for p in user_projects if p.status == 'completed'])
            failed = len([p for p in user_projects if p.status == 'failed'])
            
            # Генерации пользователя
            user_generations = db.query(Generation).filter(Generation.user_id == user_id_str).all()
            total_generations = len(user_generations)
            successful = len([g for g in user_generations if g.success])
            
            return {
                'user_id': user_id,
                'username': user.username or 'N/A',
                'total_projects': total_projects,
                'completed_projects': completed,
                'failed_projects': failed,
                'total_generations': total_generations,
                'successful_generations': successful,
                'success_rate': round((successful / total_generations * 100), 2) if total_generations > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {'error': str(e)}
        finally:
            db.close()

    @staticmethod
    def get_all_telegram_user_ids() -> list:
        """
        Список всех Telegram user_id для рассылки.
        Берёт из user_states и users (объединение).
        """
        db = SessionLocal()
        try:
            ids = set()
            for row in db.query(UserState.user_id).distinct().all():
                try:
                    ids.add(int(row[0]))
                except (ValueError, TypeError):
                    pass
            for row in db.query(User.telegram_id).distinct().all():
                try:
                    ids.add(int(row[0]))
                except (ValueError, TypeError):
                    pass
            return list(ids)
        except Exception as e:
            logger.error(f"Error getting telegram user ids: {e}")
            return []
        finally:
            db.close()

