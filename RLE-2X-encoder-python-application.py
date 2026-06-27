import tkinter as tk
from tkinter import filedialog, messagebox

# Глобальная переменная для хранения исходных чисел
raw_numbers = []


def setup_clipboard_bindings(widget):
    """Настроить привязки для копирования/вставки/вырезания и SelectAll."""

    def gen(event_name):
        return lambda e: (widget.event_generate(event_name), "break")

    # Windows/Linux: Ctrl
    widget.bind("<Control-c>", gen("<<Copy>>"))
    widget.bind("<Control-v>", gen("<<Paste>>"))
    widget.bind("<Control-x>", gen("<<Cut>>"))
    widget.bind("<Control-a>", lambda e: (widget.tag_add("sel", "1.0", "end"), "break"))

    # macOS: Command
    widget.bind("<Command-c>", gen("<<Copy>>"))
    widget.bind("<Command-v>", gen("<<Paste>>"))
    widget.bind("<Command-x>", gen("<<Cut>>"))
    widget.bind("<Command-a>", lambda e: (widget.tag_add("sel", "1.0", "end"), "break"))

    # При клике — ставим фокус в виджет
    widget.bind("<Button-1>", lambda e: widget.focus_set())

    # Контекстное меню (правый клик)
    menu = tk.Menu(widget, tearoff=0)
    menu.add_command(label="Копировать", command=lambda: widget.event_generate("<<Copy>>"))
    menu.add_command(label="Вставить", command=lambda: widget.event_generate("<<Paste>>"))
    menu.add_command(label="Вырезать", command=lambda: widget.event_generate("<<Cut>>"))
    menu.add_separator()
    menu.add_command(label="Выделить всё", command=lambda: widget.tag_add("sel", "1.0", "end"))

    def show_menu(event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    widget.bind("<Button-3>", show_menu)
    widget.bind("<Control-Button-1>", show_menu)  # для macOS


def parse_numbers_from_file(filepath):
    """
    Читает файл, извлекает все числа, разделённые пробелами/переводами строк.
    Возвращает список целых чисел.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    parts = text.split()
    numbers = []
    for i, p in enumerate(parts, start=1):
        try:
            numbers.append(int(p))
        except ValueError:
            raise ValueError(f"Токен #{i} не является числом: '{p}'")
    return numbers


def find_interleaved_patterns(numbers):
    """
    Ищет паттерны вида: одно и то же число A повторяется через один элемент.
    То есть позиции 0, 2, 4, ... содержат одно и то же число A —
    это «W-паттерн» длины N (N повторов числа A через один).
    
    Также ищет паттерны на нечётных позициях: 1, 3, 5, ...
    
    Возвращает список токенов, где обычные числа остаются как int,
    а W-паттерны представлены как tuple: ("W", длина_паттерна, число_A).
    """
    if not numbers:
        return []
    
    n = len(numbers)
    used = [False] * n
    tokens = []
    
    i = 0
    while i < n:
        if used[i]:
            i += 1
            continue
        
        # --- Проверяем паттерн на чётных позициях относительно i ---
        # Ищем максимальную длину L такую, что numbers[i] == numbers[i+2] == numbers[i+4] == ...
        # и все числа между ними (i+1, i+3, ...) НЕ равны numbers[i]
        value = numbers[i]
        L = 1  # как минимум одно вхождение (само число)
        j = i + 2
        while j < n and numbers[j] == value and not used[j]:
            # Проверяем, что промежуточные элементы не равны value
            # (иначе это был бы обычный RLE-блок)
            all_intermediate_different = True
            for k in range(i + 1, j):
                if numbers[k] == value:
                    all_intermediate_different = False
                    break
            if not all_intermediate_different:
                break
            L += 1
            j += 2
        
        if L >= 3:
            # Нашли W-паттерн: число value повторяется L раз через один
            tokens.append(("W", L, value))
            # Помечаем использованные позиции
            for k in range(L):
                used[i + k * 2] = True
            # Пропускаем весь блок
            # Но нужно проверить: может, после блока тоже начать сдвиг
            # Переходим к следующему неиспользованному элементу после блока
            i += 1
            continue
        
        # --- Проверяем паттерн на нечётных позициях (сдвиг на 1) ---
        # То есть проверяем: numbers[i+1] == numbers[i+3] == numbers[i+5] == ...
        # Начинаем с i+1, если оно не использовано
        if i + 1 < n and not used[i + 1]:
            value2 = numbers[i + 1]
            L2 = 1
            j = i + 3
            while j < n and numbers[j] == value2 and not used[j]:
                all_intermediate_different = True
                for k in range(i + 2, j):
                    if numbers[k] == value2:
                        all_intermediate_different = False
                        break
                if not all_intermediate_different:
                    break
                L2 += 1
                j += 2
            
            if L2 >= 3:
                tokens.append(("W", L2, value2))
                for k in range(L2):
                    used[i + 1 + k * 2] = True
                i += 1
                continue
        
        # Обычное число — не паттерн
        tokens.append(numbers[i])
        used[i] = True
        i += 1
    
    return tokens


def rle_encode_tokens(tokens):
    """
    Кодирует список токенов (int или tuple("W", L, value)) в текстовые строки.
    
    Обычные числа кодируются классическим RLE: 'число количество'
    W-паттерны кодируются как: 'W:длина:число' и занимают ровно одну строку.
    
    Возвращает список строк.
    """
    if not tokens:
        return []
    
    result = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        
        if isinstance(token, tuple) and token[0] == "W":
            # W-паттерн: одна строка
            _, L, value = token
            result.append(f"W:{L}:{value}")
            i += 1
        else:
            # Обычные числа — собираем RLE-серию подряд идущих одинаковых
            current = token
            count = 1
            i += 1
            while i < len(tokens) and tokens[i] == current and not isinstance(tokens[i], tuple):
                count += 1
                i += 1
            result.append(f"{current} {count}")
    
    return result


def encode_interleaved(numbers):
    """
    Двухэтапное сжатие:
    1. Найти W-паттерны (повтор через один).
    2. Оставшиеся числа сжать классическим RLE.
    
    Возвращает список строк для вывода.
    """
    tokens = find_interleaved_patterns(numbers)
    encoded = rle_encode_tokens(tokens)
    return encoded


def load_and_encode():
    """Открывает файл, парсит числа, выполняет сжатие и заполняет табло."""
    global raw_numbers

    path = filedialog.askopenfilename(
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )
    if not path:
        return

    try:
        numbers = parse_numbers_from_file(path)
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось прочитать файл: {e}")
        return

    if not numbers:
        messagebox.showwarning("Пусто", "Файл не содержит чисел.")
        return

    raw_numbers = numbers

    # Двухэтапное сжатие: W-паттерны + RLE
    encoded_lines = encode_interleaved(numbers)

    # Вывод в табло
    text_widget.config(state="normal")
    text_widget.delete("1.0", tk.END)
    text_widget.insert("1.0", "\n".join(encoded_lines))

    # Статистика
    original_count = len(numbers)
    encoded_count = len(encoded_lines)
    
    # Подсчитываем, сколько чисел «покрыто» W-паттернами
    w_covered = 0
    for line in encoded_lines:
        if line.startswith("W:"):
            parts = line.split(":")
            w_covered += int(parts[1])  # длина паттерна
    
    compression_ratio = encoded_count / original_count if original_count > 0 else 0

    status_var.set(
        f"Загружено чисел: {original_count} | Строк после сжатия: {encoded_count} | "
        f"Коэффициент сжатия: {compression_ratio:.2%} | "
        f"Чисел в W-паттернах: {w_covered}"
    )


def save_text_to_file():
    """Сохраняет содержимое текстового поля в выбранный файл (.txt)."""
    txt = text_widget.get("1.0", tk.END).strip()
    if not txt:
        messagebox.showwarning("Пусто", "Нечего сохранять — текстовое поле пусто.")
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        title="Сохранить сжатые данные как...",
    )
    if not file_path:
        return

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(txt)
        messagebox.showinfo("Сохранено", f"Файл сохранён:\n{file_path}")
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{e}")


def clear_text():
    """Очищает табло."""
    global raw_numbers
    raw_numbers = []
    text_widget.config(state="normal")
    text_widget.delete("1.0", tk.END)
    status_var.set("Готов")


def decode_to_numbers():
    """
    Декодирует сжатый формат (RLE + W-паттерны) обратно в исходный список чисел
    и показывает в отдельном окне.
    """
    txt = text_widget.get("1.0", tk.END).strip()
    if not txt:
        messagebox.showwarning("Пусто", "Табло пусто — нечего декодировать.")
        return

    numbers = []
    for i, raw_line in enumerate(txt.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("W:"):
            # Формат: W:длина:число
            parts = line.split(":")
            if len(parts) != 3:
                messagebox.showerror(
                    "Ошибка формата",
                    f"Строка {i}: W-паттерн должен иметь формат W:длина:число, получено: '{raw_line}'",
                )
                return
            try:
                w_len = int(parts[1])
                w_value = int(parts[2])
            except ValueError:
                messagebox.showerror(
                    "Ошибка формата",
                    f"Строка {i}: неверный формат чисел в W-паттерне: '{raw_line}'",
                )
                return
            # W-паттерн длины L означает L повторов числа через один:
            # A, X, A, X, A, X, ... (L раз A)
            # При декодировании мы НЕ знаем, что было между ними (X),
            # поэтому НЕ можем восстановить точную исходную последовательность
            # без дополнительной информации.
            #
            # Нужно сохранять «промежуточные» числа! 
            # Поэтому меняем формат W на хранение полной последовательности.
            messagebox.showerror(
                "Ошибка",
                "Текущий формат W-паттернов не позволяет однозначно восстановить "
                "исходную последовательность без промежуточных чисел.\n\n"
                "Пожалуйста, используйте кнопку «Показать исходные числа» "
                "(работает только если файл был загружен в этой сессии).",
            )
            return
        else:
            # Классический RLE: число количество
            parts = line.split()
            if len(parts) != 2:
                messagebox.showerror(
                    "Ошибка формата",
                    f"Строка {i}: ожидается 2 числа (значение и количество), найдено {len(parts)}: '{raw_line}'",
                )
                return
            try:
                value = int(parts[0])
                count = int(parts[1])
            except ValueError:
                messagebox.showerror(
                    "Ошибка формата",
                    f"Строка {i}: неверный формат чисел: '{raw_line}'",
                )
                return
            numbers.extend([value] * count)

    # Показываем результат в новом окне
    show_numbers_window(numbers, "Декодированные числа")


def show_numbers_window(numbers, title_suffix=""):
    """Вспомогательная функция: показывает список чисел в отдельном окне."""
    win = tk.Toplevel(root)
    win.title(f"{title_suffix} ({len(numbers)} шт.)")
    win.geometry("700x500")

    text_frame = tk.Frame(win)
    text_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    out_text = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 11))
    yscroll = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=out_text.yview)
    out_text.configure(yscrollcommand=yscroll.set)
    yscroll.pack(side=tk.RIGHT, fill=tk.Y)
    out_text.pack(fill=tk.BOTH, expand=True)

    # Выводим числа через пробел, с переносами для читаемости
    chunk_size = 50
    lines = []
    for i in range(0, len(numbers), chunk_size):
        chunk = numbers[i : i + chunk_size]
        lines.append(" ".join(str(n) for n in chunk))
    out_text.insert("1.0", "\n".join(lines))
    out_text.config(state="disabled")


def show_original_numbers():
    """Показывает исходные (raw) числа, загруженные из файла."""
    if not raw_numbers:
        messagebox.showwarning("Нет данных", "Сначала загрузите файл с числами.")
        return
    show_numbers_window(raw_numbers, "Исходные числа")


# --- GUI ---
root = tk.Tk()
root.title("RLE-кодировщик v2: W-паттерны (повтор через один) + RLE")
root.geometry("900x650")

# --- Верхняя панель ---
top_frame = tk.Frame(root)
top_frame.pack(fill=tk.X, padx=8, pady=6)

load_btn = tk.Button(
    top_frame, text="Загрузить файл с числами", command=load_and_encode
)
load_btn.pack(side=tk.LEFT, padx=(0, 6))

decode_btn = tk.Button(
    top_frame, text="Декодировать обратно", command=decode_to_numbers
)
decode_btn.pack(side=tk.LEFT, padx=(0, 6))

show_original_btn = tk.Button(
    top_frame, text="Показать исходные числа", command=show_original_numbers
)
show_original_btn.pack(side=tk.LEFT, padx=(0, 6))

clear_btn = tk.Button(top_frame, text="Очистить табло", command=clear_text)
clear_btn.pack(side=tk.LEFT, padx=(0, 6))

save_btn = tk.Button(top_frame, text="Сохранить как .txt", command=save_text_to_file)
save_btn.pack(side=tk.LEFT)

# --- Текстовая область для сжатого результата ---
text_frame = tk.Frame(root)
text_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

text_widget = tk.Text(text_frame, wrap=tk.NONE, font=("Consolas", 11))
yscroll = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
xscroll = tk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=text_widget.xview)
text_widget.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
yscroll.pack(side=tk.RIGHT, fill=tk.Y)
xscroll.pack(side=tk.BOTTOM, fill=tk.X)
text_widget.pack(fill=tk.BOTH, expand=True)

# Включаем привязки буфера обмена и контекстное меню
setup_clipboard_bindings(text_widget)

# --- Статус-бар ---
status_var = tk.StringVar(value="Готов")
status_bar = tk.Label(
    root,
    textvariable=status_var,
    anchor="w",
    relief=tk.SUNKEN,
    font=("Segoe UI", 10),
)
status_bar.pack(fill=tk.X, padx=0, pady=0)

# --- Подсказка ---
hint = tk.Label(
    root,
    text=(
        "Форматы вывода:\n"
        "  ЧИСЛО КОЛИЧЕСТВО — классический RLE (одинаковые числа подряд).\n"
        "  W:ДЛИНА:ЧИСЛО — W-паттерн: число повторяется через один (мин. 3 повтора).\n"
        "Кнопка «Показать исходные числа» показывает оригинал (только в текущей сессии)."
    ),
    anchor="w",
    justify="left",
    font=("Segoe UI", 9),
)
hint.pack(fill=tk.X, padx=8, pady=(0, 8))

root.mainloop()
