from typing import Dict, List

from sqlalchemy import case, func, select

from src import db
from src.models.category import Category
from src.models.question import Question
from src.models.quiz import Quiz
from src.models.quiz_result import QuizResult
from src.models.user_answer import UserAnswer
from src.models.variant import Variant


class CRUDExcelStatistic:

    """Класс, в котором находятся функции получения статистик."""

    async def get_user_answers_for_excel(self) -> List[Dict[str, str]]:
        """Получить отвты пользователя с названиями объектов, а не id."""
        with db.session() as session:
            results = session.execute(
                select(
                    UserAnswer.tg_user_id,
                    Category.name,
                    Quiz.title,
                    Question.title,
                    Variant.title,
                    case(
                        (Variant.is_right_choice, 'Да'),
                        else_='Нет',
                    ).label("Правильно?"),
                )
                .join(UserAnswer, UserAnswer.quiz_id == Quiz.id)
                .join(Question, UserAnswer.question_id == Question.id)
                .join(Category, Question.category_id == Category.id)
                .join(Variant, UserAnswer.answer_id == Variant.id),
            )

            return [
                {
                    'Телеграм ID': row[0],
                    'Рубрика': row[1],
                    'Викторина': row[2],
                    'Вопрос': row[3],
                    'Ответ': row[4],
                    'Правильно?': row[5],
                }
                for row in results
            ]

    async def get_categories_for_excel(self) -> List[Dict[str, str]]:
        """Получить кол-во и соотношение всех ответов по рубрикам."""
        with db.session() as session:
            results = session.execute(
                select(
                    Category.name.label("Название категории"),
                    func.count(UserAnswer.id).label("Всего ответов"),
                    func.count(
                        case((UserAnswer.is_right, UserAnswer.id)),
                    ).label("Правильных ответов"),
                    func.coalesce(
                        (func.count(case(
                            (UserAnswer.is_right, UserAnswer.id),
                        )) * 100.0) /
                        func.nullif(func.count(UserAnswer.id), 0), 0,
                    ).label("Соотношение"),
                )
                .join(Question, Question.category_id == Category.id)
                .outerjoin(UserAnswer, UserAnswer.question_id == Question.id)
                .group_by(Category.name),
            )

            return [
                {
                    'Название категории': row[0],
                    'Всего ответов': row[1],
                    'Правильных ответов': row[2],
                    'Соотношение': f'{row[3]:.2f}%',
                }
                for row in results
            ]

    async def get_quizzes_for_excel(self) -> List[Dict[str, str]]:
        """Получить кол-во и соотношение всех ответов по категориям."""
        with db.session() as session:
            results = session.execute(
                select(
                    Quiz.title.label("Название викторины"),
                    func.count(UserAnswer.id).label("Всего ответов"),
                    func.count(
                        case((UserAnswer.is_right, UserAnswer.id)),
                    ).label("Правильных ответов"),
                    func.coalesce(
                        (func.count(case(
                            (UserAnswer.is_right, UserAnswer.id),
                        )) * 100.0) /
                        func.nullif(func.count(UserAnswer.id), 0), 0,
                    ).label("Соотношение"),
                )
                .join(Quiz.questions)
                .outerjoin(UserAnswer, UserAnswer.question_id == Question.id)
                .group_by(Quiz.title),
            )

            return [
                {
                    'Название викторины': row[0],
                    'Всего ответов': row[1],
                    'Правильных ответов': row[2],
                    'Соотношение': f'{row[3]:.2f}%',
                }
                for row in results
            ]

    async def get_questions_for_excel(self) -> List[Dict[str, str]]:
        """Получить кол-во и соотношение всех ответов."""
        with db.session() as session:
            results = session.execute(
                select(
                    Question.title.label("Название вопроса"),
                    func.count(UserAnswer.id).label("Всего ответов"),
                    func.count(
                        case((UserAnswer.is_right, UserAnswer.id)),
                    ).label("Правильных ответов"),
                    func.coalesce(
                        (func.count(case(
                            (UserAnswer.is_right, UserAnswer.id),
                        )) * 100.0) /
                        func.nullif(func.count(UserAnswer.id), 0), 0,
                    ).label("Соотношение"),
                )
                .outerjoin(UserAnswer, UserAnswer.question_id == Question.id)
                .group_by(Question.title),
            )

            return [
                {
                    'Название вопроса': row[0],
                    'Всего ответов': row[1],
                    'Правильных ответов': row[2],
                    'Соотношение': f'{row[3]:.2f}%',
                }
                for row in results
            ]

    async def get_quiz_results_for_excel(self) -> List[Dict[str, str]]:
        """Получить все данные по прохождению викторин пользователем."""
        with db.session() as session:
            results = session.execute(
                select(
                    QuizResult.tg_user_id.label('Телеграм ID'),
                    Quiz.title.label('Викторина'),
                    func.count(Question.id).label('Всего вопросов'),
                    QuizResult.total_questions.label('Отвеченных вопросов'),
                    QuizResult.correct_answers_count.label(
                        'Кол-во правельных ответов',
                    ),
                )
                .join(Quiz, Quiz.id == QuizResult.quiz_id)
                .join(Quiz.questions)
                .group_by(
                    QuizResult.tg_user_id,
                    Quiz.title,
                    QuizResult.total_questions,
                    QuizResult.correct_answers_count,
                ),
            )

            return [
                {
                    'Телеграм ID': result[0],
                    'Викторина': result[1],
                    'Всего вопросов': result[2],
                    'Отвеченных вопросов': result[3],
                    'Кол-во правельных ответов': result[4],
                }
                for result in results
            ]


excel_statistic_crud = CRUDExcelStatistic()
