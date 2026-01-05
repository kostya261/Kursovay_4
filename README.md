# 🐍 Курсовая 3 Парсер вакансий с HeadHunter API

Курсовой проект по дисциплине "Программирование на Python". 
Система для сбора, фильтрации и анализа вакансий с платформы HeadHunter.

## 🚀 Основные возможности

- **📡 Получение вакансий** через HeadHunter API
- **💾 Сохранение данных** в JSON формате
- **🔍 Фильтрация вакансий** по зарплате, ключевым словам
- **📊 Сравнение вакансий** по различным параметрам
- **🎯 Гибкая настройка** параметров поиска

## 📦 Установка и настройка


1. Клонируйте репозиторий:
   [ссылка](https://github.com/kostya261/Cursovoi_3---/pull/1)
   
3. Зависимости указанные в файле: *pyproject.toml*
```
[tool.poetry]
name = "cursovoi-3"
version = "0.1.0"
description = "Третья курсовая"
authors = ["Kosarew Konstantin <kos26193@gmail.com>"]
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.13"
poetry-core = "^2.2.1"
requests = "^2.32.5"
types-requests = "^2.32.4.20250913"


[tool.poetry.group.lint.dependencies]
flake8 = "^7.3.0"
mypy = "^1.18.2"
isort = "^6.0.1"
black = "^25.9.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.4.2"
pytest-cov = "^7.0.0"
psycopg2 = "^2.9.10"

[tool.black]
line-length = 119
exclude = """ \\.git """

[tool.isort]
line_length = 119

[tool.mypy]
disallow_untyped_defs = true
warn_return_any = true
exclude = 'venv'

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

```

## Использование:

Откройте проект например в PyCharm, откройте файл main.py и запустите его.
По желанию можно его всячески модифицировать в рамках тестирования написанных функций.

В Cursovoi_3\src описаны следующие модули:
**vacancy.py, utils.py, api_hh.py, employer.py, DB_class.py**, которые и реализуют весь скромный функционал курсового проекта.

### vacancy.py
Класс Vacancy  - модель данных вакансии

Примеры использования:
```
vacancy = Vacancy(
    "Водитель Газели", "<https://hh.ru/vacancy/123456>", "100 000-150 000 руб.", "Требования: опыт работы от 3 лет..."
)
```

### employer.py
Класс Employer  - модель данных работодателя
```
employer_data = ApiHH.get_employer("1740")
employer = Employer(employer_data)
```


### utils.py

В данном модуле описана функция print_vacancy(i)

Которая просто выводит вакансию на экран

Пример использования:
```
for i in db.get_all_vacancies():
    print_vacancy(i)
```


## api_hh.py
Содержит class **ApiHH**

Реализует доступ к сайту HH посредством его API и по предварительно установленным параметрам 
возвращает список работодателей и вакансий.

## Структура проекта

Cursovoi_3/
├── src/                    # Исходный код
│   ├── api_hh.py           # Клиент HeadHunter API
│   ├── vacancy.py          # Модель вакансии
│   ├── DB_class.py         # Модель для работы с базой данных
│   ├── employer.py         # Модель работодателя
│   └── utils.py            # Вывод вакансии на экран (было больше, пустил под нож)
└── README.md              # Этот файл

👨‍💻 Автор
Константин

GitHub: https://github.com/kostya261

Email: kos261@yandex.ru


## Лицензия:
📄 Лицензия
Этот проект является курсовой работой и распространяется по лицензии MIT.В
