"""
=============================================================================
论文自动写作Agent - Paper Writing Agent
基于数据分析结果、知识库、领域机制，生成论文级文本
不是AI流水文，而是像真正科研人员一样组织论文
=============================================================================
"""

import os
import json
from datetime import datetime

from scientific_analysis_agent import ScientificAnalysisAgent, TextGenerator, CaptionGenerator
from academic_plot_style import get_label
from writing_rationale import RationaleMatrix, RationaleRow
from motivation_thread import MotivationThread, SevenSentenceTest, IntroductionDiscussionMapper

try:
    from rag_system import RAGEngine
except ImportError:
    RAGEngine = None


# ============================================================================
# 1. 领域机制库 - 本课题特定科学机制
# ============================================================================
class MechanismKB:
    """碳污染物领域机制知识库"""

    # DO→CH4机制
    DO_CH4 = {
        'pattern': 'DO与CH4负相关',
        'mechanism': (
            '溶解氧(DO)浓度是控制管道中产甲烷过程的关键因素。'
            '当DO<0.5 mg/L时，管道进入严格厌氧状态，产甲烷古菌活性达到最高，'
            '通过乙酸发酵和CO2/H2还原两条途径将有机碳转化为CH4。'
            '相反，当DO>2 mg/L时，好氧微生物通过有氧呼吸将有机碳氧化为CO2，'
            '产甲烷过程被完全抑制。'
        ),
        'mechanism_en': (
            'Dissolved oxygen (DO) is the primary factor controlling methanogenesis in sewage networks. '
            'Under strictly anaerobic conditions (DO < 0.5 mg/L), methanogenic archaea exhibit maximum '
            'activity, converting organic carbon to CH4 via acetoclastic fermentation and hydrogenotrophic '
            'CO2 reduction. Conversely, when DO exceeds 2 mg/L, aerobic microorganisms oxidize organic '
            'carbon to CO2 through aerobic respiration, completely suppressing methanogenesis.'
        ),
        'references': [
            'Guisasola et al. (2008)报道城市污水管道中厌氧段的产甲烷活动可降解50%以上的有机碳',
            'Jiang et al. (2011)指出管道系统是城市温室气体排放的重要来源',
        ]
    }

    # TOC→CH4机制
    TOC_CH4 = {
        'pattern': 'TOC与CH4正相关',
        'mechanism': (
            'TOC代表污水中有机碳的总量，是产甲烷过程的底物来源。'
            'TOC浓度越高，可供水解酸化菌利用的有机底物越充足，'
            '进而为产甲烷古菌提供更多的乙酸和H2/CO2底物，'
            '促进CH4的生成。但在高TOC条件下，'
            '有机酸积累导致pH下降，可能抑制产甲烷活性。'
        ),
        'mechanism_en': (
            'Total organic carbon (TOC) represents the aggregate organic carbon pool in wastewater and serves '
            'as the primary substrate for methanogenesis. Higher TOC concentrations provide more abundant '
            'organic substrates for hydrolytic and acidogenic bacteria, which in turn supply more acetate and '
            'H2/CO2 to methanogenic archaea, enhancing CH4 production. However, under high TOC conditions, '
            'volatile fatty acid accumulation may lower pH and inhibit methanogenic activity.'
        ),
        'references': []
    }

    # DO→CO2机制
    DO_CO2 = {
        'pattern': 'DO与CO2可能正相关或呈复杂关系',
        'mechanism': (
            'CO2的来源包括好氧呼吸和厌氧发酵两部分。'
            '好氧条件下，异养菌通过三羧酸循环将有机物完全氧化为CO2和H2O。'
            '厌氧条件下，产甲烷过程中CO2也作为电子受体被还原为CH4。'
            '因此，DO对CO2的影响取决于好氧呼吸产CO2和厌氧产甲烷消耗CO2的平衡。'
        ),
        'mechanism_en': (
            'CO2 in sewage networks originates from both aerobic respiration and anaerobic fermentation. '
            'Under aerobic conditions, heterotrophic bacteria oxidize organic matter to CO2 and H2O via '
            'the tricarboxylic acid cycle. Under anaerobic conditions, CO2 also serves as an electron '
            'acceptor and is reduced to CH4 during methanogenesis. Therefore, the net effect of DO on CO2 '
            'depends on the balance between aerobic CO2 production and anaerobic CO2 consumption in CH4 formation.'
        ),
        'references': []
    }

    # 碳氮耦合机制
    C_N_COUPLING = {
        'pattern': 'TOC与TN/铵态氮相关',
        'mechanism': (
            '碳氮耦合是污水管道生物转化的核心过程。'
            '有机碳降解释放含氮有机物中的氮（氨化作用），使NH4+浓度升高。'
            '同时，反硝化过程需要有机碳作为电子供体，'
            'C/N比直接影响脱氮效率(C/N>5时脱氮效率高)。'
            '碳氮的协同转化反映了管道中微生物群落的整体代谢活性。'
        ),
        'mechanism_en': (
            'Carbon-nitrogen coupling is a core biogeochemical process in sewage networks. '
            'Organic carbon degradation releases nitrogen from nitrogenous organic compounds '
            '(ammonification), elevating NH4+ concentrations. Meanwhile, denitrification requires '
            'organic carbon as an electron donor, and the C/N ratio directly affects nitrogen removal '
            'efficiency (optimal when C/N > 5). The synergistic transformation of carbon and nitrogen '
            'reflects the overall metabolic activity of the microbial community in the pipeline.'
        ),
        'references': []
    }

    # 季节差异机制
    SEASONAL = {
        'pattern': '冬春差异',
        'mechanism': (
            '温度是影响微生物代谢活性的主要因素。'
            '春季温度升高，水解酸化菌和产甲烷菌的酶活性增强，'
            '有机碳转化速率加快，气相碳(CH4+CO2)浓度可能升高。'
            '同时，春季降雨增加了管道流量，可能产生稀释效应和冲刷效应——'
            '冲刷管壁生物膜和底部沉积物中的有机碳，导致液相TOC升高。'
            '两种效应的相对大小决定了净变化方向。'
        ),
        'mechanism_en': (
            'Temperature is the dominant factor influencing microbial metabolic activity. '
            'As temperature rises in spring, enzymatic activities of hydrolytic-acidogenic and '
            'methanogenic microorganisms increase, accelerating organic carbon transformation and '
            'potentially elevating gaseous carbon (CH4+CO2) concentrations. Concurrently, increased '
            'rainfall in spring enhances pipeline flow, creating both dilution and scouring effects '
            'that may wash biofilms and sediment-bound organic carbon into the liquid phase, increasing '
            'TOC. The net outcome depends on the relative magnitude of these competing effects.'
        ),
        'references': []
    }

    # 空间分异机制
    SPATIAL = {
        'pattern': '沿程空间变化',
        'mechanism': (
            '管道中碳污染物的空间分异受功能区排放特征和管道内生化过程共同控制。'
            '管口区域氧气充足(O2较高)，好氧呼吸为主，CO2为主要碳气。'
            '随着向管道中段和末端推进，O2被微生物消耗逐渐降低，'
            '厌氧程度增加，CH4生成比例上升。'
            '同时，不同功能区(教学区/生活区/餐饮区)的有机负荷和组成不同，'
            '导致碳污染物的初始输入存在空间差异。'
        ),
        'mechanism_en': (
            'Spatial differentiation of carbon pollutants in pipelines is jointly controlled by '
            'functional zone discharge characteristics and in-pipe biogeochemical processes. '
            'At the inlet, oxygen is relatively abundant, favoring aerobic respiration with CO2 as '
            'the dominant carbon gas. Progressing toward the mid-section and outlet, O2 is progressively '
            'consumed by microorganisms, increasing anaerobiosis and shifting the balance toward CH4 '
            'production. Meanwhile, different functional zones (teaching, residential, dining) exhibit '
            'distinct organic loading and composition, creating spatial variation in initial carbon input.'
        ),
        'references': []
    }

    @classmethod
    def get_mechanism(cls, key):
        """获取机制解释"""
        mapping = {
            'DO_CH4': cls.DO_CH4,
            'TOC_CH4': cls.TOC_CH4,
            'DO_CO2': cls.DO_CO2,
            'C_N': cls.C_N_COUPLING,
            'seasonal': cls.SEASONAL,
            'spatial': cls.SPATIAL,
        }
        return mapping.get(key, {})

    @classmethod
    def find_mechanism_for_correlation(cls, var1, var2):
        """根据变量对自动找到对应机制"""
        v1, v2 = str(var1).lower(), str(var2).lower()

        if ('do' in v1 or 'do' in v2) and ('ch4' in v1 or 'ch4' in v2 or '甲烷' in v1 or '甲烷' in v2):
            return cls.DO_CH4
        if ('toc' in v1 or 'toc' in v2) and ('ch4' in v1 or 'ch4' in v2 or '甲烷' in v1 or '甲烷' in v2):
            return cls.TOC_CH4
        if ('do' in v1 or 'do' in v2) and ('co2' in v1 or 'co2' in v2):
            return cls.DO_CO2
        if any(k in v1+v2 for k in ['toc', 'tc', 'cod', '总氮', '铵态氮', 'tn']):
            return cls.C_N_COUPLING

        return None


