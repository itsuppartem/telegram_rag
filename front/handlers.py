import asyncio
import os
import uuid

from aiogram import F, Router, types
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, BotCommand, BotCommandScopeDefault, FSInputFile, ReplyKeyboardRemove
from aiogram.utils.markdown import hbold, hcode

from config import ADMIN_IDS, logger
from filters import IsAdmin
from keyboards import confirm_delete_keyboard
from states import UploadStates
from utils import get_fastapi_client

router = Router()


async def set_commands(bot):
    user_commands = [BotCommand(command="/start", description="Начать взаимодействие с ботом"),
        BotCommand(command="/help", description="Показать сообщение помощи"),
        BotCommand(command="/clear", description="Очистить историю чата"), ]
    admin_commands = user_commands + [BotCommand(command="/upload", description="Загрузить документ в базу знаний"),
        BotCommand(command="/list_docs", description="Список документов в базе знаний"),
        BotCommand(command="/delete_doc", description="Удалить документ (используйте ID или имя файла)"), ]

    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    if ADMIN_IDS:
        for admin_id in ADMIN_IDS:
            try:
                await bot.set_my_commands(admin_commands, scope={"type": "chat", "chat_id": admin_id})
                logger.info(f"Установлены команды администратора для пользователя {admin_id}")
            except Exception as e:
                logger.error(f"Ошибка установки команд для администратора {admin_id}: {e}")


@router.message(CommandStart())
async def handle_start(message: Message):
    logger.info(f"Пользователь {message.from_user.id} запустил бота.")
    await message.answer(f"Привет, {hbold(message.from_user.full_name)}!\n"
                         "Я ваш AI-ассистент в компании 'Company Name'.\n"
                         "Задавайте мне вопросы.\n\n"
                         "Используйте /help для просмотра доступных команд.")


@router.message(Command("help"))
async def handle_help(message: Message):
    user_help_text = ("Доступные команды:\n"
                      "/start - Перезапустить бота\n"
                      "/help - Показать это сообщение помощи\n"
                      "/clear - Удалить все ваши предыдущие сообщения из моей памяти")
    admin_help_text = user_help_text + ("\n\n"
                                        f"{hbold('Команды администратора:')}\n"
                                        "/upload - Начать процесс загрузки нового документа (txt, pdf, docx)\n"
                                        "/list_docs - Показать текущие активные документы в базе знаний\n"
                                        "/delete_doc [ID или Имя файла] - Удалить документ и его данные")

    if message.from_user.id in ADMIN_IDS:
        await message.answer(admin_help_text)
    else:
        await message.answer(user_help_text)


@router.message(Command("clear"))
async def handle_clear_history(message: Message):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} запросил очистку истории.")
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    async with get_fastapi_client() as client:
        try:
            response = await client.delete(f"/history/{user_id}")
            response.raise_for_status()
            result = response.json()
            await message.answer(result["message"])
        except Exception as e:
            logger.error(f"Ошибка очистки истории: {e}")
            await message.answer("Произошла ошибка при очистке истории. Пожалуйста, попробуйте позже.")


@router.message(Command("upload"), IsAdmin())
async def handle_upload_start(message: Message, state: FSMContext):
    logger.info(f"Администратор {message.from_user.id} инициировал загрузку.")
    await state.set_state(UploadStates.waiting_for_file)
    await message.answer(
        "Хорошо, администратор! Пожалуйста, отправьте мне документ (txt, pdf или docx), который вы хотите добавить в базу знаний.\n"
        "Отправьте /cancel для отмены.")


@router.message(Command("cancel"), F.state == UploadStates.waiting_for_file)
async def handle_upload_cancel(message: Message, state: FSMContext):
    logger.info(f"Администратор {message.from_user.id} отменил загрузку.")
    await state.clear()
    await message.answer("Загрузка отменена.", reply_markup=ReplyKeyboardRemove())


