# Academic RAG System Architecture

## 一、系统总览

```
┌─────────────────────────────────────────────────────────────┐
│                      用户交互层                              │
│   CLI │ Streamlit │ Jupyter │ VS Code Extension │ API       │
├─────────────────────────────────────────────────────────────┤
│                      工作流引擎层                             │
│   自动检索 │ 自动引用 │ 知识调用 │ 自动摘要 │ 研究空白发现     │
├─────────────────────────────────────────────────────────────┤
│                      RAG引擎层                               │
│   Query理解 → 多路召回 → 重排序 → 上下文组装 → LLM生成       │
├─────────────────────────────────────────────────────────────┤
│                      知识索引层                               │
│   向量索引 │ 全文索引 │ 图索引 │ 元数据索引 │ 关联索引         │
├─────────────────────────────────────────────────────────────┤
│                      知识存储层                               │
│   ChromaDB │ SQLite │ 文件系统 │ Zotero │ Git                │
├─────────────────────────────────────────────────────────────┤
│                      数据源层                                 │
│   SCI论文 │ 中文核心 │ 学位论文 │ GitHub │ 方法学 │ 教程      │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、知识库结构

### 目录设计

```
academic-writing/
├── knowledge-base/              # 已有：项目分析+架构知识
│   ├── 00-final-recommendation.md
│   ├── 01-github-project-analysis.md
│   ├── 02-agent-architecture.md
│   ├── 03-prompt-engineering.md
│   └── 04-workflow-design.md
│
├── rag-system/                  # 本次新建：RAG系统
│   ├── config.yaml              # 系统配置
│   ├── schema/                  # 数据模式定义
│   │   ├── document_schema.py   # 文档元数据模式
│   │   ├── chunk_schema.py      # 分块策略模式
│   │   └── citation_schema.py   # 引用模式
│   ├── ingestion/               # 数据摄入
│   │   ├── pdf_parser.py        # PDF解析（Docling/PyMuPDF）
│   │   ├── latex_parser.py      # LaTeX解析
│   │   ├── markdown_parser.py   # Markdown解析
│   │   ├── paper_structurer.py  # 论文结构化（IMRaD分割）
│   │   └── metadata_enricher.py # 元数据丰富（Semantic Scholar）
│   ├── index/                   # 索引管理
│   │   ├── vector_index.py      # ChromaDB向量索引
│   │   ├── fulltext_index.py    # 全文索引（Whoosh/Tantivy）
│   │   ├── citation_graph.py    # 引用图索引
│   │   └── bilingual_index.py   # 中英文双语索引
│   ├── retrieval/               # 检索引擎
│   │   ├── multi_retriever.py   # 多路召回
│   │   ├── reranker.py          # 重排序（Cohere/CrossEncoder）
│   │   ├── query_expander.py    # 查询扩展（中英文）
│   │   └── context_assembler.py # 上下文组装
│   ├── knowledge/               # 知识管理
│   │   ├── literature_kb.py     # 文献知识库
│   │   ├── prompt_kb.py         # Prompt知识库
│   │   ├── figure_kb.py         # 图表知识库
│   │   ├── analysis_kb.py       # 数据分析知识库
│   │   └── discussion_kb.py     # Discussion知识库
│   ├── memory/                  # 记忆系统
│   │   ├── long_term_memory.py  # 长期记忆
│   │   ├── research_context.py  # 研究方向上下文
│   │   ├── learning_log.py      # 学习日志
│   │   └── association_index.py # 关联索引
│   ├── workflow/                # 工作流
│   │   ├── auto_search.py       # 自动检索
│   │   ├── auto_cite.py         # 自动引用
│   │   ├── auto_summarize.py    # 自动摘要
│   │   ├── gap_finder.py        # 研究空白发现
│   │   └── knowledge_caller.py  # 知识自动调用
│   └── update/                  # 自动更新
│       ├── paper_monitor.py     # 新论文监控
│       ├── index_rebuilder.py   # 索引重建
│       ├── knowledge_updater.py # 知识更新
│       └── scheduler.py         # 定时任务
│
├── collections/                 # 文献集合
│   ├── papers/                  # PDF论文存储
│   │   ├── sci/                 # SCI论文
│   │   ├── chinese/             # 中文核心
│   │   ├── thesis/              # 学位论文
│   │   └── methods/             # 方法学论文
│   ├── metadata/                # 元数据
│   │   ├── papers.jsonl          # 论文元数据
│   │   └── citations.jsonl       # 引用关系
│   └── indices/                 # 索引文件
│       ├── chroma/              # ChromaDB持久化
│       └── fulltext/            # 全文索引
│
└── templates/                   # 模板
    ├── latex/                   # LaTeX模板
    │   ├── sci/                 # SCI期刊模板
