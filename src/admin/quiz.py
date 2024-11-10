from typing import Any

from flask import (
    Response,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_admin import BaseView, expose
from flask_admin.model.template import LinkRowAction
from flask_jwt_extended import jwt_required
from markupsafe import Markup
from wtforms import ValidationError
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField

from src import app
from src.admin.base import (
    CustomAdminView,
    IntegrityErrorMixin,
    NotVisibleMixin,
)
from src.constants import (
    AT_LEAST_ONE_QUESTION,
    DEFAULT_PAGE_NUMBER,
    ERROR_FOR_QUIZ,
    ITEMS_PER_PAGE,
)
from src.crud.question import question_crud
from src.crud.quiz import quiz_crud
from src.models.category import Category
from src.models.question import Question
from src.models.quiz import Quiz


class GroupedListWidget(object):

    """Кастомный виджет для отображения вопросов по рубрикам."""

    def __call__(self, field: Any, **kwargs: Any) -> Markup:
        """Срабатывает при вызове класса."""
        categories = Category.query.filter(Category.is_active).all()

        selected_questions = [
            {'id': q.id, 'title': q.title} for q in field.data
        ]

        return Markup(
            render_template(
                'admin/questions_widget.html',
                categories=categories,
                field_name=field.name,
                selected_questions=selected_questions,
            ),
        )


@app.route('/get_questions')
def get_questions() -> Response:
    """Функция для получения вопросов в конкретной категории."""
    category_id = request.args.get('category_id')
    questions = question_crud.get_questions_in_the_category(category_id)
    return jsonify([{'id': q.id, 'title': q.title} for q in questions])


class GroupedQuerySelectMultipleField(QuerySelectMultipleField):

    """Класс для создания формы выбора вопросов при создании викторины."""

    def __init__(
        self,
        label: Any = '',
        validators: Any = None,
        **kwargs: Any,
    ) -> None:
        """Пререопределяем инит класса для использования своего виджета."""
        super().__init__(label, validators, **kwargs)
        self.widget = GroupedListWidget()  # Используем наш кастомный виджет
        self.query_factory = lambda: Question.query.all()


class QuizAdmin(IntegrityErrorMixin, CustomAdminView):

    """Добавление и перевод модели викторин в админ зону."""

    delete_error_message = ERROR_FOR_QUIZ
    # Пагинация
    page_size = ITEMS_PER_PAGE

    # Поиск по полю title
    column_searchable_list = ['title']
    # Отображаемые поля в списке записей
    column_list = ['title', 'is_active']
    # Отображаемые поля в форме создания и редактирования
    form_columns = ['title', 'questions', 'is_active']

    column_labels = {
        'id': 'ID',
        'title': 'Название',
        'questions': 'Вопросы',
        'is_active': 'Активен',
    }

    form_extra_fields = {
        'questions': GroupedQuerySelectMultipleField(
            'Вопросы',
        ),
    }

    column_extra_row_actions = [
        LinkRowAction(
            'fa fa-play',
            url='test_question/{row_id}/',
            title='Пробное прохождение',
        ),
    ]

    @expose('/test_question/<int:quiz_id>/')
    def test_quiz_view(self, quiz_id: int) -> Response:
        """Перенаправление на страницу тестирования."""
        quiz = Quiz.query.get(quiz_id)
        if not quiz:
            abort('Викторина не найдена', 404)

        return redirect(
            url_for(
                'question',
                quiz_id=quiz_id,
                test=True,
            ),
        )

    def on_model_change(self, form: Any, model: Any, is_created: bool) -> None:
        """Проверка на выбор хотя бы одного вопроса для викторины."""
        if not model.questions:
            raise ValidationError(AT_LEAST_ONE_QUESTION)


class QuizListView(BaseView):

    """Создание списка викторин для статистики."""

    @expose('/')
    @jwt_required()
    def index(self) -> Response:
        """Создание списка для статистики викторин."""
        page = request.args.get('page', DEFAULT_PAGE_NUMBER, type=int)
        per_page = ITEMS_PER_PAGE

        search_query = request.args.get('search', '', type=str)
        query = Quiz.query
        if search_query:
            query = query.filter(Quiz.title.ilike(f'%{search_query}%'))

        # Пагинация
        quizzes = query.paginate(page=page, per_page=per_page, error_out=False)

        quiz_data = [
            {
                'id': quiz.id,
                'title': quiz.title,
            }
            for quiz in quizzes.items
        ]

        # Передаем данные в шаблон
        return self.render(
            'admin/quiz_list.html',
            data=quiz_data,
            pagination=quizzes,
            search_query=search_query,
        )


class QuizStatisticsView(NotVisibleMixin):

    """Представление для статистики конкретной викторины."""

    # Статистика по конкретному вопросу
    @expose('/')
    @jwt_required()
    async def index(self) -> Response:
        """Выполняем запрос статистики для конкретной викторины."""
        quiz_id = request.args.get('quiz_id')

        statictic = await quiz_crud.get_statistic(quiz_id)

        (
            quiz_title,
            total_answers,
            correct_answers,
            correct_percentage,
        ) = statictic

        return self.render(
            'admin/quiz_statistics.html',
            quiz_title=quiz_title,
            total_answers=total_answers,
            correct_answers=correct_answers,
            correct_percentage=correct_percentage,
        )
