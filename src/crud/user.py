from datetime import datetime
from typing import Optional

from src import db
from src.crud.base import CRUDBase
from src.models.user import User


class CRUDUser(CRUDBase):

    """Крад класс пользователя."""

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получение пользователя по логину.

        Keyword Arguments:
        -----------------
        telegram_id (int): тг ид пользователя

        """
        user = db.session.execute(
            db.select(User).where(User.telegram_id == telegram_id),
        )
        return user.scalars().first()

    async def get_total_users(self) -> int:
        """Получение общего количества пользователей."""
        return db.session.query(User).count()

    async def get_new_users_since(self, date: datetime) -> int:
        """Получение количества новых пользователей за период."""
        return (
            db.session.query(User)
            .filter(
                User.created_on >= date,
            )
            .count()
        )


user_crud = CRUDUser(User)