│   │   ├── chinese/             # 中文核心模板
│   │   └── thesis/              # 学位论文模板
    └── prompts/                 # Prompt模板
        ├── generation/          # 生成类Prompt
        ├── review/              # 评审类Prompt
        └── analysis/            # 分析类Prompt
```

---

## 三、数据模式定义

### 文档元数据模式

```python
from pydantic import BaseModel
from enum import Enum
from datetime import date
from typing import Optional

class DocType(str, Enum):
    SCI_PAPER = "sci_paper"
    CHINESE_PAPER = "chinese_paper"
    THESIS = "thesis"
    METHODS = "methods"
    REVIEW = "review"
    TUTORIAL = "tutorial"
    TEMPLATE = "template"
    GITHUB_PROJECT = "github_project"

class Language(str, Enum):
    EN = "en"
    ZH = "zh"
    BILINGUAL = "bilingual"

class PaperMetadata(BaseModel):
    doc_id: str                          # 唯一标识
    title: str                           # 标题
    title_zh: Optional[str]              # 中文标题
    authors: list[str]                   # 作者
    year: int                            # 发表年份
    journal: Optional[str]               # 期刊
    doi: Optional[str]                   # DOI
    abstract: Optional[str]              # 摘要
    abstract_zh: Optional[str]           # 中文摘要
    keywords: list[str]                  # 关键词
    keywords_zh: list[str]               # 中文关键词
    doc_type: DocType                    # 文档类型
    language: Language                   # 语言
    domain: str = "environmental_science" # 学科领域
    subdomain: str = "carbon_pollutant"  # 子领域
    citation_count: Optional[int]        # 引用数
    is_retracted: bool = False           # 是否撤稿
    file_path: str                       # 文件路径
    added_date: date                     # 添加日期
    zotero_key: Optional[str]            # Zotero关联
```

### 分块策略模式

```python
class ChunkType(str, Enum):
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    METHODS = "methods"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    FIGURE_CAPTION = "figure_caption"
    TABLE_CAPTION = "table_caption"
    EQUATION = "equation"
    CITATION_CONTEXT = "citation_context"  # 引用上下文
    GENERAL = "general"

class DocumentChunk(BaseModel):
    chunk_id: str
    doc_id: str
    chunk_type: ChunkType
    text: str
    text_zh: Optional[str]               # 中文翻译（可选）
    section_path: str                     # 章节路径 "1.2.3"
    page_start: Optional[int]
    page_end: Optional[int]
    char_count: int
    token_count: int
    embedding: Optional[list[float]]      # 向量
    metadata: dict                        # 额外元数据
```

### 引用模式

```python
class CitationRelation(BaseModel):
    citing_doc_id: str                    # 施引文献
    cited_doc_id: str                     # 被引文献
    context: str                          # 引用上下文
    sentiment: str                        # positive/negative/neutral
    section: ChunkType                    # 出现章节
```

---

## 四、技术栈选型

### 核心组件

| 组件 | 选型 | 理由 | 备选 |
|------|------|------|------|
| 向量数据库 | **ChromaDB** | 轻量、本地优先、Python原生 | FAISS, Qdrant |
| 全文搜索 | **Tantivy** (python-tantivy) | 高性能、Rust实现 | Whoosh, Elasticsearch |
| RAG框架 | **LlamaIndex** | 丰富的索引类型、多数据源 | LangChain |
| PDF解析 | **Docling** (IBM) | 学术PDF最优、表格/公式支持 | PyMuPDF, pdfplumber |
| Embedding | **BGE-M3** (中英双语) | 开源最强双语向量模型 | text-embedding-3 |
| 重排序 | **bge-reranker-v2** | 中英双语CrossEncoder | Cohere Rerank |
| LLM | **DeepSeek-V3** (中文) + **Claude** (英文) | 各有所长 | GPT-4 |
| 元数据丰富 | **Semantic Scholar API** | 免费、引用数据全 | CrossRef, OpenAlex |
| 文献管理 | **Zotero + pyzotero** | 成熟生态 | 自建 |
| 调度 | **APScheduler** | 轻量定时任务 | Celery |

### 为什么不选FAISS

- ChromaDB原生支持元数据过滤、持久化、增量更新
- FAISS只是向量索引库，不含存储和查询管理
- 学术场景需要丰富的元数据过滤（年份、期刊、类型）
- ChromaDB开发体验更好，LlamaIndex原生集成

### 为什么不选LangChain

- LlamaIndex更专注于RAG场景，索引类型更丰富
- LlamaIndex的Document、Index、QueryEngine抽象更清晰
- LangChain更适合通用Agent编排，RAG是其子功能

---

## 五、知识库设计

### 5.1 文献知识库（Literature KB）

**存储内容：** 所有导入的论文及其结构化内容

**组织方式：**
```
按文档类型 → 按年份 → 按期刊/来源
```

**核心功能：**
- PDF解析 → IMRaD结构化分块
- 中英文元数据
- 引用关系图
- 全文+向量双索引

**分块策略（关键）：**
```
方案：语义分块 + 章节感知