@router.message(UploadStates.waiting_for_file, F.document, IsAdmin())
async def handle_document_upload(message: Message, state: FSMContext):
    user_id = message.from_user.id
    document = message.document
    original_filename = document.file_name
    file_id = document.file_id
    logger.info(f"Администратор {user_id} загрузил документ: {original_filename} (File ID: {file_id})")

    if not original_filename.lower().endswith(('.txt', '.pdf', '.docx')):
        await message.answer(
            f"Тип файла не разрешен: {original_filename}. Пожалуйста, отправьте файл txt, pdf или docx, или /cancel.")
        return

    processing_msg = await message.answer(f"Получен файл '{original_filename}'. Обработка, пожалуйста подождите...")
    await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_DOCUMENT)

    try:
        file_info = await message.bot.get_file(file_id)
        file_path = f"uploads_telegram/{original_filename}"
        os.makedirs("uploads_telegram", exist_ok=True)
        await message.bot.download_file(file_info.file_path, file_path)

        await processing_msg.edit_text(
            f"✅ Файл '{hbold(original_filename)}' принят и поставлен в очередь на обработку.\nОбработка может занять до 20 минут.")

        async with get_fastapi_client() as client:
            with open(file_path, "rb") as f:
                files = {"file": (original_filename, f, "application/octet-stream")}
                await client.post("/upload", files=files, timeout=2400)
    except Exception as e:
        logger.error(f"Ошибка загрузки файла: {e}")
        await processing_msg.edit_text("Произошла ошибка при загрузке файла. Пожалуйста, попробуйте позже.")
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                logger.error(f"Ошибка удаления временного файла: {e}")
        await state.clear()


@router.message(Command("list_docs"), IsAdmin())
async def handle_list_docs(message: Message):
    user_id = message.from_user.id
    logger.info(f"Администратор {user_id} запросил список документов.")
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    async with get_fastapi_client() as client:
        try:
            response = await client.get("/documents")
            response.raise_for_status()
            result = response.json()
            documents = result["documents"]

            if not documents:
                await message.answer("База знаний пуста или не найдено активных документов.")
                return

            response_text = f"{hbold('Активные документы в базе знаний:')}\n\n"
            for doc in documents:
                response_text += (f"📄 {hbold(doc['filename'])}\n"
                                  f"   - ID: {hcode(doc['_id'])}\n"
                                  f"   - Загружен: {doc.get('upload_time_str', 'N/A')}\n"
                                  f"   - Фрагментов: {doc.get('chunk_count', 'N/A')}\n\n")

            if len(response_text) > 4000:
                await message.answer("Найдено много документов. Отправляю список частями...")
                for i in range(0, len(response_text), 4000):
                    await message.answer(response_text[i:i + 4000])
                    await asyncio.sleep(0.5)
            else:
                await message.answer(response_text)

        except Exception as e:
            logger.error(f"Ошибка получения списка документов: {e}")
            await message.answer("Произошла ошибка при получении списка документов. Пожалуйста, попробуйте позже.")


@router.message(Command("delete_doc"), IsAdmin())
async def handle_delete_doc_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    command_parts = message.text.split(maxsplit=1)

    if len(command_parts) < 2:
        await message.answer("Пожалуйста, укажите ID документа или имя файла для удаления.\n"
                             f"Пример: {hcode('/delete_doc my_document.pdf')} или {hcode('/delete_doc <document_id>')}\n"
                             "Используйте /list_docs для просмотра доступных документов и их ID.")
        return

    doc_id_or_filename = command_parts[1].strip()
    logger.info(f"Администратор {user_id} запросил удаление: {doc_id_or_filename}")

    await message.answer(
        f"Вы уверены, что хотите навсегда удалить документ '{hbold(doc_id_or_filename)}' и все связанные с ним данные из базы знаний?",
        reply_markup=confirm_delete_keyboard(doc_id_or_filename))


