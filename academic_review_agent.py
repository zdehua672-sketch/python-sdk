"""
=============================================================================
Academic Review & Proofreading Agent - 论文自动检查系统
10类检查 + AI痕迹识别 + 修改建议 + 审稿意见级报告
=============================================================================
"""

import re
import os
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# ============================================================================
# 数据结构
# ============================================================================
class Severity(Enum):
    CRITICAL = 'CRITICAL'   # 致命问题，拒稿级别
    MAJOR = 'MAJOR'         # 重大问题，需要修改
    MINOR = 'MINOR'         # 小问题，润色级
    INFO = 'INFO'           # 提示信息

class PaperType(Enum):
    SCI = 'sci'
    CHINESE_THESIS = 'chinese_thesis'
    CHINESE_JOURNAL = 'chinese_journal'

@dataclass
class Issue:
    """单个检查问题"""
    category: str           # 检查类别
    severity: Severity      # 严重级别
    section: str            # 所在章节
    location: str           # 具体位置描述
    problem: str            # 问题描述
    original: str           # 原文片段
    suggestion: str         # 修改建议
    fix: str = ''           # 自动修复文本

@dataclass
class SectionContent:
    """解析后的章节内容"""
    title: str = ''
    body: str = ''
    paragraphs: list = field(default_factory=list)
    sentences: list = field(default_factory=list)

@dataclass
class ReviewReport:
    """完整审稿报告"""
    issues: list = field(default_factory=list)
    scores: dict = field(default_factory=dict)
    paper_type: str = ''
    language: str = ''

    def summary(self):
        by_severity = defaultdict(int)
        by_category = defaultdict(int)
        for issue in self.issues:
            by_severity[issue.severity.value] += 1
            by_category[issue.category] += 1
        return {
            'total': len(self.issues),
            'by_severity': dict(by_severity),
            'by_category': dict(by_category),
        }


# ============================================================================
# 知识库：禁用词、规则、模板
# ============================================================================
class ReviewKB:
    """审稿知识库（从knowledge base文件提取的规则）"""

    # 英文禁用词 → 替换建议
    EN_FORBIDDEN = {
        'prove': 'demonstrate / suggest / indicate',
        'very': '删除，用具体数据替代',
        'a lot of': 'substantial / considerable',
        'get': 'obtain / acquire / derive',
        'big': 'significant / substantial / considerable',
        'good': 'favorable / effective / satisfactory',
        'bad': 'poor / unfavorable / inadequate',
        'nice': 'favorable / acceptable',
        'thing': 'factor / aspect / element',
        'stuff': 'material / substance',
        'lots of': 'numerous / considerable',
        'pretty': '相当 → moderately / relatively',
    }

    # 中文禁用词 → 替换建议
    ZH_FORBIDDEN = {
        '很多': '显著 / 大量 / 较高',
        '差不多': '近似 / 约 / 大约',
        '好': '良好 / 优良 / 较好',
        '坏': '较差 / 偏低 / 不足',
        '搞清楚': '阐明 / 揭示 / 探究',
        '用了': '采用 / 运用 / 利用',
        '一般来说': '通常 / 一般而言 / 总体而言',
        '跟': '与...呈显著相关',
        '比较大的': '显著的 / 较大的',
        '比较小的': '较小的 / 微弱的',
        '还行': '尚可 / 较为理想',
        '感觉': '认为 / 推测',
        '看起来': '表明 / 显示',
    }

    # AI痕迹特征词/句式
    AI_PATTERNS_EN = [
        r"It is (?:important|crucial|essential|worth noting) to (?:note|mention|emphasize)",
        r"(?:delve|dive) into",
        r"in the realm of",
        r"it'?s worth noting that",
        r"the (?:multifaceted|nuanced|intricate) (?:nature|interplay|landscape)",
        r"(?:further|more) research (?:is (?:needed|required|warranted))",
        r"plays a (?:crucial|pivotal|vital|key) role",
        r"(?:shed light|cast light) on",
        r"at the (?:forefront|intersection) of",
        r"(?:holistic|comprehensive|robust) (?:approach|framework|understanding)",
        r"in conclusion,? (?:this study|our (?:findings|results|study))",
        r"(?:tapestry|myriad|plethora|cornucopia)",
        r"(?:leveraging|harnessing|utilizing) (?:the|a) (?:power|potential)",
        r"(?:not only).+?(?:but also)",
        r"to (?:the best of|our knowledge)",
    ]

    AI_PATTERNS_ZH = [
        r"值得[注关]意的是",
        r"(?:深入|进[一壹]步)探讨",
        r"(?:扮演|起着)(?:关键|重要|核心)(?:角色|作用)",
        r"(?:揭示|阐明|展现了?).+(?:深刻|重要)(?:认识|理解|洞察)",
        r"(?:这[一壹]|该)(?:发现|结果)(?:具有|具有着?)(?:重要|深远)(?:意义|价值)",
        r"(?:填补|弥补)(?:了?)(?:研究)?空白",
        r"(?:首次|开创性|创新性地)(?:发现|提出|证明)",
        r"(?:尽管|虽然).+(?:但是|然而).+(?:局限|不足)",
        r"综上所述.{0,10}(?:本文|本研究)",
        r"(?:为).+(?:提供.{0,5}(?:理论|科学|数据)(?:支撑|依据|参考))",
        r"(?:具有|有着)(?:重大|深远|重要)(?:理论|实践)(?:意义|价值)",
    ]

    # 空洞表达（无实质内容的学术套话）
    HOLLOW_PATTERNS_ZH = [
        r"(?:为?).+(?:提供.{0,5}(?:参考|借鉴|依据))",
        r"(?:对?).+(?:具有.{0,5}(?:指导|参考)(?:意义|价值))",
        r"(?:研究|分析)(?:了?).+(?:的?.{0,5}(?:规律|特征|特点))",
        r"(?:丰富|完善)(?:了?)(?:相关|该领域的?)(?:理论|研究)",
        r"有待(?:进[一壹]步|深入)(?:研究|探讨|分析)",
    ]

    HOLLOW_PATTERNS_EN = [
        r"(?:provides|offers|serves as) (?:a |an )?(?:valuable|useful|important) (?:reference|insight|foundation)",
        r"(?:further|additional|more) (?:research|study|investigation) (?:is |was )?(?:needed|required|warranted|necessary)",
        r"(?:shed[s]? light|cast[s]? light) on",
        r"(?:play[s]?|played) a (?:crucial|pivotal|vital|key|significant) role",
    ]

    # SCI各章节时态要求
    SCI_TENSE_RULES = {
        'abstract_background': 'present',
        'abstract_methods': 'past',
        'abstract_results': 'past',
        'abstract_conclusion': 'present',
        'introduction': 'present',
        'methods': 'past',
        'results': 'past',
        'discussion_own': 'past',
        'discussion_literature': 'present',
        'conclusion': 'present',
    }

    # 常见动词的过去式/现在式映射
    VERB_FORMS = {
        'present': ['shows', 'indicates', 'suggests', 'demonstrates', 'reveals',
                     'is', 'are', 'has', 'have', 'provides', 'plays'],
        'past': ['showed', 'indicated', 'suggested', 'demonstrated', 'revealed',
                 'was', 'were', 'had', 'provided', 'played'],
    }

    # 夸大词汇
    OVERCLAIM_EN = ['prove', 'confirm', 'definitive', 'unprecedented',
                    'groundbreaking', 'revolutionary', 'first ever',
                    'novel discovery', 'breakthrough']
    OVERCLAIM_ZH = ['首次发现', '证实', '确证', '重大突破', '开创性',
                    '革命性', '前所未有', '根本性']


