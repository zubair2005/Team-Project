import tkinter as tk
from tkinter import ttk
from typing import Callable, Iterable, List, Sequence, Tuple


class MessageBoard(tk.Frame):
    def __init__(self, master: tk.Misc, post_callback: Callable[[str], None], fetch_callback: Callable[[], Sequence[str]]):
        super().__init__(master)
        self.post_callback = post_callback
        self.fetch_callback = fetch_callback

        tk.Label(self, text="Chat", font=("Helvetica", 12, "bold")).pack(pady=(0, 4))

        self.text = tk.Text(self, state="disabled", height=10, width=40)
        self.text.pack(fill=tk.BOTH, expand=True)

        entry_frame = tk.Frame(self)
        entry_frame.pack(fill=tk.X, pady=4)

        self.entry = tk.Entry(entry_frame)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(entry_frame, text="Refresh", command=self.refresh).pack(side=tk.RIGHT)
        tk.Button(entry_frame, text="Send", command=self._send).pack(side=tk.RIGHT, padx=4)

        self.refresh()

    def refresh(self) -> None:
        messages = self.fetch_callback()
        self.text.config(state="normal")
        self.text.delete("1.0", tk.END)
        for msg in messages:
            self.text.insert(tk.END, msg + "\n")
        self.text.config(state="disabled")

    def _send(self) -> None:
        content = self.entry.get().strip()
        if not content:
            return
        self.post_callback(content)
        self.entry.delete(0, tk.END)
        self.refresh()


class Table(ttk.Treeview):
    def __init__(self, master: tk.Misc, columns: Iterable[str]):
        super().__init__(master, columns=columns, show="headings")
        for col in columns:
            self.heading(col, text=col)
            self.column(col, width=120)

    def load_rows(self, rows: List[Sequence[str]]) -> None:
        self.delete(*self.get_children())
        for row in rows:
            self.insert("", tk.END, values=row)


class BarChart(tk.Canvas):
    def __init__(self, master: tk.Misc, width: int = 400, height: int = 240):
        super().__init__(master, width=width, height=height, background="white", highlightthickness=1, highlightbackground="#cccccc")
        self.width = width
        self.height = height

    def draw(self, data: List[Tuple[str, int]], title: str = "") -> None:
        self.delete("all")
        
        # Draw title
        if title:
            self.create_text(self.width // 2, 16, text=title, font=("Helvetica", 11, "bold"), fill="#2c3e50")

        if not data:
            self.create_text(self.width // 2, self.height // 2, text="No data", fill="#95a5a6", font=("Helvetica", 10))
            return

        labels, values = zip(*data)
        max_value = max(values) if values else 0
        if max_value == 0:
            max_value = 1

        margin = 45
        chart_height = self.height - margin * 2
        chart_width = self.width - margin * 2
        bar_width = chart_width / max(len(values), 1)

        # Draw gridlines
        for i in range(5):
            y = self.height - margin - (i * chart_height / 4)
            self.create_line(margin, y, self.width - margin, y, fill="#ecf0f1", width=1)

        # Draw bars with gradient-like effect
        colors = ["#3498db", "#2ecc71", "#9b59b6", "#e74c3c", "#f39c12", "#1abc9c"]
        
        for idx, value in enumerate(values):
            x0 = margin + idx * bar_width + 8
            x1 = margin + (idx + 1) * bar_width - 8
            bar_height = (value / max_value) * chart_height
            y0 = self.height - margin - bar_height
            y1 = self.height - margin
            
            color = colors[idx % len(colors)]
            self.create_rectangle(x0, y0, x1, y1, fill=color, outline="", width=0)
            
            # Value label above bar
            self.create_text((x0 + x1) / 2, y0 - 12, text=str(value), font=("Helvetica", 9, "bold"), fill="#2c3e50")
            
            # X-axis label (truncate if too long)
            label = str(labels[idx])
            if len(label) > 10:
                label = label[:9] + "…"
            self.create_text((x0 + x1) / 2, self.height - margin + 14, text=label, font=("Helvetica", 8), fill="#34495e")


class DualBarChart(tk.Canvas):
    def __init__(self, master: tk.Misc, width: int = 400, height: int = 240):
        super().__init__(master, width=width, height=height, background="white", highlightthickness=1, highlightbackground="#cccccc")
        self.width = width
        self.height = height

    def draw(self, data: List[Tuple[str, int, int]], labels: Tuple[str, str] = ("A", "B"), title: str = "") -> None:
        self.delete("all")
        
        # Draw title
        if title:
            self.create_text(self.width // 2, 16, text=title, font=("Helvetica", 11, "bold"), fill="#2c3e50")

        if not data:
            self.create_text(self.width // 2, self.height // 2, text="No data", fill="#95a5a6", font=("Helvetica", 10))
            return

        max_value = max(max(a, b) for _, a, b in data)
        if max_value == 0:
            max_value = 1

        margin = 45
        chart_height = self.height - margin * 2
        chart_width = self.width - margin * 2
        bar_group_width = chart_width / max(len(data), 1)
        bar_width = (bar_group_width - 10) / 2

        # Draw gridlines
        for i in range(5):
            y = self.height - margin - (i * chart_height / 4)
            self.create_line(margin, y, self.width - margin, y, fill="#ecf0f1", width=1)

        # Better colors: blue for first, green for second
        colors = ["#3498db", "#27ae60"]

        for idx, (label, val1, val2) in enumerate(data):
            base_x = margin + idx * bar_group_width
            for jdx, value in enumerate((val1, val2)):
                x0 = base_x + jdx * bar_width + 4
                x1 = x0 + bar_width - 4
                bar_height = (value / max_value) * chart_height
                y0 = self.height - margin - bar_height
                y1 = self.height - margin
                color = colors[jdx]
                self.create_rectangle(x0, y0, x1, y1, fill=color, outline="", width=0)
                self.create_text((x0 + x1) / 2, y0 - 12, text=str(value), font=("Helvetica", 9, "bold"), fill="#2c3e50")

            # X-axis label (truncate if needed)
            label_text = str(label)
            if len(label_text) > 10:
                label_text = label_text[:9] + "…"
            self.create_text(base_x + bar_group_width / 2, self.height - margin + 14, text=label_text, font=("Helvetica", 8), fill="#34495e")

        # Legend
        legend_y = margin - 24
        self.create_rectangle(margin, legend_y, margin + 14, legend_y + 14, fill=colors[0], outline="")
        self.create_text(margin + 18, legend_y + 7, text=labels[0], anchor=tk.W, font=("Helvetica", 9), fill="#2c3e50")
        self.create_rectangle(margin + 100, legend_y, margin + 114, legend_y + 14, fill=colors[1], outline="")
        self.create_text(margin + 118, legend_y + 7, text=labels[1], anchor=tk.W, font=("Helvetica", 9), fill="#2c3e50")


