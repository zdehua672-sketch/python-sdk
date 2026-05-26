"""
Self-Evolving Academic AI Engine
================================
可持续进化的科研AI系统核心引擎

组件:
  KnowledgeStore   - JSON结构化知识库（替代硬编码字典）
  FeedbackCollector - 反馈收集与学习
  EvolutionEngine  - 进化引擎：参数调优+知识更新+资源发现+版本管理

设计原则:
  1. 零外部依赖（仅标准库）
  2. 所有知识JSON化，可被Agent读取
  3. 每次使用产生反馈，反馈驱动进化
  4. 版本化所有变更，可回滚
"""

import json
import os
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import Counter
from copy import deepcopy

try:
    from revision_audit import audit_revision
except ImportError:
    audit_revision = None


# ============================================================
# 1. KnowledgeStore - JSON结构化知识库
# ============================================================

class KnowledgeStore:
    """JSON结构化知识库，替代硬编码字典和静态markdown"""

    STORE_DIR = "knowledge_store"

    # 知识分类
    CATEGORIES = {
        "mechanisms": "碳污染物生成/转化机制",
        "review_rules": "审稿规则（AI检测/禁用词/时态）",
        "writing_templates": "写作模板（句式/结构/讨论）",
        "domain_terms": "领域术语",
        "methods": "分析方法",
        "parameters": "系统参数（阈值/权重）",
        "resources": "外部资源（论文/项目/工具）",
        "feedback_log": "反馈日志",
        "rationale_matrix": "写作推理矩阵（发现→机制→证据→引用）",
        "revision_history": "修订历史（版本间变化追踪）",
    }

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or os.path.dirname(os.path.abspath(__file__)))
        self.store_dir = self.base_dir / self.STORE_DIR
        self.store_dir.mkdir(exist_ok=True)

        # 初始化各知识分类
        self._stores: Dict[str, dict] = {}
        for cat in self.CATEGORIES:
            self._stores[cat] = self._load(cat)

    def _path(self, category: str) -> Path:
        return self.store_dir / f"{category}.json"

    def _load(self, category: str) -> dict:
        path = self._path(category)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        # 自动初始化缺失的JSON文件
        default = self._default_store(category)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default

    def _default_store(self, category: str) -> dict:
        return {
            "meta": {
                "category": category,
                "description": self.CATEGORIES.get(category, ""),
                "version": 1,
                "created": datetime.now(timezone.utc).isoformat(),
                "updated": datetime.now(timezone.utc).isoformat(),
                "source": "initial",
            },
            "entries": {},
            "changelog": [],
        }

    def save(self, category: str):
        """保存指定分类"""
        store = self._stores.get(category)
        if store:
            store["meta"]["updated"] = datetime.now(timezone.utc).isoformat()
            with open(self._path(category), "w", encoding="utf-8") as f:
                json.dump(store, f, ensure_ascii=False, indent=2)

    def save_all(self):
        """保存所有分类"""
        for cat in self._stores:
            self.save(cat)

    def get(self, category: str, key: str = None) -> Any:
        """获取知识条目"""
        store = self._stores.get(category, {})
        if key is None:
            return store.get("entries", {})
        entry = store.get("entries", {}).get(key)
        return entry["value"] if entry else None

    def set(self, category: str, key: str, value: Any,
            source: str = "manual", confidence: float = 1.0):
        """设置知识条目（带版本和置信度）"""
        store = self._stores.setdefault(category, self._default_store(category))
        entries = store.setdefault("entries", {})

        old_value = entries.get(key, {}).get("value")
        entries[key] = {
            "value": value,
            "confidence": confidence,
            "source": source,
            "updated": datetime.now(timezone.utc).isoformat(),
            "version": entries.get(key, {}).get("version", 0) + 1,
        }

        # 记录变更
        if old_value != value:
            store["changelog"].append({
                "action": "update" if old_value is not None else "create",
                "key": key,
                "old": old_value if old_value is not None else None,
                "new": value if not isinstance(value, (dict, list)) else str(value)[:200],
                "source": source,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            store["meta"]["version"] = store["meta"].get("version", 0) + 1

        self.save(category)

    def delete(self, category: str, key: str, reason: str = ""):
        """删除知识条目"""
        store = self._stores.get(category)
        if store and key in store.get("entries", {}):
            old = store["entries"].pop(key)
            store["changelog"].append({
                "action": "delete",
                "key": key,
                "old": str(old.get("value", ""))[:200],
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            self.save(category)

    def search(self, category: str, query: str) -> List[Tuple[str, Any]]:
        """搜索知识条目"""
        entries = self.get(category)
        results = []
        query_lower = query.lower()
        for key, entry in entries.items():
            val_str = json.dumps(entry if isinstance(entry, dict) else entry,
                                ensure_ascii=False).lower()
            if query_lower in key.lower() or query_lower in val_str:
                results.append((key, entry if isinstance(entry, dict) else entry))
        return results

    def stats(self) -> dict:
        """知识库统计"""
        result = {}
        for cat, store in self._stores.items():
            entries = store.get("entries", {})
            result[cat] = {
                "count": len(entries),
                "version": store.get("meta", {}).get("version", 0),
                "changelog_len": len(store.get("changelog", [])),
            }
        return result

    # --- 从现有代码/文件导入知识 ---

    def import_from_review_agent(self):
        """从 academic_review_agent.py 的 ReviewKB 导入审稿规则"""
        try:
            import academic_review_agent as ara
            kb = ara.ReviewKB

            # AI检测模式
            for i, pat in enumerate(getattr(kb, 'AI_PATTERNS_EN', [])):
                self.set("review_rules", f"ai_pattern_en_{i}", pat,
                         source="ReviewKB", confidence=0.9)
            for i, pat in enumerate(getattr(kb, 'AI_PATTERNS_ZH', [])):
                self.set("review_rules", f"ai_pattern_zh_{i}", pat,
                         source="ReviewKB", confidence=0.9)

            # 禁用词
            for word, suggestion in getattr(kb, 'EN_FORBIDDEN', {}).items():
                self.set("review_rules", f"forbidden_en_{word}",
                         {"word": word, "suggestion": suggestion},
                         source="ReviewKB", confidence=0.95)
            for word, suggestion in getattr(kb, 'ZH_FORBIDDEN', {}).items():
                self.set("review_rules", f"forbidden_zh_{word}",
                         {"word": word, "suggestion": suggestion},
                         source="ReviewKB", confidence=0.95)

            # 夸大词汇
            for word in getattr(kb, 'OVERCLAIM_WORDS_EN', []):
                self.set("review_rules", f"overclaim_en_{word}", word,
                         source="ReviewKB", confidence=0.9)
            for word in getattr(kb, 'OVERCLAIM_WORDS_ZH', []):
                self.set("review_rules", f"overclaim_zh_{word}", word,
                         source="ReviewKB", confidence=0.9)

            # 空洞表达
            for i, pat in enumerate(getattr(kb, 'HOLLOW_PATTERNS_EN', [])):
                self.set("review_rules", f"hollow_en_{i}", pat,
                         source="ReviewKB", confidence=0.85)
            for i, pat in enumerate(getattr(kb, 'HOLLOW_PATTERNS_ZH', [])):
                self.set("review_rules", f"hollow_zh_{i}", pat,
                         source="ReviewKB", confidence=0.85)

            return True
        except ImportError:
            return False

    def import_from_paper_writer(self):
        """从 paper_writing_agent.py 的 MechanismKB 导入机制知识"""
        try:
            import paper_writing_agent as pwa
            kb = pwa.MechanismKB

            # MechanismKB 使用类变量存储知识
            for attr_name in dir(kb):
                if attr_name.startswith('_'):
                    continue
                attr = getattr(kb, attr_name)
                if isinstance(attr, dict) and attr_name.isupper():
                    for key, val in attr.items():
                        self.set("mechanisms", f"{attr_name.lower()}_{key}", val,
                                 source="MechanismKB", confidence=0.95)
            return True
        except ImportError:
            return False

    def import_from_mechanism_kb_md(self):
        """从 mechanism-kb.md 导入机制知识"""
        md_path = self.base_dir / "academic-writing" / "mechanism-kb.md"
        if not md_path.exists():
            return False

        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 按二级标题分割
        sections = re.split(r'^## (.+)$', content, flags=re.MULTILINE)
        for i in range(1, len(sections), 2):
            title = sections[i].strip()
            body = sections[i + 1].strip() if i + 1 < len(sections) else ""
            key = re.sub(r'[^\w一-鿿]', '_', title).strip('_').lower()
            self.set("mechanisms", f"section_{key}", {
                "title": title,
                "content": body[:2000],  # 截断避免过大
                "source_file": "mechanism-kb.md",
            }, source="mechanism-kb.md", confidence=0.95)
        return True

    def import_scorer_weights(self):
        """从 academic_review_agent.py 导入评分权重"""
        try:
            import academic_review_agent as ara
            scorer = ara.Scorer
            dimensions = getattr(scorer, 'DIMENSIONS', {})
            for dim, config in dimensions.items():
                self.set("parameters", f"score_weight_{dim}",
                         config if isinstance(config, dict) else {"weight": config},
                         source="Scorer", confidence=0.8)
            return True
        except ImportError:
            return False

    def import_all(self):
        """从所有现有代码导入知识"""
        results = {}
        results["review_agent"] = self.import_from_review_agent()
        results["paper_writer"] = self.import_from_paper_writer()
        results["mechanism_kb"] = self.import_from_mechanism_kb_md()
        results["scorer"] = self.import_scorer_weights()
        return results


# ============================================================
# 2. FeedbackCollector - 反馈收集与学习
# ============================================================

@dataclass
class FeedbackEntry:
    """单条反馈"""
    timestamp: str
    feedback_type: str  # review/writing/visualization/manual
    category: str       # 具体类别
    context: dict       # 上下文信息
    rating: int = 0     # 1-5评分
    comment: str = ""   # 用户评论
    action_taken: str = ""  # 系统采取的行动


class FeedbackCollector:
    """反馈收集器：记录每次使用中的学习信号"""

    def __init__(self, store: KnowledgeStore):
        self.store = store

    def log_review_feedback(self, paper_text: str, report_issues: list,
                            accepted: list, rejected: list, comment: str = ""):
        """记录审稿反馈：哪些issue被接受/拒绝"""
        entry = {
            "type": "review_calibration",
            "paper_length": len(paper_text),
            "total_issues": len(report_issues),
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "accepted_categories": [i.get("category", "") for i in accepted],
            "rejected_categories": [i.get("category", "") for i in rejected],
            "comment": comment,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 存储反馈
        key = f"review_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.store.set("feedback_log", key, entry, source="review_feedback")

        # 根据反馈调整审稿规则权重
        self._adjust_review_weights(accepted, rejected)

    def log_writing_feedback(self, section: str, original: str,
                             improved: str, rating: int, comment: str = ""):
        """记录写作反馈：用户对生成内容的评价"""
        entry = {
            "type": "writing_quality",
            "section": section,
            "original_len": len(original),
            "improved_len": len(improved),
            "rating": rating,  # 1-5
            "comment": comment,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        key = f"writing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.store.set("feedback_log", key, entry, source="writing_feedback")

        # 低评分时标记需要改进的模板
        if rating <= 2:
            self._flag_weak_template(section, original)

    def log_analysis_feedback(self, chart_type: str, data_profile: dict,
                              rating: int, comment: str = ""):
        """记录分析/可视化反馈"""
        entry = {
            "type": "visualization_quality",
            "chart_type": chart_type,
            "data_profile": data_profile,
            "rating": rating,
            "comment": comment,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        key = f"viz_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.store.set("feedback_log", key, entry, source="viz_feedback")

    def log_discovery(self, source_type: str, title: str, url: str,
                      relevance: float, summary: str = ""):
        """记录发现的新资源（论文/项目/工具）"""
        entry = {
            "type": "resource_discovery",
            "source_type": source_type,  # paper/github/tool/method
            "title": title,
            "url": url,
            "relevance": relevance,  # 0-1
            "summary": summary,
            "status": "discovered",  # discovered -> reviewed -> integrated
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        key = f"{source_type}_{hashlib.md5(title.encode()).hexdigest()[:8]}"
        self.store.set("resources", key, entry, source="auto_discovery",
                        confidence=relevance)

    def _adjust_review_weights(self, accepted: list, rejected: list):
        """根据审稿反馈调整规则权重"""
        # 被拒绝的issue类型 → 降低置信度
        for issue in rejected:
            cat = issue.get("category", "")
            severity = issue.get("severity", "")
            param_key = f"checker_weight_{cat}_{severity}"
            current = self.store.get("parameters", param_key) or {"weight": 1.0}
            new_weight = max(0.3, current.get("weight", 1.0) * 0.9)
            self.store.set("parameters", param_key,
                          {"weight": new_weight, "adjustment": "decreased"},
                          source="feedback_learning", confidence=0.7)

        # 被接受的issue类型 → 提升置信度
        for issue in accepted:
            cat = issue.get("category", "")
            severity = issue.get("severity", "")
            param_key = f"checker_weight_{cat}_{severity}"
            current = self.store.get("parameters", param_key) or {"weight": 1.0}
            new_weight = min(1.5, current.get("weight", 1.0) * 1.05)
            self.store.set("parameters", param_key,
                          {"weight": new_weight, "adjustment": "increased"},
                          source="feedback_learning", confidence=0.7)

    def _flag_weak_template(self, section: str, original: str):
        """标记需要改进的模板"""
        key = f"weak_{section}_{hashlib.md5(original.encode()).hexdigest()[:8]}"
        self.store.set("writing_templates", key, {
            "section": section,
            "text": original[:500],
            "flag": "low_rating",
            "needs_improvement": True,
        }, source="feedback_learning", confidence=0.6)

    def get_feedback_stats(self) -> dict:
        """获取反馈统计"""
        all_feedback = self.store.get("feedback_log")
        stats = {"total": 0, "by_type": {}, "avg_rating": {}}
        ratings_by_type = {}

        for key, entry in all_feedback.items():
            val = entry.get("value", entry) if isinstance(entry, dict) else entry
            if isinstance(val, dict):
                ftype = val.get("type", "unknown")
                stats["total"] += 1
                stats["by_type"][ftype] = stats["by_type"].get(ftype, 0) + 1
                if val.get("rating"):
                    ratings_by_type.setdefault(ftype, []).append(val["rating"])

        for ftype, ratings in ratings_by_type.items():
            stats["avg_rating"][ftype] = round(sum(ratings) / len(ratings), 2)

        return stats


# ============================================================
# 3. GitHubMonitor - GitHub项目自动监控
# ============================================================

class GitHubMonitor:
    """
    GitHub项目自动监控器

    使用 gh CLI 搜索、分析、跟踪学术AI相关项目。
    支持按关键词/主题搜索，自动评估项目质量，存入知识库。
    """

    # 搜索领域配置
    SEARCH_DOMAINS = {
        "academic_writing": {
            "queries": [
                "academic paper writing",
                "paper generation",
                "thesis writing",
            ],
            "min_stars": 30,
        },
        "data_analysis": {
            "queries": [
                "scientific data analysis",
                "research visualization",
                "statistical analysis",
            ],
            "min_stars": 50,
        },
        "agent_framework": {
            "queries": [
                "multi-agent",
                "AI agent framework",
                "agentic workflow",
            ],
            "min_stars": 100,
        },
        "rag_system": {
            "queries": [
                "RAG system",
                "retrieval augmented",
                "knowledge base",
            ],
            "min_stars": 50,
        },
        "visualization": {
            "queries": [
                "scientific plotting",
                "publication figures",
                "matplotlib style",
                "matplotlib journal style",
                "academic figure generation",
            ],
            "min_stars": 100,
        },
        "environmental_science": {
            "queries": [
                "water quality analysis",
                "carbon emission",
                "environmental monitoring",
            ],
            "min_stars": 20,
        },
    }

    def __init__(self, store: KnowledgeStore):
        self.store = store

    def search(self, query: str, language: str = None,
               sort: str = "stars", limit: int = 10,
               min_stars: int = 0) -> list:
        """
        搜索GitHub仓库

        Parameters
        ----------
        query : str, 搜索关键词
        language : str, 编程语言过滤
        sort : str, 排序方式 (stars/forks/updated)
        limit : int, 最大结果数
        min_stars : int, 最低star数

        Returns
        -------
        list of dict, 每个包含 full_name, description, stars, url 等
        """
        cmd = [
            "gh", "search", "repos", query,
            "--limit", str(limit),
            "--sort", sort,
            "--json", "fullName,description,stargazersCount,forksCount,"
                       "language,updatedAt,url,isArchived",
        ]
        if language:
            cmd.extend(["--language", language])

        try:
            import subprocess
            result = subprocess.run(
                cmd, capture_output=True, timeout=30
            )
            if result.returncode != 0:
                return []

            stdout = result.stdout.decode('utf-8', errors='replace')
            repos = json.loads(stdout)
            filtered = []
            for repo in repos:
                if repo.get("isArchived"):
                    continue
                if repo.get("stargazersCount", 0) < min_stars:
                    continue
                filtered.append({
                    "full_name": repo["fullName"],
                    "description": repo.get("description", ""),
                    "stars": repo.get("stargazersCount", 0),
                    "forks": repo.get("forksCount", 0),
                    "language": repo.get("language", ""),
                    "updated_at": repo.get("updatedAt", ""),
                    "url": repo.get("url", ""),
                    "topics": [],
                })
            return filtered
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return []

    def get_repo_details(self, full_name: str) -> dict:
        """获取仓库详细信息"""
        try:
            import subprocess
            result = subprocess.run(
                ["gh", "api", f"repos/{full_name}"],
                capture_output=True, timeout=15
            )
            if result.returncode != 0:
                return {}
            data = json.loads(result.stdout.decode('utf-8', errors='replace'))
            # 只保留需要的字段
            keep = ["name","description","stargazers_count","forks_count",
                    "open_issues_count","language","license","created_at",
                    "updated_at","pushed_at","default_branch","topics"]
            return {k: data.get(k) for k in keep if k in data}
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return {}

    def get_recent_commits(self, full_name: str, days: int = 30) -> list:
        """获取最近提交记录"""
        from datetime import timedelta
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        try:
            import subprocess
            result = subprocess.run(
                ["gh", "api", f"repos/{full_name}/commits",
                 "-f", f"since={since}", "-f", "per_page=20"],
                capture_output=True, timeout=15
            )
            if result.returncode != 0:
                return []
            data = json.loads(result.stdout.decode('utf-8', errors='replace'))
            if not isinstance(data, list):
                return []
            return [c.get("commit", {}).get("message", "").split("\n")[0]
                    for c in data[:20] if c.get("commit")]
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return []

    def get_readme_summary(self, full_name: str, max_chars: int = 2000) -> str:
        """获取README摘要"""
        try:
            import subprocess
            result = subprocess.run(
                ["gh", "api", f"repos/{full_name}/readme"],
                capture_output=True, timeout=15
            )
            if result.returncode != 0:
                return ""
            import base64
            data = json.loads(result.stdout.decode('utf-8', errors='replace'))
            content = base64.b64decode(data.get("content", "")).decode('utf-8', errors='ignore')
            return content[:max_chars]
        except Exception:
            return ""

    def analyze_repo(self, full_name: str) -> dict:
        """综合分析一个仓库"""
        details = self.get_repo_details(full_name)
        if not details:
            return {}

        stars = details.get("stargazers_count", 0)
        forks = details.get("forks_count", 0)
        issues = details.get("open_issues_count", 0)
        topics = details.get("topics", [])

        # 计算活跃度
        pushed_at = details.get("pushed_at", "")
        try:
            last_push = datetime.fromisoformat(pushed_at.replace('Z', '+00:00'))
            days_since_push = (datetime.now(timezone.utc) - last_push).days
        except (ValueError, TypeError):
            days_since_push = 999

        # 活跃度评分 (0-1)
        if days_since_push <= 30:
            activity = 1.0
        elif days_since_push <= 90:
            activity = 0.7
        elif days_since_push <= 180:
            activity = 0.4
        else:
            activity = 0.1

        # 质量评分
        quality = min(1.0, (stars / 1000) * 0.4 +
                         (forks / 200) * 0.2 +
                         activity * 0.3 +
                         (1.0 if details.get("license") else 0.0) * 0.1)

        # 获取最近提交
        commits = self.get_recent_commits(full_name, days=30)

        return {
            "full_name": full_name,
            "description": details.get("description", ""),
            "stars": stars,
            "forks": forks,
            "open_issues": issues,
            "language": details.get("language", ""),
            "license": details.get("license", {}).get("spdx_id", "") if details.get("license") else "",
            "topics": topics,
            "created_at": details.get("created_at", ""),
            "pushed_at": pushed_at,
            "days_since_push": days_since_push,
            "activity_score": round(activity, 2),
            "quality_score": round(quality, 2),
            "recent_commits_count": len(commits),
            "recent_commits": commits[:5],
            "url": f"https://github.com/{full_name}",
        }

    def scan_domain(self, domain: str, max_per_query: int = 5) -> dict:
        """
        扫描一个领域，搜索+分析+存储

        Parameters
        ----------
        domain : str, SEARCH_DOMAINS中的领域名
        max_per_query : int, 每个查询最多结果数

        Returns
        -------
        dict, {found: int, new: int, repos: list}
        """
        config = self.SEARCH_DOMAINS.get(domain)
        if not config:
            return {"error": f"未知领域: {domain}"}

        min_stars = config.get("min_stars", 0)
        all_repos = {}
        existing = self.store.get("resources")

        for query in config["queries"]:
            repos = self.search(query, limit=max_per_query, min_stars=min_stars)
            for repo in repos:
                name = repo["full_name"]
                if name not in all_repos:
                    all_repos[name] = repo

        # 分析新发现的仓库
        new_count = 0
        analyzed = []
        for name, repo in all_repos.items():
            key = f"github_{name.replace('/', '_')}"
            if key in existing:
                continue  # 已有记录

            # 详细分析
            details = self.analyze_repo(name)
            if details:
                self.store.set("resources", key, {
                    "type": "github_project",
                    "domain": domain,
                    **details,
                    "status": "discovered",
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                }, source="github_monitor", confidence=details.get("quality_score", 0.5))
                new_count += 1
                analyzed.append(details)

        return {
            "domain": domain,
            "found": len(all_repos),
            "new": new_count,
            "repos": sorted(analyzed, key=lambda x: x.get("stars", 0), reverse=True),
        }

    def scan_all_domains(self) -> dict:
        """扫描所有领域"""
        results = {}
        total_new = 0
        for domain in self.SEARCH_DOMAINS:
            result = self.scan_domain(domain)
            results[domain] = result
            total_new += result.get("new", 0)

        return {
            "domains_scanned": len(results),
            "total_new_repos": total_new,
            "details": results,
        }

    def get_tracked_repos(self) -> list:
        """获取所有已跟踪的仓库"""
        resources = self.store.get("resources")
        tracked = []
        for key, entry in resources.items():
            val = entry.get("value", entry) if isinstance(entry, dict) else entry
            if isinstance(val, dict) and val.get("type") == "github_project":
                tracked.append({
                    "key": key,
                    "name": val.get("full_name", ""),
                    "stars": val.get("stars", 0),
                    "quality": val.get("quality_score", 0),
                    "activity": val.get("activity_score", 0),
                    "status": val.get("status", ""),
                    "domain": val.get("domain", ""),
                })
        return sorted(tracked, key=lambda x: x.get("stars", 0), reverse=True)

    def check_updates(self) -> list:
        """检查已跟踪仓库的更新"""
        resources = self.store.get("resources")
        updates = []

        for key, entry in resources.items():
            val = entry.get("value", entry) if isinstance(entry, dict) else entry
            if not isinstance(val, dict) or val.get("type") != "github_project":
                continue

            name = val.get("full_name", "")
            if not name:
                continue

            # 检查当前状态
            current = self.analyze_repo(name)
            if not current:
                continue

            old_stars = val.get("stars", 0)
            new_stars = current.get("stars", 0)

            if new_stars != old_stars:
                updates.append({
                    "repo": name,
                    "old_stars": old_stars,
                    "new_stars": new_stars,
                    "star_change": new_stars - old_stars,
                    "old_commits": val.get("recent_commits_count", 0),
                    "new_commits": current.get("recent_commits_count", 0),
                })

                # 更新知识库
                updated_data = {**val, **current}
                self.store.set("resources", key, updated_data,
                              source="github_update_check",
                              confidence=current.get("quality_score", 0.5))

        return updates

    def generate_scan_report(self, results: dict) -> str:
        """生成扫描报告"""
        lines = [
            "=" * 50,
            "GitHub 项目扫描报告",
            "=" * 50,
            f"扫描领域: {results.get('domains_scanned', 0)}个",
            f"新发现项目: {results.get('total_new_repos', 0)}个",
            "",
        ]

        for domain, detail in results.get("details", {}).items():
            if detail.get("new", 0) == 0:
                continue
            lines.append(f"\n--- {domain} ({detail['found']}个发现, {detail['new']}个新增) ---")
            for repo in detail.get("repos", [])[:5]:
                stars = repo.get("stars", 0)
                name = repo.get("full_name", "")
                desc = (repo.get("description", "") or "")[:80]
                lines.append(f"  [{stars}★] {name}")
                if desc:
                    lines.append(f"         {desc}")

        return "\n".join(lines)


# ============================================================
# 4. EvolutionEngine - 进化引擎
# ============================================================

class EvolutionEngine:
    """
    进化引擎：协调知识更新、反馈学习、资源发现、参数调优

    进化循环:
      1. 收集使用反馈 → 调整参数
      2. 发现新资源 → 更新知识库
      3. 分析知识差距 → 生成学习计划
      4. 验证知识质量 → 淘汰过时知识
      5. 生成进化报告
    """

    def __init__(self, base_dir: str = None):
        self.store = KnowledgeStore(base_dir)
        self.feedback = FeedbackCollector(self.store)
        self.github = GitHubMonitor(self.store)
        self.base_dir = self.store.base_dir
        self._evolution_log: List[dict] = []

    # --- 进化周期 ---

    def initialize(self) -> dict:
        """初始化：从现有代码导入所有知识"""
        results = self.store.import_all()
        self._log_evolution("initialize", "从现有代码导入知识", results)
        return results

    def evolve_cycle(self, include_github_scan=True) -> dict:
        """执行一次完整进化周期"""
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "steps": {},
        }

        # Step 1: 分析反馈
        feedback_analysis = self._analyze_feedback()
        report["steps"]["feedback_analysis"] = feedback_analysis

        # Step 2: 参数调优
        param_updates = self._tune_parameters(feedback_analysis)
        report["steps"]["param_updates"] = param_updates

        # Step 2.5: GitHub资源发现
        if include_github_scan:
            try:
                github_scan = self.github.scan_all_domains()
                report["steps"]["github_scan"] = github_scan
            except Exception as e:
                report["steps"]["github_scan"] = {"error": str(e)}

        # Step 3: 知识差距分析
        gaps = self._find_knowledge_gaps()
        report["steps"]["knowledge_gaps"] = gaps

        # Step 4: 知识质量验证
        quality = self._validate_knowledge_quality()
        report["steps"]["quality_check"] = quality

        # Step 4.5: 修订审计 — 追踪知识库版本间变化
        revision = self._audit_revision()
        report["steps"]["revision_audit"] = revision

        # Step 5: 生成进化摘要
        summary = self._generate_evolution_summary(report)
        report["summary"] = summary

        self._log_evolution("evolve_cycle", "完整进化周期", report)
        return report

    # --- 反馈分析 ---

    def _analyze_feedback(self) -> dict:
        """分析反馈数据，识别模式"""
        all_feedback = self.store.get("feedback_log")
        analysis = {
            "total_entries": len(all_feedback),
            "patterns": [],
            "actionable_items": [],
        }

        # 统计被拒绝的审稿类别
        rejected_cats = Counter()
        accepted_cats = Counter()
        low_ratings = []

        for key, entry in all_feedback.items():
            val = entry.get("value", entry) if isinstance(entry, dict) else entry
            if not isinstance(val, dict):
                continue

            if val.get("type") == "review_calibration":
                for cat in val.get("rejected_categories", []):
                    rejected_cats[cat] += 1
                for cat in val.get("accepted_categories", []):
                    accepted_cats[cat] += 1

            if val.get("rating", 5) <= 2:
                low_ratings.append({
                    "type": val.get("type"),
                    "section": val.get("section", ""),
                    "comment": val.get("comment", ""),
                })

        # 识别需要调整的规则
        for cat, count in rejected_cats.most_common(5):
            if count >= 2:  # 同一类别被拒绝2次以上
                analysis["actionable_items"].append({
                    "action": "reduce_sensitivity",
                    "category": cat,
                    "rejected_count": count,
                    "reason": f"该类别的审稿规则被用户拒绝{count}次，可能过于严格",
                })

        analysis["rejected_categories"] = dict(rejected_cats)
        analysis["accepted_categories"] = dict(accepted_cats)
        analysis["low_rating_count"] = len(low_ratings)

        return analysis

    def _tune_parameters(self, feedback_analysis: dict) -> dict:
        """根据反馈分析调优参数"""
        updates = {}

        for item in feedback_analysis.get("actionable_items", []):
            if item["action"] == "reduce_sensitivity":
                cat = item["category"]
                # 降低该类别的权重
                weight_key = f"sensitivity_{cat}"
                current = self.store.get("parameters", weight_key) or {"value": 1.0}
                new_val = max(0.5, current.get("value", 1.0) * 0.9)
                self.store.set("parameters", weight_key,
                              {"value": new_val, "reason": item["reason"]},
                              source="auto_tuning", confidence=0.7)
                updates[weight_key] = {"old": current.get("value"), "new": new_val}

        return updates

    # --- 知识差距分析 ---

    def _find_knowledge_gaps(self) -> dict:
        """识别知识库中的空白"""
        gaps = {
            "missing_mechanisms": [],
            "weak_templates": [],
            "outdated_resources": [],
            "suggestions": [],
        }

        # 检查机制知识完整性
        expected_mechanisms = [
            "ch4_generation", "co2_generation", "toc_degradation",
            "do_impact", "cn_coupling", "seasonal_effect",
            "spatial_differentiation", "biofilm_dynamics",
        ]
        existing_mechanisms = self.store.get("mechanisms")
        for mech in expected_mechanisms:
            found = any(mech in k for k in existing_mechanisms)
            if not found:
                gaps["missing_mechanisms"].append(mech)

        # 检查弱模板
        templates = self.store.get("writing_templates")
        for key, val in templates.items():
            entry = val.get("value", val) if isinstance(val, dict) else val
            if isinstance(entry, dict) and entry.get("needs_improvement"):
                gaps["weak_templates"].append(key)

        # 检查资源时效性
        resources = self.store.get("resources")
        for key, val in resources.items():
            entry = val.get("value", val) if isinstance(val, dict) else val
            if isinstance(entry, dict):
                ts = entry.get("timestamp", "")
                if ts:
                    try:
                        discovered = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        days_old = (datetime.now(timezone.utc) - discovered).days
                        if days_old > 90 and entry.get("status") == "discovered":
                            gaps["outdated_resources"].append(key)
                    except (ValueError, TypeError):
                        pass

        # 生成建议
        if gaps["missing_mechanisms"]:
            gaps["suggestions"].append(
                f"缺少{len(gaps['missing_mechanisms'])}个机制知识条目，建议补充: "
                + ", ".join(gaps["missing_mechanisms"][:3])
            )
        if gaps["weak_templates"]:
            gaps["suggestions"].append(
                f"有{len(gaps['weak_templates'])}个弱模板需要改进"
            )

        return gaps

    # --- 知识质量验证 ---

    def _validate_knowledge_quality(self) -> dict:
        """验证知识库质量"""
        quality = {"categories": {}, "issues": []}

        for cat in KnowledgeStore.CATEGORIES:
            entries = self.store.get(cat)
            cat_quality = {
                "total": len(entries),
                "high_confidence": 0,
                "medium_confidence": 0,
                "low_confidence": 0,
                "avg_confidence": 0,
            }

            confidences = []
            for key, entry in entries.items():
                if isinstance(entry, dict):
                    conf = entry.get("confidence", 0.5)
                    confidences.append(conf)
                    if conf >= 0.8:
                        cat_quality["high_confidence"] += 1
                    elif conf >= 0.5:
                        cat_quality["medium_confidence"] += 1
                    else:
                        cat_quality["low_confidence"] += 1

                    # 标记低置信度条目
                    if conf < 0.4:
                        quality["issues"].append({
                            "category": cat,
                            "key": key,
                            "confidence": conf,
                            "action": "考虑删除或验证",
                        })

            if confidences:
                cat_quality["avg_confidence"] = round(
                    sum(confidences) / len(confidences), 3
                )
            quality["categories"][cat] = cat_quality

        return quality

    def _audit_revision(self) -> dict:
        """修订审计 — 追踪知识库版本间变化"""
        if audit_revision is None:
            return {"status": "skipped", "reason": "revision_audit not available"}

        # 收集当前各知识分类的文本摘要
        current_parts = []
        for cat in KnowledgeStore.CATEGORIES:
            entries = self.store.get(cat)
            if entries:
                summary = f"[{cat}] {len(entries)} entries"
                for key, entry in list(entries.items())[:3]:
                    if isinstance(entry, dict):
                        val = entry.get("value", entry.get("description", ""))
                        if isinstance(val, str):
                            summary += f"\n  {key}: {val[:60]}"
                current_parts.append(summary)
        current_text = '\n\n'.join(current_parts)

        # 与上次快照比较
        snapshot_path = self.store.store_dir / "revision_history.json"
        if snapshot_path.exists():
            try:
                with open(snapshot_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                last_snapshot = history.get("last_snapshot", "")
                if last_snapshot:
                    result = audit_revision(last_snapshot, current_text)
                    summary_data = {
                        "unchanged_ratio": result.unchanged_ratio,
                        "new_ratio": result.new_ratio,
                        "shallow_warning": result.shallow_warning,
                        "paragraphs_original": result.original_paragraphs,
                        "paragraphs_revised": result.revised_paragraphs,
                    }
                    # 保存新快照
                    history["last_snapshot"] = current_text
                    history["last_audit"] = summary_data
                    history["updated"] = datetime.now(timezone.utc).isoformat()
                    with open(snapshot_path, 'w', encoding='utf-8') as f:
                        json.dump(history, f, ensure_ascii=False, indent=2)
                    return summary_data
            except Exception as e:
                logger.debug(f"Revision audit error: {e}")

        # 首次运行，保存初始快照
        snapshot_data = {
            "last_snapshot": current_text,
            "last_audit": None,
            "updated": datetime.now(timezone.utc).isoformat(),
        }
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2)
        return {"status": "initialized", "message": "初始快照已保存，下次进化周期将进行修订审计"}

    # --- 资源发现（基于Web搜索） ---

    def discover_resources(self, query: str, source_type: str = "paper",
                           max_results: int = 5) -> list:
        """
        发现新资源（论文/项目/工具）

        注意：此方法返回搜索建议，实际搜索由外部工具（WebSearch）执行。
        结果通过 feedback.log_discovery() 写入知识库。
        """
        # 生成搜索查询变体
        queries = self._generate_search_queries(query, source_type)

        suggestions = []
        for q in queries[:max_results]:
            suggestions.append({
                "query": q,
                "source_type": source_type,
                "purpose": "知识库扩展",
                "priority": "medium",
            })

        return suggestions

    def _generate_search_queries(self, base_query: str,
                                 source_type: str) -> list:
        """生成搜索查询变体"""
        queries = [base_query]

        if source_type == "paper":
            queries.extend([
                f"{base_query} 2024 2025 2026",
                f"{base_query} review",
                f"{base_query} environmental science",
            ])
        elif source_type == "github":
            queries.extend([
                f"{base_query} github python",
                f"{base_query} open source academic",
                f"{base_query} research tool",
            ])
        elif source_type == "method":
            queries.extend([
                f"{base_query} methodology",
                f"{base_query} analytical method",
            ])

        return queries

    # --- 进化报告 ---

    def _log_evolution(self, action: str, description: str, data: dict):
        """记录进化事件"""
        self._evolution_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "description": description,
            "data_summary": {
                k: (len(v) if isinstance(v, (list, dict)) else v)
                for k, v in data.items()
            } if isinstance(data, dict) else str(data)[:200],
        })

    def _generate_evolution_summary(self, report: dict) -> str:
        """生成进化摘要"""
        lines = ["=== 进化周期报告 ==="]
        lines.append(f"时间: {report['timestamp']}")

        fa = report["steps"].get("feedback_analysis", {})
        lines.append(f"\n反馈分析: 共{fa.get('total_entries', 0)}条反馈")
        if fa.get("actionable_items"):
            lines.append(f"  可执行调整: {len(fa['actionable_items'])}项")

        pu = report["steps"].get("param_updates", {})
        if pu:
            lines.append(f"\n参数调优: 更新了{len(pu)}个参数")
            for key, vals in pu.items():
                lines.append(f"  {key}: {vals.get('old')} -> {vals.get('new')}")

        gaps = report["steps"].get("knowledge_gaps", {})
        if gaps.get("suggestions"):
            lines.append(f"\n知识差距:")
            for s in gaps["suggestions"]:
                lines.append(f"  - {s}")

        quality = report["steps"].get("quality_check", {})
        if quality.get("issues"):
            lines.append(f"\n质量警告: {len(quality['issues'])}个低置信度条目")

        lines.append(f"\n进化日志累计: {len(self._evolution_log)}条记录")
        return "\n".join(lines)

    def get_evolution_status(self) -> dict:
        """获取系统进化状态"""
        return {
            "knowledge_stats": self.store.stats(),
            "feedback_stats": self.feedback.get_feedback_stats(),
            "evolution_log_count": len(self._evolution_log),
            "last_evolution": self._evolution_log[-1] if self._evolution_log else None,
        }

    def get_evolution_report(self) -> str:
        """获取人类可读的进化报告"""
        status = self.get_evolution_status()
        lines = [
            "=" * 50,
            "Self-Evolving Academic AI - 系统状态",
            "=" * 50,
            "",
            "知识库统计:",
        ]

        for cat, stats in status["knowledge_stats"].items():
            desc = KnowledgeStore.CATEGORIES.get(cat, cat)
            lines.append(f"  [{cat}] {desc}: {stats['count']}条, v{stats['version']}")

        lines.append(f"\n反馈统计:")
        fs = status["feedback_stats"]
        lines.append(f"  总反馈: {fs['total']}条")
        for ftype, count in fs.get("by_type", {}).items():
            avg = fs.get("avg_rating", {}).get(ftype, "N/A")
            lines.append(f"  {ftype}: {count}条, 平均评分: {avg}")

        if status["last_evolution"]:
            le = status["last_evolution"]
            lines.append(f"\n上次进化: {le['timestamp']}")
            lines.append(f"  操作: {le['action']} - {le['description']}")

        lines.append(f"\n进化日志: {status['evolution_log_count']}条记录")
        return "\n".join(lines)

    def export_knowledge_for_agent(self, agent_name: str) -> dict:
        """为指定Agent导出其需要的知识子集"""
        agent_knowledge_map = {
            "review_agent": ["review_rules", "parameters", "domain_terms"],
            "writing_agent": ["mechanisms", "writing_templates", "domain_terms", "methods"],
            "visualization_agent": ["methods", "parameters"],
            "analysis_agent": ["methods", "mechanisms", "parameters"],
        }

        categories = agent_knowledge_map.get(agent_name, [])
        export = {}
        for cat in categories:
            entries = self.store.get(cat)
            # 只导出高置信度的知识
            filtered = {}
            for key, entry in entries.items():
                if isinstance(entry, dict) and entry.get("confidence", 0) >= 0.6:
                    filtered[key] = entry.get("value", entry)
                elif not isinstance(entry, dict):
                    filtered[key] = entry
            export[cat] = filtered

        return export


# ============================================================
# 4. 便捷函数
# ============================================================

def init_engine(base_dir: str = None) -> EvolutionEngine:
    """初始化进化引擎并导入所有现有知识"""
    engine = EvolutionEngine(base_dir)
    engine.initialize()
    return engine


def run_evolution(base_dir: str = None) -> str:
    """执行一次进化周期，返回报告"""
    engine = EvolutionEngine(base_dir)
    engine.initialize()
    report = engine.evolve_cycle()
    return report.get("summary", "进化完成")


def get_status(base_dir: str = None) -> str:
    """获取系统状态"""
    engine = EvolutionEngine(base_dir)
    engine.initialize()
    return engine.get_evolution_report()


# ============================================================
# CLI入口
# ============================================================

if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    cmd = args[0] if args else "status"

    if cmd == "init":
        engine = init_engine()
        print(engine.get_evolution_report())
    elif cmd == "evolve":
        print(run_evolution())
    elif cmd == "status":
        print(get_status())
    elif cmd == "import":
        engine = EvolutionEngine()
        results = engine.initialize()
        print("导入结果:")
        for source, ok in results.items():
            print(f"  {source}: {'OK' if ok else 'SKIP'}")
    elif cmd == "scan":
        domain = args[1] if len(args) > 1 else None
        engine = EvolutionEngine()
        engine.initialize()
        if domain and domain != "all":
            result = engine.github.scan_domain(domain)
            print(f"扫描 {domain}: 发现{result.get('found', 0)}个, 新增{result.get('new', 0)}个")
            for repo in result.get("repos", [])[:10]:
                print(f"  [{repo.get('stars', 0)}★] {repo.get('full_name', '')}")
        else:
            results = engine.github.scan_all_domains()
            print(engine.github.generate_scan_report(results))
    elif cmd == "tracked":
        engine = EvolutionEngine()
        engine.initialize()
        repos = engine.github.get_tracked_repos()
        print(f"已跟踪 {len(repos)} 个项目:")
        for r in repos[:20]:
            print(f"  [{r['stars']}★ Q={r['quality']}] {r['name']} ({r['domain']})")
    elif cmd == "updates":
        engine = EvolutionEngine()
        engine.initialize()
        updates = engine.github.check_updates()
        if updates:
            print(f"发现 {len(updates)} 个更新:")
            for u in updates:
                print(f"  {u['repo']}: ★{u['old_stars']}->{u['new_stars']}")
        else:
            print("暂无更新")
    else:
        print("用法: python self_evolving_engine.py [init|evolve|status|import|scan|tracked|updates]")
        print("  scan [domain|all]  - 扫描GitHub项目")
        print("  tracked            - 查看已跟踪项目")
        print("  updates            - 检查项目更新")
