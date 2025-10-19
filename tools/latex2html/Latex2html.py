import os, re
import json
import html
import string
from pathlib import Path
from collections import defaultdict

# 生成HTML页面框架
def create_html_template(title, content, headExtra = ''):
  mathjax_config = {
    "tex": {
      "inlineMath": [["$", "$"], ["\\(", "\\)"]],
      "displayMath": [["$$", "$$"], ["\\[", "\\]"]],
      "processEscapes": "true",
      "tags": "ams"
    },
    "svg": {
      "fontCache": "global"
    }
  }

  content = f'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link rel="stylesheet" href="styles.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism-tomorrow.min.css">
  <script>
    window.MathJax = {mathjax_config};
  </script>
  {headExtra}
</head>

<body>
  <div class="container">
    {content}
  </div>
''' 
  
  html_template_path = os.path.join(os.path.dirname(__file__), "template.html.in")
  with open(html_template_path, mode='r', encoding='utf-8-sig') as f:
    content += f.read()

  return content

def generate_index(latex_content, output_dir):
  book_info = latex_content['book_info']

  header_part = f'''
    <header>
      <h1 style="text-align: center;" style="font-size:40px;">{book_info["title"]}</h1>
      <p class="subtitle">{book_info["subtitle"]}</p>
      <div class="author-info">
        <p>作者：{book_info["authors"]}</p>
        <p>译者：<a href="{book_info["translator"]["link"]}">{book_info["translator"]["name"]}</a></p>
      </div>
      <img src="{book_info["cover_image"]}" alt="Book Cover" class="book-cover">
    </header>
'''
  
  header_part += generate_toc(latex_content['catalogue_info'])
  
  index_html = create_html_template(book_info["title"], header_part, headExtra='')

  with open(output_dir / "index.html", "w", encoding="utf-8") as f:
    f.write(index_html)

  # 复制 styles.css 到输出目录
  import shutil
  src_css = os.path.join(os.path.dirname(__file__), "styles.css")
  dst_css = os.path.join(output_dir, "styles.css")
  try:
    shutil.copy2(src_css, dst_css)
  except Exception as e:
    print(f"复制 styles.css 失败: {e}")

def generate_toc(catalogue_info):
  if not catalogue_info:
    return '<div class="toc"><h2>目录</h2><p>未找到章节内容</p></div>'

  toc_html = '\n    <div class="toc"><h2 style="text-align: center;">目录</h2><ul>\n'

  for chapter in catalogue_info:
    filename = chapter['index'] + '.html'
    title = chapter['title']
    level = chapter.get('level', 1)

    match level:
      case 0:
        # 部分标题
        toc_html += f'\n      <li class="toc-part"><a href="{filename}" style="font-size:20px;">{title}</a></li>\n'
      case 1:
        # 章节标题
        toc_html += f'\n      <li class="toc-chapter"><a href="{filename}" style="font-size:18px;">{title}</a></li>\n'
      case 2:
        # 小节标题
        toc_html += f'      <li class="toc-section" style="margin-left: 20px;" style="font-size:16px;"><a href="{filename}">{title}</a></li>\n'

  toc_html += '\n    </ul></div>\n'
  return toc_html

def create_navigation(chapters, current_index):
  prev_link = ''
  next_link = ''
  toc_link = '<div class="back-to-toc" style="text-align:left"><a href="index.html">返回目录</a></div>'

  if current_index > 0:
    prev_chapter = chapters[current_index - 1]
    prev_filename = prev_chapter["section_name"] + '.html'
    prev_link = f'<a href="{prev_filename}" class="prev-link">« 上一章：{prev_chapter["section_title"]}</a>'
  else:
    prev_link = '<span></span>'

  if current_index < len(chapters) - 1:
    next_chapter = chapters[current_index + 1]
    next_filename = next_chapter["section_name"] + '.html'
    next_link = f'<a href="{next_filename}" class="next-link">下一章：{next_chapter["section_title"]} »</a>'
  else:
    next_link = '<span></span>'

  return f'''