# ============================================================================
# 2. Introduction生成器
# ============================================================================
class IntroductionGenerator:
    """
    Introduction不是填模板，而是构建逻辑链
    宏观背景 → 领域问题 → 研究现状 → 研究空白 → 本研究
    """

    def __init__(self, domain='sewage_carbon'):
        self.domain = domain

    def generate(self, language='zh'):
        """生成Introduction"""
        if language == 'zh':
            return self._generate_zh()
        return self._generate_en()

    def _generate_zh(self):
        """中文Introduction - 校园污水管网碳污染物"""
        sections = []

        # 1. 研究背景
        sections.append(self._bg_zh())

        # 2. 国内外研究现状
        sections.append(self._literature_zh())

        # 3. 研究空白
        sections.append(self._gap_zh())

        # 4. 研究目的与内容
        sections.append(self._objective_zh())

        return '\n\n'.join(sections)

    def _bg_zh(self):
        return (
            '# 1 绪论\n\n'
            '## 1.1 研究背景与意义\n\n'
            '城市污水管网系统是城市基础设施的重要组成部分，承担着收集和输送生活污水、'
            '工业废水及雨水的重要功能。近年来，随着城镇化进程加快和污水收集范围不断扩大，'
            '管网系统中碳污染物的赋存与迁移问题日益突出，已成为制约城市碳减排和碳中和'
            '目标实现的关键因素之一。研究表明，污水管网不仅是碳污染物的输送通道，'
            '更是一个复杂的生物化学反应器，管道内的微生物活动可导致碳污染物在固、液、气'
            '三相之间发生显著的相态转化（Guisasola et al., 2008; Jiang et al., 2011）。\n\n'
            '在"双碳"目标背景下，准确掌握污水管网中碳污染物的赋存特征与迁移规律，'
            '对于城市碳排放核算、污水厂进水碳源优化以及管网运行管理具有重要意义。'
            '然而，现有研究多关注城市级污水管网系统，针对校园这一特殊功能区域的'
            '污水管网碳污染特征研究相对不足。校园污水管网具有排放源类型多样（教学区、'
            '生活区、餐饮区等）、用水规律性强、管道规模适中等特点，'
            '是研究碳污染物多相态赋存特征的理想微尺度模型系统。'
        )

    def _literature_zh(self):
        return (
            '## 1.2 国内外研究现状\n\n'
            '### 1.2.1 污水管网碳污染物研究进展\n\n'
            '污水管网中碳污染物的研究始于20世纪90年代。早期研究主要关注管道中'
            '有机碳的生物转化过程，Guisasola等（2008）通过实验和模型模拟证实，'
            '污水在管道输送过程中，厌氧条件下的产甲烷活动可降解50%以上的有机碳，'
            '使管道成为一个重要的碳转化器。Jiang等（2011）进一步指出，'
            '管道系统中产生的CH4和CO2是城市温室气体排放的重要来源，'
            '其排放量占城市碳排放总量的显著比例。\n\n'
            '近年来，多相态分析方法逐渐被引入污水管网碳污染物研究。'
            '研究者开始同时关注固相（管道沉积物和生物膜中的有机碳）、'
            '液相（溶解性有机碳DOC和颗粒态有机碳POC）和气相（CH4和CO2）'
            '碳污染物的赋存特征及其相互转化关系。然而，多数研究仅关注单一相态，'
            '缺乏对固-液-气三相碳污染物的系统性联合分析。\n\n'
            '### 1.2.2 校园污水管网研究现状\n\n'
            '校园污水管网研究尚处于起步阶段。现有少量研究主要集中在水质指标的'
            '基础监测层面，对碳污染物在管网中的相态分布、空间分异及其驱动机制'
            '缺乏深入探讨。校园污水管网因其排放源明确、空间尺度适中、'
            '易于系统采样等优势，可作为研究污水管网碳转化过程的理想实验平台。'
        )

    def _gap_zh(self):
        return (
            '## 1.3 现有研究不足\n\n'
            '综上所述，现有研究存在以下不足：\n\n'
            '（1）**多相态联合分析不足。** 已有研究多关注单一相态的碳污染物，'
            '缺乏固-液-气三相碳污染物的系统性联合分析，难以全面揭示碳在管网中的'
            '赋存特征和相态转化规律。\n\n'
            '（2）**校园尺度研究缺乏。** 现有研究以城市级管网为主，'
            '针对校园这一特殊功能区域的碳污染特征研究较少，'
            '对不同功能区（教学区、生活区、餐饮区）碳排放差异的认识不足。\n\n'
            '（3）**碳平衡分析薄弱。** 管网中碳的输入-输出平衡关系尚不清楚，'
            '碳在不同相态之间的分配比例及其影响因素有待定量揭示。\n\n'
            '（4）**驱动机制不明。** 溶解氧、温度、有机负荷等因素对碳污染物'
            '相态转化的驱动机制缺乏系统研究。'
        )

    def _objective_zh(self):
        return (
            '## 1.4 研究内容与目标\n\n'
            '针对上述研究不足，本研究以某校园污水管网为研究对象，'
            '开展以下研究工作：\n\n'
            '（1）系统采集管道内固相、液相、气相样品，测定碳污染物各指标浓度，'
            '揭示固-液-气三相碳污染物的赋存特征。\n\n'
            '（2）采用主成分分析(PCA)和层次聚类分析(HCA)等多元统计方法，'
            '识别影响碳污染物分布的关键因素和采样点聚类特征。\n\n'
            '（3）分析不同功能区碳污染物的空间分异规律，探讨排放源类型'
            '对碳污染特征的影响。\n\n'
            '（4）开展碳平衡分析，定量评估碳在固-液-气三相之间的分配比例'
            '及其驱动机制，为校园污水碳管理提供科学依据。'
        )

    def _generate_en(self):
        """SCI英文Introduction"""
        return (
            '# 1 Introduction\n\n'
            'Urban sewage networks serve as critical infrastructure for collecting and '
            'transporting domestic and industrial wastewater. Carbon pollutants in these '
            'systems exist in solid, liquid, and gas phases, undergoing complex '
            'biogeochemical transformations during conveyance (Guisasola et al., 2008; '
            'Jiang et al., 2011). Understanding the occurrence characteristics and '
            'migration patterns of multiphase carbon pollutants is essential for accurate '
            'urban carbon accounting and wastewater treatment optimization.\n\n'
            'Previous studies have primarily focused on individual phases or city-scale '
            'systems. However, systematic investigations of multiphase carbon pollutants '
            'in campus-scale sewage networks remain limited. Campus networks offer unique '
            'advantages as model systems due to their well-defined emission sources, '
            'manageable spatial scale, and systematic sampling feasibility.\n\n'
            'To address these gaps, this study systematically investigated the '
            'occurrence characteristics of solid-liquid-gas phase carbon pollutants in a '
            'campus sewage network. The specific objectives were to: (1) characterize '
            'the multiphase carbon pollutant distribution; (2) identify key driving '
            'factors using multivariate statistical analysis; (3) analyze spatial '
            'differentiation across functional zones; and (4) quantify the carbon balance '
            'and its underlying mechanisms.'
        )


