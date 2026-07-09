#!/usr/bin/env python
"""Small Tkinter GUI for converting PDF files to images."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from pdf_to_images import SUPPORTED_FORMATS, PdfConversionOptions, convert_pdf_to_images


class PdfToImagesApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PDF 转图片")
        self.geometry("640x420")
        self.minsize(600, 380)

        self.pdf_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.format_var = tk.StringVar(value="png")
        self.dpi_var = tk.StringVar(value="200")
        self.first_page_var = tk.StringVar()
        self.last_page_var = tk.StringVar()
        self.status_var = tk.StringVar(value="请选择 PDF 文件")
        self.last_output_dir: Path | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        root = ttk.Frame(self, padding=18)
        root.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(1, weight=1)

        ttk.Label(root, text="PDF 文件").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(root, textvariable=self.pdf_var).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(root, text="选择", command=self.choose_pdf).grid(row=0, column=2)

        ttk.Label(root, text="输出目录").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(root, textvariable=self.output_var).grid(row=1, column=1, sticky="ew", padx=8)
        ttk.Button(root, text="选择", command=self.choose_output_dir).grid(row=1, column=2)

        settings = ttk.LabelFrame(root, text="转换设置", padding=12)
        settings.grid(row=2, column=0, columnspan=3, sticky="ew", pady=14)
        settings.columnconfigure(1, weight=1)
        settings.columnconfigure(3, weight=1)

        ttk.Label(settings, text="图片格式").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Combobox(
            settings,
            textvariable=self.format_var,
            values=SUPPORTED_FORMATS,
            state="readonly",
            width=12,
        ).grid(row=0, column=1, sticky="w", padx=8)

        ttk.Label(settings, text="DPI").grid(row=0, column=2, sticky="w", padx=(18, 0))
        ttk.Spinbox(settings, from_=72, to=600, increment=10, textvariable=self.dpi_var, width=10).grid(
            row=0, column=3, sticky="w", padx=8
        )

        ttk.Label(settings, text="起始页").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(settings, textvariable=self.first_page_var, width=14).grid(
            row=1, column=1, sticky="w", padx=8
        )
        ttk.Label(settings, text="结束页").grid(row=1, column=2, sticky="w", padx=(18, 0))
        ttk.Entry(settings, textvariable=self.last_page_var, width=14).grid(
            row=1, column=3, sticky="w", padx=8
        )

        actions = ttk.Frame(root)
        actions.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(4, 12))
        actions.columnconfigure(0, weight=1)

        self.convert_button = ttk.Button(actions, text="开始转换", command=self.start_conversion)
        self.convert_button.grid(row=0, column=1, padx=6)
        self.open_button = ttk.Button(actions, text="打开输出目录", command=self.open_output_dir, state="disabled")
        self.open_button.grid(row=0, column=2)

        self.progress = ttk.Progressbar(root, mode="determinate", maximum=100)
        self.progress.grid(row=4, column=0, columnspan=3, sticky="ew", pady=8)

        ttk.Label(root, textvariable=self.status_var).grid(row=5, column=0, columnspan=3, sticky="w")

    def choose_pdf(self) -> None:
        filename = filedialog.askopenfilename(
            title="选择 PDF 文件",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if filename:
            self.pdf_var.set(filename)
            if not self.output_var.get():
                pdf_path = Path(filename)
                self.output_var.set(str(pdf_path.with_name(f"{pdf_path.stem}_images")))

    def choose_output_dir(self) -> None:
        dirname = filedialog.askdirectory(title="选择输出目录")
        if dirname:
            self.output_var.set(dirname)

    def parse_optional_int(self, value: str) -> int | None:
        value = value.strip()
        return int(value) if value else None

    def start_conversion(self) -> None:
        try:
            pdf_path = Path(self.pdf_var.get().strip())
            output_text = self.output_var.get().strip()
            options = PdfConversionOptions(
                pdf_path=pdf_path,
                output_dir=Path(output_text) if output_text else None,
                image_format=self.format_var.get(),
                dpi=int(self.dpi_var.get().strip()),
                first_page=self.parse_optional_int(self.first_page_var.get()),
                last_page=self.parse_optional_int(self.last_page_var.get()),
            )
        except ValueError:
            messagebox.showerror("输入错误", "DPI 和页码必须是数字。")
            return

        self.convert_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.progress.configure(value=0)
        self.status_var.set("正在读取 PDF 页数...")
        threading.Thread(target=self.run_conversion, args=(options,), daemon=True).start()

    def run_conversion(self, options: PdfConversionOptions) -> None:
        try:
            output_dir, files = convert_pdf_to_images(options, self.report_progress)
        except Exception as exc:
            self.after(0, self.finish_with_error, str(exc))
            return
        self.after(0, self.finish_successfully, output_dir, len(files))

    def report_progress(self, done: int, total: int, image_path: Path) -> None:
        self.after(0, self.update_progress, done, total, image_path)

    def update_progress(self, done: int, total: int, image_path: Path) -> None:
        percent = int(done / total * 100)
        self.progress.configure(value=percent)
        self.status_var.set(
            f"正在转换：{done} / {total} 页 ({percent}%)，已生成 {image_path.name}"
        )

    def finish_successfully(self, output_dir: Path, count: int) -> None:
        self.progress.configure(value=100)
        self.convert_button.configure(state="normal")
        self.open_button.configure(state="normal")
        self.last_output_dir = output_dir
        self.status_var.set(f"转换完成：生成 {count} 张图片，目录：{output_dir}")
        messagebox.showinfo("完成", f"已生成 {count} 张图片。")

    def finish_with_error(self, message: str) -> None:
        self.progress.configure(value=0)
        self.convert_button.configure(state="normal")
        self.status_var.set("转换失败")
        messagebox.showerror("转换失败", message)

    def open_output_dir(self) -> None:
        if not self.last_output_dir:
            return
        if os.name == "nt":
            os.startfile(self.last_output_dir)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(self.last_output_dir)], check=False)
        else:
            subprocess.run(["xdg-open", str(self.last_output_dir)], check=False)


if __name__ == "__main__":
    app = PdfToImagesApp()
    app.mainloop()
