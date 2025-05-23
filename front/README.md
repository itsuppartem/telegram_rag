
# AI Assistant Telegram Bot for "_____"

## 1. Краткое описание

Данный микросервис представляет собой Telegram-бота, разработанного в качестве пользовательского интерфейса для AI-ассистента компании "______". Сервис обеспечивает взаимодействие пользователей с системой Retrieval Augmented Generation (RAG), позволяя задавать вопросы на естественном языке и получать ответы, основанные на внутренней базе знаний. Администраторы имеют расширенные возможности по управлению контентом базы знаний.

## 2. Архитектура и технологии

Сервис реализован на языке **Python 3.10+** с использованием следующих ключевых технологий:

*   **aiogram 3.x:** Современный асинхронный фреймворк для разработки Telegram-ботов. Выбран за его высокую производительность, удобный API, поддержку FSM (Finite State Machines) для управления состояниями и гибкую систему фильтров.
*   **httpx:** Асинхронный HTTP-клиент для взаимодействия с бэкенд-сервисом (FastAPI). Обеспечивает неблокирующие сетевые запросы, что критично для производительности бота.
*   **python-dotenv:** Для управления конфигурационными параметрами через переменные окружения, что является стандартной практикой для безопасной и гибкой настройки приложения.

**Взаимодействие с бэкендом:**
Бот не реализует основную бизнес-логику (RAG, управление документами, хранение истории) самостоятельно, а выступает в роли клиентского приложения для бэкенд-сервиса (предположительно, реализованного на FastAPI). Бэкенд отвечает за:
    *   Обработку и векторизацию документов.
    *   Хранение документов и их векторов (предположительно, в MongoDB и Qdrant).
    *   Выполнение RAG-запросов для генерации ответов.
    *   Управление историей диалогов пользователей.

Такое разделение позволяет масштабировать и обновлять фронтенд (бот) и бэкенд независимо друг от друга.


## 3. Настройка окружения

Создайте файл `.env` в корневой директории проекта и заполните его необходимыми значениями:

```env
# Токен вашего Telegram-бота, полученный от @BotFather
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"

# Базовый URL бэкенд-сервиса FastAPI
FASTAPI_BASE_URL="http://localhost:8000" # или другой адрес, если бэкенд развернут удаленно

# Список ID администраторов Telegram, разделенных запятыми.
TELEGRAM_ADMIN_IDS="123456789,987654321"
```

**Важно:**
*   `TELEGRAM_BOT_TOKEN`: Получите у @BotFather в Telegram.
*   `FASTAPI_BASE_URL`: Укажите адрес, по которому доступен ваш FastAPI бэкенд.
*   `TELEGRAM_ADMIN_IDS`: Перечислите числовые ID пользователей Telegram, которые будут иметь административные права. ID можно узнать, например, у бота @userinfobot.

## 4. Запуск сервиса

Для запуска бота выполните команду из корневой директории проекта:

```bash
python bot.py
```

Логи работы бота будут выводиться в консоль.

## 5. Основные команды

### 5.1. Команды для всех пользователей

*   `/start` - Начать взаимодействие с ботом, отображает приветственное сообщение.
*   `/help` - Показать список доступных команд и их описание.
*   `/clear` - Очистить историю диалога пользователя (удаляет данные на стороне бэкенда).

### 5.2. Команды для администраторов

Доступны только пользователям, чьи ID указаны в `TELEGRAM_ADMIN_IDS`.

*   `/upload` - Запустить процесс загрузки нового документа (поддерживаемые форматы: .txt, .pdf, .docx) в базу знаний. Бот запросит файл.
*   `/list_docs` - Показать список всех документов, загруженных в базу знаний, с их ID, временем загрузки и количеством фрагментов.
*   `/delete_doc <ID или Имя файла>` - Удалить указанный документ и все связанные с ним данные из базы знаний. Бот запросит подтверждение перед удалением.

## 6. API Взаимодействие (с бэкендом)

Бот взаимодействует с бэкенд-сервисом по протоколу **REST API**.

*   **Аутентификация:** В текущей реализации бот не отправляет явных токенов аутентификации или API-ключей на бэкенд. Предполагается, что бэкенд-сервис может быть защищен на сетевом уровне или доверяет запросам от IP-адреса бота.