@router.callback_query(F.data.startswith("confirm_delete:"))
async def handle_confirm_delete(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    if user_id not in ADMIN_IDS:
        await callback_query.answer("Вы не авторизованы для этого действия.", show_alert=True)
        return

    doc_id_or_filename = callback_query.data.split(":", 1)[1]
    logger.info(f"Администратор {user_id} подтвердил удаление: {doc_id_or_filename}")

    await callback_query.message.edit_text(f"Удаление '{doc_id_or_filename}'...")
    await callback_query.bot.send_chat_action(callback_query.message.chat.id, ChatAction.TYPING)

    async with get_fastapi_client() as client:
        try:
            response = await client.delete(f"/documents/{doc_id_or_filename}")
            response.raise_for_status()
            result = response.json()

            if result["success"]:
                await callback_query.message.edit_text(f"✅ {result['message']}")
            else:
                await callback_query.message.edit_text(f"❌ {result['message']}")

        except Exception as e:
            logger.error(f"Ошибка удаления документа: {e}")
            await callback_query.message.edit_text(
                f"❌ Произошла ошибка при удалении документа. Пожалуйста, попробуйте позже.")

    await callback_query.answer()


@router.callback_query(F.data == "cancel_delete")
async def handle_cancel_delete(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} отменил удаление.")
    await callback_query.message.edit_text("Удаление отменено.")
    await callback_query.answer()


@router.message(Command("upload", "list_docs", "delete_doc"))
async def handle_admin_command_unauthorized(message: Message):
    logger.warning(
        f"Неавторизованная попытка использования команды администратора пользователем {message.from_user.id}: {message.text}")
    await message.answer("Извините, вы не авторизованы для использования этой команды.")


@router.message(F.text & ~F.text.startswith('/'))
async def handle_text_message(message: Message):
    user_id = message.from_user.id
    question = message.text
    logger.info(f"Получен вопрос от пользователя {user_id}: '{question[:100]}...'")

    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    processing_msg = await message.reply("Обработка вашего вопроса, пожалуйста подождите...")

    try:
        async with get_fastapi_client() as client:
            response = await client.post("/ask", json={"user_id": user_id, "question": question}, timeout=250.0)
            response.raise_for_status()
            result = response.json()

            answer = result["answer"]
            metrics = result["metrics"]

            logger.info(f"Получены метрики: {metrics}")

            if len(answer) > 4000:
                await processing_msg.edit_text("Ответ довольно длинный, отправляю его частями...")
                for i in range(0, len(answer), 4000):
                    await message.answer(answer[i:i + 4000])
                    await asyncio.sleep(0.5)
            else:
                await processing_msg.edit_text(answer)

            metrics_text = (f"📊 Метрики ответа:\n"
                            f"• Источник: {metrics.get('prompt_source', 'N/A')}\n"
                            f"• Категория: {metrics.get('classified_category', 'N/A')}\n"
                            f"• Использовано фрагментов: {metrics.get('rag_metrics', {}).get('used_chunks', 'N/A')}\n"
                            f"• Средний скор релевантности: {float(metrics.get('rag_metrics', {}).get('average_relevance_score', 0)):.3f}\n"
                            f"• Время генерации: {float(metrics.get('rag_metrics', {}).get('generation_time', 0)):.1f}с\n"
                            f"• Токены контекста: {metrics.get('rag_metrics', {}).get('context_tokens', 'N/A')}\n"
                            f"• Токены ответа: {metrics.get('rag_metrics', {}).get('answer_tokens', 'N/A')}\n"
                            f"• Фильтры Qdrant: {', '.join(metrics.get('rag_metrics', {}).get('qdrant_filters', ['Нет']))}")
            await message.answer(metrics_text)

            os.makedirs("temp_metrics", exist_ok=True)
            metrics_file = f"temp_metrics/rag_metrics_{user_id}_{uuid.uuid4()}.txt"
            try:
                with open(metrics_file, "w", encoding="utf-8") as f:
                    f.write(f"=== RAG Metrics for User ID: {user_id} ===\n")
                    f.write(f"Question: {question}\n")
                    f.write(f"Answer: {answer}\n\n")
                    f.write("=== Metrics ===\n")
                    f.write(f"Prompt Source: {metrics.get('prompt_source', 'N/A')}\n")
                    f.write(f"Category: {metrics.get('classified_category', 'N/A')}\n")
                    f.write(f"Used Chunks: {metrics.get('rag_metrics', {}).get('used_chunks', 'N/A')}\n")
                    f.write(
                        f"Average Relevance Score: {metrics.get('rag_metrics', {}).get('average_relevance_score', 0):.3f}\n")
                    f.write(f"Generation Time: {metrics.get('rag_metrics', {}).get('generation_time', 0):.1f}s\n")
                    f.write(f"Context Tokens: {metrics.get('rag_metrics', {}).get('context_tokens', 'N/A')}\n")
                    f.write(f"Answer Tokens: {metrics.get('rag_metrics', {}).get('answer_tokens', 'N/A')}\n")
                    f.write(
                        f"Qdrant Filters: {', '.join(metrics.get('rag_metrics', {}).get('qdrant_filters', ['None']))}\n\n")
                    f.write("=== Context Chunks ===\n")
                    for i, chunk in enumerate(metrics.get('rag_metrics', {}).get('context_chunks', [])):
                        f.write(f"\n--- Chunk {i + 1} ---\n")
                        f.write(f"{chunk}\n")

                await message.answer_document(document=FSInputFile(metrics_file),
                    caption="Подробные метрики и использованные фрагменты")
            except Exception as e:
                logger.error(f"Ошибка создания или отправки файла метрик: {e}")
                await message.answer("Произошла ошибка при создании файла с метриками.")
            finally:
                try:
                    if os.path.exists(metrics_file):
                        os.remove(metrics_file)
                except Exception as e:
                    logger.error(f"Ошибка удаления файла метрик: {e}")

    except Exception as e:
        logger.exception(f"Ошибка обработки сообщения для пользователя {user_id}: {e}")
        await processing_msg.edit_text(
            "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.")