# ============================================================================
# 章节解析器
# ============================================================================
class SectionParser:
    """将论文解析为独立章节"""

    # 中文章节标题模式
    ZH_SECTION_PATTERNS = {
        'title': r'^(?!#)(?!\d+\.)(.{5,80})$',
        'abstract': r'(?:摘\s*要|摘要)',
        'keywords': r'(?:关键词|关键字)',
        'introduction': r'(?:1\s*[\.\、]\s*(?:引言|绪论|前言)|引言|绪论|前言)',
        'methods': r'(?:2\s*[\.\、]\s*(?:材料.*方法|研究方法|实验方法|方法)|材料.*方法|研究方法|实验方法)',
        'results': r'(?:3\s*[\.\、]\s*(?:结果|结果与分析|结果.*讨论|结果与讨论)|结果.*分析|结果与讨论)',
        'discussion': r'(?:4\s*[\.\、]\s*(?:讨论|讨论与分析)|讨论)',
        'conclusion': r'(?:5\s*[\.\、]\s*(?:结论|总结)|结论|总结)',
        'references': r'(?:参考文献|References)',
        'acknowledgments': r'(?:致谢|Acknowledgments?)',
    }

    # 英文章节标题模式
    EN_SECTION_PATTERNS = {
        'title': r'^(?!#)(.{10,120})$',
        'abstract': r'(?i)^(?:abstract|summary)\s*$',
        'keywords': r'(?i)^keywords?\s*[:\.]',
        'introduction': r'(?i)^(?:\d+[\.\)]\s*)?introduction\s*$',
        'methods': r'(?i)^(?:\d+[\.\)]\s*)?(?:materials?\s*(?:and|&)\s*methods?|methodology|experimental\s*(?:section|procedures?))\s*$',
        'results': r'(?i)^(?:\d+[\.\)]\s*)?results?\s*(?:(?:and|&)\s*(?:discussion|analysis))?\s*$',
        'discussion': r'(?i)^(?:\d+[\.\)]\s*)?discussion\s*$',
        'conclusion': r'(?i)^(?:\d+[\.\)]\s*)?(?:conclusions?|summary|concluding\s*remarks?)\s*$',
        'references': r'(?i)^(?:references|bibliography|literature\s*cited)\s*$',
        'acknowledgments': r'(?i)^(?:acknowledgments?|funding)\s*$',
    }

    @classmethod
    def detect_language(cls, text):
        """检测论文语言"""
        chinese_chars = len(re.findall(r'[一-鿿]', text))
        total_alpha = len(re.findall(r'[a-zA-Z]', text))
        if chinese_chars > total_alpha * 0.3:
            return 'zh'
        return 'en'

    @classmethod
    def parse(cls, text, language=None):
        """
        解析论文为章节字典

        Returns
        -------
        dict: {section_name: SectionContent}
        """
        if language is None:
            language = cls.detect_language(text)

        patterns = cls.ZH_SECTION_PATTERNS if language == 'zh' else cls.EN_SECTION_PATTERNS

        # 按行扫描，识别章节标题
        lines = text.split('\n')
        sections = {}
        current_section = 'preamble'
        current_lines = []

        for line in lines:
            stripped = line.strip()
            matched_section = None

            for sec_name, pattern in patterns.items():
                if sec_name == 'title':
                    continue
                if re.search(pattern, stripped):
                    matched_section = sec_name
                    break

            if matched_section:
                # 保存之前的章节
                if current_lines:
                    sections[current_section] = cls._build_section(current_lines)
                current_section = matched_section
                current_lines = [stripped]
            else:
                current_lines.append(line)

        # 保存最后一个章节
        if current_lines:
            sections[current_section] = cls._build_section(current_lines)

        return sections

    @classmethod
    def _build_section(cls, lines):
        """构建SectionContent"""
        title = lines[0].strip() if lines else ''
        body = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ''
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', body) if p.strip()]
        sentences = []
        for para in paragraphs:
            # 中文按句号分割，英文按句号+空格分割
            if re.search(r'[一-鿿]', para):
                sents = re.split(r'[。！？；]', para)
            else:
                sents = re.split(r'(?<=[.!?])\s+', para)
            sentences.extend([s.strip() for s in sents if s.strip() and len(s.strip()) > 5])

        return SectionContent(title=title, body=body, paragraphs=paragraphs, sentences=sentences)