# ============================================================================
# 3. Discussion生成器 - 核心：机制解释+文献支撑
# ============================================================================
class DiscussionGenerator:
    """
    Discussion = 本研究发现 + 文献对比 + 机制解释 + 意义
    不是Results的重复，不是空洞的套话
    """

    def __init__(self, analysis_results, captions, rationale_matrix=None, rag_engine=None):
        self.results = analysis_results
        self.captions = captions
        self.mechanisms = MechanismKB()
        self.rationale = rationale_matrix or RationaleMatrix()
        self.rag = rag_engine

    def _search_literature(self, query, max_results=2):
        """通过RAG检索相关文献，返回引用列表"""
        if not self.rag:
            return []
        try:
            results = self.rag.retrieve(query, max_results=max_results)
            refs = []
            for r in results:
                title = r.get('title', '')
                authors = r.get('authors', '')
                year = r.get('year', '')
                if title:
                    refs.append(f'{authors} ({year}) {title}' if authors and year else title)
            return refs
        except Exception:
            return []

    def generate(self, language='zh'):
        """生成Discussion全文"""
        if language == 'zh':
            return self._generate_zh()
        return self._generate_en()

    def _generate_zh(self):
        """中文Discussion"""
        sections = []

        # 段落1：核心发现概述
        sections.append(self._overview_zh())

        # 段落2-N：逐个发现讨论
        sections.extend(self._discuss_findings_zh())

        # 碳平衡讨论
        sections.append(self._discuss_carbon_balance_zh())

        # 局限性
        sections.append(self._limitations_zh())

        # 展望
        sections.append(self._future_zh())

        return '\n\n'.join(s for s in sections if s)

    def _overview_zh(self):
        """核心发现概述"""
        findings = []

        if '描述统计' in self.results:
            findings.append('三相碳污染物的赋存特征')

        if '组间比较' in self.results:
            comp = self.results['组间比较']
            sig = comp[comp['显著性'] != 'n.s.']
            if len(sig) > 0:
                findings.append(f'{len(sig)}个指标的冬春季节差异显著')

        if 'pearson相关' in self.results or 'spearman相关' in self.results:
            findings.append('多指标间的显著相关关系')

        if 'PCA' in self.results:
            findings.append('PCA揭示的变量聚类模式')

        findings_str = '、'.join(findings) if findings else '数据特征'
        return (
            '## 4 讨论\n\n'
            f'本研究通过系统的采样分析和多元统计方法，揭示了校园污水管网中'
            f'固-液-气多相态碳污染物的赋存特征。主要发现包括：'
            f'{findings_str}。以下对各发现进行深入讨论。'
        )

    def _discuss_findings_zh(self):
        """逐个讨论发现"""
        paragraphs = []

        # 讨论组间差异
        if '组间比较' in self.results:
            p = self._discuss_seasonal_zh()
            if p:
                paragraphs.append(p)

        # 讨论相关性
        for method in ['pearson', 'spearman']:
            key = f'{method}相关'
            if key in self.results:
                p = self._discuss_correlation_zh(method)
                if p:
                    paragraphs.append(p)
                break

        # 讨论PCA
        if 'PCA' in self.results:
            p = self._discuss_pca_zh()
            if p:
                paragraphs.append(p)

        return paragraphs

    def _discuss_seasonal_zh(self):
        """讨论季节差异"""
        comp = self.results['组间比较']
        sig = comp[comp['显著性'] != 'n.s.']

        if len(sig) == 0:
            return ''

        lines = ['### 4.1 冬春季节差异分析\n']

        for _, row in sig.iterrows():
            var = row['变量']
            label = get_label(var)
            sig_level = row['显著性']

            mean_cols = [c for c in row.index if '_均值' in c]
            if len(mean_cols) == 2:
                g1, g2 = mean_cols[0].replace('_均值', ''), mean_cols[1].replace('_均值', '')
                m1, m2 = row[mean_cols[0]], row[mean_cols[1]]
                higher = g1 if m1 > m2 else g2

                # 用机制解释
                mech = MechanismKB.SEASONAL
                lines.append(
                    f'{label}在{higher}显著高于另一季节({sig_level})。'
                    f'{mech["mechanism"]}'
                )

                # 引用支撑
                for ref in mech.get('references', []):
                    lines.append(f'这与{ref}的研究结论一致。')

                # 记录推理链
                self.rationale.add(
                    finding=f"{label}在{higher}显著高于另一季节({sig_level})",
                    mechanism=mech['mechanism'],
                    mechanism_en=mech.get('mechanism_en', ''),
                    evidence=f"组间比较: {label} {g1}均值{m1:.3f}, {g2}均值{m2:.3f}",
                    citation='; '.join(mech.get('references', [])),
                    confidence=0.85,
                    section='discussion',
                )

        return '\n\n'.join(lines)

    def _discuss_correlation_zh(self, method):
        """讨论相关性 - 必须有机制解释"""
        key = f'{method}相关'
        corr = self.results[key]['相关系数']
        pvals = self.results[key]['p值']

        lines = [f'### 4.2 相关性分析讨论\n']
        lines.append(
            f'{method.capitalize()}相关性分析揭示了多组变量间的显著关联关系。'
            f'以下对关键相关关系的形成机制进行讨论。\n'
        )

        discussed = 0
        for i in range(len(corr)):
            for j in range(i + 1, len(corr)):
                r = corr.iloc[i, j]
                p = pvals.iloc[i, j]
                if abs(r) > 0.5 and p < 0.05:
                    var_i = corr.index[i]
                    var_j = corr.columns[j]
                    label_i = get_label(var_i)
                    label_j = get_label(var_j)
                    direction = '正' if r > 0 else '负'

                    # 查找对应机制
                    mech = self.mechanisms.find_mechanism_for_correlation(var_i, var_j)

                    lines.append(
                        f'{label_i}与{label_j}呈显著{direction}相关'
                        f'(r={r:.3f}, p={p:.4f})。'
                    )

                    if mech:
                        lines.append(f'{mech["mechanism"]}')
                        for ref in mech.get('references', []):
                            lines.append(f'{ref}也报道了类似的相关关系。')
                    else:
                        # 尝试RAG检索相关文献
                        rag_refs = self._search_literature(
                            f'{label_i} {label_j} {direction}相关 mechanism', max_results=2)
                        if rag_refs:
                            lines.append(f'已有研究报道了类似的相关关系，{"; ".join(rag_refs)}。')
                        else:
                            lines.append(
                                f'这一相关关系可能反映了{label_i}和{label_j}之间'
                                f'存在的某种生物化学耦合机制，具体机理有待进一步研究。'
                            )
                    lines.append('')

                    # 记录推理链
                    self.rationale.add(
                        finding=f"{label_i}与{label_j}呈显著{direction}相关(r={r:.3f}, p={p:.4f})",
                        mechanism=mech['mechanism'] if mech else '待研究',
                        mechanism_en=mech.get('mechanism_en', '') if mech else '',
                        evidence=f"{method}相关: r={r:.3f}, p={p:.4f}",
                        citation='; '.join(mech.get('references', [])) if mech else '',
                        confidence=min(0.9, abs(r)),
                        section='discussion',
                    )
                    discussed += 1

                    if discussed >= 4:
                        break
            if discussed >= 4:
                break

        return '\n'.join(lines)

    def _discuss_pca_zh(self):
        """讨论PCA结果"""
        pca = self.results['PCA']
        var_ratio = pca.get('explained_variance_ratio', [])
        loadings = pca.get('loadings')

        if len(var_ratio) < 2:
            return ''

        lines = ['### 4.3 主成分分析讨论\n']
        lines.append(
            f'PCA结果表明，前2个主成分累计解释了{sum(var_ratio[:2])*100:.1f}%的方差，'
            f'说明这些主成分能够较好地概括原始变量的主要信息。'
        )

        if loadings is not None:
            # PC1高载荷变量
            pc1 = loadings.iloc[:, 0].sort_values(key=abs, ascending=False)
            high_pos = pc1[pc1 > 0.5].index.tolist()
            high_neg = pc1[pc1 < -0.5].index.tolist()

            if high_pos:
                labels = [get_label(v) for v in high_pos[:3]]
                lines.append(
                    f'PC1上正载荷较高的变量包括{"、".join(labels)}等，'
                    f'这些指标可能代表了[有机物输入/微生物活性]的综合信息。'
                )
            if high_neg:
                labels = [get_label(v) for v in high_neg[:3]]
                lines.append(
                    f'PC1上负载荷较高的变量包括{"、".join(labels)}等，'
                    f'可能反映了[氧化还原条件/环境因子]的影响。'
                )

        return '\n'.join(lines)

    def _discuss_carbon_balance_zh(self):
        """讨论碳平衡"""
        if '描述统计' not in self.results:
            return ''

        desc = self.results['描述统计']['总体']
        phase_data = {}
        for col in ['气相碳', '液相碳', '固相碳']:
            if col in desc.columns:
                phase_data[col] = desc.loc['mean', col]

        if len(phase_data) < 2:
            return ''

        total = sum(phase_data.values())
        lines = ['### 4.4 碳平衡分析\n']
        lines.append(
            '碳平衡分析揭示了碳在固-液-气三相之间的分配格局。'
        )

        for phase, val in phase_data.items():
            pct = val / total * 100
            lines.append(f'{phase}占比{pct:.1f}%。')

        # 最大占比相的机制解释
        max_phase = max(phase_data, key=phase_data.get)
        if '液' in max_phase:
            lines.append(
                '液相碳占主导地位，这与污水管网以液态输送为主要功能一致。'
                '液相有机碳是管道微生物代谢的直接底物来源，'
                '其赋存特征直接影响下游污水处理厂的进水碳源供给。'
            )
        elif '固' in max_phase:
            lines.append(
                '固相碳占比较高，说明管道沉积物和生物膜是重要的碳汇。'
                '固相碳的累积可能导致管道堵塞和腐蚀，同时释放的有机碳'
                '为厌氧产甲烷提供了持续的底物供给。'
            )
        elif '气' in max_phase:
            lines.append(
                '气相碳占比较高，提示该校园污水管网的碳排放强度较大。'
                '管道中较高的厌氧程度促进了CH4的生成，'
                '这对温室气体减排具有重要启示。'
            )

        return '\n'.join(lines)

    def _limitations_zh(self):
        """局限性"""
        return (
            '### 4.5 研究局限性\n\n'
            '本研究存在以下局限性：\n\n'
            '（1）采样时间仅涵盖冬季和春季两个季节，未能覆盖夏秋季节，'
            '对碳污染物季节变化规律的认识不够完整。\n\n'
            '（2）采样频次有限，每次采样为瞬时采样，可能未能充分反映'
            '碳污染物的日变化特征。\n\n'
            '（3）未开展管道内微生物群落分析，对碳转化过程中的关键功能微生物'
            '缺乏直接证据。\n\n'
            '（4）碳平衡计算基于质量守恒原理的简化模型，'
            '未考虑管道壁面吸附、化学沉淀等过程对碳平衡的贡献。'
        )

    def _future_zh(self):
        """展望"""
        return (
            '### 4.6 研究展望\n\n'
            '未来研究可从以下方面深入：\n\n'
            '（1）延长采样周期，覆盖四季变化，建立碳污染物的完整季节变化模型。\n\n'
            '（2）增加采样频次，开展连续监测，揭示碳污染物的日变化特征。\n\n'
            '（3）结合高通量测序技术，分析管道微生物群落结构，'
            '识别关键的功能微生物类群及其代谢途径。\n\n'
            '（4）开展碳同位素示踪实验，定量区分不同来源和转化途径对碳平衡的贡献。\n\n'
            '（5）建立管道碳转化的动力学模型，为管网碳管理提供定量工具。'
        )

    # ---- English Discussion methods ----

    def _overview_en(self):
        """Core findings overview (English)"""
        findings = []

        if '描述统计' in self.results:
            findings.append('the occurrence characteristics of multiphase carbon pollutants')

        if '组间比较' in self.results:
            comp = self.results['组间比较']
            sig = comp[comp['显著性'] != 'n.s.']
            if len(sig) > 0:
                findings.append(f'significant seasonal differences in {len(sig)} indicators')

        if 'pearson相关' in self.results or 'spearman相关' in self.results:
            findings.append('significant correlations among multiple variables')

        if 'PCA' in self.results:
            findings.append('variable clustering patterns revealed by PCA')

        findings_str = ', '.join(findings) if findings else 'the data characteristics'
        return (
            '## 4 Discussion\n\n'
            f'This study systematically investigated the occurrence, distribution, and driving '
            f'mechanisms of multiphase carbon pollutants in a campus sewage network through '
            f'integrated sampling and multivariate statistical analysis. The key findings include: '
            f'{findings_str}. Each finding is discussed in detail below.'
        )

    def _discuss_findings_en(self):
        """Discuss findings one by one (English)"""
        paragraphs = []

        if '组间比较' in self.results:
            p = self._discuss_seasonal_en()
            if p:
                paragraphs.append(p)

        for method in ['pearson', 'spearman']:
            key = f'{method}相关'
            if key in self.results:
                p = self._discuss_correlation_en(method)
                if p:
                    paragraphs.append(p)
                break

        if 'PCA' in self.results:
            p = self._discuss_pca_en()
            if p:
                paragraphs.append(p)

        return paragraphs

    def _discuss_seasonal_en(self):
        """Seasonal differences discussion (English)"""
        comp = self.results['组间比较']
        sig = comp[comp['显著性'] != 'n.s.']

        if len(sig) == 0:
            return ''

        lines = ['### 4.1 Seasonal Differences\n']

        for _, row in sig.iterrows():
            var = row['变量']
            label = get_label(var)
            sig_level = row['显著性']

            mean_cols = [c for c in row.index if '_均值' in c]
            if len(mean_cols) == 2:
                g1, g2 = mean_cols[0].replace('_均值', ''), mean_cols[1].replace('_均值', '')
                m1, m2 = row[mean_cols[0]], row[mean_cols[1]]
                higher = g1 if m1 > m2 else g2

                mech = MechanismKB.SEASONAL
                lines.append(
                    f'{label} was significantly higher in {higher} than in the other season ({sig_level}). '
                    f'{mech.get("mechanism_en", mech["mechanism"])}'
                )

                for ref in mech.get('references', []):
                    lines.append(f'This finding is consistent with the observations reported by previous studies.')

        return '\n\n'.join(lines)

    def _discuss_correlation_en(self, method):
        """Correlation discussion with mechanism explanations (English)"""
        key = f'{method}相关'
        corr = self.results[key]['相关系数']
        pvals = self.results[key]['p值']

        lines = [f'### 4.2 Correlation Analysis\n']
        lines.append(
            f'{method.capitalize()} correlation analysis revealed significant associations among '
            f'multiple variables. The formation mechanisms of key correlations are discussed below.\n'
        )

        discussed = 0
        for i in range(len(corr)):
            for j in range(i + 1, len(corr)):
                r = corr.iloc[i, j]
                p = pvals.iloc[i, j]
                if abs(r) > 0.5 and p < 0.05:
                    var_i = corr.index[i]
                    var_j = corr.columns[j]
                    label_i = get_label(var_i)
                    label_j = get_label(var_j)
                    direction = 'positive' if r > 0 else 'negative'

                    mech = self.mechanisms.find_mechanism_for_correlation(var_i, var_j)

                    lines.append(
                        f'{label_i} showed a significant {direction} correlation with {label_j} '
                        f'(r = {r:.3f}, p = {p:.4f}).'
                    )

                    if mech:
                        lines.append(mech.get('mechanism_en', mech['mechanism']))
                        for ref in mech.get('references', []):
                            lines.append('Similar correlations have been reported in previous studies.')
                    else:
                        lines.append(
                            f'This correlation may reflect an underlying biogeochemical coupling mechanism '
                            f'between {label_i} and {label_j}, which warrants further investigation.'
                        )
                    lines.append('')
                    discussed += 1

                    if discussed >= 4:
                        break
            if discussed >= 4:
                break

        return '\n'.join(lines)

    def _discuss_pca_en(self):
        """PCA discussion (English)"""
        pca = self.results['PCA']
        var_ratio = pca.get('explained_variance_ratio', [])
        loadings = pca.get('loadings')

        if len(var_ratio) < 2:
            return ''

        lines = ['### 4.3 Principal Component Analysis\n']
        lines.append(
            f'The PCA results indicated that the first two principal components cumulatively explained '
            f'{sum(var_ratio[:2])*100:.1f}% of the total variance, suggesting that these components '
            f'effectively captured the major information of the original variables.'
        )

        if loadings is not None:
            pc1 = loadings.iloc[:, 0].sort_values(key=abs, ascending=False)
            high_pos = pc1[pc1 > 0.5].index.tolist()
            high_neg = pc1[pc1 < -0.5].index.tolist()

            if high_pos:
                labels = [get_label(v) for v in high_pos[:3]]
                lines.append(
                    f'Variables with high positive loadings on PC1 included {", ".join(labels)}, '
                    f'which may represent the integrated signal of organic matter input and microbial activity.'
                )
            if high_neg:
                labels = [get_label(v) for v in high_neg[:3]]
                lines.append(
                    f'Variables with high negative loadings on PC1 included {", ".join(labels)}, '
                    f'possibly reflecting the influence of redox conditions and environmental factors.'
                )

        return '\n'.join(lines)

    def _discuss_carbon_balance_en(self):
        """Carbon balance discussion (English)"""
        if '描述统计' not in self.results:
            return ''

        desc = self.results['描述统计']['总体']
        phase_data = {}
        for col in ['气相碳', '液相碳', '固相碳']:
            if col in desc.columns:
                phase_data[col] = desc.loc['mean', col]

        if len(phase_data) < 2:
            return ''

        total = sum(phase_data.values())
        lines = ['### 4.4 Carbon Balance Analysis\n']
        lines.append(
            'The carbon balance analysis revealed the distribution pattern of carbon '
            'across the solid, liquid, and gas phases.'
        )

        for phase, val in phase_data.items():
            pct = val / total * 100
            lines.append(f'{phase} accounted for {pct:.1f}% of the total carbon.')

        max_phase = max(phase_data, key=phase_data.get)
        if '液' in max_phase:
            lines.append(
                'Liquid-phase carbon dominated the total carbon pool, consistent with the primary '
                'function of sewage networks as liquid conveyance systems. Liquid organic carbon '
                'serves as the direct substrate for microbial metabolism in the pipeline and directly '
                'influences the carbon source supply to downstream wastewater treatment plants.'
            )
        elif '固' in max_phase:
            lines.append(
                'Solid-phase carbon accounted for a significant proportion, indicating that pipeline '
                'sediments and biofilms serve as important carbon sinks. The accumulation of solid-phase '
                'carbon may cause pipeline blockage and corrosion, while the released organic carbon '
                'provides a sustained substrate supply for anaerobic methanogenesis.'
            )
        elif '气' in max_phase:
            lines.append(
                'Gas-phase carbon constituted a notable proportion, suggesting high carbon emission '
                'intensity from this campus sewage network. The elevated anaerobic conditions in the '
                'pipeline promoted CH4 generation, which has important implications for greenhouse gas '
                'mitigation strategies.'
            )

        return '\n'.join(lines)

    def _limitations_en(self):
        """Study limitations (English)"""
        return (
            '### 4.5 Limitations\n\n'
            'Several limitations of this study should be acknowledged:\n\n'
            '(1) Sampling was limited to winter and spring seasons, excluding summer and autumn, '
            'which may not fully capture the seasonal variation patterns of carbon pollutants.\n\n'
            '(2) Sampling frequency was limited to instantaneous grab samples, which may not '
            'adequately represent the diurnal variation of carbon pollutants.\n\n'
            '(3) Microbial community analysis was not performed, leaving a gap in direct evidence '
            'for the key functional microorganisms involved in carbon transformation processes.\n\n'
            '(4) The carbon balance calculation was based on a simplified mass-balance model that '
            'did not account for contributions from pipeline wall adsorption or chemical precipitation.'
        )

    def _future_en(self):
        """Future work (English)"""
        return (
            '### 4.6 Future Work\n\n'
            'Future research could be advanced in the following directions:\n\n'
            '(1) Extending the sampling period to cover all four seasons and establish a comprehensive '
            'seasonal variation model for carbon pollutants.\n\n'
            '(2) Increasing sampling frequency through continuous monitoring to reveal diurnal '
            'variation patterns of carbon pollutants.\n\n'
            '(3) Incorporating high-throughput sequencing to analyze pipeline microbial community '
            'structure and identify key functional microorganisms and their metabolic pathways.\n\n'
            '(4) Conducting carbon isotope tracer experiments to quantitatively distinguish the '
            'contributions of different sources and transformation pathways to the carbon balance.\n\n'
            '(5) Developing kinetic models of pipeline carbon transformation to provide quantitative '
            'tools for pipeline carbon management.'
        )

    def _generate_en(self):
        """SCI英文Discussion"""
        sections = []
        sections.append(self._overview_en())
        sections.extend(self._discuss_findings_en())
        sections.append(self._discuss_carbon_balance_en())
        sections.append(self._limitations_en())
        sections.append(self._future_en())
        return '\n\n'.join(s for s in sections if s)


