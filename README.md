# API-сервис сокращения ссылок

## Основное API

- **POST** /links/shorten – создание короткой ссылки с помощью генерации уникального кода либо строки пользователя
 
  Параметеры:
  - **expires_at** - дата удаления ссылки с точностью до минуты в формате **2025-04-01T20:37**, параметр необязателен
  - **user_id** - идентификатор пользователя, если тот залогинен
    
  Формат JSON:
  ```
  {
    "original_url": "string",
    "custom_alias": "string"
  }
  ```
  - **original_url** - оригинальный url для создания короткой ссылки
  - **custom_alias** - строка для создания кастомной короткой ссылки, необязательный параметр, проверяется на уникальность

- **GET** /links/{short_code} – перенаправление на оригинальный URL по коду
- **DELETE** /links/{short_code} – удаление короткой ссылки, метод доступен только зарегистрированным пользователям (требуется передача токена в хедере запроса)
- **PUT** /links/{short_code} – обновление кода короткой ссылки, метод доступен только зарегистрированным пользователям (требуется передача токена в хедере запроса)

- **GET** /links/{short_code}/stats - отображение оригинального url и получение статистики по короткой ссылке: даты создания, количества переходов и даты последнего использования

- **GET** /links/search?original_url={url} - поиск короткой ссылки по оригинальному URL


- Дополнительная функциональность:
  - **GET** /links/all - получение всех активных коротких ссылок пользователя с информацией о них, метод доступен только зарегистрированным пользователям (требуется передача токена в хедере запроса)
  - **GET** /links/history_expired - отображение истории всех истекших ссылок пользователя с информацией о них, метод доступен только зарегистрированным пользователям (требуется передача токена в хедере запроса)

## API регистрации и авторизации

- **POST** /auth/register - регистрация нового пользователя
  
  Формат JSON:
  ```
  {
    "email": "user@example.com",
    "password": "string",
    "is_active": true,
    "is_superuser": false,
    "is_verified": false
  }
  ```
- **POST** /auth/jwt/login - логин, требуется ввести email и пароль, указанные при регистрации
  
  Ответ будет содержать токен (**access_token**), который нужно будет передавать в хедере при обращении к сервисам, доступным только зарегистрированным пользователям:
  ```
  {
    "access_token": "long_token_string",
    "token_type": "bearer"
  }
  ```
- **POST** /auth/jwt/logout - логаут, требуется передать токен в хедере

## Примеры запросов

- **GET** http://localhost:8000/links/wBkxl
- **GET** http://localhost:8000/links/search?original_url=https://www.google.ru/
- **GET** http://localhost:8000/links/all
- **GET** http://localhost:8000/links/history_expired
- **PUT** http://localhost:8000/links/wBkxl

## Запуск приложения
Запуск приложения происходит через **docker compose**. 

Для этого в корне проекта нужно создать файл **.env** с переменными окружения:
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5431
POSTGRES_DB=url_shortener_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

SECRET=12345

DAYS_TO_EXPIRE=5
```

А затем там же нужно вызвать команду:

```docker compose up --build```

Непосредственно перед стартом самого приложения происходит запуск миграций БД.

##  База данных
**PostgreSQL**

Таблицы:
- **user**
- **link**

**user**:
- **id**, integer: идентификатор пользователя
- **email**, string: почта
- **hashed_password**, string: захешированный пароль
- **is_active**, boolean: индикатор, что аккаунт пользователя активен
- **is_superuser**, boolean: индикатор, что пользователь является суперюзером (поле не используется в приложении)
- **is_verified**, boolean: индикатор, что пользователь прошел верификацию (поле не используется в приложении)

**link**:
- **id**, integer: идентификатор ссылки
- **original_url**, string: оригинальный url ссылки
- **short_code**, string: уникальный код короткой ссылки
- **creation_date**, timestamp: дата создания короткой ссылки
- **expires_at**, timestamp: дата удаления ссылки с точностью до минуты, может быть **null**
- **clicks_count**, integer: количество переходов по ссылке
- **last_usage_at**, timestamp: дата последнего использования, может быть **null**
- **deleted**, boolean: индикатор того, что ссылка удалена
- **user_id**, integer: идентификатор пользователя, внешний ключ на таблицу **user**, может быть **null**
