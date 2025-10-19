#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys, re
from pathlib import Path

def main(args):
  
  input_dir = Path(args.input)
  output_dir = Path(args.output)

  book_file = input_dir / "book.tex"

  import LatexReader
  latex_content = \
    LatexReader.process_tex(
      book_file, 
      input_dir, 
      output_dir, 
      is_root=True
    )

  import Latex2html
  html_content = \
  Latex2html.latex_to_html(
    latex_content, 
    input_dir, 
    output_dir
  )

if __name__ == "__main__":

  def parse_args():
    parser = argparse.ArgumentParser(description="Convert LaTeX book to HTML")
    parser.add_argument("-i", "--input", required=True, help="输入 LaTeX 项目根目录路径")
    parser.add_argument("-o", "--output", required=True, help="输出 HTML 文件目录")
    return parser.parse_args()

  args = parse_args()
  print(f"解析参数:{args}")

  input_path = Path(args.input).resolve()
  output_dir = Path(args.output).resolve()
  print(f"输入文件: {input_path}, 输出目录: {output_dir}")

  if not input_path.is_dir():
    print(f"输入 {input_path} 不是目录！")
    sys.exit(1)
  
  main_tex_file = input_path / "book.tex"
  if not main_tex_file.is_file():
    print(f"输入 {input_path} 不包含 book.tex 文件！")
    sys.exit(1)
  print(f"找到主 LaTeX 文件: {main_tex_file}")

  Path(output_dir).mkdir(parents=True, exist_ok=True)

  main(args)
