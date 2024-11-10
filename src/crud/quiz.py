from typing import Optional, Tuple

from sqlalchemy import select  # , true
from sqlalchemy.orm import Query

from src import db
from src.crud.base import CRUDBase
from src.models.question import Question
from src.models.quiz import Quiz
from src.models.user_answer import UserAnswer


class CRUDQuiz(CRUDBase):

    """Круд класс викторин."""

    # async def get_by_category_id(
    #     self,
    #     category_id: int,
    #     is_active: bool = true(),
    # ) -> Query:
    #     """Получение викторин по id рубрики как запрос Query."""
    #     return db.session.query(Quiz).filter(
    #         Quiz.category_id == category_id,
    #         Quiz.is_active == is_active,
    #         Quiz.questions.any(Question.is_active == is_active),
    #     )

    def get_multi_query(self) -> Query:
        """Создать список объектов."""
        return Quiz.query

    async def get_by_id(self, quiz_id: int) -> Optional[Quiz]:
        """Получить викторину по ID."""
        return (
            db.session.execute(
                select(Quiz).where(Quiz.id == quiz_id),
            )
            .scalars()
            .first()
        )

    async def get_statistic(self, quiz_id: int) -> Tuple:
        """Получить статистику по викторине."""
        try:
            quiz = db.session.query(Quiz).filter(Quiz.id == quiz_id).first()

            if not quiz:
                return ('Нет данных', 0, 0, 0)

            # Получаем все вопросы викторины
            questions_subquery = (
                db.session.query(Question.id)
                .filter(Question.quizzes.any(id=quiz_id))
                .subquery()
            )

            total_answers = (
                db.session.query(UserAnswer)
                .filter(
                    UserAnswer.question_id.in_(questions_subquery),
                    UserAnswer.quiz_id == quiz_id,
                )
                .count()
            )

            correct_answers = (
                db.session.query(UserAnswer)
                .filter(
                    UserAnswer.question_id.in_(questions_subquery),
                    UserAnswer.quiz_id == quiz_id,
                    UserAnswer.is_right,
                )
                .count()
            )

            if total_answers > 0:
                correct_percentage = round(
                    (correct_answers / total_answers) * 100.0,
                    2,
                )
            else:
                correct_percentage = 0
            return (
                quiz.title,
                total_answers,
                correct_answers,
                correct_percentage,
            )
        except Exception:
            db.session.rollback()
            return ('Нет данных', 0, 0, 0)

    async def get_total_quizzes(self) -> int:
        """Получить общее количество викторин."""
        return Quiz.query.count()


quiz_crud = CRUDQuiz(Quiz)