1. 一级分块：按IMRaD章节
   Abstract / Introduction / Methods / Results / Discussion / Conclusion

2. 二级分块：段落级（500-1000 tokens）
   保持段落完整性，不跨段切割

3. 特殊分块：
   - 图表标题单独提取
   - 公式单独提取
   - 引用上下文单独标记（含被引论文ID）
```

### 5.2 Prompt知识库（Prompt KB）

**存储内容：** 所有可复用的Prompt模板

**组织方式：**
```
按功能 → 按场景 → 按语言
```

**分类：**
```
prompt-kb/
├── generation/           # 生成类
│   ├── introduction/
│   ├── methods/
│   ├── results/
│   ├── discussion/
│   ├── abstract/
│   └── conclusion/
├── review/              # 评审类
│   ├── single_dimension/
│   ├── comprehensive/
│   └── rebuttal/
├── analysis/            # 分析类
│   ├── literature_review/
│   ├── gap_analysis/
│   └── data_interpretation/
└── search/              # 检索类
    ├── query_expansion/
    ├── keyword_extraction/
    └── relevance_scoring/
```

**Prompt元数据：**
```python
class PromptTemplate(BaseModel):
    prompt_id: str
    name: str
    category: str
    scenario: str
    language: Language
    template: str                          # 含{变量}占位符
    variables: list[str]                   # 变量列表
    example_input: dict                    # 示例输入
    example_output: str                    # 示例输出
    effectiveness_score: float             # 使用效果评分
    usage_count: int                       # 使用次数
    tags: list[str]
```

### 5.3 图表知识库（Figure KB）

**存储内容：** 图表设计规范、配色方案、代码模板

**组织方式：**
```
按图表类型 → 按应用场景
```

**分类：**
```
figure-kb/
├── chart_types/          # 图表类型
│   ├── bar_chart/
│   ├── boxplot/
│   ├── heatmap/
│   ├── pca_biplot/
│   ├── dendrogram/
│   ├── scatter/
│   ├── line/
│   └── pie/
├── color_schemes/        # 配色方案
│   ├── colorblind_friendly/
│   ├── grayscale/
│   └── domain_specific/  # 固相=棕, 液相=蓝, 气相=灰
├── layouts/              # 排版
│   ├── 2x2/
│   ├── 1x3/
│   └── mixed/
└── templates/            # 代码模板
    ├── matplotlib/
    ├── seaborn/
    └── plotly/
```

**图表元数据：**
```python
class FigureTemplate(BaseModel):
    template_id: str
    chart_type: str
    scenario: str                          # "空间分布", "相关性", "差异比较"
    code: str                              # Python代码模板
    description: str
    domain_tags: list[str]
```

### 5.4 数据分析知识库（Analysis KB）

**存储内容：** 统计方法、数据→文字转换模板、分析流程

**组织方式：**
```
按分析类型 → 按步骤
```

**分类：**
```
analysis-kb/
├── descriptive/          # 描述性统计
├── normality/            # 正态性检验
├── significance/         # 差异性检验
├── correlation/          # 相关性分析
├── regression/           # 回归分析
├── pca/                  # 主成分分析
├── hca/                  # 层次聚类
├── carbon_balance/       # 碳平衡计算
└── narrative_templates/  # 数据→文字模板
    ├── mean_sd/
    ├── comparison/
    ├── correlation/
    ├── spatial_distribution/
    └── temporal_trend/
```

### 5.5 Discussion知识库（Discussion KB）

**存储内容：** Discussion结构模型、解释框架、对比写法

**组织方式：**
```
按结构模型 → 按功能段落
```

**分类：**
```
discussion-kb/
├── structure_models/     # 结构模型
│   ├── funnel/           # 漏斗模型
│   ├── comparison/       # 比较模型
│   └── problem_solution/ # 问题-解决模型
├── paragraph_types/      # 段落类型
│   ├── finding_summary/
│   ├── literature_comparison/
│   ├── mechanism_explanation/
│   ├── limitation/
│   └── future_work/
└── domain_patterns/      # 领域特定模式
    └── carbon_pollutant/