# ============================================================================
# 10类检查器
# ============================================================================

# ---------- 1. SCI格式检查 ----------
class SCIChecker:
    """SCI论文格式检查"""

    @staticmethod
    def check(sections, language='en'):
        issues = []
        kb = ReviewKB

        # 标题检查
        if 'preamble' in sections:
            preamble = sections['preamble'].body
            first_line = preamble.split('\n')[0].strip() if preamble else ''

            # 缩写检查
            abbrevs = re.findall(r'\b(?:TOC|COD|BOD|DO|TN|TP|CH4|CO2|NH4|NO3|PCA|HCA)\b', first_line)
            if abbrevs:
                issues.append(Issue(
                    category='SCI格式', severity=Severity.MAJOR,
                    section='标题', location='标题行',
                    problem=f'标题中使用了未展开的缩写: {", ".join(abbrevs)}',
                    original=first_line,
                    suggestion='标题中所有缩写应展开为全称，如 TOC → total organic carbon'
                ))

            # 字数检查
            words = first_line.split()
            if language == 'en' and len(words) > 20:
                issues.append(Issue(
                    category='SCI格式', severity=Severity.MINOR,
                    section='标题', location='标题行',
                    problem=f'标题过长({len(words)}词)，建议控制在15词以内',
                    original=first_line,
                    suggestion='精简标题，保留核心要素：[方法] of [对象] in [范围]'
                ))

        # 摘要检查
        if 'abstract' in sections:
            abstract = sections['abstract'].body
            # 引用检查
            refs = re.findall(r'\[\d+\]', abstract)
            if refs:
                issues.append(Issue(
                    category='SCI格式', severity=Severity.CRITICAL,
                    section='摘要', location='摘要正文',
                    problem=f'摘要中包含参考文献引用 {refs}',
                    original=refs[0],
                    suggestion='摘要中不允许出现参考文献编号，删除所有[N]引用'
                ))

            # 图表引用检查
            fig_refs = re.findall(r'(?:Fig\.?\s*\d|Table\s*\d|图\s*\d|表\s*\d)', abstract)
            if fig_refs:
                issues.append(Issue(
                    category='SCI格式', severity=Severity.CRITICAL,
                    section='摘要', location='摘要正文',
                    problem=f'摘要中包含图表引用: {fig_refs}',
                    original=fig_refs[0],
                    suggestion='摘要中不应引用图表，直接描述数据结果'
                ))

            # 定量数据检查
            has_numbers = bool(re.search(r'\d+\.?\d*\s*(?:mg|ppm|%|mg/L|±|p\s*[<=])', abstract))
            if not has_numbers and len(abstract) > 100:
                issues.append(Issue(
                    category='SCI格式', severity=Severity.MAJOR,
                    section='摘要', location='结果部分',
                    problem='摘要中缺少定量数据（数值、统计量）',
                    original=abstract[:100] + '...',
                    suggestion='摘要结果部分应包含关键定量数据，如浓度值、p值、R²等'
                ))

        # 结论检查
        if 'conclusion' in sections:
            conclusion = sections['conclusion'].body

            # 参考文献
            refs = re.findall(r'\[\d+\]', conclusion)
            if refs:
                issues.append(Issue(
                    category='SCI格式', severity=Severity.MAJOR,
                    section='结论', location='结论正文',
                    problem='结论中包含参考文献引用',
                    original=refs[0] if refs else '',
                    suggestion='结论中不应引用参考文献'
                ))

            # 夸大词汇
            for word in kb.OVERCLAIM_EN if language == 'en' else kb.OVERCLAIM_ZH:
                if word.lower() in conclusion.lower():
                    issues.append(Issue(
                        category='SCI格式', severity=Severity.MAJOR,
                        section='结论', location='结论正文',
                        problem=f'结论中使用了夸大词汇: "{word}"',
                        original=word,
                        suggestion=f'替换为更谨慎的表述，如 suggest / indicate / demonstrate'
                    ))

        return issues


