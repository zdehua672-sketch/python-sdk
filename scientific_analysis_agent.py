"""
=============================================================================
科研数据分析Agent - Scientific Data Analysis Agent
智能编排 + 数据→文字自动生成 + 自动图注
输出"论文可直接使用"的分析结果
=============================================================================
"""

import pandas as pd
import numpy as np
from scipy import stats
import os
import json
from datetime import datetime

from data_loader import DataLoader
from statistical_analysis import StatisticalAnalyzer
from plotting_functions import ThesisPlotter
from academic_plot_style import get_label, format_chemical


# ============================================================================
# 1. 分析编排器 - 智能判断该做什么分析
# ============================================================================
class AnalysisOrchestrator:
    """
    智能分析编排器
    根据数据特征自动判断：哪些分析应该做、哪些图应该画、哪些结果值得讨论
    """

    def __init__(self, df, season_col='季节'):
        self.df = df
        self.season_col = season_col
        self.variable_info = self._classify_variables()
        self.recommendations = {}

    def _classify_variables(self):
        """自动识别变量类型和可用性"""
        info = {
            'gas': [],      # 气相变量
            'liquid': [],   # 液相变量
            'solid': [],    # 固相变量
            'env': [],      # 环境变量
            'all_numeric': []
        }

        gas_keywords = ['CH4', 'CO2', 'N2O', 'VOCs', 'H2S', 'O2', '甲烷', '氧化亚氮']
        solid_keywords = ['固总碳', '有机碳', '无机碳', 'DOC(mg/kg)', '全磷', '铵态氮（mg/kg', '硝态氮（mg/kg']
        env_keywords = ['气温', '泥水', '采样', '井深', '管径', '本底']

        for col in self.df.columns:
            if not pd.api.types.is_numeric_dtype(self.df[col]):
                continue
            if col in ['气相碳', '液相碳', '固相碳', 'TOC比例', 'IC比例', '气液碳比', 'CH4_TOCT比']:
                continue

            non_null = self.df[col].dropna()
            if len(non_null) < 3:
                continue

            info['all_numeric'].append(col)
            col_lower = str(col).lower()

            is_gas = any(k.lower() in col_lower for k in gas_keywords)
            is_solid = any(k in col for k in solid_keywords)
            is_env = any(k in col for k in env_keywords)

            if is_gas:
                info['gas'].append(col)
            elif is_solid:
                info['solid'].append(col)
            elif is_env:
                info['env'].append(col)
            else:
                info['liquid'].append(col)

        return info

    def decide_analyses(self):
        """智能决策：应该做哪些分析"""
        decisions = {}
        has_season = self.season_col in self.df.columns
        seasons = self.df[self.season_col].unique() if has_season else []

        # 1. 描述性统计 - 永远做
        decisions['descriptive'] = {
            'do': True,
            'reason': '基础分析，所有论文必备',
            'variables': self.variable_info['all_numeric']
        }

        # 2. 正态性检验 - 永远做（决定后续检验方法）
        decisions['normality'] = {
            'do': True,
            'reason': '决定参数/非参数检验选择',
            'variables': self.variable_info['all_numeric']
        }

        # 3. 组间比较 - 有季节数据时做
        if has_season and len(seasons) >= 2:
            decisions['group_comparison'] = {
                'do': True,
                'reason': f'检测到{len(seasons)}个季节组({",".join(str(s) for s in seasons)})，需检验差异',
                'variables': self.variable_info['all_numeric'],
                'group_col': self.season_col
            }

        # 4. 相关性分析 - 变量>=3个时做
        if len(self.variable_info['all_numeric']) >= 3:
            decisions['correlation'] = {
                'do': True,
                'reason': f'{len(self.variable_info["all_numeric"])}个变量，适合做相关性分析',
                'variables': self.variable_info['all_numeric']
            }

        # 5. PCA - 变量>=3个且样本>=10个时做
        n_samples = len(self.df)
        if len(self.variable_info['all_numeric']) >= 3 and n_samples >= 10:
            decisions['pca'] = {
                'do': True,
                'reason': f'{n_samples}个样本×{len(self.variable_info["all_numeric"])}个变量，适合降维',
                'variables': self.variable_info['all_numeric'],
                'n_components': min(2, len(self.variable_info['all_numeric']))
            }

        # 6. HCA - 样本>=5个时做
        if n_samples >= 5:
            decisions['hca'] = {
                'do': True,
                'reason': f'{n_samples}个样本，适合聚类分析',
            }

        # 7. 回归分析 - 检查有意义的变量对
        regression_pairs = self._find_regression_pairs()
        if regression_pairs:
            decisions['regression'] = {
                'do': True,
                'reason': f'发现{len(regression_pairs)}对有科研意义的变量组合',
                'pairs': regression_pairs
            }

        # 8. 碳平衡 - 有三相碳数据时做
        has_gas = len(self.variable_info['gas']) > 0
        has_liquid = len(self.variable_info['liquid']) > 0
        has_solid = len(self.variable_info['solid']) > 0
        phase_count = sum([has_gas, has_liquid, has_solid])
        if phase_count >= 2:
            decisions['carbon_balance'] = {
                'do': True,
                'reason': f'检测到{phase_count}相碳数据，可做碳平衡分析',
            }

        self.recommendations = decisions
        return decisions

    def _find_regression_pairs(self):
        """找到有科研意义的回归变量对"""
        pairs = []
        key_pairs = [
            ('TOC（mg/L)', 'CH4平均值', '有机碳-甲烷关系'),
            ('TOC（mg/L)', 'CO2', '有机碳-二氧化碳关系'),
            ('DO(mg/L)', 'CH4平均值', '溶解氧-甲烷关系'),
            ('COD（mg/L)', 'CH4平均值', '化学需氧量-甲烷关系'),
            ('TOC（mg/L)', '总氮（mg/L)', '碳氮耦合关系'),
            ('铵态氮（mg/L)', 'CH4平均值', '氮转化-甲烷关系'),
        ]
        cols = set(self.variable_info['all_numeric'])
        for x, y, desc in key_pairs:
            if x in cols and y in cols:
                pairs.append({'x': x, 'y': y, 'description': desc})
        return pairs

    def decide_figures(self):
        """智能决策：应该画哪些图"""
        figs = {}
        decisions = self.recommendations or self.decide_analyses()

        # 饼图 - 有多相数据
        if self.variable_info['gas'] and (self.variable_info['liquid'] or self.variable_info['solid']):
            figs['phase_pie'] = {'do': True, 'title': '固液气三相碳组成'}

        # 箱线图 - 有组间比较
        if 'group_comparison' in decisions:
            for phase, cols in [('gas', self.variable_info['gas']),
                                ('liquid', self.variable_info['liquid']),
                                ('solid', self.variable_info['solid'])]:
                if cols:
                    figs[f'{phase}_boxplot'] = {
                        'do': True,
                        'title': f'{phase}_boxplot',
                        'variables': cols
                    }

        # 相关性热图
        if 'correlation' in decisions:
            figs['correlation_heatmap'] = {'do': True, 'title': 'Pearson相关性矩阵'}

        # PCA双标图
        if 'pca' in decisions:
            figs['pca_biplot'] = {'do': True, 'title': 'PCA双标图'}

        # HCA树状图
        if 'hca' in decisions:
            figs['hca_dendrogram'] = {'do': True, 'title': '层次聚类分析'}

        # 回归图
        if 'regression' in decisions:
            figs['regression'] = {
                'do': True,
                'title': '回归分析',
                'pairs': decisions['regression']['pairs']
            }

        # 空间分布图
        if self.variable_info['gas']:
            figs['spatial_gas'] = {'do': True, 'title': '气相碳污染物空间分布', 'variables': self.variable_info['gas']}
        if self.variable_info['liquid']:
            figs['spatial_liquid'] = {'do': True, 'title': '液相碳污染物空间分布', 'variables': self.variable_info['liquid']}

        return figs

    def identify_discussion_points(self, analysis_results):
        """识别哪些结果值得讨论"""
        points = []

        # 检查组间比较结果
        if '组间比较' in analysis_results:
            comp = analysis_results['组间比较']
            sig_vars = comp[comp['显著性'] != 'n.s.']
            for _, row in sig_vars.iterrows():
                points.append({
                    'type': 'seasonal_difference',
                    'variable': row['变量'],
                    'significance': row['显著性'],
                    'priority': 'high' if row['显著性'] in ['***', '**'] else 'medium'
                })

        # 检查相关性结果
        for method in ['pearson', 'spearman']:
            key = f'{method}相关'
            if key in analysis_results:
                corr = analysis_results[key]['相关系数']
                pvals = analysis_results[key]['p值']
                for i in range(len(corr)):
                    for j in range(i + 1, len(corr)):
                        r = corr.iloc[i, j]
                        p = pvals.iloc[i, j]
                        if abs(r) > 0.6 and p < 0.05:
                            points.append({
                                'type': 'strong_correlation',
                                'variables': (corr.index[i], corr.columns[j]),
                                'r': r, 'p': p,
                                'priority': 'high'
                            })

        # 检查PCA结果
        if 'PCA' in analysis_results:
            var_ratio = analysis_results['PCA'].get('方差贡献率', [])
            if len(var_ratio) >= 2 and sum(var_ratio[:2]) > 0.7:
                points.append({
                    'type': 'pca_interpretation',
                    'cumulative_variance': sum(var_ratio[:2]),
                    'priority': 'high'
                })

        return sorted(points, key=lambda x: {'high': 0, 'medium': 1, 'low': 2}.get(x['priority'], 3))


