from src import db
from src.models.base import BaseModel, IsActiveMixin
from src.models.quiz_question import quiz_questions


class Quiz(BaseModel, IsActiveMixin):

    """Модель викторины.

    Содержит основную информацию о викторине, такую как название и рубрика.

    """

    __tablename__ = 'quizzes'

    title = db.Column(
        db.String(30),
        nullable=False,
        comment='Название викторины.',
        unique=True,
    )

    questions = db.relationship(
        'Question',
        secondary=quiz_questions,
        back_populates='quizzes',
        lazy='subquery',
    )

    # Связь с таблицей результатов викторины
    results = db.relationship(
        'QuizResult',
        backref='quiz',
    )

    def __str__(self) -> str:
        """Отображение названия объекта в админ зоне."""
        return self.title