<div class="navigation">
  {prev_link}
  {next_link}
</div>
''', toc_link

def convert_itemize_to_html(latex_text):
  # 替换 \begin{itemize} 和 \end{itemize}
  text = latex_text.replace(r'\begin{itemize}', '<ul>')
  text = text.replace(r'\end{itemize}', '</ul>')

  begin_types = re.findall(r'\\begin\{([^}]+)\}', text)
  for env_name in begin_types:
    match env_name:
      case 'enumerate':
        text = convert_enumerate_to_html(text)
      case 'cpp':
        text = process_cpp_env(text)
      case 'myTip':
        text = process_my_tip(text)
      case 'myNotic':
        text = process_my_notic(text)
      case '_':
        pass

  def replacement_function(match):
    # match.group(1) 对应 \verb|...| 部分
    # match.group(2) 对应 -> 部分
    verb_content = match.group(1)
    arrow = match.group(2)
    
    if verb_content is not None:
      # 如果匹配到了 \verb|...|，则原样返回这部分内容
      return verb_content
    else:
      # 如果匹配到了 ->，则将其替换为 'A' (或您想要的任何内容，如 '&rarr;')
      return '&rarr;'
  text = re.sub(r'(\\verb\|[^|]*\|)|(->)', replacement_function, text)

  text = text.replace('---', '——')
  text = text.replace(r'\#', '#')
  text = text.replace(r'\%', '%')
  text = text.replace(r'-{}-', '--')
  text = text.replace(r'\_', '_')
  text = text.replace(r'\&', '&')
  #text = text.replace('->', '&rarr;')
  text = re.sub(r'\\verb(.)(.+?)\1', r'\2', text)
  text = re.sub(
    r'\\url\{([^}]+)\}',  # 匹配 \url{任意内容直到}
    r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
    text
  )
  text = re.sub(r'\\footnote\{(.*?)\}', r'<span class="footnote">\1</span>', text)

  # 处理 \item
  def item_replacer(match):
    content = match.group(1)#.strip()

    def matches_tag_pattern(s):
      status = re.search(r'<\/?[a-zA-Z]+\b[^>]*>', s) is not None
      return status

    content_list = []
    for line in content.splitlines():
      if '&rarr;' in line:
        line_list = []
        for sec in line.split('&rarr;'):
          line_list.append(f"{html.escape(sec)}")
        content_list.append(f"<p>{'&rarr;'.join(line_list)}</p>")
      elif matches_tag_pattern(line):
        content_list.append(f"<p>{line}</p>")
      else:
        content_list.append(f"<p>{html.escape(line)}</p>")

    content = "\n".join(content_list)
    return f'  <li>{content}</li>' if content else '  <li></li>'

  text = re.sub(r'\\item\s*\n?(.*?)(?=\\item|\\begin|\\end|$)', item_replacer, text, flags=re.DOTALL)

  return text

def convert_enumerate_to_html(latex_text):
  # 替换 \begin{enumerate} 和 \end{enumerate}
  text = latex_text.replace(r'\begin{enumerate}', '<ol>')
  text = text.replace(r'\end{enumerate}', '</ol>')

  begin_types = re.findall(r'\\begin\{([^}]+)\}', text)
  for env_name in begin_types:
    match env_name:
      case 'enumerate':
        text = convert_enumerate_to_html(text)
      case 'cpp':
        text = process_cpp_env(text)
      case 'myTip':
        text = process_my_tip(text)
      case 'myNotic':
        text = process_my_notic(text)
      case '_':
        pass

  text = text.replace('---', '——')
  text = text.replace(r'\#', '#')
  text = text.replace(r'\%', '%')
  text = text.replace(r'\_', '_')
  text = text.replace(r'\&', '&')
  text = text.replace('->', '&rarr;')
  text = re.sub(r'\\verb(.)(.+?)\1', r'\2', text)
  text = re.sub(
    r'\\url\{([^}]+)\}',  # 匹配 \url{任意内容直到}
    r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
    text
  )

  # 处理 \item
  def item_replacer(match):

    content = match.group(1)#.strip()

    def matches_tag_pattern(s):
      status = re.search(r'<\/?[a-zA-Z]+\b[^>]*>', s) is not None
      return status

    content_list = []
    for line in content.splitlines():
      if '&rarr;' in line:
        line_list = []
        for sec in line.split('&rarr;'):
          line_list.append(f"{html.escape(sec)}")
        content_list.append(f"<p>{'&rarr;'.join(line_list)}</p>")
      elif matches_tag_pattern(line):
        content_list.append(f"<p>{line}</p>")
      else:
        content_list.append(f"<p>{html.escape(line)}</p>")
    return f'  <li>{content}</li>' if content else '  <li></li>'

  text = re.sub(r'\\item\s*\n?(.*?)(?=\\item|\\begin|\\end|$)', item_replacer, text, flags=re.DOTALL)

  return text

def convert_no_multi_row_col_longtable_to_html(html):
  def table_replacer(match):
    raw_content = match.group(1)
    # 清理辅助结构和注释
    content = re.sub(r'\\endfirsthead[\s\S]*?\\endhead', '', raw_content)
    content = re.sub(r'\\multicolumn\{.*?\}\{.*?\}\{.*?\}\s*\\\\', '', content)
    content = re.sub(r'\\hline', '', content)
    content = re.sub(r'\\cline\{[^}]*\}', '', content)  # 移除\cline

    # 保护百分号，去注释
    content = content.replace(r'\%', 'TEMP_ESCAPED_PERCENT')
    content = re.sub(r'%.*$', '', content, flags=re.MULTILINE)
    content = content.replace('TEMP_ESCAPED_PERCENT', r'\%').strip()

    # 清理表格列格式声明
    content = re.sub(r'^\s*\{[|lcr\s]*\}\s*', '', content, flags=re.MULTILINE)

    # 保护 AT\&T
    content = re.sub(r'AT\\&T', 'TEMP_ATT_MARKER', content)

    # 保护行内 \\（非行尾）
    lines = content.split('\n')
    processed_lines = [re.sub(r'\\\\(?!\s*$)', 'TEMP_LINEBREAK_MARKER', line) for line in lines]
    content = '\n'.join(processed_lines)

    # 拆分为行
    rows = [row.strip() for row in re.split(r'\\\\\s*', content) if row.strip()]

    html_table = '<table border=\"1\">\n'
    header_parsed = False

    for row in rows:
      temp_row = row.replace(r'\&', 'TEMP_ESCAPED_AMP')
      columns = [col.replace('TEMP_ESCAPED_AMP', r'\&').strip() for col in temp_row.split('&')]

      if not header_parsed:
        html_table += '  <thead>\n    <tr>\n'
        for col in columns:
          content = re.sub(r'\\textbf\{(.*?)\}', r'<strong>\1</strong>', col)
          content = re.sub(r'\\parbox\[t\]\{[^}]*\}\{([^}]*)\}', r'\1', content, flags=re.DOTALL)
          content = content.replace('TEMP_ATT_MARKER', 'AT&T')
          content = content.replace('TEMP_LINEBREAK_MARKER', '<br>')
          content = re.sub(r'AT\\&T', 'AT&T', content)
          content = re.sub(r'\bATT\b', 'AT&T', content)
          content = re.sub(r'\\begin\{tabular\}\[c\]\{@\{\}l@\{\}\}', '', content)
          content = re.sub(r'\\end\{tabular\}', '', content)
          content = content.replace(r'\$', '&#36;')
          content = content.replace(r'\%', '&#37;')
          content = content.replace(r'\&', '&')
          content = content.replace(r'\_', '&#95;')
          content = content.replace(r'\{', '&#123;')
          content = content.replace(r'\}', '&#125;')
          html_table += f'      <th>{content}</th>\n'
        html_table += '    </tr>\n  </thead>\n  <tbody>\n'
        header_parsed = True
      else:
        html_table += '    <tr>\n'
        for col in columns:
          content = col
          content = re.sub(r'\\parbox\[t\]\{[^}]*\}\{([^}]*)\}', r'\1', content, flags=re.DOTALL)
          content = content.replace('TEMP_ATT_MARKER', 'AT&T')
          content = content.replace('TEMP_LINEBREAK_MARKER', '<br>')
          content = re.sub(r'AT\\&T', 'AT&T', content)
          content = re.sub(r'\bATT\b', 'AT&T', content)
          content = re.sub(r'\\begin\{tabular\}\[c\]\{@\{\}l@\{\}\}', '', content)
          content = re.sub(r'\\end\{tabular\}', '', content)
          content = content.replace(r'\$', '&#36;')
          content = content.replace(r'\%', '&#37;')
          content = content.replace(r'\&', '&')
          content = content.replace(r'\_', '&#95;')
          content = content.replace(r'\{', '&#123;')
          content = content.replace(r'\}', '&#125;')
          html_table += f'      <td>{content}</td>\n'
        html_table += '    </tr>\n'
    html_table += '  </tbody>\n</table>\n'
    return html_table

  html = html.replace('---', '——')
  html = re.sub(r'^\\begin\{longtable\}.*$', r'\\begin{longtable}', html, flags=re.MULTILINE)
  html = re.sub(r'\\begin\{longtable\}\s*([\s\S]*?)\\end\{longtable\}', table_replacer, html)
  return html

def convert_longtable_to_html(ori_latex):
  def table_replacer(match):
    raw_content = match.group(1)

    content = re.sub(r'\\endfirsthead[\s\S]*?\\endhead', '', raw_content)
    content = re.sub(r'\\hline', '', content)
    content = content.replace(r'\%', 'TEMP_ESCAPED_PERCENT')
    content = re.sub(r'%.*$', '', content, flags=re.MULTILINE)
    content = content.replace('TEMP_ESCAPED_PERCENT', r'\%').strip()
    content = re.sub(r'^\s*\{[|lcr\s]*\}\s*', '', content, flags=re.MULTILINE)

    lines = re.split(r'\\\\\s*', content)

    have_multi_row_or_col = False
    for line in lines:

      if not line.strip():
        continue

      if have_multi_row_or_col:
        break

      tokens = re.split(r'(?<!\\)&', line)
      for token in tokens:
        token = token.strip()

        mrow = re.match(r'\\multirow\{(\d+)\}\{[^\}]*\}\{(.*)\}', token)
        mcol = re.match(r'\\multicolumn\{(\d+)\}\{[^\}]*\}\{(.*)\}', token)

        if mrow or mcol:
          have_multi_row_or_col = True
          break

    if not have_multi_row_or_col:
      return match.group(0), False
    
    rows = []
    for line in lines:

      if not line.strip():
        continue

      cols = []
      tokens = re.split(r'(?<!\\)&', line)
      for token in tokens:
        token = token.strip()
        rowspan = 1
        colspan = 1

        mrow = re.match(r'\\multirow\{(\d+)\}\{[^\}]*\}\{(.*)\}', token)
        if mrow:
          rowspan = int(mrow.group(1))
          token = mrow.group(2).strip()

        mcol = re.match(r'\\multicolumn\{(\d+)\}\{[^\}]*\}\{(.*)\}', token)
        if mcol:
          colspan = int(mcol.group(1))
          token = mcol.group(2).strip()

        cols.append({
          'content': token,
          'rowspan': rowspan,
          'colspan': colspan
        })
      rows.append(cols)

    # 初步预估最大列数
    max_cols = max(sum(cell['colspan'] for cell in row) for row in rows)
    table_matrix = []

    for _ in range(len(rows)):
      table_matrix.append([None] * max_cols)

    for r, row in enumerate(rows):
      # 防止 \multirow 超出当前行数
      max_rowspan = max((cell['rowspan'] for cell in row), default=1)
      while len(table_matrix) < r + max_rowspan:
        table_matrix.append([None] * max_cols)

      col_pos = 0
      for cell in row:
        # 跳过已占用位置
        while col_pos < len(table_matrix[r]) and table_matrix[r][col_pos] is not None:
          col_pos += 1

        for dr in range(cell['rowspan']):
          for dc in range(cell['colspan']):
            rr = r + dr
            cc = col_pos + dc

            # 确保行足够长
            while cc >= len(table_matrix[rr]):
              table_matrix[rr].append(None)

            if dr == 0 and dc == 0:
              table_matrix[rr][cc] = cell
            else:
              table_matrix[rr][cc] = 'SPAN'

        col_pos += cell['colspan']

    # 转换为 HTML
    html = '<table border="1">\n'
    for row in table_matrix:
      html += '  <tr>\n'
      for cell in row:
        if cell is None or cell == 'SPAN':
          continue
        attrs = ''
        if cell['rowspan'] > 1:
          attrs += f' rowspan="{cell["rowspan"]}"'
        if cell['colspan'] > 1:
          attrs += f' colspan="{cell["colspan"]}"'
        if not "cline" in cell["content"]:
          html += f'    <td{attrs}>{cell["content"]}</td>\n'
      html += '  </tr>\n'
    html += '</table>\n'
    return html, True

  latex = ori_latex.replace('---', '——')
  latex = re.sub(r'^\\begin\{longtable\}.*$', r'\\begin{longtable}', latex, flags=re.MULTILINE)
  #latex = re.sub(r'\\begin\{longtable\}\s*([\s\S]*?)\\end\{longtable\}', table_replacer, latex)
  #longtable_matches = re.finditer(r'\\begin\{longtable\}.*?\\end\{longtable\}', latex, flags=re.DOTALL)
  longtable_matches = re.finditer(r'\\begin\{longtable\}(.*?)\\end\{longtable\}', latex, flags=re.DOTALL)

  out_latex = ""
  have_multi_row_or_col = False
  if longtable_matches:
    for match in longtable_matches:
      out_latex, have_multi_row_or_col = table_replacer(match)

  if not have_multi_row_or_col:
    out_latex = convert_no_multi_row_col_longtable_to_html(ori_latex)

  return out_latex

def process_cpp_env(html_text):
  def replacer(match):
    code = match.group(1)
    # 去掉每行结尾空格
    lines = [line.rstrip() for line in code.splitlines()]

    # 过滤掉前置空行
    while lines and lines[0] == '':
      lines = lines[1:]

    cleaned_code = '\n'.join(lines)
    escaped_code = html.escape(cleaned_code)
    return f'<pre class="line-numbers"><code class="language-cpp">{escaped_code}</code></pre>'

  html_text = re.sub(r'\\begin\{cpp\}([\s\S]*?)\\end\{cpp\}', replacer, html_text)
  return html_text

def process_rust_env(html_text):
  def replacer(match):
    code = match.group(1)
    # 去掉每行结尾空格
    lines = [line.rstrip() for line in code.splitlines()]
    
    # 过滤掉前置空行
    while lines and lines[0] == '':
      lines = lines[1:]

    cleaned_code = '\n'.join(lines)
    return f'<pre class="line-numbers"><code class="language-rust">{cleaned_code}</code></pre>'

  html_text = re.sub(r'\\begin\{rust\}([\s\S]*?)\\end\{rust\}', replacer, html_text)
  return html_text

def process_shell_env(html_text):
  def shell_replacer(match):
    content = match.group(1)
    # HTML转义
    clean_content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').strip()
    if not clean_content:
      clean_content = '# (此处内容已省略)'
    return f'<pre><code class="language-shell">{clean_content}</code></pre>'

  html_text = re.sub(r'\\begin\{shell\}([\s\S]*?)\\end\{shell\}', shell_replacer, html_text)
  return html_text

def process_my_tip(html):
  def replacer(match):
    import html
    title = match.group(1)
    content = match.group(2)

    title = title.replace(r'\_', '_')
    content = content.replace(r'\_', '_')

    paragraphs = []
    match_type_map =  defaultdict(int)
    in_block = False
    for p in content.splitlines():
      begin_match = re.search(r'\\begin\{([^\}]+)\}', p)
      end_match = re.search(r'\\end\{([^\}]+)\}', p)

      if begin_match:
        env_name_begin = begin_match.group(1)
        match_type_map[env_name_begin] += 1
        paragraphs.append(p)
        in_block = True
      elif end_match:
        env_name_end = end_match.group(1)
        match_type_map[env_name_end] -= 1
        paragraphs.append(p)
        if match_type_map[env_name_end] == 0:
          in_block = False
      elif in_block:
        paragraphs.append(p)
      else:
        if '<a href=' in p:
          paragraphs.append(f'<p class="zh">{p.strip()}</p>')
        else:
          p = p.replace('->;', '&rarr;')
          p = re.sub(r'\\verb(.)(.+?)\1', r'\2', p)
          paragraphs.append(f'<p class="zh">{html.escape(p.strip())}</p>')

    inner_html = '\n'.join(paragraphs)

    begin_types = re.findall(r'\\begin\{([^}]+)\}', inner_html)

    for env_name in begin_types:
      match env_name:
        case 'itemize':
          inner_html = convert_itemize_to_html(inner_html)
        case 'enumerate':
          inner_html = convert_enumerate_to_html(inner_html)
        case 'cpp':
          inner_html = process_cpp_env(inner_html)
        case '_':
          pass

    return f'<div class="tip-box tip"><strong>{title}</strong>{inner_html}</div>'

  html = html.replace('---', '——')
  html = re.sub(
    r'\\url\{([^}]+)\}',  # 匹配 \url{任意内容直到}
    r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
    html
  )
  html = re.sub(r'\\begin\{myTip\}\{(.*?)\}([\s\S]*?)\\end\{myTip\}', replacer, html)
  return html

def process_my_notic(html):
  def replacer(match):
    import html
    title = match.group(1)
    content = match.group(2)

    title = title.replace(r'\_', '_')
    content = content.replace(r'\_', '_')

    paragraphs = []
    match_type_map =  defaultdict(int)
    in_block = False
    for p in content.splitlines():
      begin_match = re.search(r'\\begin\{([^\}]+)\}', p)
      end_match = re.search(r'\\end\{([^\}]+)\}', p)

      if begin_match:
        env_name_begin = begin_match.group(1)
        match_type_map[env_name_begin] += 1
        paragraphs.append(p)
        in_block = True
      elif end_match:
        env_name_end = end_match.group(1)
        match_type_map[env_name_end] -= 1
        paragraphs.append(p)
        if match_type_map[env_name_end] == 0:
          in_block = False
      elif in_block:
        paragraphs.append(p)
      else:
        if '<a href=' in p:
          paragraphs.append(f'<p class="zh">{p.strip()}</p>')
        else:
          p = p.replace('->;', '&rarr;')
          p = re.sub(r'\\verb(.)(.+?)\1', r'\2', p)
          paragraphs.append(f'<p class="zh">{html.escape(p.strip())}</p>')

    inner_html = '\n'.join(paragraphs)

    begin_types = re.findall(r'\\begin\{([^}]+)\}', inner_html)

    for env_name in begin_types:
      match env_name:
        case 'itemize':
          inner_html = convert_itemize_to_html(inner_html)
        case 'enumerate':
          inner_html = convert_enumerate_to_html(inner_html)
        case 'cpp':
          inner_html = process_cpp_env(inner_html)
        case '_':
          pass

    return f'<div class="tip-box note"><strong>{title}</strong>{inner_html}</div>'

  html = html.replace('---', '——')
  html = re.sub(r'\\url\{(https?://[^\}]+)\}', r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>', html)
  html = re.sub(r'\\begin\{myNotic\}\{(.*?)\}([\s\S]*?)\\end\{myNotic\}', replacer, html)
  return html

def convert_my_graphic(html, image_root_dir, output_dir):
  def replacer(match):
    import shutil
    scale = match.group(1)
    image_path = match.group(2)

    ori_image_path = image_root_dir / image_path
    if os.path.exists(ori_image_path):
      image_dist_dir = output_dir / Path(image_path).parent
      os.makedirs(image_dist_dir, exist_ok=True)
      shutil.copy2(ori_image_path, image_dist_dir)
    else:
      print(f"Warning: 图片文件 {image_path} 不存在，无法复制到输出目录。")
      exit(-10)

    caption = match.group(3)
    percentage = float(scale) * 100
    return f'''
    <div class="image-block" style="text-align: center;">
      <div><img src="{image_path}" style="width: {percentage}%;" alt="{caption}"></div>
      <div class="caption">{caption}</div>
    </div>'''
  return re.sub(r'\\myGraphic\{([\d.]+)\}\{(.*?)\}\{(.*?)\}', replacer, html)

def convert_center_to_html(html_text):
  html_text = html_text.replace('---', '——')
  html_text = re.sub(r'\\textbf\{(.*?)\}', r'<strong>\1</strong>', html_text)
  html_text = re.sub(r'\\textit\{(.*?)\}', r'<em>\1</em>', html_text)
  html_text = re.sub(r'\\begin\{center\}([\s\S]*?)\\end\{center\}', r'<div style="text-align:center">\1</div>', html_text)
  return html_text

def convert_flushright_to_html(html_text):
  html_text = html_text.replace('---', '——')
  html_text = re.sub(r'\\textbf\{(.*?)\}', r'<strong>\1</strong>', html_text)
  html_text = re.sub(r'\\textit\{(.*?)\}', r'<em>\1</em>', html_text)
  html_text = re.sub(r'\\begin\{flushright\}([\s\S]*?)\\end\{flushright\}', r'<div style="text-align:right">\1</div>', html_text)
  html_text = re.sub(r'\\hspace\*{\\fill}', '<br>', html_text)
  html_text = "\n".join(f"<p>{line}</p>" for line in html_text.splitlines())
  
  return html_text

def process_latex_env(paragraph_content):
  begin_match = re.search(r'\\begin\{([^\}]+)\}', paragraph_content)

  if not begin_match:
    return paragraph_content, False
  
  env_name = begin_match.group(1)

  match env_name:
    case 'flushright':
      paragraph_content = convert_flushright_to_html(paragraph_content)
    case 'itemize':
      paragraph_content = convert_itemize_to_html(paragraph_content)
    case 'enumerate':
      paragraph_content = convert_enumerate_to_html(paragraph_content)
    case 'center':
      paragraph_content = convert_center_to_html(paragraph_content)
    case 'longtable':
      paragraph_content = convert_longtable_to_html(paragraph_content)
    case 'shell':
      paragraph_content = process_shell_env(paragraph_content)
    case 'cpp':
      paragraph_content = process_cpp_env(paragraph_content)
    case 'rust':
      paragraph_content = process_rust_env(paragraph_content)
    case 'myTip':
      paragraph_content = process_my_tip(paragraph_content)
    case 'myNotic':
      paragraph_content = process_my_notic(paragraph_content)
    case '_':
      print("unkown environment:", env_name)
      exit(-10)

  return paragraph_content, True

def process_special_paragraph(paragraph_content, image_root_dir, output_dir):
  paragraph_content, matched_latex_env = process_latex_env(paragraph_content)

  if matched_latex_env:
    return paragraph_content
  else:
    # 替换特殊字符
    paragraph_content = paragraph_content.replace(r'>{}>', '>>')
    paragraph_content = paragraph_content.replace(r'<{}<', '<<')
    paragraph_content = paragraph_content.replace(r'-{}-', '--')
    paragraph_content = paragraph_content.replace(r'\#', '#')
    paragraph_content = paragraph_content.replace(r'\%', '%')
    paragraph_content = paragraph_content.replace(r'\_', '_')
    paragraph_content = paragraph_content.replace(r'\&', '&')
    paragraph_content = paragraph_content.replace(r'\}', '}')
    paragraph_content = paragraph_content.replace(r'\{', '{')
    paragraph_content = paragraph_content.replace('---', '——')

    paragraph_content = html.escape(paragraph_content)

    paragraph_content = paragraph_content.replace('-&gt;', '&rarr;')

    paragraph_content = convert_my_graphic(paragraph_content, image_root_dir, output_dir)
    
    paragraph_content = re.sub(r'\\hspace\*{\\fill}', '<br>', paragraph_content)
    paragraph_content = re.sub(r'\\mySubsubsection\{(.*?)\}\{(.*?)\}', r'<h4 class="filename">\1 \2</h4>', paragraph_content)
    paragraph_content = re.sub(r'\\mySubsection\{(.*?)\}\{(.*?)\}', r'<h3 class="subsection">\1 \2</h3>', paragraph_content)
    paragraph_content = re.sub(r'\\mySubsectionNoFile\{(.*?)\}\{(.*?)\}', r'<h3 class="subsection">\1\2</h3>', paragraph_content)
    paragraph_content = re.sub(r'\\mySamllsectionNoContent\{(.*?)\}', r'<h3 class="samllsection">\1</h3>', paragraph_content)
    paragraph_content = re.sub(r'\\textbf\{(.*?)\}', r'<strong>\1</strong>', paragraph_content)
    paragraph_content = re.sub(r'\\textit\{(.*?)\}', r'<em>\1</em>', paragraph_content)
    paragraph_content = re.sub(r'\\texttt\{(.*?)\}', r'<code>\1</code>', paragraph_content)
    paragraph_content = re.sub(r'\\href\{(.*?)\}\{(.*?)\}', r'<a href="\1">\2</a>', paragraph_content)
    paragraph_content = re.sub(
      r'\\url\{([^}]+)\}',  # 匹配 \url{任意内容直到}
      r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
      paragraph_content
    )
    paragraph_content = re.sub(r'\$\s*\\sim\s*\$', '~', paragraph_content)
    paragraph_content = re.sub(r'\\verb(.)(.+?)\1', r'\2', paragraph_content)
    paragraph_content = re.sub(r'\\footnote\{(.*?)\}', r'<span class="footnote">\1</span>', paragraph_content)
    
    paragraph_content = re.sub(r'\\filename\{(.*?)\}', r'<div class="filename">\1</div>', paragraph_content)

    return f'<p class="zh">{paragraph_content}</p>'

def generate_content(latex_content, input_dir, output_dir):
  content_info = latex_content['content_info']
  book_info = latex_content['book_info']
  catalogue_info = latex_content['catalogue_info']

  index_tex_path = latex_content['index_tex_path']
  book_dir_name = Path(index_tex_path).parent.name
  image_root_dir = Path(input_dir) / book_dir_name

  for section_index, section_info in enumerate(content_info):
    output_path = output_dir / f"{section_info['section_name']}.html"

    content_lines = []
    for paragraph_line in section_info['section_content']:
      processed_line = process_special_paragraph(paragraph_line, image_root_dir, output_dir)
      if len(processed_line) > 0:
        content_lines.append(f"{processed_line}")

    if len(content_lines) > 0:

      section = ""

      section_type = section_info['section_type']
      match section_type:
        case 'Part':
          section = f'<div class="part-header"><h1>{catalogue_info[section_index]["title"]}</h1></div>'
        case 'Chapter':
          section = f'<section class="chapter"><h1 class="chapter-title">{catalogue_info[section_index]["title"]}</h1></section>'
        case 'Subsection':
          section = f'<section class="section"><h1 class="section-title">{catalogue_info[section_index]["title"]}</h1></section>'
        case '_':
          pass

      navigation, toc_link = create_navigation(content_info, section_index)
      title =  section_info['section_title'] + ' - ' + book_info['title']
      content = '\n'.join(content_lines)
      content_final = f'''
<div class="chapter-container">
  {navigation}{toc_link}
  {section}
  {content}
  {toc_link}{navigation}
</div>
'''
      
      final_html = create_html_template(title, content_final)

      with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html)

def latex_to_html(latex_content, input_dir, output_dir):
  generate_index(latex_content, output_dir)
  generate_content(latex_content, input_dir, output_dir)