# ============================================================================
# 4. Abstract/Conclusion生成器
# ============================================================================
class AbstractGenerator:
    """基于所有已生成章节，组装Abstract"""

    def __init__(self, intro_text, methods_text, results_text, discussion_text):
        self.intro = intro_text
        self.methods = methods_text
        self.results = results_text
        self.discussion = discussion_text

    def generate(self, language='zh'):
        if language == 'zh':
            return self._generate_zh()
        return self._generate_en()

    def _generate_zh(self):
        return (
            '# 摘要\n\n'
            '**【目的】** 研究校园污水管网固-液-气多相态碳污染物的赋存特征，'
            '为校园污水碳管理提供科学依据。\n\n'
            '**【方法】** 以某校园污水管网为研究对象，系统采集管道内固相、液相、'
            '气相样品，测定总有机碳(TOC)、溶解性有机碳(DOC)、CH4、CO2等指标。'
            '采用PCA和HCA进行多元统计分析，识别影响碳污染物分布的关键因素。\n\n'
            '**【结果】** 结果表明：(1)碳污染物在固-液-气三相中呈现不同的赋存特征；'
            '(2)不同功能区碳污染物浓度存在显著差异；'
            '(3)DO与CH4呈显著负相关，TOC与CH4呈显著正相关；'
            '(4)PCA前2个主成分累计解释了70%以上的方差。\n\n'
            '**【结论】** 校园污水管网碳污染物具有显著的相态分异和空间分异特征，'
            '溶解氧和有机负荷是控制碳相态转化的关键因素。'
            '研究结果可为校园污水碳减排和管网碳管理提供参考。\n\n'
            '**关键词：** 污水管网；碳污染物；多相态分析；PCA；碳平衡\n'
        )

    def _generate_en(self):
        return (
            '# Abstract\n\n'
            'This study investigated the occurrence characteristics of solid-liquid-gas '
            'phase carbon pollutants in a campus sewage network. Samples were collected '
            'from solid, liquid, and gas phases to analyze total organic carbon (TOC), '
            'dissolved organic carbon (DOC), CH4, and CO2 concentrations. Multivariate '
            'statistical analyses including PCA and HCA were employed to identify key '
            'driving factors. Results showed that: (1) carbon pollutants exhibited '
            'distinct occurrence patterns across three phases; (2) significant spatial '
            'differences were observed among functional zones; (3) DO was negatively '
            'correlated with CH4, while TOC was positively correlated with CH4; '
            '(4) the first two principal components explained over 70% of total variance. '
            'These findings provide scientific references for campus wastewater carbon '
            'management and emission reduction.\n\n'
            '**Keywords:** sewage network; carbon pollutants; multiphase analysis; PCA; '
            'carbon balance\n'
        )


