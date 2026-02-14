"""
Скрипт для копирования telegram_bot.py в проект.
Запускать из корня репозитория. Путь к исходному файлу задаётся в SOURCE или аргументом.
"""
import shutil
import sys
from pathlib import Path

# Корень проекта (каталог, где лежит copy_file.py)
ROOT = Path(__file__).resolve().parent
DEST = ROOT / "backend" / "bot" / "telegram_bot.py"

# Путь к исходному файлу: аргумент командной строки или значение по умолчанию
SOURCE_DEFAULT = Path(r"c:\Users\user\Downloads\telegram_bot.py")
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCE_DEFAULT


def main():
    if not SOURCE.exists():
        print(f"Ошибка: файл не найден: {SOURCE}")
        sys.exit(1)
    if not SOURCE.is_file():
        print(f"Ошибка: путь не является файлом: {SOURCE}")
        sys.exit(1)
    DEST.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy(SOURCE, DEST)
        print(f"Скопировано: {SOURCE} -> {DEST}")
    except OSError as e:
        print(f"Ошибка копирования: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

