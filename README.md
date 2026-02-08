# visdrone Detector

## 📁 Структура проекта

В качестве backend выбран фреймворк Flask.

Frontend написан на javascript.

В папку app/weights необходимо поместить веса, которые можно скачать по ссылке

https://drive.google.com/drive/folders/1aUku-up4LSJO3YqUB2yc0rx6Ax0cejqw?usp=sharing

## 🚀 Установка и создание виртуального окружения

```bash
# 1. Клонируем репозиторий
git clone https://github.com/dimokode/visdrone.git
cd visdrone

# 2. Создаём виртуальное окружение
python -m venv .venv

# 3. Активируем виртуальное окружение
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 4. Устанавливаем зависимости
pip install -r requirements.txt
```


---
## 🖥 Запуск проекта
```bash
cd app

python app.py
```
Сервер будет доступен по адресу: ``http://127.0.0.1:5000``