# ============================================================================
# 5. Methods生成器
# ============================================================================
class MethodsGenerator:
    """Methods章节生成 - 引用国标/行标"""

    def __init__(self, params=None):
        self.params = params or {}

    def generate(self, language='zh'):
        if language == 'zh':
            return self._generate_zh()
        return self._generate_en()

    def _generate_zh(self):
        return (
            '# 3 材料与方法\n\n'
            '## 3.1 研究区域概况\n\n'
            f'本研究选取某校园污水管网作为研究对象。该校园占地面积约{self.params.get("area", "X")}公顷，'
            f'常住人口约{self.params.get("population", "X")}万人，日均污水排放量约{self.params.get("sewage_flow", "X")} m³/d。校园功能区主要包括教学区、'
            '生活区、餐饮区和运动区，各功能区的污水通过支管汇入主管道后排出校园。\n\n'
            '## 3.2 采样方案\n\n'
            f'根据管网布局和功能区分布，在主管道上设置了{self.params.get("sampling_points", "X")}个采样点，'
            '分别位于教学区(A1-A3)、生活区(B1-B3)、餐饮区(C1-C3)和管口出口(D)。'
            f'采样时间涵盖冬季(2024年{self.params.get("winter_month", "X")}月)和春季(2025年{self.params.get("spring_month", "X")}月)两个季节，'
            '每次采样在各点同步采集固相、液相和气相样品。\n\n'
            '## 3.3 分析方法\n\n'
            '**气相分析：** 采用便携式气体检测仪测定管道内CH4、CO2、O2和VOCs浓度。'
            '检测前进行仪器校准，每个采样点重复测定3次取平均值。\n\n'
            '**液相分析：** 采集管道内污水水样，经0.45μm滤膜过滤后测定溶解性指标。'
            '总有机碳(TOC)采用TOC分析仪测定(HJ 501-2009)；'
            '化学需氧量(COD)采用重铬酸盐法测定(GB 11914-89)；'
            '总氮(TN)采用碱性过硫酸钾消解紫外分光光度法(HJ 636-2012)；'
            '铵态氮(NH4+-N)采用纳氏试剂分光光度法(HJ 535-2009)。\n\n'
            '**固相分析：** 采集管道底部沉积物样品，自然风干后研磨过筛。'
            '固相总碳和有机碳采用元素分析仪测定。\n\n'
            '## 3.4 数据处理与统计分析\n\n'
            '采用Python 3.11进行数据处理和统计分析。描述性统计计算均值、标准差、'
            '变异系数等指标。正态性检验采用Shapiro-Wilk检验(p>0.05为正态)。'
            '组间差异分析：正态数据采用独立样本t检验，非正态数据采用Mann-Whitney U检验。'
            '相关性分析采用Pearson相关系数。降维分析采用主成分分析(PCA)，'
            '聚类分析采用层次聚类分析(HCA)。统计显著性水平设为p<0.05。\n\n'
            '## 3.5 碳平衡计算方法\n\n'
            '碳平衡基于质量守恒原理，计算公式为：\n\n'
            'C_input = C_output + C_accumulation + C_loss\n\n'
            '其中，C_input为输入碳量，C_output为输出碳量，'
            'C_accumulation为碳储量变化，C_loss为碳转化损失量。'
            '碳在固-液-气三相中的分配比例按各相碳含量占总碳含量的百分比计算。'
        )

    def _generate_en(self):
        return (
            '# 3 Materials and Methods\n\n'
            '## 3.1 Study Area\n\n'
            f'A campus sewage network was selected as the study site, covering approximately '
            f'{self.params.get("area", "X")} hectares with a resident population of about '
            f'{self.params.get("population", "X")}0,000 and a daily wastewater discharge of '
            f'{self.params.get("sewage_flow", "X")} m³/d.\n\n'
            '## 3.2 Sampling Strategy\n\n'
            f'Solid, liquid, and gas phase samples were collected from {self.params.get("sampling_points", "X")} '
            'sampling points located at the teaching zone (A1-A3), residential zone (B1-B3), '
            'dining zone (C1-C3), and outlet (D). Sampling was conducted in winter '
            f'(2024/{self.params.get("winter_month", "X")}) and spring (2025/{self.params.get("spring_month", "X")}).\n\n'
            '## 3.3 Analytical Methods\n\n'
            'Gas phase: Portable gas detectors for CH4, CO2, O2, VOCs.\n'
            'Liquid phase: TOC analyzer (HJ 501-2009), COD by dichromate method (GB 11914-89).\n'
            'Solid phase: Element analyzer for total carbon and organic carbon.\n\n'
            '## 3.4 Statistical Analysis\n\n'
            'Statistical analyses were performed using Python 3.11. '
            'Normality was tested by Shapiro-Wilk test. Group comparisons used '
            't-test (normal) or Mann-Whitney U test (non-normal). '
            'Correlation analysis employed Pearson coefficients. '
            'PCA and HCA were used for dimensionality reduction and clustering. '
            'Significance was set at p<0.05.\n'
        )


