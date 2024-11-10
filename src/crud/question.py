from typing import Optional, Tuple

from sqlalchemy import null, select, true
from sqlalchemy.orm import defer

from src import db
from src.crud.base import CRUDBase
from src.models.question import Question
from src.models.user_answer import UserAnswer
from src.models.variant import Variant

# from src.models.quiz import Quiz


class CRUDQuestion(CRUDBase):

    """Круд класс для вопросов."""

    async def get_new(
        self,
        user_id: int,
        quiz_id: int,
        is_active: bool = true(),
    ) -> Optional[Question]:
        """Получить новый вопрос."""
        return (
            db.session.execute(
                select(Question)
                .options(defer(Question.image))
                .where(
                    Question.quizzes.any(id=quiz_id),
                    Question.is_active == is_active,
                    UserAnswer.id == null(),
                )
                .outerjoin(
                    UserAnswer,
                    (Question.id == UserAnswer.question_id)
                    & (UserAnswer.user_id == user_id)
                    & (UserAnswer.quiz_id == quiz_id),
                )
                .limit(1),
            )
            .scalars()
            .first()
        )

    async def get_all_by_quiz_id(
        self,
        quiz_id: int,
        is_active: bool = true(),
    ) -> list[Question]:
        """Получить все вопросы по идентификатору теста."""
        return (
            db.session.execute(
                select(Question)
                .options(defer(Question.image))
                .where(
                    Question.quizzes.any(id=quiz_id),
                    Question.is_active == is_active,
                )
                .order_by(Question.id),
            )
            .scalars()
            .all()
        )

    async def get_right_answers(self, question_id: int) -> str:
        """Получить правильные ответы по вопросу."""
        return (
            db.session.execute(
                select(Variant.title).where(
                    Variant.question_id == question_id,
                    Variant.is_right_choice == true(),
                ),
            )
            .scalars()
            .first()
        )

    async def get_statistic(self, question_id: int) -> Tuple:
        """Получить статистику по вопросу."""
        try:
            question = (
                db.session.query(Question)
                .filter(Question.id == question_id)
                .first()
            )
            if not question:
                return ('Нет данных', 0, 0, 0)

            question_text = question.title

            user_answers = (
                db.session.query(UserAnswer.is_right)
                .filter(UserAnswer.question_id == question_id)
                .all()
            )

            total_answers = len(user_answers)
            correct_answers = sum(1 for ua in user_answers if ua.is_right)

            if total_answers > 0:
                correct_percentage = round(
                    (correct_answers / total_answers) * 100.0,
                    2,
                )
            else:
                correct_percentage = 0

            return (
                question_text,
                total_answers,
                correct_answers,
                correct_percentage,
            )
        except Exception:
            db.session.rollback()
            return ('Нет данных', 0, 0, 0)

    async def get_total_questions(self) -> int:
        """Получить общее количество вопросов."""
        return db.session.query(Question).count()

    def get_questions_in_the_category(
        self,
        category_id: int,
    ) -> list[Question]:
        """Получить все вопросы в конкретной категории."""
        return Question.query.filter_by(category_id=category_id).all()


question_crud = CRUDQuestion(Question)
