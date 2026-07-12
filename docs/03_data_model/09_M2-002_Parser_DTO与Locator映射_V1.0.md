# M2-002：Parser DTO与Locator映射 V1.0

> 本文定义应用层接口，不修改17类核心对象。

---

## 1. 新增输入DTO

建议：

```python
class WebInput:
    url: HttpUrl | None
    path: Path | None
    content_selector: str | None
    max_bytes: int | None

class PdfInput:
    path: Path
    page_ranges: list[PageRange]
    table_mode: Literal["off", "best_effort"]
    max_bytes: int | None
    max_pages: int | None

class TranscriptInput:
    path: Path
    format: Literal["srt", "vtt"] | None
```

每种输入必须满足：

```text
合法来源只有一个
```

例如 WebInput 不允许同时设置 path 和 url。

---

## 2. ParserConfig

```python
class ParserConfig:
    parser_name: str
    parser_version: str
    options: dict[str, JSONScalar]
    config_hash: str
```

`config_hash`基于：

```text
稳定排序后的规范化JSON
```

禁止使用：

- Python对象repr；
- 未排序dict；
- 临时文件路径；
- 当前时间；
- 随机值。

---

## 3. ParseReport

```python
class ParseStatus:
    PARSED
    PARTIALLY_PARSED
    FAILED

class ParseReport:
    status
    raw_content_hash
    semantic_content_hash
    parser_config_hash
    input_bytes
    unit_count
    warning_codes
    metrics
```

建议 metrics：

```text
page_count
selected_page_count
pages_with_text
pages_without_text
table_count
table_row_count
caption_count
overlap_count
html_element_count
duration_ms
```

---

## 4. ParsedUnit

```python
class ParsedUnit:
    sequence_no
    unit_type
    text
    locator
    speaker
    parent_sequence_no
    quality_flags
```

质量标志示例：

```text
HTML_FALLBACK_TO_BODY
HTML_SELECTOR_NOT_FOUND
PDF_PAGE_NO_TEXT
PDF_TABLE_EXTRACTION_PARTIAL
PDF_READING_ORDER_UNCERTAIN
TRANSCRIPT_OVERLAP
TRANSCRIPT_EMPTY_CUE_DROPPED
```

---

## 5. 核心对象映射

### Source

```text
Web URL：
  canonical_source_key = normalized origin

Local HTML/PDF/Transcript：
  使用用户提供source_key或现有M2-001规则
```

### Document

```text
document_type：
  HTML/URL → WEB_ARTICLE
  PDF → PDF或COMPANY_FILING/RESEARCH_REPORT（用户可覆盖）
  Transcript → VIDEO或AUDIO（用户可覆盖）
```

Document external_ids建议：

```text
raw_content_hash
semantic_content_hash
parser_config_hash
canonical_url
```

这些是字符串标识，不改变核心Schema。

### ContentUnit

映射：

```text
ParsedUnit.unit_type → ContentUnit.unit_type
ParsedUnit.text → ContentUnit.text
ParsedUnit.locator → ContentUnit.locator
ParsedUnit.speaker → ContentUnit.speaker
parent_sequence_no → parent_unit_id
```

### ProcessingRun

Processor信息：

```text
module = collector/parser模块路径
code_version = Aurora版本
model_provider = null
model_name = null
prompt_version = null
```

M2-002不调用模型。

---

## 6. Hash规范

### HTML语义序列

```text
title
main content units by DOM order
table rows
```

排除：

- script/style；
- 导航；
- 动态请求ID；
- 抓取时间；
- HTTP header。

### PDF语义序列

```text
selected page number
unit type
normalized text
table rows
```

### Transcript语义序列

```text
start_ms
end_ms
speaker
normalized text
```

时间戳必须参与Hash。

---

## 7. 不允许的metadata使用

不得将以下关键契约只放入自由 metadata：

- parser_config_hash；
- raw_content_hash；
- semantic_content_hash；
- 主要Locator；
- parent关系；
- parse status。

它们必须进入明确DTO、external_ids、核心字段或ProcessingRun。

PDF bbox如果临时存在，只能作为Parser内部运行数据，不作为长期稳定契约。