# ---------- 2. 中文论文格式检查 ----------
class ChineseChecker:
    """中文论文格式检查"""

    @staticmethod
    def check(sections, language='zh'):
        if language != 'zh':
            return []
        issues = []

        # 摘要检查
        if 'abstract' in sections:
            abstract = sections['abstract'].body
            # "本文"检查
            if '本文' in abstract or '本论文' in abstract:
                issues.append(Issue(
                    category='中文格式', severity=Severity.MINOR,
                    section='摘要', location='摘要正文',
                    problem='摘要中使用了"本文/本论文"',
                    original='本文',
                    suggestion='摘要中删除"本文"，直接陈述研究内容'
                ))

        # 引言检查
        if 'introduction' in sections:
            intro = sections['introduction'].body
            if len(intro) < 500:
                issues.append(Issue(
                    category='中文格式', severity=Severity.MAJOR,
                    section='引言', location='引言全文',
                    problem=f'引言过短({len(intro)}字)，建议≥800字',
                    original=intro[:50] + '...',
                    suggestion='补充背景文献、研究现状和研究空白的论述'
                ))

            # 检查是否有"然而"等转折词标识研究空白
            gap_markers = ['然而', '但是', '但', '尽管', '目前']
            has_gap = any(m in intro for m in gap_markers)
            if not has_gap:
                issues.append(Issue(
                    category='中文格式', severity=Severity.MAJOR,
                    section='引言', location='引言中段',
                    problem='引言中缺少转折词（然而/但是/尽管），可能未明确指出研究空白',
                    original='',
                    suggestion='在引言中段用"然而"等转折词引出现有研究的不足'
                ))

        # GB/T 7714参考文献格式检查
        if 'references' in sections:
            ref_text = sections['references'].body
            refs = re.split(r'\n\s*\[\d+\]', ref_text)
            for i, ref in enumerate(refs[:5]):  # 检查前5条
                if not ref.strip():
                    continue
                # 检查期刊论文格式 [J]
                if '[J]' in ref:
                    # 检查是否有卷(期):页码格式
                    if not re.search(r'\d+\(\d+\):\s*\d+', ref):
                        issues.append(Issue(
                            category='中文格式', severity=Severity.MINOR,
                            section='参考文献', location=f'第{i+1}条',
                            problem='参考文献格式不完整，缺少"卷(期):起止页码"',
                            original=ref[:80] + '...',
                            suggestion='GB/T 7714格式: 作者. 题名[J]. 刊名, 年, 卷(期): 页码.'
                        ))

        # 标点规范检查
        for sec_name, sec in sections.items():
            body = sec.body
            # 中文文字段落中使用英文逗号
            cn_text_blocks = re.findall(r'[一-鿿，。；：]{10,}', body)
            for block in cn_text_blocks[:3]:
                if ',' in block and '，' not in block:
                    issues.append(Issue(
                        category='中文格式', severity=Severity.MINOR,
                        section=sec_name, location='正文',
                        problem='中文文段中使用了英文逗号',
                        original=block[:50],
                        suggestion='中文文段应使用全角逗号"，"'
                    ))
                    break

        return issues


# ---------- 3. 错别字检查 ----------
class TypoChecker:
    """错别字和拼写检查"""

    # 常见学术错别字
    ZH_TYPOS = {
        '分折': '分析', '研完': '研究', '现像': '现象',
        '原素': '元素', '幅射': '辐射', '融恰': '融洽',
        '气侯': '气候', '碳源': '碳源', '水份': '水分',
        '反映': '反应', '包函': '包含', '具全': '具体',
        '关连': '关联', '沿续': '延续', '消毁': '销毁',
    }

    EN_TYPOS = {
        'teh': 'the', 'recieve': 'receive', 'occurence': 'occurrence',
        'seperate': 'separate', 'definately': 'definitely',
        'occured': 'occurred', 'comparision': 'comparison',
        'analisis': 'analysis', 'paramaters': 'parameters',
        'significient': 'significant', 'concentrationn': 'concentration',
        'dissloved': 'dissolved', 'enviroment': 'environment',
        'polluant': 'pollutant', 'speciment': 'specimen',
    }

    @staticmethod
    def check(sections, language='en'):
        issues = []
        typos = TypoChecker.ZH_TYPOS if language == 'zh' else TypoChecker.EN_TYPOS

        for sec_name, sec in sections.items():
            body = sec.body
            for wrong, correct in typos.items():
                matches = [(m.start(), m.group()) for m in re.finditer(re.escape(wrong), body, re.IGNORECASE)]
                for pos, match in matches[:2]:  # 每个词最多报2次
                    context = body[max(0, pos-20):pos+20]
                    issues.append(Issue(
                        category='错别字', severity=Severity.MINOR,
                        section=sec_name, location=f'位置{pos}',
                        problem=f'疑似错别字/拼写错误: "{match}"',
                        original=context,
                        suggestion=f'修正为: "{correct}"',
                        fix=correct,
                    ))

        return issues


# ---------- 4. 学术语法检查 ----------
class GrammarChecker:
    """学术语法检查（禁用词+口语化）"""

    @staticmethod
    def check(sections, language='en'):
        issues = []
        forbidden = ReviewKB.EN_FORBIDDEN if language == 'en' else ReviewKB.ZH_FORBIDDEN

        for sec_name, sec in sections.items():
            if sec_name in ('references', 'acknowledgments'):
                continue
            body = sec.body
            for word, suggestion in forbidden.items():
                if language == 'zh':
                    pattern = re.escape(word)
                else:
                    pattern = r'\b' + re.escape(word) + r'\b'
                matches = list(re.finditer(pattern, body, re.IGNORECASE))
                for m in matches[:2]:
                    context = body[max(0, m.start()-15):m.end()+15]
                    issues.append(Issue(
                        category='学术语法', severity=Severity.MINOR,
                        section=sec_name, location=f'禁用词',
                        problem=f'非学术用语: "{word}"',
                        original=context,
                        suggestion=f'替换为: {suggestion}',
                    ))

        return issues


# ---------- 5. 引文规范检查 ----------
class CitationChecker:
    """引文规范检查"""

    @staticmethod
    def check(sections, language='en'):
        issues = []

        # 统计正文中引用次数
        all_text = ' '.join(sec.body for sec in sections.values() if sec.body)
        citations = re.findall(r'\[(\d+(?:[-,]\d+)*)\]', all_text)
        unique_refs = set()
        for c in citations:
            for part in re.split(r'[,]', c):
                if '-' in part:
                    start, end = part.split('-')
                    for i in range(int(start), int(end)+1):
                        unique_refs.add(i)
                else:
                    unique_refs.add(int(part))

        # 引用数量检查
        if len(unique_refs) < 15:
            issues.append(Issue(
                category='引文规范', severity=Severity.MAJOR if len(unique_refs) < 10 else Severity.MINOR,
                section='全文', location='参考文献',
                problem=f'参考文献数量偏少({len(unique_refs)}篇)，SCI论文通常需要25-50篇',
                original=f'共引用{len(unique_refs)}篇文献',
                suggestion='补充领域内近5年的重要文献'
            ))

        # 引用分布检查
        for sec_name in ['introduction', 'discussion']:
            if sec_name in sections:
                sec_refs = re.findall(r'\[\d+\]', sections[sec_name].body)
                if len(sec_refs) < 3:
                    issues.append(Issue(
                        category='引文规范', severity=Severity.MAJOR,
                        section=sec_name, location='正文',
                        problem=f'{sec_name}章节引用不足({len(sec_refs)}处)',
                        original='',
                        suggestion=f'{sec_name}应充分引用文献支撑论述'
                    ))

        return issues


