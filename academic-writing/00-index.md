---
name: 00-index
description: 学术写作知识系统索引 - 模块导航、使用指南、快速查找
metadata:
  type: knowledge-base
  domain: academic-writing
  priority: 5
---

# 学术写作知识系统 - 索引

## 系统概述

本系统是针对环境科学（碳污染物多相态分析方向）的学术写作辅助知识库，包含10个核心模块，覆盖从写作规则到领域知识的完整链路。

```
┌─────────────────────────────────────────────────────┐
│                  用户：我要写论文                      │
├─────────────────────────────────────────────────────┤
│                                                      │
│  写什么？    → 09结构模板    确定框架                 │
│  怎么写？    → 01/02写作规则  中英文规范              │
│  用什么词？  → 03句式库      可直接套用的句子         │
│  图表怎么做？ → 05图表设计   规范+配色+代码           │
│  数据怎么写？ → 06分析逻辑   数据→文字转换模板        │
│  Discussion？ → 04讨论库     结构模型+机制框架        │
│  领域知识？  → 10领域知识    术语+期刊+方法           │
│  机制解释？  → mechanism-kb  碳污染物生成/转化机制    │
│  被拒了？    → 07审稿回复    Response模板+策略        │
│  常见错误？  → 08错误清单    检查+避免               │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## 模块列表

### 核心写作模块

| 编号 | 文件 | 名称 | 优先级 | 说明 |
|------|------|------|--------|------|
| 01 | [01-sci-rules.md](01-sci-rules.md) | SCI写作规则 | ★★★★★ | 英文论文时态/语态/结构/检查清单 |
| 02 | [02-chinese-rules.md](02-chinese-rules.md) | 中文论文规则 | ★★★★★ | 中文核心格式/语言/各章写法 |
| 03 | [03-sentence-bank.md](03-sentence-bank.md) | 句式库 | ★★★★☆ | 中英文学术句子模板，可直接套用 |
| 09 | [09-structure-templates.md](09-structure-templates.md) | 结构模板 | ★★★★★ | 硕论/SCI/中文核心的章节模板 |

### 内容辅助模块

| 编号 | 文件 | 名称 | 优先级 | 说明 |
|------|------|------|--------|------|
| 04 | [04-discussion-library.md](04-discussion-library.md) | Discussion库 | ★★★★☆ | 漏斗/对比模型，段落模板 |
| 05 | [05-figure-design.md](05-figure-design.md) | 图表设计 | ★★★★☆ | SCI图表规范+配色+排版 |
| 06 | [06-data-analysis-logic.md](06-data-analysis-logic.md) | 分析逻辑 | ★★★★☆ | 统计方法→文字转换模板 |
| 10 | [10-domain-knowledge.md](10-domain-knowledge.md) | 领域知识 | ★★★★☆ | 碳污染物术语+期刊+方法 |

### 辅助模块

| 编号 | 文件 | 名称 | 优先级 | 说明 |
|------|------|------|--------|------|
| 07 | [07-reviewer-comments.md](07-reviewer-comments.md) | 审稿回复 | ★★★☆☆ | Response模板+rebuttal策略 |
| 08 | [08-common-mistakes.md](08-common-mistakes.md) | 常见错误 | ★★★☆☆ | 各章节错误清单+检查表 |
| KB | [mechanism-kb.md](mechanism-kb.md) | 机制知识库 | ★★★★☆ | DO/TOC→CH4/CO2机制解释 |

### 外部知识库（knowledge-base/）

| 文件 | 名称 | 说明 |
|------|------|------|
| [00-final-recommendation.md](knowledge-base/00-final-recommendation.md) | 最终方案 | NORA+CrewAI+LangGraph混合架构 |
| [01-github-project-analysis.md](knowledge-base/01-github-project-analysis.md) | 项目分析 | 20+ GitHub学术项目分析 |
| [02-agent-architecture.md](knowledge-base/02-agent-architecture.md) | Agent架构 | 6种编排模式+记忆系统 |
| [03-prompt-engineering.md](knowledge-base/03-prompt-engineering.md) | Prompt工程 | 各章节Prompt模板 |
| [04-workflow-design.md](knowledge-base/04-workflow-design.md) | 工作流设计 | Agent定义+技术栈 |
| [05-rag-architecture.md](knowledge-base/05-rag-architecture.md) | RAG架构 | 5层系统+5类知识库 |

---

## 使用场景速查

### 场景1：写硕论

```
步骤1: 09-structure-templates → 硕论框架
步骤2: 02-chinese-rules → 中文写作规范
步骤3: 06-data-analysis-logic → 数据→文字
步骤4: 04-discussion-library → Discussion结构
步骤5: mechanism-kb → 机制解释
步骤6: 05-figure-design → 图表制作
步骤7: 08-common-mistakes → 自查
```

### 场景2：投SCI期刊

```
步骤1: 09-structure-templates → SCI框架
步骤2: 01-sci-rules → 英文写作规范
步骤3: 03-sentence-bank → 英文句式
步骤4: 06-data-analysis-logic → 数据叙述
步骤5: 04-discussion-library → Discussion
步骤6: 05-figure-design → Figure制作
步骤7: 08-common-mistakes → 自查
```

### 场景3：回复审稿意见

```
步骤1: 07-reviewer-comments → 回复模板
步骤2: 根据意见类型选择句式
步骤3: 修改论文
步骤4: 08-common-mistakes → 修改后自查
```

### 场景4：写Discussion

```
步骤1: 04-discussion-library → 结构模型选择
步骤2: mechanism-kb → 找到对应机制
步骤3: 03-sentence-bank → 套用句式
步骤4: 01/02-sci/chinese-rules → 语言规范
```

---

## 模块间关系

```
09结构模板 ←── 所有写作的框架基础
  │
  ├── 01/02写作规则 ←── 语言层面
  │     │
  │     └── 03句式库 ←── 直接套用
  │
  ├── 06分析逻辑 ←── 数据→文字
  │     │
  │     └── 10领域知识 ←── 术语+方法背景
  │
  ├── 04讨论库 ←── Discussion专用
  │     │
  │     └── mechanism-kb ←── 机制解释支撑
  │
  └── 05图表设计 ←── 可视化

07审稿回复 ←── 独立模块，投稿后使用
08常见错误 ←── 质量检查，各阶段使用
```

---

## 代码模块关联

| 代码文件 | 关联知识库模块 | 说明 |
|---------|---------------|------|
| `data_loader.py` | 10-domain-knowledge | 数据范围用于异常值判断 |
| `statistical_analysis.py` | 06-data-analysis-logic | 统计结果→文字模板 |
| `plotting_functions.py` | 05-figure-design | 图表样式+配色 |
| `academic_plot_style.py` | 05-figure-design | Okabe-Ito配色方案 |
| `scientific_analysis_agent.py` | 06 + 10 + 05 | 自动分析→文字→图表 |
| `paper_writing_agent.py` | 03 + 04 + mechanism-kb | 自动论文生成 |
