import asyncio
import time
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, List

import pandas as pd
import requests
from flask import Response, jsonify, redirect, request, url_for
from flask_admin import BaseView, expose
from flask_jwt_extended import (
    current_user,
    jwt_required,
    verify_jwt_in_request,
)
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.worksheet import Worksheet

from src.bot import bot
from src.crud.category import category_crud
from src.crud.excel_statistic import excel_statistic_crud
from src.crud.question import question_crud
from src.crud.quiz import quiz_crud
from src.crud.quiz_result import quiz_result_crud
from src.crud.telegram_user import telegram_user_crud
from src.crud.user import user_crud
from src.crud.user_answer import user_answer_crud
from src.models.user import User


class OverAllStatisticsView(BaseView):

    """Обобщенная статистика."""

    @expose('/')
    @jwt_required()
    async def index(self) -> Response:
        """Обобщенная статистика."""
        verify_jwt_in_request()
        if not current_user.is_admin:
            return redirect(url_for('categories'))

        now = datetime.utcnow()
        last_day = now - timedelta(days=1)
        last_week = now - timedelta(weeks=1)
        last_month = now - timedelta(days=30)
        today_start = datetime(now.year, now.month, now.day)

        total_users = await user_crud.get_total_users()
        total_users_played_quiz = (
            await telegram_user_crud.get_total_users_played_quiz()
        )
        total_users_completed_quiz = (
            await telegram_user_crud.get_total_users_completed_quiz()
        )

        new_users_last_day = await user_crud.get_new_users_since(last_day)
        new_users_last_week = await user_crud.get_new_users_since(last_week)
        new_users_last_month = await user_crud.get_new_users_since(last_month)
        users_created_today = await user_crud.get_new_users_since(today_start)

        users_played_quiz_last_day = (
            await telegram_user_crud.get_users_played_quiz_since(last_day)
        )
        users_played_quiz_last_week = (
            await telegram_user_crud.get_users_played_quiz_since(last_week)
        )
        users_played_quiz_last_month = (
            await telegram_user_crud.get_users_played_quiz_since(last_month)
        )

        users_completed_quiz_last_day = (
            await telegram_user_crud.get_users_completed_quiz_since(last_day)
        )
        users_completed_quiz_last_week = (
            await telegram_user_crud.get_users_completed_quiz_since(last_week)
        )
        users_completed_quiz_last_month = (
            await telegram_user_crud.get_users_completed_quiz_since(last_month)
        )

        total_completed_quizzes = (
            await quiz_result_crud.get_total_completed_quizzes()
        )
        total_questions_answered = await user_answer_crud.get_total_answers()
        total_questions = await question_crud.get_total_questions()
        total_quizzes = await quiz_crud.get_total_quizzes()
        total_categories = await category_crud.get_total_categories()

        context = {
            'total_users': total_users,
            'total_users_played_quiz': total_users_played_quiz,
            'total_users_completed_quiz': total_users_completed_quiz,
            'new_users_last_day': new_users_last_day,
            'new_users_last_week': new_users_last_week,
            'new_users_last_month': new_users_last_month,
            'users_played_quiz_last_day': users_played_quiz_last_day,
            'users_played_quiz_last_week': users_played_quiz_last_week,
            'users_played_quiz_last_month': users_played_quiz_last_month,
            'users_completed_quiz_last_day': users_completed_quiz_last_day,
            'users_completed_quiz_last_week': users_completed_quiz_last_week,
            'users_completed_quiz_last_month': users_completed_quiz_last_month,
            'users_created_today': users_created_today,
            'total_completed_quizzes': total_completed_quizzes,
            'total_questions_answered': total_questions_answered,
            'total_questions': total_questions,
            'total_quizzes': total_quizzes,
            'total_categories': total_categories,
        }

        return self.render('admin/statistics.html', **context)

    @expose('/export', methods=['POST'])
    # @jwt_required()
    def export(self) -> Response:
        """Экспорт обобщенной статистики в Excel."""

        def run_async(coro: Any) -> asyncio.Future:
            """Запускаем асинхронную функцию и получаем результат."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

        # Run async functions synchronously
        users = run_async(telegram_user_crud.get_multi())

        start_time = time.time()
        # Сбор данных
        df_user_statistics = run_async(collect_user_statistics(users))
        df_answers = run_async(collect_answers_data())
        df_quiz_results = run_async(collect_quiz_results_data())
        df_category_statistics = run_async(collect_category_statistics())
        df_quiz_statistics = run_async(collect_quiz_statistics())
        df_question_statistics = run_async(collect_question_statistics())
        print(f'Сбор данных занял: {time.time() - start_time}')

        start_time = time.time()
        # Создание Excel файла
        excel_file = run_async(
            save_to_excel(
                df_user_statistics,
                df_answers,
                df_quiz_results,
                df_category_statistics,
                df_quiz_statistics,
                df_question_statistics,
            ),
        )
        print(f'Создание excel файла заняло: {time.time() - start_time}')

        # Получаем chat_id из запроса
        data = request.get_json()
        chat_id = data.get('chat_id')

        start_time = time.time()
        # Отправка сообщения и файла в Telegram
        run_async(send_telegram_message_and_file(chat_id, excel_file))
        print(f'Отправка файла заняла: {time.time() - start_time}')

        return jsonify({'message': 'Сообщение и файл успешно отправлены.'})


async def collect_user_statistics(users: List[User]) -> pd.DataFrame:
    """Статистика пользователей."""
    user_data = []
    for user in users:
        quizzes_results = user.quizzes_results
        total_quizzes = len(quizzes_results)
        total_answers = sum(
            result.total_questions for result in quizzes_results
        )
        correct_answers = sum(
            result.correct_answers_count for result in quizzes_results
        )
        ratio = (
            (correct_answers / total_answers * 100) if total_answers > 0 else 0
        )

        user_data.append(
            {
                'Имя пользователя': user.name.replace('None ', ''),
                'Телеграм ID': user.telegram_id,
                'Создан': user.created_on,
                'Кол-во запущенных викторин': total_quizzes,
                'Всего ответов': total_answers,
                'Правильных ответов': correct_answers,
                'Соотношение': f'{ratio:.2f}%',
            },
        )
    return pd.DataFrame(user_data)


async def collect_answers_data() -> pd.DataFrame:
    """Данные о ответах пользователей."""
    answers_data = await excel_statistic_crud.get_user_answers_for_excel()
    return pd.DataFrame(answers_data)


async def collect_quiz_results_data() -> pd.DataFrame:
    """Данные о результатах викторин."""
    quiz_results_data = await excel_statistic_crud.get_quiz_results_for_excel()
    return pd.DataFrame(quiz_results_data)


async def collect_category_statistics() -> pd.DataFrame:
    """Собирает статистику по категориям."""
    category_statistic = await excel_statistic_crud.get_categories_for_excel()
    return pd.DataFrame(category_statistic)


async def collect_quiz_statistics() -> pd.DataFrame:
    """Собирает статистику по викторинам."""
    category_quiz = await excel_statistic_crud.get_quizzes_for_excel()
    return pd.DataFrame(category_quiz)


async def collect_question_statistics() -> pd.DataFrame:
    """Собирает статистику по вопросам."""
    question_quiz = await excel_statistic_crud.get_questions_for_excel()
    return pd.DataFrame(question_quiz)


async def save_to_excel(
    df_user_statistics: pd.DataFrame,
    df_answers: pd.DataFrame,
    df_quiz_results: pd.DataFrame,
    df_category_statistics: pd.DataFrame,
    df_quiz_statistics: pd.DataFrame,
    df_question_statistics: pd.DataFrame,
) -> BytesIO:
    """Сохраняет данные в Excel файл."""
    excel_file = BytesIO()
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        # Устанавливаем начальный столбец для первого DataFrame
        start_col = 0

        if not df_user_statistics.empty:
            df_user_statistics.to_excel(
                writer,
                sheet_name='Статистика пользователей',
                index=False,
            )
            await format_excel_columns(
                writer.sheets['Статистика пользователей'],
            )

        if not df_answers.empty:
            df_answers.to_excel(
                writer,
                sheet_name='Ответы на вопросы',
                index=False,
            )
            await format_excel_columns(writer.sheets['Ответы на вопросы'])

        if not df_quiz_results.empty:
            df_quiz_results.to_excel(
                writer,
                sheet_name='Результаты всех викторин',
                index=False,
            )
            await format_excel_columns(
                writer.sheets['Результаты всех викторин'],
            )

        # Цикл по каждому DataFrame
        for df in [
            df_category_statistics, df_quiz_statistics, df_question_statistics,
        ]:
            if not df.empty:
                # Записываем DataFrame в указанный начальный столбец
                df.to_excel(
                    writer,
                    sheet_name='Обобщенная статистика',
                    startcol=start_col,
                    index=False,
                )
                # Увеличиваем start_col для следующего DataFrame
                # (+1 для пустого столбца)
                start_col += len(df.columns) + 1

        # Форматируем столбцы с использованием вашей функции
        worksheet = writer.sheets['Обобщенная статистика']
        await format_excel_columns(worksheet)

    excel_file.seek(0)  # Возврат к началу файла для чтения
    return excel_file


async def send_telegram_message_and_file(chat_id: int, file: BytesIO) -> None:
    """Отправляет сообщение и файл пользователю через Telegram API."""
    message = 'Экспорт завершен. Вот ваши данные.'

    response_message = requests.post(
        f'https://api.telegram.org/bot{bot.token}/sendMessage',
        data={'chat_id': chat_id, 'text': message},
    )

    if response_message.status_code != 200:
        raise Exception('Не удалось отправить сообщение в бот')

    current_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M')
    response_file = requests.post(
        f'https://api.telegram.org/bot{bot.token}/sendDocument',
        data={'chat_id': chat_id},
        files={'document': (f'{current_datetime} exported_data.xlsx', file)},
    )

    if response_file.status_code != 200:
        raise Exception('Не удалось отправить файл в бот')


async def format_excel_columns(worksheet: Worksheet) -> None:
    """Форматирование столбцов в Excel файле."""
    for column in worksheet.columns:
        max_length = 0
        column_letter = column[0].column_letter

        # Установка стилей для заголовков
        if column[0].value is not None:
            column[0].font = Font(bold=True, color='000000', name='Calibri')
            column[0].fill = PatternFill(
                start_color='808080',
                end_color='808080',
                fill_type='solid',
            )
            column[0].alignment = Alignment(horizontal='center')
            column[0].border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin'),
            )

        for cell in column:
            if cell.value is not None:
                cell_length = len(str(cell.value))
                if cell_length > max_length:
                    max_length = cell_length

                # Установка выравнивания по центру для данных
                cell.alignment = Alignment(horizontal='center')

        adjusted_width = max_length + 2
        worksheet.column_dimensions[column_letter].width = adjusted_width

        # Добавление фильтра для каждого столбца
        worksheet.auto_filter.ref = worksheet.dimensions