# ---------- 6. 图表规范检查 ----------
class FigureChecker:
    """图表规范检查"""

    @staticmethod
    def check(sections, language='en'):
        issues = []
        all_text = ' '.join(sec.body for sec in sections.values() if sec.body)

        # 图表引用格式检查
        if language == 'en':
            bad_refs = re.findall(r'as (?:shown|illustrated|depicted) in (?:Fig|Figure)\.?\s*\d', all_text, re.IGNORECASE)
            for ref in bad_refs[:3]:
                issues.append(Issue(
                    category='图表规范', severity=Severity.MINOR,
                    section='Results', location='图表引用',
                    problem=f'图表引用格式不规范: "{ref}"',
                    original=ref,
                    suggestion='使用括号引用: (Fig. X) 而非 "as shown in Fig. X"'
                ))
        else:
            bad_refs = re.findall(r'如图\d', all_text)
            for ref in bad_refs[:3]:
                issues.append(Issue(
                    category='图表规范', severity=Severity.MINOR,
                    section='结果', location='图表引用',
                    problem=f'图表引用格式不规范: "{ref}"',
                    original=ref,
                    suggestion='使用括号引用: (图X) 而非 "如图X所示"'
                ))

        # Results中是否引用了图表
        if 'results' in sections:
            results_text = sections['results'].body
            fig_refs = re.findall(r'(?:Fig|Figure|图)\.?\s*\d', results_text, re.IGNORECASE)
            if len(fig_refs) < 2:
                issues.append(Issue(
                    category='图表规范', severity=Severity.MAJOR,
                    section='Results', location='结果正文',
                    problem='结果部分图表引用过少，数据应与图表对应',
                    original='',
                    suggestion='在Results中逐一引用图表，如 "The TOC concentrations varied... (Fig. 1)"'
                ))

        # 坐标轴单位检查（从图注推断）
        caption_pattern = r'(?:Fig\.?\s*\d|图\s*\d)[^\n]+'
        captions = re.findall(caption_pattern, all_text, re.IGNORECASE)
        for cap in captions[:5]:
            if not re.search(r'\(.+\)', cap) and not re.search(r'（.+）', cap):
                issues.append(Issue(
                    category='图表规范', severity=Severity.MINOR,
                    section='图表', location='图注',
                    problem='图注可能缺少单位信息',
                    original=cap,
                    suggestion='图注应包含统计方法和单位，如 "(Mean±SD, n=15)"'
                ))

        return issues


# ---------- 7. 数据逻辑检查 ----------
class DataLogicChecker:
    """数据逻辑一致性检查"""

    @staticmethod
    def check(sections, language='en'):
        issues = []

        # 检查Results中的p值是否合理
        if 'results' in sections:
            results = sections['results'].body
            p_values = re.findall(r'p\s*[=<>≤≥]\s*0\.?\d*', results, re.IGNORECASE)

            for pv in p_values[:5]:
                num_match = re.search(r'0\.?\d*', pv)
                if num_match:
                    val = float(num_match.group())
                    if val > 0.05 and 'significant' in results.lower():
                        # 检查上下文
                        idx = results.find(pv)
                        context = results[max(0, idx-50):idx+50]
                        if 'significant' in context.lower():
                            issues.append(Issue(
                                category='数据逻辑', severity=Severity.CRITICAL,
                                section='Results', location='统计检验',
                                problem=f'数据矛盾: p={val} ≥ 0.05 但描述为 "significant"',
                                original=context,
                                suggestion='p ≥ 0.05 时应使用 "not significant" 或 "no significant difference"'
                            ))

            # 检查百分比加总
            pcts = re.findall(r'(\d+\.?\d*)\s*%', results)
            if len(pcts) >= 3:
                try:
                    pct_vals = [float(p) for p in pcts[:10]]
                    total = sum(pct_vals)
                    if 95 < total < 105 and len(pct_vals) >= 3:
                        # 这可能是分类百分比，需要加总100
                        pass  # 只提示不报错
                except ValueError:
                    pass

        # 检查Results和Discussion的数据一致性
        if 'results' in sections and 'discussion' in sections:
            results_nums = set(re.findall(r'\d+\.?\d*\s*(?:mg/L|ppm|%)', sections['results'].body))
            discussion_nums = set(re.findall(r'\d+\.?\d*\s*(?:mg/L|ppm|%)', sections['discussion'].body))
            # Discussion中引用的结果数据应在Results中出现
            unique_in_disc = discussion_nums - results_nums
            for num in list(unique_in_disc)[:3]:
                issues.append(Issue(
                    category='数据逻辑', severity=Severity.MINOR,
                    section='Discussion', location='数据引用',
                    problem=f'Discussion中的数据 "{num}" 在Results中未找到',
                    original=num,
                    suggestion='确保Discussion引用的数据与Results一致'
                ))

        return issues


