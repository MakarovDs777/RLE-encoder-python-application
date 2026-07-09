import tkinter as tk
from tkinter import filedialog, messagebox

# Глобальная переменная для хранения исходного текста
raw_text = ""


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

    widget.bind("<Button-2>", show_menu)  # Windows/Linux правый клик
    widget.bind("<Button-3>", show_menu)  # macOS правый клик


def read_file_content(filepath):
    """Читает файл и возвращает всё содержимое как строку."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    if not content.strip():
        raise ValueError("Файл пуст.")
    return content


def rle_encode_chars(text):
    """
    Посимвольное RLE-кодирование.
    Каждый символ кодируется как 'символ количество'.
    Пробелы отображаются как '_' для наглядности.

    Пример: 'aaabb' -> ['a 3', 'b 2']
            '@13-22#223' -> ['@ 1', '1 1', '3 1', '- 1', '2 2', '# 1', '2 1', '3 1']
    """
    if not text:
        return []

    result = []
    current_char = text[0]
    count = 1

    for char in text[1:]:
        if char == current_char:
            count += 1
        else:
            # Пробелы заменяем на '_' для наглядности
            display_char = current_char if current_char != " " else "_"
            result.append(f"{display_char} {count}")
            current_char = char
            count = 1

    # Последняя серия
    display_char = current_char if current_char != " " else "_"
    result.append(f"{display_char} {count}")
    return result


def rle_decode_chars(encoded_lines):
    """
    Декодирует RLE-строки обратно в исходную последовательность символов.
    '_' в начале строки декодируется обратно в пробел.
    """
    result = []
    for line in encoded_lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise ValueError(f"Неверный формат строки: '{line}'")

        char = parts[0]
        count = int(parts[1])

        # '_' обратно в пробел
        if char == "_":
            char = " "

        result.append(char * count)

    return "".join(result)


def load_and_encode():
    """Открывает файл, выполняет посимвольное RLE-кодирование и заполняет табло."""
    global raw_text

    path = filedialog.askopenfilename(
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )
    if not path:
        return

    try:
        content = read_file_content(path)
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось прочитать файл:\n{e}")
        return

    raw_text = content

    # Посимвольное RLE-кодирование
    encoded_lines = rle_encode_chars(content)

    # Вывод в табло
    text_widget.config(state="normal")
    text_widget.delete("1.0", tk.END)
    text_widget.insert("1.0", "\n".join(encoded_lines))

    # Статистика
    original_len = len(content)
    encoded_len = len(encoded_lines)
    status_var.set(
        f"Символов в исходном тексте: {original_len} | "
        f"Серий (RLE-пар): {encoded_len} | "
        f"Коэффициент сжатия: {encoded_len * 2 / original_len:.2%}"
    )


def encode_from_textarea():
    """
    Кодирует текст, вставленный/набранный в текстовое поле.
    Позволяет работать без загрузки файла — просто вставить текст и нажать кнопку.
    """
    global raw_text

    content = text_widget.get("1.0", tk.END)
    if not content.strip():
        messagebox.showwarning("Пусто", "Текстовое поле пусто.")
        return

    raw_text = content
    encoded_lines = rle_encode_chars(content)

    text_widget.config(state="normal")
    text_widget.delete("1.0", tk.END)
    text_widget.insert("1.0", "\n".join(encoded_lines))

    original_len = len(content)
    encoded_len = len(encoded_lines)
    status_var.set(
        f"Символов в исходном тексте: {original_len} | "
        f"Серий (RLE-пар): {encoded_len} | "
        f"Коэффициент сжатия: {encoded_len * 2 / original_len:.2%}"
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
    global raw_text
    raw_text = ""
    text_widget.config(state="normal")
    text_widget.delete("1.0", tk.END)
    status_var.set("Готов")


def decode_rle_to_text():
    """
    Декодирует RLE из текстового поля обратно в исходную строку
    и показывает в отдельном окне.
    """
    txt = text_widget.get("1.0", tk.END).strip()
    if not txt:
        messagebox.showwarning("Пусто", "Табло пусто — нечего декодировать.")
        return

    lines = txt.splitlines()
    try:
        decoded = rle_decode_chars(lines)
    except ValueError as e:
        messagebox.showerror("Ошибка формата", str(e))
        return

    # Показываем результат в новом окне
    win = tk.Toplevel(root)
    win.title(f"Декодированный текст ({len(decoded)} символов)")
    win.geometry("700x500")

    text_frame = tk.Frame(win)
    text_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    out_text = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 11))
    yscroll = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=out_text.yview)
    out_text.configure(yscrollcommand=yscroll.set)
    yscroll.pack(side=tk.RIGHT, fill=tk.Y)
    out_text.pack(fill=tk.BOTH, expand=True)

    out_text.insert("1.0", decoded)
    out_text.config(state="disabled")


# --- GUI ---

root = tk.Tk()
root.title("RLE-кодировщик: посимвольное сжатие")
root.geometry("900x650")

# --- Верхняя панель ---
top_frame = tk.Frame(root)
top_frame.pack(fill=tk.X, padx=8, pady=6)

load_btn = tk.Button(
    top_frame, text="Загрузить файл", command=load_and_encode
)
load_btn.pack(side=tk.LEFT, padx=(0, 6))

encode_btn = tk.Button(
    top_frame, text="Кодировать текст из поля", command=encode_from_textarea
)
encode_btn.pack(side=tk.LEFT, padx=(0, 6))

decode_btn = tk.Button(
    top_frame, text="Декодировать обратно", command=decode_rle_to_text
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
        "Посимвольное RLE-кодирование. Каждая строка: СИМВОЛ КОЛИЧЕСТВО. "
        "Пробелы отображаются как '_'. "
        "Можно вставить/набрать текст в поле и нажать «Кодировать текст из поля», "
        "либо загрузить файл. Кнопка «Декодировать обратно» восстанавливает исходную строку."
    ),
    anchor="w",
    font=("Segoe UI", 9),
    wraplength=880,
)
hint.pack(fill=tk.X, padx=8, pady=(0, 8))

root.mainloop()
