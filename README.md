# PDF 转图片工具

这是一个简单的命令行工具：把 PDF 的每一页转换成一张图片。

## GUI 界面

双击运行：

```powershell
start_gui.bat
```

或者在终端运行：

```powershell
python .\pdf_to_images_gui.py
```

界面中可以选择 PDF 文件、输出目录、图片格式、DPI，以及要转换的页码范围。转换时会显示逐页进度和百分比。

## 依赖

- Python 3.10+
- Poppler 的 `pdftoppm` 命令

当前 Codex 环境已经检测到 `pdftoppm`。如果你在自己的电脑上运行时提示找不到 `pdftoppm`，请安装 Poppler，并把 `pdftoppm` 加入 `PATH`。

## 用法

```powershell
python .\pdf_to_images.py "C:\path\to\input.pdf"
```

默认会在 PDF 同目录生成一个 `PDF文件名_images` 文件夹，每页输出一张 PNG。

指定输出目录：

```powershell
python .\pdf_to_images.py "C:\path\to\input.pdf" -o "C:\path\to\images"
```

指定图片格式和清晰度：

```powershell
python .\pdf_to_images.py "C:\path\to\input.pdf" --format jpeg --dpi 300
```

只转换部分页码：

```powershell
python .\pdf_to_images.py "C:\path\to\input.pdf" --first-page 2 --last-page 5
```

如果 `pdftoppm` 不在 PATH，可以手动指定：

```powershell
python .\pdf_to_images.py "C:\path\to\input.pdf" --pdftoppm "C:\path\to\pdftoppm.exe"
```