# ---------- 8. Discussion逻辑检查 ----------
class DiscussionChecker:
    """Discussion逻辑质量检查"""

    @staticmethod
    def check(sections, language='en'):
        issues = []

        if 'discussion' not in sections:
            return issues

        disc = sections['discussion'].body
        paragraphs = sections['discussion'].paragraphs

        # 检查是否只是复述结果
        if 'results' in sections:
            results = sections['results'].body
            # 提取Results中的数据句式
            result_patterns = re.findall(r'(?:was|were|ranged from|mean|average|±)\s', results, re.IGNORECASE)
            disc_patterns = re.findall(r'(?:was|were|ranged from|mean|average|±)\s', disc, re.IGNORECASE)

            if len(disc_patterns) > len(disc.split()) * 0.05:  # Discussion中描述性语句过多
                issues.append(Issue(
                    category='Discussion逻辑', severity=Severity.MAJOR,
                    section='Discussion', location='整体',
                    problem='Discussion可能只是复述了Results，缺少机制解释',
                    original='',
                    suggestion='Discussion应解释"为什么"而不仅是"是什么"。每个发现应有：\n'
                               '1. 发现描述（简短）\n2. 机制解释（为什么）\n3. 文献对比（与谁一致/不同）'
                ))

        # 检查是否有机制解释
        mechanism_keywords_en = [
            'because', 'due to', 'attributed to', 'resulted from',
            'mechanism', 'pathway', 'process', 'metabolism',
            'anaerobic', 'aerobic', 'microbial', 'degradation',
        ]
        mechanism_keywords_zh = [
            '因为', '由于', '归因于', '源于', '机制', '途径',
            '过程', '代谢', '厌氧', '好氧', '微生物', '降解',
        ]
        keywords = mechanism_keywords_zh if language == 'zh' else mechanism_keywords_en

        mech_count = sum(1 for k in keywords if k.lower() in disc.lower())
        if mech_count < 3:
            issues.append(Issue(
                category='Discussion逻辑', severity=Severity.CRITICAL,
                section='Discussion', location='全文',
                problem=f'Discussion缺少机制解释（仅检测到{mech_count}个机制关键词）',
                original='',
                suggestion='每个发现都需要机制解释：\n'
                           '- 从微生物/化学/物理过程角度解释原因\n'
                           '- 引用支持该机制的文献\n'
                           '- 例如："CH4浓度升高可归因于厌氧条件下产甲烷菌活性增强"'
            ))

        # 检查是否有文献对比
        lit_compare = re.findall(r'(?:consistent with|similar to|in agreement|in line with|'
                                  r'与.*一致|与.*类似|与.*相符|'
                                  r'differed from|contrary to|unlike|'
                                  r'与.*不同|不同于)', disc, re.IGNORECASE)
        if len(lit_compare) < 2:
            issues.append(Issue(
                category='Discussion逻辑', severity=Severity.MAJOR,
                section='Discussion', location='文献对比',
                problem='Discussion缺少与文献的对比讨论',
                original='',
                suggestion='至少每个主要发现应与1-2篇文献对比：\n'
                           '- "与XX等[ref]的研究一致，本研究发现..."\n'
                           '- "不同于XX等[ref]的报道，本研究中..."'
            ))

        # 检查是否有局限性讨论
        limitation_keywords = ['limit', 'caveat', 'shortcoming', 'drawback',
                               '局限', '不足', '限制', '有待']
        has_limitations = any(k.lower() in disc.lower() for k in limitation_keywords)
        if not has_limitations:
            issues.append(Issue(
                category='Discussion逻辑', severity=Severity.MINOR,
                section='Discussion', location='文末',
                problem='Discussion缺少研究局限性讨论',
                original='',
                suggestion='在Discussion末尾添加1段局限性：\n'
                           '"本研究存在以下局限：(1) 采样时间有限；(2) ..."'
            ))

        return issues


# ---------- 9. AI痕迹检查 ----------
class AIDetector:
    """AI生成文本痕迹检查"""

    @staticmethod
    def check(sections, language='en'):
        issues = []
        patterns = ReviewKB.AI_PATTERNS_EN if language == 'en' else ReviewKB.AI_PATTERNS_ZH
        hollow = ReviewKB.HOLLOW_PATTERNS_EN if language == 'en' else ReviewKB.HOLLOW_PATTERNS_ZH

        for sec_name, sec in sections.items():
            if sec_name in ('references', 'acknowledgments', 'preamble'):
                continue
            body = sec.body

            # AI套话模式匹配
            for pattern in patterns:
                matches = list(re.finditer(pattern, body, re.IGNORECASE))
                for m in matches[:2]:
                    context = body[max(0, m.start()-10):m.end()+10]
                    issues.append(Issue(
                        category='AI痕迹', severity=Severity.MAJOR,
                        section=sec_name, location='疑似AI句式',
                        problem=f'检测到AI常用句式',
                        original=context.strip(),
                        suggestion='替换为更自然的学术表达，避免模板化套话'
                    ))

            # 空洞表达检查
            for pattern in hollow:
                matches = list(re.finditer(pattern, body, re.IGNORECASE))
                for m in matches[:2]:
                    context = body[max(0, m.start()-10):m.end()+10]
                    issues.append(Issue(
                        category='AI痕迹', severity=Severity.MINOR,
                        section=sec_name, location='空洞表达',
                        problem='空洞学术套话，缺乏实质内容',
                        original=context.strip(),
                        suggestion='删除或替换为有具体数据支撑的表述'
                    ))

        # 检查全文句式重复度
        all_sentences = []
        for sec in sections.values():
            all_sentences.extend(sec.sentences)

        if len(all_sentences) > 10:
            # 检查句式开头重复
            starts = [s[:15] for s in all_sentences if len(s) > 15]
            from collections import Counter
            start_counts = Counter(starts)
            repeated = [(k, v) for k, v in start_counts.items() if v >= 3]
            for pattern, count in repeated[:3]:
                issues.append(Issue(
                    category='AI痕迹', severity=Severity.MINOR,
                    section='全文', location='句式重复',
                    problem=f'句式开头重复{count}次: "{pattern}..."',
                    original=pattern,
                    suggestion='变换句式开头，避免单调重复。交替使用：\n'
                               '- 主动句/被动句\n'
                               '- 长句/短句\n'
                               '- 数据开头/方法开头/结论开头'
                ))

        return issues


