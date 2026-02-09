import os

def count_files_in_directory(path):
    # Получаем список всех элементов в папке
    all_items = os.listdir(path)
    
    # Фильтруем только файлы (исключаем подпапки)
    files = [item for item in all_items if os.path.isfile(os.path.join(path, item))]
    
    return len(files)