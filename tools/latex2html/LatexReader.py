import re, os, json
from pathlib import Path
from typing import List, Dict

def safe_extract_path(text: str) -> str | None:
  if not text:
    return None

  # 移除非法字符：<>:"\|?* 以及控制字符（ASCII 0-31）
  cleaned = re.sub(r'[<>:"\\|?*\x00-\x1F]', '', text)

  # 拒绝路径穿越
  if '..' in cleaned:
    return None

  return cleaned

def read_file_sync(path):
  with open(path, mode='r', encoding='utf-8-sig') as f:
    return f.read()
  
def parse_book_info(center_text: str) -> dict:
  result = {}

  # 提取图片路径
  img_match = re.search(r'\\includegraphics\[.*?\]\{(.+?)\}', center_text)
  if img_match:
    result['cover_image'] = Path(img_match.group(1).strip())

  # 提取标题（\textbf{} + 下一行）
  title_match = re.search(r'\\textbf\{(.+?)\}\s*\\\\\[\d+pt\]\s*\\normalsize\s*(.+?)\s*\\\\', center_text, re.DOTALL)
  if title_match:
    result['title'] = title_match.group(1).strip()
    result['subtitle'] = title_match.group(2).strip()

  # 作者
  author_match = re.search(r'作者:\s*(.+)', center_text)
  if author_match:
    result['authors'] = author_match.group(1).strip()

  # 译者（包含 \href）
  translator_match = re.search(r'译者：\\href\{(.+?)\}\{(.+?)\}', center_text)
  if translator_match:
    result['translator'] = {
      'name': translator_match.group(2).strip(),
      'link': translator_match.group(1).strip()
    }

  return result

def parse_book_index(processed_content, input_dir, output_dir):

  # 处理 \subfile 命令
  subfile_regex = re.compile(r'\\subfile\{([^{}]+)\}')
  for match in subfile_regex.finditer(processed_content):
    subfile_path = safe_extract_path(match.group(1))
    if not subfile_path:
      continue

    resolved_path = input_dir / subfile_path
    if resolved_path.exists():
      try:
        print(f"Including subfile: {resolved_path.resolve()}")
        processed_content = \
          read_file_sync(resolved_path.resolve()) \
          .replace('---', '——')
      except Exception as err:
        print(f"Error including subfile {resolved_path.resolve()}: {err}")
    else:
      print(f"Warning: Could not find file for {resolved_path.resolve()}")

  book_dir_name = resolved_path.parent.name

  # 提取 \begin{document} ... \end{document} 中的内容（若为根）
  document_match = re.search(r'\\begin\{document\}([\s\S]*?)\\end\{document\}', processed_content)
  if document_match:
    processed_content = document_match.group(1)

  def extract_center_block(latex_text: str) -> str | None:
    match = re.search(r'\\begin\{center\}([\s\S]*?)\\end\{center\}', latex_text)
    if match:
      return match.group(1).strip()
    return None
  
  latex_reader_result = {}
  latex_reader_result['index_tex_path'] = str(resolved_path.as_posix())

  center_block = extract_center_block(processed_content)
  if center_block:
    info = parse_book_info(center_block)
    if info["cover_image"].exists():
      import shutil
      shutil.copy(info["cover_image"], output_dir)
    latex_reader_result['book_info'] = info

  if 'index.tex' in subfile_path:
    def get_toc(latex_text: str) -> List[Dict[str, str | int]]:
      toc = []

      pattern = re.compile(
        r'\\my(Chapter|ChapterNoContents|Subsection|Part|PartGray)\{(.*?)\}\{(.*?)\}\{(.*?)\}'
      )

      for match in pattern.finditer(latex_text):
        command_type, arg1, arg2, file_path = match.groups()
        file_path = str(Path(book_dir_name).joinpath(file_path).as_posix())

        # 提取章节编号基准，例如 "chapter1"
        chapter_match = re.search(r'chapter(\d+)/(\d+|0)\.tex$', file_path)
        if chapter_match:
          chapter_id = f"chapter{chapter_match.group(1)}"
          sub_index = int(chapter_match.group(2))
        else:
          chapter_id = None
          sub_index = None

        # 构建标题和层级
        section_type = ""
        if command_type in ('Part', 'PartGray'):
          section_type = 'Part'
          title = f"{arg1}: {arg2}".strip()
          level = 0
          parts = Path(file_path).parts
          section_index = parts[-2]
        elif command_type in ('Chapter', 'ChapterNoContents'):
          section_type = 'Chapter'
          title = f"{arg1} {arg2}".strip()
          level = 1
          if chapter_id:
            chapter_number = chapter_id.replace(section_type.lower(), "")
            section_index = f"{chapter_number}.0."
          else:
            section_index = ""
        elif command_type in ('Subsection'):
          section_type = 'Subsection'
          title = f"{arg1} {arg2}".strip()
          level = 2
          if chapter_id:
            chapter_number = chapter_id.replace(section_type.lower(), "")
            section_index = f"{chapter_number}.{sub_index}."
          else:
            section_index = ""
        else:
          continue  # skip unknown

        if section_index == "":
          section_index = Path(file_path).stem

        title = title.replace(r'\_', '_')

        toc.append({
          "type": section_type,
          "title": title,
          "index": section_index,
          "re_input_dir_path": file_path,
          "level": level
        })

      return toc
    
    toc = get_toc(processed_content)
    latex_reader_result['catalogue_info'] = toc
    #print(f"Extracted TOC: {json.dumps(toc, indent=2, ensure_ascii=False)}")

  if 'catalogue_info' in latex_reader_result:
    latex_reader_result['content_info'] = []
    for items in latex_reader_result['catalogue_info']:
      latex_reader_result['content_info'].append(
        {
          "section_name" : items["index"],
          "section_title" : items["title"],
          "section_type" : items["type"],
          "section_content" : process_tex(items['re_input_dir_path'], input_dir, output_dir)
        }
      )

  #processed_content = json.dumps(latex_reader_result, indent=2, ensure_ascii=False)

  #print(f"processed_content {processed_content}")

  return latex_reader_result

def parse_book_content(processed_content):
  paragraph_list = []
  env_names = []
  multiline_content = []

  for line in processed_content.splitlines():
    #print(repr(line))
    process_line = line#.strip()

    begin_match = re.search(r'\\begin\{([^\}]+)\}', line)
    if begin_match:
      begin_env_name = begin_match.group(1)
      env_names.append(begin_env_name)

    end_match = re.search(r'\\end\{([^\}]+)\}', line)
    if end_match:
      end_env_name = end_match.group(1)
      if env_names[-1] == end_env_name:
        env_name = env_names.pop()
      else:
        print(f"Warning: Mismatched end tag {end_env_name} for {env_names[-1]}")
        exit(-1)

    if len(env_names) > 0:
      multiline_content.append(process_line)

    if len(process_line) > 0 and len(env_names) == 0:

      if process_line[0] == '%':
        # Skip comment lines
        continue

      multiline_content.append(process_line)
      current_paragraph = "\n".join(multiline_content).strip()
      paragraph_list.append(current_paragraph)
      multiline_content.clear()

  return paragraph_list

def process_tex(file_path, input_dir, output_dir, is_root: bool = False):

  try:
    print(f"Processing {file_path}...")
    content = read_file_sync(file_path)
    processed_content = content

    if is_root:
      return parse_book_index(
        processed_content, 
        input_dir, 
        output_dir
        )
    else:
      return parse_book_content(processed_content)

  except Exception as err:
    print(f"Error processing {file_path}: {err}")
    return None