# ---------- 10. 学术重复表达检查 ----------
class RepetitionChecker:
    """学术重复表达检查"""

    @staticmethod
    def check(sections, language='en'):
        issues = []

        # 检查Abstract与Conclusion重复
        if 'abstract' in sections and 'conclusion' in sections:
            abstract = sections['abstract'].body
            conclusion = sections['conclusion'].body

            # 提取数字和关键词
            abs_nums = set(re.findall(r'\d+\.?\d*', abstract))
            con_nums = set(re.findall(r'\d+\.?\d*', conclusion))

            if abs_nums and con_nums:
                overlap = abs_nums & con_nums
                if len(overlap) > 3 and len(abs_nums) > 3:
                    overlap_ratio = len(overlap) / min(len(abs_nums), len(con_nums))
                    if overlap_ratio > 0.7:
                        issues.append(Issue(
                            category='学术重复', severity=Severity.MAJOR,
                            section='结论', location='全文',
                            problem=f'结论与摘要高度重复（数据重叠率{overlap_ratio:.0%}）',
                            original='',
                            suggestion='结论应比摘要更精炼，侧重研究贡献而非重复数据'
                        ))

        # 检查章节内部重复段落
        for sec_name, sec in sections.items():
            if len(sec.paragraphs) < 3:
                continue
            for i in range(len(sec.paragraphs)):
                for j in range(i+1, len(sec.paragraphs)):
                    p1_words = set(sec.paragraphs[i].split())
                    p2_words = set(sec.paragraphs[j].split())
                    if len(p1_words) > 10 and len(p2_words) > 10:
                        similarity = len(p1_words & p2_words) / min(len(p1_words), len(p2_words))
                        if similarity > 0.6:
                            issues.append(Issue(
                                category='学术重复', severity=Severity.MINOR,
                                section=sec_name, location=f'第{i+1}段与第{j+1}段',
                                problem=f'段落间内容重复度高({similarity:.0%})',
                                original=sec.paragraphs[i][:60] + '...',
                                suggestion='合并或删除重复段落，确保每段有独特的贡献'
                            ))

        # 检查高频词（学术八股）
        if language == 'zh':
            overused = ['研究表明', '结果显示', '分析发现', '可以发现']
        else:
            overused = ['the results showed', 'it was found that', 'the analysis revealed',
                        'as shown in', 'it can be seen that']

        for sec_name, sec in sections.items():
            if sec_name in ('references', 'acknowledgments', 'preamble'):
                continue
            body = sec.body.lower() if language == 'en' else sec.body
            for phrase in overused:
                count = body.count(phrase.lower() if language == 'en' else phrase)
                if count >= 4:
                    issues.append(Issue(
                        category='学术重复', severity=Severity.MINOR,
                        section=sec_name, location='高频表达',
                        problem=f'表达重复: "{phrase}" 出现{count}次',
                        original=phrase,
                        suggestion='交替使用同义表达：\n'
                                   + '\n'.join(f'  - {p}' for p in overused if p != phrase)
                    ))

        return issues


# ============================================================================
# 综合评分系统
# ============================================================================
class Scorer:
    """论文质量评分"""

    DIMENSIONS = {
        'SCI格式': {'weight': 0.15, 'description': '格式规范性'},
        '中文格式': {'weight': 0.10, 'description': '中文格式规范'},
        '错别字': {'weight': 0.10, 'description': '拼写正确性'},
        '学术语法': {'weight': 0.10, 'description': '语言学术性'},
        '引文规范': {'weight': 0.10, 'description': '引用规范性'},
        '图表规范': {'weight': 0.10, 'description': '图表规范性'},
        '数据逻辑': {'weight': 0.15, 'description': '数据一致性'},
        'Discussion逻辑': {'weight': 0.10, 'description': '讨论深度'},
        'AI痕迹': {'weight': 0.05, 'description': '自然度'},
        '学术重复': {'weight': 0.05, 'description': '原创性'},
    }

    @classmethod
    def score(cls, issues):
        """根据问题计算各维度得分(0-10)"""
        scores = {}
        penalty = defaultdict(float)

        for issue in issues:
            if issue.severity == Severity.CRITICAL:
                penalty[issue.category] += 2.0
            elif issue.severity == Severity.MAJOR:
                penalty[issue.category] += 1.0
            elif issue.severity == Severity.MINOR:
                penalty[issue.category] += 0.3

        for dim, config in cls.DIMENSIONS.items():
            p = penalty.get(dim, 0)
            score = max(1.0, 10.0 - p)
            scores[dim] = round(score, 1)

        # 加权总分
        total = sum(scores.get(dim, 10) * config['weight']
                    for dim, config in cls.DIMENSIONS.items())
        scores['总分'] = round(total, 1)

        return scores