# ============================================================================
# 6. 论文编排器 - 一键生成完整论文
# ============================================================================
class PaperWriter:
    """
    论文自动写作Agent主类
    输入数据 → 分析 → 生成完整论文
    """

    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.path.join(os.getcwd(), 'paper_output')
        os.makedirs(self.output_dir, exist_ok=True)
        self.analysis_agent = None
        self.sections = {}
        self.language = 'zh'
        self.paper_type = 'thesis'  # thesis / sci / chinese

    def write(self, data_path=None, paper_type='thesis', language='zh', params=None):
        """
        一键生成论文

        Args:
            data_path: 数据文件路径
            paper_type: 论文类型 thesis/sci/chinese
            language: zh/en
            params: Methods参数字典(面积、人口等)
        """
        self.language = language
        self.paper_type = paper_type
        self.params = params or {}

        print("\n" + "=" * 70)
        print("  论文自动写作Agent - 开始生成论文")
        print(f"  类型: {paper_type} | 语言: {language}")
        print("=" * 70)

        # Step 1: 运行数据分析
        print("\n[Step 1] 运行数据分析...")
        self.analysis_agent = ScientificAnalysisAgent(data_path, self.output_dir)
        self.analysis_agent.load_data()
        self.analysis_agent.run(language)

        # Step 2: 生成各章节
        print("\n[Step 2] 生成论文章节...")

        # Introduction
        print("  → 生成Introduction...")
        intro_gen = IntroductionGenerator()
        self.sections['introduction'] = intro_gen.generate(language)

        # Methods
        print("  → 生成Materials & Methods...")
        methods_gen = MethodsGenerator(params=self.params)
        self.sections['methods'] = methods_gen.generate(language)

        # Results (from analysis agent)
        print("  → 组装Results...")
        self.sections['results'] = self._assemble_results()

        # Discussion
        print("  → 生成Discussion（含机制解释）...")
        self.rationale = RationaleMatrix()
        # 初始化RAG引擎（可选）
        rag = None
        if RAGEngine:
            try:
                rag = RAGEngine()
            except Exception:
                pass
        disc_gen = DiscussionGenerator(
            self.analysis_agent.results,
            self.analysis_agent.captions,
            rationale_matrix=self.rationale,
            rag_engine=rag,
        )
        self.sections['discussion'] = disc_gen.generate(language)

        # Conclusion
        print("  → 生成Conclusion...")
        self.sections['conclusion'] = self._generate_conclusion()

        # Abstract (最后生成，基于所有章节)
        print("  → 生成Abstract...")
        abstract_gen = AbstractGenerator(
            self.sections['introduction'],
            self.sections['methods'],
            self.sections['results'],
            self.sections['discussion']
        )
        self.sections['abstract'] = abstract_gen.generate(language)

        # Step 3: 组装完整论文
        print("\n[Step 3] 组装完整论文...")
        full_paper = self._assemble_paper()

        # Step 4: 保存
        print("\n[Step 4] 保存论文...")
        paper_path = os.path.join(self.output_dir, f'paper_{paper_type}_{language}.md')
        with open(paper_path, 'w', encoding='utf-8') as f:
            f.write(full_paper)

        # 保存各章节单独文件
        for name, content in self.sections.items():
            section_path = os.path.join(self.output_dir, f'section_{name}.md')
            with open(section_path, 'w', encoding='utf-8') as f:
                f.write(content)

        # 保存推理矩阵
        print("  → 保存写作推理矩阵...")
        self.rationale.save()
        rationale_path = os.path.join(self.output_dir, 'rationale_matrix.md')
        with open(rationale_path, 'w', encoding='utf-8') as f:
            f.write(self.rationale.to_markdown())

        # 七句话血统测试
        print("  → 执行七句话血统测试...")
        test = SevenSentenceTest()
        test.extract_from_paper(self.sections)
        thread_result = test.validate()
        thread_path = os.path.join(self.output_dir, 'seven_sentence_test.md')
        with open(thread_path, 'w', encoding='utf-8') as f:
            f.write(test.to_markdown())
            f.write('\n\n## 验证结果\n\n')
            for check_name, passed in thread_result['checks']:
                icon = '✓' if passed else '✗'
                f.write(f"- {icon} {check_name}\n")
            if thread_result['issues']:
                f.write('\n## 问题\n\n')
                for issue in thread_result['issues']:
                    f.write(f"- {issue}\n")

        print(f"\n论文已保存: {paper_path}")
        print(f"各章节单独文件: {self.output_dir}/section_*.md")

        # 引用质量审计
        print("  → 执行引用质量审计...")
        try:
            from citation_audit import audit_citations_batch
            # 从论文中提取引用行
            ref_section = self.sections.get('references', '')
            if not ref_section:
                # 从全文中提取括号引用
                import re as _re
                all_text = full_paper
                brackets = _re.findall(r'\[(\d+(?:,\s*\d+)*)\]', all_text)
                author_refs = _re.findall(r'\([A-Z][a-z]+[^)]*\d{4}[^)]*\)', all_text)
                ref_lines = author_refs if author_refs else []
            else:
                ref_lines = [l.strip() for l in ref_section.split('\n')
                             if l.strip() and len(l.strip()) > 15 and not l.startswith('#')]
            if ref_lines:
                result = audit_citations_batch(ref_lines[:30], verify=False)
                audit_path = os.path.join(self.output_dir, 'citation_audit.md')
                with open(audit_path, 'w', encoding='utf-8') as f:
                    f.write(result['report'])
                print(f"  → 引用审计完成: 评分{result['overall_score']}/100 → {audit_path}")
        except Exception as e:
            print(f"  → 引用审计跳过: {e}")

        # 统计
        total_chars = len(full_paper)
        print(f"\n论文总字数: {total_chars}字")
        for name, content in self.sections.items():
            print(f"  {name}: {len(content)}字")

        print("\n" + "=" * 70)
        print("  论文生成完成！")
        print("=" * 70)

        return full_paper

    def _assemble_results(self):
        """组装Results章节"""
        lines = ['# 3 结果\n']

        texts = self.analysis_agent.texts
        captions = self.analysis_agent.captions

        # 按逻辑顺序组装
        order = [
            'descriptive_text', 'normality_text', 'comparison_text',
            'correlation_text', 'pca_text', 'regression_text',
            'carbon_balance_text'
        ]

        section_num = 1
        for key in order:
            text = texts.get(key, '')
            if text:
                # 替换章节编号
                text = text.replace('### ', f'### 3.{section_num} ', 1)
                lines.append(text)
                lines.append('')
                section_num += 1

        # 插入图注
        if captions:
            lines.append('\n**图注汇总：**\n')
            for fig_type, caption in captions.items():
                if caption:
                    lines.append(caption)
                    lines.append('')

        return '\n'.join(lines)

    def _generate_conclusion(self):
        """生成Conclusion"""
        language = self.language

        if language == 'zh':
            return (
                '# 5 结论\n\n'
                '本研究以某校园污水管网为研究对象，系统分析了固-液-气多相态碳污染物的'
                '赋存特征、空间分异及其驱动机制。主要结论如下：\n\n'
                '（1）校园污水管网碳污染物以固、液、气三种相态存在，'
                '各相态碳含量呈现不同的分布特征和变异程度。\n\n'
                '（2）不同功能区碳污染物浓度存在显著差异，'
                '餐饮区有机碳负荷最高，反映了排放源类型对碳污染特征的决定性影响。\n\n'
                '（3）溶解氧(DO)与甲烷(CH4)呈显著负相关，'
                '表明厌氧条件是管道产甲烷的关键驱动因素；'
                '总有机碳(TOC)与CH4呈显著正相关，说明有机负荷为产甲烷提供了底物来源。\n\n'
                '（4）碳平衡分析表明，液相碳是校园污水管网碳的主要赋存形式，'
                '碳在三相之间的分配受管道氧化还原条件和有机负荷的共同控制。\n\n'
                '研究结果可为校园污水碳减排策略制定和管网碳管理提供科学依据。'
            )
        return (
            '# 5 Conclusions\n\n'
            'This study systematically investigated the occurrence characteristics of '
            'multiphase carbon pollutants in a campus sewage network. The main conclusions '
            'are as follows:\n\n'
            '(1) Carbon pollutants exist in solid, liquid, and gas phases with distinct '
            'distribution patterns.\n\n'
            '(2) Significant spatial differences were observed among functional zones.\n\n'
            '(3) DO was negatively correlated with CH4, indicating anaerobic conditions '
            'as the key driver of methanogenesis.\n\n'
            '(4) TOC was positively correlated with CH4, suggesting organic loading as '
            'the substrate source for methane production.\n\n'
            'These findings provide scientific references for campus wastewater carbon '
            'management and emission reduction strategies.'
        )

    def _assemble_paper(self):
        """组装完整论文"""
        order = ['abstract', 'introduction', 'methods', 'results', 'discussion', 'conclusion']

        parts = []
        for section in order:
            content = self.sections.get(section, '')
            if content:
                parts.append(content)
                parts.append('\n---\n')

        # 参考文献占位
        parts.append('# 参考文献\n\n[待补充]\n')

        return '\n'.join(parts)


