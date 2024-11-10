from datetime import datetime
from typing import Optional

from sqlalchemy import distinct, func, null, select, true

from src import db
from src.crud.base import CRUDBase
from src.models.quiz_result import QuizResult
from src.models.telegram_user import TelegramUser


class CRUDTelegramUser(CRUDBase):

    """Класс для работы с моделью TelegramUser через CRUD."""

    async def get_by_telegram_id(
        self,
        telegram_id: int,
    ) -> Optional[TelegramUser]:
        """Получение пользователя по telegram_id."""
        return (
            db.session.execute(
                db.select(TelegramUser).where(
                    TelegramUser.telegram_id == telegram_id,
                ),
            )
            .scalars()
            .first()
        )

    async def exists_by_telegram_id(self, telegram_id: int) -> bool:
        """Проверка существования пользователя по telegram_id."""
        return db.session.query(
            db.exists().where(TelegramUser.telegram_id == telegram_id),
        ).scalar()

    async def get_total_users_played_quiz(self) -> int:
        """Получение общего количества пользователей, игравших в викторину."""
        query = (
            select(func.count(distinct(TelegramUser.id)))
            .select_from(TelegramUser)
            .join(QuizResult, TelegramUser.id == QuizResult.tg_user_id)
            .where(QuizResult.id != null())
            # Assuming None is used to represent null in your models
        )
        return db.session.execute(query).scalar()

    async def get_total_users_completed_quiz(self) -> int:
        """Получение общего количества пользователей.

        прошедших хотя бы одну викторину до конца.
        """
        query = (
            select(func.count(distinct(TelegramUser.id)))
            .select_from(TelegramUser)
            .outerjoin(QuizResult, TelegramUser.id == QuizResult.tg_user_id)
            .where(QuizResult.id != null(), QuizResult.is_complete == true())
            # Assuming None is used to represent null in your models
        )
        return db.session.execute(query).scalar()

    async def get_users_played_quiz_since(self, date: datetime) -> int:
        """Получение количества пользователей.

        игравших в викторину с указанной даты.
        """
        query = (
            select(func.count(distinct(TelegramUser.id)))
            .select_from(TelegramUser)
            .outerjoin(QuizResult, TelegramUser.id == QuizResult.tg_user_id)
            .where(
                QuizResult.id != null(),
                TelegramUser.created_on >= date,
            )
        )
        # Assuming None is used to represent null in your models
        return db.session.execute(query).scalar()

    async def get_users_completed_quiz_since(self, date: datetime) -> int:
        """Получение количества пользователей.

        прошедших викторину до конца с указанной даты.
        """
        query = (
            select(func.count(distinct(TelegramUser.id)))
            .select_from(TelegramUser)
            .outerjoin(QuizResult, TelegramUser.id == QuizResult.tg_user_id)
            .where(
                QuizResult.id != null(),
                QuizResult.is_complete == true(),
                TelegramUser.created_on >= date,
            )
        )
        # Assuming None is used to represent null in your models
        return db.session.execute(query).scalar()


telegram_user_crud = CRUDTelegramUser(TelegramUser)