```

---

## 六、检索系统设计

### 多路召回策略

```
用户查询
    │
    ├─→ [向量检索] ChromaDB (语义相似)
    │       BGE-M3 embedding
    │       返回 top-20
    │
    ├─→ [全文检索] Tantivy (关键词匹配)
    │       BM25评分
    │       返回 top-20
    │
    ├─→ [引用检索] Citation Graph
    │       被引/施引论文
    │       返回 top-10
    │
    └─→ [元数据过滤] SQLite
            年份/期刊/类型
            精确过滤

    │
    ▼
[融合去重] → 合并结果，去除重复
    │
    ▼
[重排序] bge-reranker-v2
    │   CrossEncoder精排
    │   返回 top-10
    │
    ▼
[上下文组装]
    │   按相关性排序
    │   控制token总量
    │   注入元数据（作者/年份/期刊）
    │
    ▼
[LLM生成]
    │   带引用的回答
    │   中英文自适应
    │
    ▼
输出
```

### 中英文混合检索

```python
class BilingualRetriever:
    """中英文混合检索器"""

    def retrieve(self, query: str, language: str = "auto") -> list:
        # 1. 语言检测
        if language == "auto":
            language = detect_language(query)

        # 2. 查询扩展
        expanded_queries = self.expand_query(query, language)
        # 中文查询 → 同时搜索中文+英文翻译
        # 英文查询 → 同时搜索英文+中文翻译

        # 3. 多路召回
        results = []
        for q in expanded_queries:
            results.extend(self.vector_search(q))
            results.extend(self.fulltext_search(q))

        # 4. 去重+重排序
        return self.rerank(deduplicate(results))

    def expand_query(self, query: str, language: str) -> list[str]:
        """查询扩展：生成同义查询"""
        if language == "zh":
            # 中文 → 英文翻译 + 同义词扩展
            return [query, translate_zh_to_en(query), ...]
        else:
            # 英文 → 中文翻译 + 同义词扩展
            return [query, translate_en_to_zh(query), ...]
```

### 多论文联合推理

```python
class MultiPaperReasoner:
    """多论文联合推理"""

    def synthesize(self, question: str, papers: list[PaperMetadata]) -> str:
        # 1. 提取每篇论文的相关段落
        relevant_chunks = self.extract_relevant(question, papers)

        # 2. 构建对比矩阵
        comparison = self.build_comparison(relevant_chunks)

        # 3. 识别共识与分歧
        consensus, disagreements = self.find_patterns(comparison)

        # 4. 生成综合回答
        return self.generate_answer(
            question, consensus, disagreements, papers
        )

    def build_comparison(self, chunks: list[DocumentChunk]) -> dict:
        """构建论文间对比矩阵"""
        # 按维度组织：方法/结果/结论
        # 标注：一致/矛盾/互补
        pass

    def find_patterns(self, comparison: dict) -> tuple:
        """识别共识与分歧"""
        # 共识：多篇论文一致的发现
        # 分歧：矛盾的结论及可能原因
        pass
```

---

## 七、记忆系统设计

### 三层记忆架构

```
┌─────────────────────────────────────────────┐
│  长期记忆（持久化存储）                        │
│                                             │
│  ├─ 文献知识库 (ChromaDB + SQLite)           │
│  ├─ 研究方向向量 (研究主题embedding)          │
│  ├─ 引用关系图 (NetworkX)                    │
│  ├─ 领域知识图谱 (实体-关系-属性)             │
│  └─ 学习日志 (每次交互的反馈)                 │
│                                             │
├─────────────────────────────────────────────┤
│  中期记忆（会话/项目级）                       │
│                                             │
│  ├─ 当前研究上下文 (研究主题+已读论文)        │
│  ├─ 写作状态 (当前章节+已完成内容)            │
│  ├─ 检索历史 (最近查询+结果反馈)              │
│  └─ 知识关联 (本项目涉及的概念/方法)          │
│                                             │
├─────────────────────────────────────────────┤
│  短期记忆（当前交互）                         │
│                                             │
│  ├─ 当前查询理解                             │
│  ├─ 检索结果                                 │
│  ├─ 生成上下文                               │
│  └─ 用户反馈                                 │
│                                             │
└─────────────────────────────────────────────┘
```

### 研究方向关联

```python
class ResearchContext:
    """研究方向上下文"""

    def __init__(self, research_topic: str):
        self.topic = research_topic
        self.topic_embedding = embed(research_topic)
        self.related_papers: list[str] = []      # 已读论文ID
        self.key_concepts: list[str] = []         # 核心概念
        self.research_gap: Optional[str] = None   # 识别的研究空白
        self.cited_papers: list[str] = []         # 已引用论文

    def find_related_papers(self, kb: LiteratureKB) -> list:
        """基于研究方向找到相关论文"""
        # 向量相似度 + 关键词匹配 + 引用网络
        pass

    def update_context(self, new_paper: PaperMetadata):
        """阅读新论文后更新研究上下文"""
        self.related_papers.append(new_paper.doc_id)
        self.key_concepts = self.extract_concepts(new_paper)
        pass