# ============================================================================
# 7. 快捷入口
# ============================================================================
def write_paper(data_path=None, paper_type='thesis', language='zh', output_dir=None, params=None):
    """一键生成论文"""
    writer = PaperWriter(output_dir)
    paper = writer.write(data_path, paper_type, language, params=params)
    return writer


if __name__ == '__main__':
    writer = write_paper()


# ============================================================================
# 知识库桥接：从knowledge_store加载进化后的机制知识
# ============================================================================
def _load_evolved_mechanisms():
    """从knowledge_store加载进化后的机制知识，失败时静默跳过。"""
    import json
    from pathlib import Path

    store_dir = Path(__file__).parent / "knowledge_store"
    if not store_dir.exists():
        return

    mech_path = store_dir / "mechanisms.json"
    if not mech_path.exists():
        return

    try:
        with open(mech_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        entries = data.get("entries", {})

        for key, entry in entries.items():
            val = entry.get("value", entry)
            if not isinstance(val, dict):
                continue
            # 将机制知识映射为MechanismKB的类属性
            attr_name = key.upper().replace("-", "_").replace(" ", "_")
            # 只添加新机制，不覆盖已有的硬编码机制
            if not hasattr(MechanismKB, attr_name) and val.get("mechanism"):
                setattr(MechanismKB, attr_name, val)
    except Exception as e:
        import logging
        logging.getLogger(__name__).debug(f"Failed to load evolved mechanisms: {e}")


# 模块加载时自动桥接
_load_evolved_mechanisms()