# ============================================================================
# 2. 文字生成器 - 数据→论文文字
# ============================================================================
class TextGenerator:
    """
    数据→论文文字 自动生成器
    读取统计分析结果，填充模板，输出论文可直接使用的中文段落
    """

    def __init__(self, analyzer_results, variable_info):
        self.results = analyzer_results
        self.var_info = variable_info

    def generate_all(self):
        """生成所有章节的文字"""
        sections = {}

        sections['descriptive_text'] = self._gen_descriptive()
        sections['normality_text'] = self._gen_normality()
        sections['comparison_text'] = self._gen_comparison()
        sections['correlation_text'] = self._gen_correlation()
        sections['pca_text'] = self._gen_pca()
        sections['regression_text'] = self._gen_regression()
        sections['carbon_balance_text'] = self._gen_carbon_balance()

        return {k: v for k, v in sections.items() if v}

    def _gen_descriptive(self):
        """生成描述性统计文字"""
        if '描述统计' not in self.results:
            return ''

        desc = self.results['描述统计']['总体']
        lines = ['### 描述性统计结果\n']

        for col in desc.columns:
            mean = desc.loc['mean', col]
            std = desc.loc['std', col]
            min_val = desc.loc['min', col]
            max_val = desc.loc['max', col]
            n = int(desc.loc['count', col])

            cv = (std / mean * 100) if mean != 0 else 0

            label = get_label(col)
            cv_desc = '高变异' if cv > 100 else ('中等变异' if cv > 30 else '低变异')

            lines.append(
                f'{label}的变化范围为{min_val:.2f}~{max_val:.2f}，'
                f'平均值为{mean:.2f}±{std:.2f}(n={n})，'
                f'变异系数CV={cv:.1f}%，属于{cv_desc}。'
            )

        # 分组统计
        if self.results['描述统计'].get('分组') is not None:
            grouped = self.results['描述统计']['分组']
            seasons = grouped.index.get_level_values(0).unique()
            lines.append(f'\n按季节分组：')
            for col in desc.columns[:6]:  # 只写前6个变量
                label = get_label(col)
                season_vals = []
                for s in seasons:
                    try:
                        m = grouped.loc[s, (col, 'mean')]
                        sd = grouped.loc[s, (col, 'std')]
                        season_vals.append(f'{s}({m:.2f}±{sd:.2f})')
                    except (KeyError, TypeError):
                        pass
                if season_vals:
                    lines.append(f'{label}：{"，".join(season_vals)}。')

        return '\n'.join(lines)

    def _gen_normality(self):
        """生成正态性检验文字"""
        if '正态性检验' not in self.results:
            return ''

        df = self.results['正态性检验']
        normal = df[df['正态性'] == '是']['变量'].tolist()
        non_normal = df[df['正态性'] == '否']['变量'].tolist()

        lines = ['### 正态性检验结果\n']
        lines.append(
            f'Shapiro-Wilk正态性检验结果表明，'
            f'{len(normal)}个变量符合正态分布(p>0.05)，'
            f'{len(non_normal)}个变量不符合正态分布(p≤0.05)。'
        )
        if non_normal:
            non_normal_labels = [get_label(v) for v in non_normal[:5]]
            lines.append(f'非正态变量包括：{"、".join(non_normal_labels)}等。')
            lines.append('对于非正态分布的变量，后续组间比较采用Mann-Whitney U非参数检验。')

        return '\n'.join(lines)

    def _gen_comparison(self):
        """生成组间比较文字"""
        if '组间比较' not in self.results:
            return ''

        df = self.results['组间比较']
        lines = ['### 组间差异分析结果\n']

        sig = df[df['显著性'] != 'n.s.']
        nonsig = df[df['显著性'] == 'n.s.']

        lines.append(
            f'组间比较结果显示，{len(sig)}个变量在不同季节之间存在显著差异，'
            f'{len(nonsig)}个变量的季节差异不显著。'
        )

        for _, row in sig.iterrows():
            label = get_label(row['变量'])
            method = row['方法']
            p = row['p值']
            sig_level = row['显著性']

            # 找到两组的均值列
            mean_cols = [c for c in row.index if '_均值' in c]
            if len(mean_cols) == 2:
                g1_name = mean_cols[0].replace('_均值', '')
                g2_name = mean_cols[1].replace('_均值', '')
                m1 = row[mean_cols[0]]
                m2 = row[mean_cols[1]]

                higher = g1_name if m1 > m2 else g2_name
                lower = g2_name if m1 > m2 else g1_name
                higher_val = max(m1, m2)
                lower_val = min(m1, m2)

                lines.append(
                    f'{label}在{higher}({higher_val:.2f})显著高于{lower}({lower_val:.2f})'
                    f'({method}，p={p:.4f}{sig_level})。'
                )

        return '\n'.join(lines)

    def _gen_correlation(self):
        """生成相关性分析文字"""
        for method in ['pearson', 'spearman']:
            key = f'{method}相关'
            if key in self.results:
                corr = self.results[key]['相关系数']
                pvals = self.results[key]['p值']
                break
        else:
            return ''

        lines = ['### 相关性分析结果\n']
        lines.append(f'{method.capitalize()}相关性分析结果如图X所示。')

        # 找显著的强相关
        strong_pos = []
        strong_neg = []
        for i in range(len(corr)):
            for j in range(i + 1, len(corr)):
                r = corr.iloc[i, j]
                p = pvals.iloc[i, j]
                if abs(r) > 0.6 and p < 0.05:
                    var_i = get_label(corr.index[i])
                    var_j = get_label(corr.columns[j])
                    if r > 0:
                        strong_pos.append((var_i, var_j, r, p))
                    else:
                        strong_neg.append((var_i, var_j, r, p))

        if strong_pos:
            lines.append('\n显著正相关：')
            for v1, v2, r, p in strong_pos[:5]:
                stars = '***' if p < 0.001 else ('**' if p < 0.01 else '*')
                lines.append(f'- {v1}与{v2}呈显著正相关(r={r:.3f}, p{stars})')

        if strong_neg:
            lines.append('\n显著负相关：')
            for v1, v2, r, p in strong_neg[:5]:
                stars = '***' if p < 0.001 else ('**' if p < 0.01 else '*')
                lines.append(f'- {v1}与{v2}呈显著负相关(r={r:.3f}, p{stars})')

        if not strong_pos and not strong_neg:
            lines.append('各变量之间未发现|r|>0.6的强相关关系。')

        return '\n'.join(lines)

    def _gen_pca(self):
        """生成PCA分析文字"""
        if 'PCA' not in self.results:
            return ''

        pca = self.results['PCA']
        var_ratio = pca.get('explained_variance_ratio', pca.get('方差贡献率', []))
        loadings = pca.get('loadings', pca.get('载荷矩阵'))

        lines = ['### 主成分分析(PCA)结果\n']

        if len(var_ratio) >= 2:
            lines.append(
                f'主成分分析结果表明，前2个主成分的方差贡献率分别为'
                f'{var_ratio[0]*100:.1f}%和{var_ratio[1]*100:.1f}%，'
                f'累计方差贡献率为{sum(var_ratio[:2])*100:.1f}%。'
            )

            if sum(var_ratio[:2]) > 0.7:
                lines.append('累计贡献率超过70%，说明前2个主成分能较好地代表原始变量的信息。')

        if loadings is not None:
            # PC1高载荷变量
            pc1_loadings = loadings.iloc[:, 0].abs().sort_values(ascending=False)
            high_vars = pc1_loadings[pc1_loadings > 0.5].index.tolist()
            if high_vars:
                high_labels = [get_label(v) for v in high_vars[:5]]
                lines.append(
                    f'PC1上载荷较高的变量包括{"、".join(high_labels)}等，'
                    f'反映了[待解释]的信息。'
                )

        return '\n'.join(lines)

    def _gen_regression(self):
        """生成回归分析文字"""
        if '回归分析' not in self.results:
            return ''

        reg = self.results['回归分析']
        lines = ['### 回归分析结果\n']

        for key, result in reg.items():
            if not isinstance(result, dict):
                continue
            r2 = result.get('r_squared', result.get('r2', 0))
            r = result.get('r', 0)
            p = result.get('p_value', result.get('p', 1))
            slope = result.get('slope', 0)
            intercept = result.get('intercept', 0)
            x_col = result.get('x_col', 'X')
            y_col = result.get('y_col', 'Y')

            x_label = get_label(x_col)
            y_label = get_label(y_col)

            if r2 > 0.3 and p < 0.05:
                sign = '+' if intercept >= 0 else ''
                lines.append(
                    f'{x_label}与{y_label}的回归方程为：'
                    f'y = {slope:.4f}x {sign} {intercept:.4f}，'
                    f'R²={r2:.3f}(p={p:.4f})。'
                )
                if r2 > 0.7:
                    lines.append(f'拟合优度较高(R²>0.7)，说明{x_label}能较好地解释{y_label}的变化。')
                elif r2 > 0.5:
                    lines.append(f'拟合优度中等(R²>0.5)。')

        return '\n'.join(lines)

    def _gen_carbon_balance(self):
        """生成碳平衡分析文字"""
        if '描述统计' not in self.results:
            return ''

        desc = self.results['描述统计']['总体']
        lines = ['### 碳平衡分析\n']

        phase_data = {}
        for col in ['气相碳', '液相碳', '固相碳']:
            if col in desc.columns:
                phase_data[col] = desc.loc['mean', col]

        if len(phase_data) >= 2:
            total = sum(phase_data.values())
            for phase, val in phase_data.items():
                pct = val / total * 100
                lines.append(f'{phase}占比{pct:.1f}%。')

        return '\n'.join(lines)


