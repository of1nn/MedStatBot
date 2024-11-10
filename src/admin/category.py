from flask import Response, request
from flask_admin import BaseView, expose
from flask_jwt_extended import jwt_required

from src.admin.base import (
    CustomAdminView,
    IntegrityErrorMixin,
    NotVisibleMixin,
)
from src.constants import (
    DEFAULT_PAGE_NUMBER,
    ERROR_FOR_CATEGORY,
    ITEMS_PER_PAGE,
)
from src.crud.category import category_crud
from src.models.category import Category


class CategoryAdmin(IntegrityErrorMixin, CustomAdminView):

    """Добавление и перевод модели рубрик в админ зону."""

    delete_error_message = ERROR_FOR_CATEGORY

    column_labels = {
        'name': 'Название',
        'is_active': 'Активен',
    }

    # Устанавливаем размер страницы для пагинации
    page_size = ITEMS_PER_PAGE

    # Указываем, по каким колонкам можно искать
    column_searchable_list = ['name']


class CategoryListView(BaseView):

    """Создание списка рубрик для статистики."""

    @expose('/')
    @jwt_required()
    def index(self) -> Response:
        """Создание списка для статистики рубрик."""
        page = request.args.get('page', DEFAULT_PAGE_NUMBER, type=int)
        per_page = ITEMS_PER_PAGE

        search_query = request.args.get('search', '', type=str)
        query = category_crud.get_query()
        if search_query:
            query = query.filter(Category.name.ilike(f'%{search_query}%'))

        # Пагинация
        categories = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False,
        )

        category_data = [
            {
                'id': category.id,
                'name': category.name,
            }
            for category in categories.items
        ]

        # Передаем данные в шаблон
        return self.render(
            'admin/category_list.html',
            data=category_data,
            pagination=categories,
            search_query=search_query,
        )


class CategoryStatisticsView(NotVisibleMixin):

    """Представление для статистики конкретной рубрики."""

    @expose('/')
    @jwt_required()
    async def index(self) -> Response:
        """Статистика по конкретной рубрике."""
        category_id = request.args.get('category_id')

        statictic = await category_crud.get_statistic(category_id)

        (
            category_name,
            total_answers,
            correct_answers,
            correct_percentage,
        ) = statictic

        return self.render(
            'admin/category_statistics.html',
            category_name=category_name,
            total_answers=total_answers,
            correct_answers=correct_answers,
            correct_percentage=correct_percentage,
        )