```

### 持续学习机制

```python
class LearningLogger:
    """学习日志：记录每次交互的反馈"""

    def log_retrieval(self, query: str, results: list, feedback: dict):
        """记录检索反馈：哪些结果有用/没用"""
        pass

    def log_generation(self, prompt_id: str, output: str, quality: float):
        """记录生成质量：用于优化Prompt"""
        pass

    def log_citation(self, context: str, cited_paper: str, appropriate: bool):
        """记录引用是否恰当"""
        pass

    def get_improvement_suggestions(self) -> list:
        """基于学习日志给出改进建议"""
        pass
```

---

## 八、自动更新机制

### 论文监控

```python
class PaperMonitor:
    """新论文监控"""

    def __init__(self, research_topics: list[str]):
        self.topics = research_topics

    def check_arxiv(self) -> list[PaperMetadata]:
        """检查arXiv新论文"""
        pass

    def check_semantic_scholar(self) -> list[PaperMetadata]:
        """检查Semantic Scholar新论文"""
        pass

    def check_citations(self, my_papers: list[str]) -> list:
        """检查谁引用了我的参考文献"""
        pass

    def run_daily(self):
        """每日执行"""
        new_papers = []
        new_papers.extend(self.check_arxiv())
        new_papers.extend(self.check_semantic_scholar())

        # 过滤相关论文
        relevant = self.filter_by_relevance(new_papers)

        # 自动索引
        for paper in relevant:
            self.index_paper(paper)

        return relevant
```

### 索引更新

```python
class IndexManager:
    """索引管理"""

    def add_document(self, doc_path: str):
        """增量添加文档"""
        # 解析 → 分块 → embedding → 索引
        pass

    def rebuild_index(self):
        """全量重建索引"""
        pass

    def update_metadata(self, doc_id: str, new_metadata: dict):
        """更新元数据（如引用数）"""
        pass
```

---

## 九、Zotero集成

```python
class ZoteroConnector:
    """Zotero文献管理集成"""

    def __init__(self, library_id: str, api_key: str):
        from pyzotero import zotero
        self.zot = zotero.Zotero(library_id, 'user', api_key)

    def sync_collection(self, collection_name: str) -> list:
        """同步指定集合的论文"""
        items = self.zot.collection_items(collection_name)
        papers = []
        for item in items:
            # 下载PDF
            pdf_path = self.download_pdf(item)
            # 提取元数据
            metadata = self.extract_metadata(item)
            papers.append((pdf_path, metadata))
        return papers

    def import_to_rag(self, papers: list):
        """将Zotero论文导入RAG系统"""
        for pdf_path, metadata in papers:
            # 解析PDF
            chunks = self.parser.parse(pdf_path, metadata)
            # 索引
            self.indexer.index(chunks)
```

---

## 十、技术栈总结

```
┌─────────────────────────────────────────┐
│             LLM层                        │
│  DeepSeek-V3 (中文) │ Claude (英文)     │
│  Ollama (本地备份)                        │
├─────────────────────────────────────────┤
│             Embedding层                  │
│  BGE-M3 (中英双语) │ OpenAI (备选)      │
├─────────────────────────────────────────┤
│             RAG框架层                    │
│  LlamaIndex (核心)                       │
├─────────────────────────────────────────┤
│             检索层                        │
│  ChromaDB (向量) │ Tantivy (全文)       │
│  bge-reranker-v2 (重排序)               │
├─────────────────────────────────────────┤
│             解析层                        │
│  Docling (PDF) │ 自建LaTeX解析器        │
├─────────────────────────────────────────┤
│             存储层                        │
│  ChromaDB │ SQLite │ 文件系统 │ Git     │
├─────────────────────────────────────────┤
│             集成层                        │
│  Zotero │ Semantic Scholar │ arXiv API │
└─────────────────────────────────────────┘
```