# ============================================================================
# 主Agent
# ============================================================================
class AcademicReviewAgent:
    """
    论文自动检查Agent

    10类检查 → 评分 → 修改建议 → 审稿意见级报告
    """

    CHECKERS = [
        ('SCI格式', SCIChecker),
        ('中文格式', ChineseChecker),
        ('错别字', TypoChecker),
        ('学术语法', GrammarChecker),
        ('引文规范', CitationChecker),
        ('图表规范', FigureChecker),
        ('数据逻辑', DataLogicChecker),
        ('Discussion逻辑', DiscussionChecker),
        ('AI痕迹', AIDetector),
        ('学术重复', RepetitionChecker),
    ]

    def __init__(self, paper_type='sci', language='auto'):
        self.paper_type = paper_type
        self.language = language

    def review(self, text_or_path):
        """
        审稿入口

        Parameters
        ----------
        text_or_path : str
            论文文本或文件路径（.md/.txt）

        Returns
        -------
        ReviewReport
        """
        # 加载文本
        if os.path.isfile(text_or_path):
            with open(text_or_path, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            text = text_or_path

        # 检测语言
        if self.language == 'auto':
            self.language = SectionParser.detect_language(text)

        # 解析章节
        sections = SectionParser.parse(text, self.language)

        print(f"\n{'='*60}")
        print(f"Academic Review Agent - 论文自动检查")
        print(f"语言: {self.language} | 类型: {self.paper_type}")
        print(f"检测到{len(sections)}个章节: {', '.join(sections.keys())}")
        print(f"{'='*60}\n")

        # 运行所有检查器
        all_issues = []
        for name, checker in self.CHECKERS:
            try:
                issues = checker.check(sections, self.language)
                all_issues.extend(issues)
                if issues:
                    print(f"  [{name}] 发现{len(issues)}个问题")
                else:
                    print(f"  [{name}] 通过")
            except Exception as e:
                print(f"  [{name}] 检查出错: {e}")

        # 评分
        scores = Scorer.score(all_issues)

        # 生成报告
        report = ReviewReport(
            issues=all_issues,
            scores=scores,
            paper_type=self.paper_type,
            language=self.language,
        )

        return report

    def generate_report(self, report, output_path=None):
        """生成可读的审稿报告"""
        lines = []
        lines.append('=' * 60)
        lines.append('论文审稿报告 - Academic Review Report')
        lines.append('=' * 60)

        # 评分摘要
        lines.append('')
        lines.append('## 评分 Summary')
        lines.append('')
        for dim, config in Scorer.DIMENSIONS.items():
            score = report.scores.get(dim, 10)
            bar = '#' * int(score) + '.' * (10 - int(score))
            status = 'OK' if score >= 7 else ('--' if score >= 5 else '!!')
            lines.append(f'  {status} {dim:12s} [{bar}] {score:.1f}/10  {config["description"]}')
        lines.append(f'  {"-"*45}')
        lines.append(f'  ★ 加权总分: {report.scores.get("总分", 0):.1f}/10')

        # 总结
        summary = report.summary()
        lines.append('')
        lines.append(f'## 问题统计: 共{summary["total"]}个')
        for sev, count in sorted(summary['by_severity'].items()):
            lines.append(f'  {sev}: {count}个')
        lines.append('')

        # 按严重级别排列问题
        lines.append('## 详细问题列表')
        severity_order = {Severity.CRITICAL: 0, Severity.MAJOR: 1, Severity.MINOR: 2, Severity.INFO: 3}
        sorted_issues = sorted(report.issues, key=lambda x: severity_order.get(x.severity, 9))

        for i, issue in enumerate(sorted_issues, 1):
            sev_icon = {'CRITICAL': '🔴', 'MAJOR': '🟡', 'MINOR': '🔵', 'INFO': 'ℹ️'}
            lines.append('')
            lines.append(f'--- [{i}/{len(sorted_issues)}] {sev_icon.get(issue.severity.value, "")} {issue.severity.value} ---')
            lines.append(f'类别: {issue.category}')
            lines.append(f'章节: {issue.section}')
            lines.append(f'问题: {issue.problem}')
            if issue.original:
                lines.append(f'原文: {issue.original}')
            lines.append(f'建议: {issue.suggestion}')
            if issue.fix:
                lines.append(f'修复: {issue.fix}')

        # 终稿审稿意见模板
        lines.append('')
        lines.append('=' * 60)
        lines.append('## 模拟审稿意见 (Reviewer Comments)')
        lines.append('')

        critical = [i for i in report.issues if i.severity == Severity.CRITICAL]
        major = [i for i in report.issues if i.severity == Severity.MAJOR]

        if critical:
            lines.append('### Major Issues (必须修改)')
            for i, issue in enumerate(critical, 1):
                lines.append(f'{i}. [{issue.category}] {issue.problem}')
                lines.append(f'   Suggestion: {issue.suggestion}')
                lines.append('')

        if major:
            lines.append('### Minor Issues (建议修改)')
            for i, issue in enumerate(major, 1):
                lines.append(f'{i}. [{issue.category}] {issue.problem}')
                lines.append(f'   Suggestion: {issue.suggestion}')
                lines.append('')

        if not critical and not major:
            lines.append('No major issues found. The manuscript is in good shape.')

        # 综合评价
        total = report.scores.get('总分', 0)
        lines.append('### Overall Assessment')
        if total >= 8.5:
            lines.append('The manuscript is well-written and ready for submission with minor polishing.')
        elif total >= 7.0:
            lines.append('The manuscript is generally acceptable but needs moderate revision.')
        elif total >= 5.0:
            lines.append('The manuscript requires substantial revision before it can be considered for publication.')
        else:
            lines.append('The manuscript requires major restructuring and rewriting.')

        report_text = '\n'.join(lines)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\n报告已保存至: {output_path}")

        return report_text


# ============================================================================
# 便捷入口
# ============================================================================
def review_paper(text_or_path, paper_type='sci', language='auto', output_path=None):
    """
    一键审稿

    Parameters
    ----------
    text_or_path : str, 论文文本或文件路径
    paper_type : 'sci' | 'chinese_thesis' | 'chinese_journal'
    language : 'auto' | 'zh' | 'en'
    output_path : str, 报告输出路径

    Returns
    -------
    ReviewReport, report_text: str
    """
    agent = AcademicReviewAgent(paper_type=paper_type, language=language)
    report = agent.review(text_or_path)
    report_text = agent.generate_report(report, output_path=output_path)
    return report, report_text
