
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
    widget.bind("<Control-x>", gen("<<Cut>>"))
    widget.bind("<Control-v>", gen("<<Paste>>"))
    widget.bind(
        "<Control-a>",
        lambda e: (widget.tag_add("sel", "1.0", "end"), "break"),
    )

    # macOS: Command
    widget.bind("<Command-c>", gen("<<Copy>>"))
    widget.bind("<Command-x>", gen("<<Cut>>"))
    widget.bind("<Command-v>", gen("<<Paste>>"))
    widget.bind(
        "<Command-a>",
        lambda e: (widget.tag_add("sel", "1.0", "end"), "break"),
    )

    # При клике — ставим фокус в виджет
    widget.bind("<Button-1>", lambda e: widget.focus_set())

    # Контекстное меню (правый клик)
    menu = tk.Menu(widget, tearoff=0)
    menu.add_command(
        label="Копировать",
        command=lambda: widget.event_generate("<<Copy>>"),
    )
    menu.add_command(
        label="Вставить",
        command=lambda: widget.event_generate("<<Paste>>"),
    )
    menu.add_command(
        label="Вырезать",
        command=lambda: widget.event_generate("<<Cut>>"),
    )
    menu.add_separator()
    menu.add_command(
        label="Выделить всё",
        command=lambda: widget.tag_add("sel", "1.0", "end"),
    )

    def show_menu(event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    widget.bind("<Button-3>", show_menu)  # Windows/Linux
    widget.bind("<Button-2>", show_menu)  # macOS


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


def rle_encode(numbers):
    """
    Кодирует список чисел в RLE (run-length encoding).
    Возвращает список строк формата: 'число количество'
    Пример: [0,0,0,255,255] -> ['0 3', '255 2']
    """
    if not numbers:
        return []

    result = []
    current_value = numbers[0]
    count = 1

    for num in numbers[1:]:
        if num == current_value:
            count += 1
        else:
            result.append(f"{current_value} {count}")
            current_value = num
            count = 1

    # Последняя серия
    result.append(f"{current_value} {count}")
    return result


def compress_singles(encoded_lines):
    """
    Пост-обработка RLE-результата:
    Группы подряд идущих строк вида 'X 1' (число X с количеством 1)
    заменяются на одну строку 'W:N:X', где N — количество таких строк,
    а X — значение, которое повторяется.
    Сами значения (без '1') дублируются следом для возможности
    восстановления при декодировании.

    Пример:
      ['248 1', '252 1', '250 1', '248 1', '255 3', '10 1', '20 1']
      -> ['W:4:1', '248', '252', '250', '248', '255 3', 'W:2:1', '10', '20']
    """
    if not encoded_lines:
        return []

    result = []
    i = 0
    while i < len(encoded_lines):
        line = encoded_lines[i]
        parts = line.split()
        # Проверяем, имеет ли строка формат 'число 1'
        if len(parts) == 2 and parts[1] == "1":
            value = parts[0]
            count = 0
            start = i
            # Собираем все подряд идущие 'X 1' с одинаковым X
            while i < len(encoded_lines):
                p = encoded_lines[i].split()
                if len(p) == 2 and p[1] == "1" and p[0] == value:
                    count += 1
                    i += 1
                else:
                    break
            # Добавляем W-строку
            result.append(f"W:{count}:{value}")
            # Добавляем сами значения (без '1') для восстановления
            for j in range(start, start + count):
                result.append(encoded_lines[j].split()[0])
        else:
            result.append(line)
            i += 1

    return result


def load_and_encode():
    """Открывает файл, парсит числа, выполняет RLE-кодирование и заполняет табло."""
    global raw_numbers

    path = filedialog.askopenfilename(
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )
    if not path:
        return

    try:
        numbers = parse_numbers_from_file(path)
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось прочитать файл:\n{e}")
        return

    if not numbers:
        messagebox.showwarning("Пусто", "Файл не содержит чисел.")
        return

    raw_numbers = numbers

    # RLE-кодирование + сжатие одиночных серий
    encoded_lines = compress_singles(rle_encode(numbers))

    # Вывод в табло
    text_widget.config(state="normal")
    text_widget.delete("1.0", tk.END)
    text_widget.insert("1.0", "\n".join(encoded_lines))

    # Статистика
    status_var.set(
        f"Загружено чисел: {len(numbers)} | "
        f"Строк в табло: {len(encoded_lines)} | "
        f"Коэффициент сжатия: {len(encoded_lines) / len(numbers):.2%}"
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
        title="Сохранить RLE-данные как...",
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


def decode_rle_to_numbers():
    """
    Декодирует RLE (включая W-сжатие) из текстового поля обратно
    в исходный список чисел и показывает в отдельном окне.
    """
    txt = text_widget.get("1.0", tk.END).strip()
    if not txt:
        messagebox.showwarning("Пусто", "Табло пусто — нечего декодировать.")
        return

    numbers = []
    i = 0
    lines_list = txt.splitlines()
    while i < len(lines_list):
        raw_line = lines_list[i].strip()
        if not raw_line:
            i += 1
            continue

        # Проверяем, является ли строка W-сжатием
        if raw_line.startswith("W:"):
            w_parts = raw_line.split(":")
            if len(w_parts) != 3:
                messagebox.showerror(
                    "Ошибка формата",
                    f"Строка {i+1}: неверный формат W-записи: '{raw_line}' "
                    f"(ожидается W:N:X)",
                )
                return
            try:
                w_count = int(w_parts[1])
                w_value = int(w_parts[2])
            except ValueError:
                messagebox.showerror(
                    "Ошибка формата",
                    f"Строка {i+1}: неверные числа в W-записи: '{raw_line}'",
                )
                return
            # Следующие w_count строк — это сами значения
            for j in range(w_count):
                i += 1
                if i >= len(lines_list):
                    messagebox.showerror(
                        "Ошибка формата",
                        f"W-запись '{raw_line}' ожидает {w_count} значений, "
                        f"но файл закончился",
                    )
                    return
                val_line = lines_list[i].strip()
                try:
                    numbers.append(int(val_line))
                except ValueError:
                    messagebox.showerror(
                        "Ошибка формата",
                        f"Строка {i+1}: ожидается число, получено: '{val_line}'",
                    )
                    return
        else:
            # Обычная RLE-строка: значение количество
            parts = raw_line.split()
            if len(parts) != 2:
                messagebox.showerror(
                    "Ошибка формата",
                    f"Строка {i+1}: ожидается 2 числа (значение и количество), "
                    f"найдено {len(parts)}: '{raw_line}'",
                )
                return
            try:
                value = int(parts[0])
                count = int(parts[1])
            except ValueError:
                messagebox.showerror(
                    "Ошибка формата",
                    f"Строка {i+1}: неверный формат чисел: '{raw_line}'",
                )
                return
            numbers.extend([value] * count)

        i += 1

    # Показываем результат в новом окне
    win = tk.Toplevel(root)
    win.title(f"Декодированные числа ({len(numbers)} шт.)")
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
    lines_output = []
    for idx in range(0, len(numbers), chunk_size):
        chunk = numbers[idx : idx + chunk_size]
        lines_output.append(" ".join(str(n) for n in chunk))
    out_text.insert("1.0", "\n".join(lines_output))
    out_text.config(state="disabled")


# --- GUI ---
root = tk.Tk()
root.title("RLE-кодировщик: сжатие одинаковых чисел подряд + W-сжатие")
root.geometry("900x650")

# --- Верхняя панель ---
top_frame = tk.Frame(root)
top_frame.pack(fill=tk.X, padx=8, pady=6)

load_btn = tk.Button(
    top_frame, text="Загрузить файл с числами", command=load_and_encode
)
load_btn.pack(side=tk.LEFT, padx=(0, 6))

decode_btn = tk.Button(
    top_frame, text="Декодировать обратно", command=decode_rle_to_numbers
)
decode_btn.pack(side=tk.LEFT, padx=(0, 6))

clear_btn = tk.Button(top_frame, text="Очистить табло", command=clear_text)
clear_btn.pack(side=tk.LEFT, padx=(0, 6))

save_btn = tk.Button(top_frame, text="Сохранить как .txt", command=save_text_to_file)
save_btn.pack(side=tk.LEFT)

# --- Текстовая область для RLE-результата ---
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
        "Формат вывода: ЧИСЛО КОЛИЧЕСТВО (RLE-кодирование). "
        "Группы одиночных значений сжимаются в W:N:X, где N — количество, "
        "X — значение. Кнопка «Декодировать обратно» восстанавливает "
        "исходную последовательность."
    ),
    anchor="w",
    font=("Segoe UI", 9),
)
hint.pack(fill=tk.X, padx=8, pady=(0, 8))

root.mainloop()