# ============================================================================
# 3. 图注生成器 - 自动生成中英文图注
# ============================================================================
class CaptionGenerator:
    """
    自动生成论文级图注
    """

    @staticmethod
    def generate(fig_type, fig_data, language='zh'):
        """根据图类型生成图注"""
        generators = {
            'phase_pie': CaptionGenerator._caption_pie,
            'gas_boxplot': CaptionGenerator._caption_boxplot,
            'liquid_boxplot': CaptionGenerator._caption_boxplot,
            'solid_boxplot': CaptionGenerator._caption_boxplot,
            'correlation_heatmap': CaptionGenerator._caption_heatmap,
            'pca_biplot': CaptionGenerator._caption_pca,
            'hca_dendrogram': CaptionGenerator._caption_hca,
            'regression': CaptionGenerator._caption_regression,
            'spatial_gas': CaptionGenerator._caption_spatial,
            'spatial_liquid': CaptionGenerator._caption_spatial,
        }

        gen_func = generators.get(fig_type)
        if gen_func:
            return gen_func(fig_data, language)
        return ''

    @staticmethod
    def _caption_pie(data, lang):
        if lang == 'zh':
            return (
                '图X 固液气三相碳污染物组成比例\n'
                '图中数值表示各相态碳含量占总碳的百分比。'
                '碳含量为各采样点的算术平均值。'
            )
        return (
            'Fig. X Composition of solid-liquid-gas phase carbon pollutants\n'
            'Values represent the percentage of each phase to total carbon. '
            'Carbon content is the arithmetic mean of all sampling points.'
        )

    @staticmethod
    def _caption_boxplot(data, lang):
        season = data.get('season', '冬春')
        variables = data.get('variables', [])
        var_names = ', '.join([get_label(v) for v in variables[:4]])

        if lang == 'zh':
            return (
                f'图X {season}季{var_names}箱线图比较\n'
                f'箱线图展示中位数、四分位距和异常值。'
                f'星号表示Mann-Whitney U检验显著性：* p<0.05，** p<0.01，*** p<0.001。'
            )
        return (
            f'Fig. X Boxplot comparison of {var_names} between seasons\n'
            f'Boxplots show median, interquartile range, and outliers. '
            f'Asterisks indicate Mann-Whitney U test significance: * p<0.05, ** p<0.01, *** p<0.001.'
        )

    @staticmethod
    def _caption_heatmap(data, lang):
        method = data.get('method', 'Pearson')
        if lang == 'zh':
            return (
                f'图X {method}相关性矩阵\n'
                f'颜色深浅表示相关系数大小，红色为正相关，蓝色为负相关。'
                f'* p<0.05，** p<0.01，*** p<0.001。'
            )
        return (
            f'Fig. X {method} correlation matrix\n'
            f'Color intensity indicates correlation magnitude. '
            f'Red = positive, blue = negative. * p<0.05, ** p<0.01, *** p<0.001.'
        )

    @staticmethod
    def _caption_pca(data, lang):
        var_ratio = data.get('variance_ratio', [0, 0])
        if lang == 'zh':
            return (
                f'图X 主成分分析(PCA)双标图\n'
                f'PC1和PC2分别解释了{var_ratio[0]*100:.1f}%和{var_ratio[1]*100:.1f}%的方差。'
                f'箭头表示变量在主成分空间中的载荷方向和大小。'
            )
        return (
            f'Fig. X PCA biplot\n'
            f'PC1 and PC2 explain {var_ratio[0]*100:.1f}% and {var_ratio[1]*100:.1f}% of variance respectively. '
            f'Arrows indicate variable loading directions and magnitudes.'
        )

    @staticmethod
    def _caption_hca(data, lang):
        if lang == 'zh':
            return (
                '图X 层次聚类分析(HCA)树状图\n'
                '采用Ward连接法，距离度量为欧氏距离。'
                '截断线位置表示聚类数目。'
            )
        return (
            'Fig. X Hierarchical cluster analysis dendrogram\n'
            'Ward linkage method with Euclidean distance metric. '
            'Dashed line indicates cluster cut-off.'
        )

    @staticmethod
    def _caption_regression(data, lang):
        x_var = get_label(data.get('x', 'X'))
        y_var = get_label(data.get('y', 'Y'))
        r2 = data.get('r2', 0)
        p = data.get('p', 1)

        if lang == 'zh':
            return (
                f'图X {x_var}与{y_var}的线性回归关系\n'
                f'实线为回归拟合线，阴影区域为95%置信区间。'
                f'R²={r2:.3f}，p={p:.4f}。'
            )
        return (
            f'Fig. X Linear regression between {x_var} and {y_var}\n'
            f'Solid line: regression fit. Shaded area: 95% confidence interval. '
            f'R²={r2:.3f}, p={p:.4f}.'
        )

    @staticmethod
    def _caption_spatial(data, lang):
        variables = data.get('variables', [])
        var_names = ', '.join([get_label(v) for v in variables[:4]])

        if lang == 'zh':
            return (
                f'图X 碳污染物空间分布特征\n'
                f'展示{var_names}沿采样点的空间变化。'
                f'虚线表示功能区划分界线。'
            )
        return (
            f'Fig. X Spatial distribution of carbon pollutants\n'
            f'Shows spatial variation of {var_names} along sampling points. '
            f'Dashed lines indicate functional zone boundaries.'
        )


