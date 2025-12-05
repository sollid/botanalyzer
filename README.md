# 🛡️ BotAnalyzer Pro

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![ClickHouse](https://img.shields.io/badge/ClickHouse-24.3-yellow.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32-red.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)

**BotAnalyzer Pro** — это мощная аналитическая платформа для глубокого анализа трафика веб-сервера (Nginx). Система специализируется на **SEO-аудите**, выявлении **аномалий безопасности** и классификации **ботов** (AI, Search, Spam).

---

## 🌟 Ключевые Возможности

### 🕷️ 1. SEO & Crawl Budget
*   **Googlebot Monitor**: Проверка подлинности ботов Google через Reverse DNS (отсеивает фейков).
*   **Crawl Budget**: Визуализация того, как поисковики расходуют краулинговый бюджет по разделам сайта (Blog vs Products).
*   **Status Codes**: Мониторинг ошибок 404/5xx глазами поисковых систем.

### 🔒 2. Security & Anomalies
*   **Rate Limiting (RPS)**: Детекция IP-адресов с аномально частыми запросами.
*   **Bad Bot Fingerprinting**: Определение паразитного трафика (MJ12, Ahrefs, Bytespider, AI-scrapers).
*   **404 Attack Detector**: Выявление сканеров уязвимостей, перебирающих несуществующие URL.

### 📚 3. Энциклопедия Ботов (Bot Encyclopedia)
*   **Knowledge Base**: Встроенная база знаний о сотнях ботов с описанием и оценкой риска.
*   **Live Traffic Correlation**: Показывает, какие боты активны на вашем сайте прямо сейчас.
*   **Управление**: Вы можете редактировать описания ботов и добавлять новых прямо через интерфейс!

### ⚡ 4. Производительность
*   **ClickHouse**: Колоночная СУБД позволяет анализировать гигабайты логов за миллисекунды.
*   **Multiprocessing Ingest**: Загрузчик логов использует все ядра CPU для быстрого парсинга архивов `.gz`.

---

## 🛠️ Установка и Запуск

### 📋 1. Предварительные требования
*   **Docker Desktop**: [Скачать](https://www.docker.com/products/docker-desktop/).
    *   *Windows*: Обязательно включите **WSL 2** (`wsl --install`) и интеграцию с ним в настройках Docker.
*   **RAM**: Минимум 4 ГБ (рекомендуется 8 ГБ+ для ClickHouse).
*   **GeoIP База**: Требуется бесплатный файл `GeoLite2-Country.mmdb` от MaxMind.

### 🚀 2. Установка (Пошагово)

1.  **Клонируйте репозиторий:**
    ```bash
    git clone https://github.com/sollid/botanalyzer.git
    cd botanalyzer
    ```

2.  **Добавьте базу GeoIP:**
    *   Зарегистрируйтесь на [MaxMind](https://www.maxmind.com/en/geolite2/signup).
    *   Скачайте файл `GeoLite2-Country.mmdb`.
    *   Положите его в корень папки проекта (рядом с `docker-compose.yml`).

3.  **Загрузите логи:**
    *   Создайте папку `logs/` в корне проекта.
    *   Скопируйте туда ваши логи Nginx (поддерживаются `.log` и `.gz`).
    ```bash
    mkdir logs
    cp /path/to/your/access.log.gz logs/
    ```

4.  **Запустите:**
    ```bash
    docker-compose up -d --build
    ```

После запуска откройте браузер: **http://localhost:8501**

---

## 🔄 Работа с Логами (Ingestion Process)

### Как загрузить новые логи?
Система автоматически сканирует папку `logs/` при старте контейнера.

**Сценарий А: Добавление логов "на лету"**
1.  Положите новые файлы `.gz` в папку `logs/`.
2.  Запустите команду переиндексации внутри контейнера:
    ```bash
    docker exec -d log_analyzer_app python src/ingest.py
    ```
    *Скрипт пропустит уже загруженные файлы и добавит только новые.*

**Сценарий Б: Полная перегрузка (С чистого листа)**
Если вы хотите очистить базу и загрузить всё заново:
```bash
# 1. Остановите контейнеры и удалите том с данными БД
docker-compose down
docker volume rm botanalyzer_gemini_clickhouse_data

# 2. Запустите заново
docker-compose up -d
```

### Конфигурация парсера
Если ваши логи имеют нестандартный формат, отредактируйте `src/ingest.py`:
*   `ACCESS_LOG_PATTERN`: Regex для access логов.
*   `ERROR_LOG_PATTERN`: Regex для error логов.

---

## 📂 Структура Проекта

| Путь | Описание |
| :--- | :--- |
| `logs/` | Сюда кладем файлы логов (игнорируется git) |
| `clickhouse_data/` | Файлы базы данных (игнорируется git) |
| `src/app.py` | Основной код Dashboard (Streamlit) |
| `src/ingest.py` | ETL скрипт для парсинга и загрузки данных |
| `src/bot_manager.py` | Менеджер конфигурации ботов (JSON) |
| `data/bot_config.json` | Файл с вашими настройками ботов (создается автоматически) |
| `docker-compose.yml` | Описание сервисов (App + DB) |

---

## ❓ Troubleshooting

**Q: Я не вижу данных на дашборде.**
A: Процесс загрузки занимает время. Проверьте логи контейнера:
```bash
docker logs -f log_analyzer_app
```
Если видите "Ingestion complete" — данные загружены.

**Q: Ошибка "Could not connect to database".**
A: ClickHouse еще не успел запуститься. Подождите 10-15 секунд и обновите страницу.

**Q: Ошибка с WSL на Windows.**
A: Выполните `wsl --update` в PowerShell от администратора и перезагрузите компьютер.