*   **Ключевые эндпоинты бэкенда, используемые ботом:**
    *   `POST /ask`
        *   Назначение: Отправка вопроса пользователя для получения ответа от RAG-системы.
        *   Тело запроса: `{"user_id": int, "question": str}`
        *   Ответ: `{"answer": str, "metrics": dict}`
    *   `POST /upload`
        *   Назначение: Загрузка файла документа для добавления в базу знаний.
        *   Тело запроса: `multipart/form-data` с файлом.
        *   Ответ: Сообщение о статусе обработки.
    *   `GET /documents`
        *   Назначение: Получение списка документов из базы знаний.
        *   Ответ: `{"documents": list[dict]}`
    *   `DELETE /documents/{doc_id_or_filename}`
        *   Назначение: Удаление документа из базы знаний.
        *   Path parameter: `doc_id_or_filename` (ID или имя файла).
        *   Ответ: `{"success": bool, "message": str}`
    *   `DELETE /history/{user_id}`
        *   Назначение: Очистка истории диалога для указанного пользователя.
        *   Path parameter: `user_id` (Telegram ID пользователя).
        *   Ответ: `{"message": str}`

## 7. Примеры использования

### 7.1. Сценарий: Пользователь задает вопрос

1.  **Пользователь:** Отправляет текстовое сообщение боту, например: "Какие условия предоставления корпоративной связи?"
2.  **Бот:**
    *   Отображает сообщение: "Обработка вашего вопроса, пожалуйста подождите..."
    *   Отправляет запрос на бэкенд: `POST /ask` с `{"user_id": <ID_пользователя>, "question": "Какие условия предоставления корпоративной связи?"}`.
3.  **Бэкенд:** Обрабатывает запрос через RAG-систему, находит релевантную информацию в базе знаний, генерирует ответ.
4.  **Бот:**
    *   Получает ответ от бэкенда.
    *   Отправляет пользователю сгенерированный ответ.
    *   Отправляет пользователю сообщение с метриками ответа (источник, категория, время генерации, использованные фрагменты и т.д.).
    *   Отправляет пользователю файл с подробными метриками и использованными фрагментами контекста.

### 7.2. Сценарий: Администратор загружает новый документ

1.  **Администратор:** Отправляет команду `/upload`.
2.  **Бот:** Отвечает: "Хорошо, администратор! Пожалуйста, отправьте мне документ (txt, pdf или docx)... Отправьте /cancel для отмены." (Переходит в состояние `UploadStates.waiting_for_file`).
3.  **Администратор:** Отправляет файл `internal_policy.pdf` боту.
4.  **Бот:**
    *   Проверяет расширение файла.
    *   Отображает сообщение: "Получен файл 'internal_policy.pdf'. Обработка, пожалуйста подождите..."
    *   Локально сохраняет файл во временную директорию `uploads_telegram/`.
    *   Отправляет запрос на бэкенд: `POST /upload` с файлом `internal_policy.pdf` (multipart/form-data).
    *   После получения подтверждения от бэкенда (что файл принят в обработку):
        *   Редактирует сообщение: "✅ Файл 'internal_policy.pdf' принят и поставлен в очередь на обработку..."
    *   Удаляет временный файл.
    *   Выходит из состояния загрузки.
5.  **Бэкенд:** Асинхронно обрабатывает файл, индексирует его и добавляет в базу знаний.

### 7.3. Сценарий: Администратор удаляет документ

1.  **Администратор:** Отправляет команду `/delete_doc internal_policy.pdf` (или `/delete_doc <ID_документа>`, полученный из `/list_docs`).
2.  **Бот:** Отвечает: "Вы уверены, что хотите навсегда удалить документ 'internal_policy.pdf'...? " с кнопками "Да, УДАЛИТЬ" и "Отмена".
3.  **Администратор:** Нажимает кнопку "Да, УДАЛИТЬ".
4.  **Бот:**
    *   Редактирует сообщение: "Удаление 'internal_policy.pdf'..."
    *   Отправляет запрос на бэкенд: `DELETE /documents/internal_policy.pdf`.
5.  **Бэкенд:** Находит и удаляет документ и все связанные с ним данные.
6.  **Бот:** Получает ответ от бэкенда и редактирует сообщение: "✅ Документ 'internal_policy.pdf' успешно удален." (или сообщение об ошибке).

