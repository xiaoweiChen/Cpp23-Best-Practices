import fitz  # PyMuPDF
#import numpy as np
from PIL import Image

def pdf_page_to_a4_image_centered(pdf_path, output_image_path, dpi=300):
    """
    将PDF第一页居中放置在A4尺寸的白色背景上
    """
    a4_width_mm = 210
    a4_height_mm = 297
    a4_width_inch = a4_width_mm / 25.4
    a4_height_inch = a4_height_mm / 25.4
    target_width_px = int(a4_width_inch * dpi)
    target_height_px = int(a4_height_inch * dpi)

    doc = fitz.open(pdf_path)
    page = doc[0]

    # 计算缩放比例，使内容完整显示在A4内
    scale_x = target_width_px / page.rect.width
    scale_y = target_height_px / page.rect.height
    scale = min(scale_x, scale_y)
    
    # 计算缩放后的实际内容尺寸
    content_width = int(page.rect.width * scale)
    content_height = int(page.rect.height * scale)
    
    # 计算居中位置
    x_offset = (target_width_px - content_width) // 2
    y_offset = (target_height_px - content_height) // 2

    # 渲染页面
    matrix = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # 创建A4大小的白色背景
    a4_img = Image.new("RGB", (target_width_px, target_height_px), "white")
    
    # 将渲染的图片粘贴到A4画布上（居中）
    a4_img.paste(img, (x_offset, y_offset))

    # 保存
    a4_img.save(output_image_path, dpi=(dpi, dpi), quality=95)
    print(f"已成功将第一页居中保存为A4尺寸图片: {output_image_path}")
    doc.close()

# 使用
pdf_page_to_a4_image_centered("C++23 Best Practices (Jason Turner) (Z-Library).pdf", "cover.png", dpi=300)