# ============================================================================
# 4. 主编排器 - 一键运行全部分析
# ============================================================================
class ScientificAnalysisAgent:
    """
    科研数据分析Agent主类
    输入数据 → 自动分析 → 输出论文可直接使用的图表+文字
    """

    def __init__(self, data_path=None, output_dir=None):
        self.data_path = data_path
        self.output_dir = output_dir or os.path.join(os.getcwd(), 'analysis_output')
        os.makedirs(self.output_dir, exist_ok=True)

        self.df = None
        self.analyzer = None
        self.orchestrator = None
        self.plotter = None
        self.results = {}
        self.texts = {}
        self.captions = {}

    def load_data(self, df=None):
        """加载数据"""
        if df is not None:
            self.df = df
        elif self.data_path:
            loader = DataLoader(self.data_path)
            self.df = loader.load_data()
        else:
            loader = DataLoader()
            loader.load_data()
            self.df = loader.get_analysis_ready_data()

        print(f"数据加载完成: {self.df.shape[0]}行 × {self.df.shape[1]}列")
        return self

    def run(self, language='zh'):
        """一键运行全部分析"""
        if self.df is None:
            self.load_data()

        print("\n" + "=" * 70)
        print("  科研数据分析Agent - 开始自动分析")
        print("=" * 70)

        # Step 1: 智能编排
        print("\n[Step 1] 智能分析决策...")
        self.orchestrator = AnalysisOrchestrator(self.df)
        decisions = self.orchestrator.decide_analyses()
        fig_decisions = self.orchestrator.decide_figures()

        for name, decision in decisions.items():
            status = '✓ 执行' if decision['do'] else '✗ 跳过'
            print(f"  {status} {name}: {decision['reason']}")

        # Step 2: 统计分析
        print("\n[Step 2] 执行统计分析...")
        self.analyzer = StatisticalAnalyzer(self.df)

        if decisions.get('descriptive', {}).get('do'):
            self.results['描述统计'] = self.analyzer.descriptive_statistics()

        if decisions.get('normality', {}).get('do'):
            self.results['正态性检验'] = self.analyzer.normality_test()

        if decisions.get('group_comparison', {}).get('do'):
            self.results['组间比较'] = self.analyzer.compare_groups()

        if decisions.get('correlation', {}).get('do'):
            corr, pvals = self.analyzer.correlation_analysis(method='pearson')
            self.results['pearson相关'] = {'相关系数': corr, 'p值': pvals}

        if decisions.get('pca', {}).get('do'):
            self.results['PCA'] = self.analyzer.pca_analysis()

        if decisions.get('hca', {}).get('do'):
            self.results['HCA'] = self.analyzer.hca_analysis()

        if decisions.get('regression', {}).get('do'):
            self.results['回归分析'] = {}
            for pair in decisions['regression']['pairs']:
                result = self.analyzer.regression_analysis(pair['x'], pair['y'])
                if result:
                    key = f"{pair['x']}→{pair['y']}"
                    self.results['回归分析'][key] = result

        # Step 3: 生成图表
        print("\n[Step 3] 生成论文级图表...")
        self.plotter = ThesisPlotter(self.df, self.output_dir)

        figure_list = []
        if fig_decisions.get('phase_pie', {}).get('do'):
            self.plotter.plot_phase_composition()
            figure_list.append('phase_pie')

        for phase in ['gas', 'liquid', 'solid']:
            key = f'{phase}_boxplot'
            if fig_decisions.get(key, {}).get('do'):
                getattr(self.plotter, f'plot_{phase}_boxplot', lambda: None)()
                figure_list.append(key)

        if fig_decisions.get('correlation_heatmap', {}).get('do'):
            self.plotter.plot_correlation_heatmap()
            figure_list.append('correlation_heatmap')

        if fig_decisions.get('pca_biplot', {}).get('do'):
            self.plotter.plot_pca_biplot()
            figure_list.append('pca_biplot')

        if fig_decisions.get('hca_dendrogram', {}).get('do'):
            self.plotter.plot_hca_dendrogram()
            figure_list.append('hca_dendrogram')

        if fig_decisions.get('regression', {}).get('do'):
            self.plotter.plot_all_regressions()
            figure_list.append('regression')

        # Step 4: 生成图注
        print("\n[Step 4] 自动生成图注...")
        for i, fig_type in enumerate(figure_list, 1):
            fig_data = fig_decisions.get(fig_type, {})
            caption = CaptionGenerator.generate(fig_type, fig_data, language)
            self.captions[fig_type] = caption
            if caption:
                print(f"\n--- 图注 {i} ({fig_type}) ---")
                print(caption)

        # Step 5: 生成论文文字
        print("\n[Step 5] 自动生成Results文字...")
        self.texts = TextGenerator(self.results, self.orchestrator.variable_info).generate_all()

        # Step 6: 识别讨论要点
        print("\n[Step 6] 识别Discussion要点...")
        discussion_points = self.orchestrator.identify_discussion_points(self.results)

        # Step 7: 输出完整报告
        print("\n[Step 7] 生成分析报告...")
        report = self._build_report(language)

        report_path = os.path.join(self.output_dir, 'analysis_report.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n报告已保存: {report_path}")

        # 保存结构化结果
        results_path = os.path.join(self.output_dir, 'analysis_results.json')
        serializable = self._make_serializable(self.results)
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2, default=str)

        print("\n" + "=" * 70)
        print("  分析完成！")
        print(f"  图表输出: {self.output_dir}")
        print(f"  报告文件: {report_path}")
        print("=" * 70)

        return self

    def _build_report(self, language='zh'):
        """构建完整分析报告"""
        lines = [
            '# 科研数据分析报告\n',
            f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n',
            f'数据规模: {self.df.shape[0]}个样本 × {self.df.shape[1]}个变量\n',
            '---\n',
        ]

        # 分析决策摘要
        lines.append('## 分析决策\n')
        for name, decision in self.orchestrator.recommendations.items():
            lines.append(f"- {'✓' if decision['do'] else '✗'} **{name}**: {decision['reason']}")

        # 各章节文字
        lines.append('\n---\n')
        for section_name, text in self.texts.items():
            if text:
                lines.append(f'\n{text}\n')

        # 图注汇总
        lines.append('\n---\n## 图注汇总\n')
        for i, (fig_type, caption) in enumerate(self.captions.items(), 1):
            if caption:
                lines.append(f'\n{caption}\n')

        # Discussion要点
        if hasattr(self.orchestrator, '_last_discussion_points'):
            lines.append('\n---\n## Discussion建议要点\n')
            for pt in self.orchestrator._last_discussion_points:
                lines.append(f"- [{pt['priority']}] {pt['type']}: {pt}")

        return '\n'.join(lines)

    def _make_serializable(self, obj):
        """将numpy/pandas对象转为可JSON序列化的格式"""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (pd.DataFrame, pd.Series)):
            return obj.to_dict()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        return obj


# ============================================================================
# 5. 快捷入口
# ============================================================================
def run_analysis(data_path=None, output_dir=None, language='zh'):
    """一键运行科研数据分析"""
    agent = ScientificAnalysisAgent(data_path, output_dir)
    agent.load_data()
    agent.run(language)
    return agent


if __name__ == '__main__':
    agent = run_analysis()
