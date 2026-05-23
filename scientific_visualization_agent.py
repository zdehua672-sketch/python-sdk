"""
=============================================================================
Scientific Visualization Agent - 论文级自动绘图系统
支持SCI/Nature/中文三种风格 + 10种图表类型 + Origin/R代码生成
=============================================================================
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib import rcParams
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import seaborn as sns
from scipy import stats as scipy_stats

# 复用现有模块（不修改）
from academic_plot_style import (
    CHINESE_FONT, ENGLISH_FONT, OKABE_ITO, TABLEAU_10,
    PHASE_COLORS, SEASON_COLORS, CARBON_COLORS,
    get_label, format_chemical, significance_stars,
    add_significance_bars, save_figure, set_plot_style
)
from plotting_functions import ThesisPlotter
from statistical_analysis import StandardScaler, PCA, LinearRegression, r2_score

# 可选依赖检测
_HAS_SCIENCEPLOTS = False
_HAS_STATANNOTATIONS = False
_HAS_ADJUSTTEXT = False
_HAS_PLOTLY = False
_HAS_KALEIDO = False

try:
    import scienceplots
    _HAS_SCIENCEPLOTS = True
except ImportError:
    pass

try:
    from statannotations.Annotator import Annotator
    _HAS_STATANNOTATIONS = True
except ImportError:
    pass

try:
    from adjustText import adjust_text
    _HAS_ADJUSTTEXT = True
except ImportError:
    pass

try:
    import plotly.graph_objects as go
    import plotly.io as pio
    _HAS_PLOTLY = True
    try:
        import kaleido
        _HAS_KALEIDO = True
    except ImportError:
        pass
except ImportError:
    pass


# ============================================================================
# StylePresets - 期刊风格预设
# ============================================================================
class StylePresets:
    """三种期刊风格：SCI(ES&T) / Nature / 中文核心"""

    PRESETS = {
        'sci': {
            'font.family': 'sans-serif',
            'font.sans-serif': ['Arial', 'DejaVu Sans'],
            'font.size': 7,
            'axes.titlesize': 9,
            'axes.labelsize': 8,
            'xtick.labelsize': 7,
            'ytick.labelsize': 7,
            'legend.fontsize': 7,
            'figure.figsize': (7.0, 5.25),
            'figure.dpi': 300,
            'lines.linewidth': 1.0,
            'lines.markersize': 5,
            'axes.linewidth': 0.8,
            'xtick.major.width': 0.8,
            'ytick.major.width': 0.8,
            'xtick.major.size': 4,
            'ytick.major.size': 4,
            'xtick.direction': 'in',
            'ytick.direction': 'in',
            'axes.grid': True,
            'grid.color': '#E0E0E0',
            'grid.linestyle': '--',
            'grid.alpha': 0.5,
            'axes.spines.top': False,
            'axes.spines.right': False,
            'savefig.dpi': 600,
            'savefig.format': 'pdf',
        },
        'nature': {
            'font.family': 'sans-serif',
            'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
            'font.size': 5.5,
            'axes.titlesize': 7,
            'axes.labelsize': 6,
            'xtick.labelsize': 5.5,
            'ytick.labelsize': 5.5,
            'legend.fontsize': 5.5,
            'figure.figsize': (3.50, 2.63),
            'figure.dpi': 300,
            'lines.linewidth': 0.8,
            'lines.markersize': 4,
            'axes.linewidth': 0.5,
            'xtick.major.width': 0.5,
            'ytick.major.width': 0.5,
            'xtick.major.size': 3,
            'ytick.major.size': 3,
            'xtick.direction': 'out',
            'ytick.direction': 'out',
            'axes.grid': False,
            'axes.spines.top': False,
            'axes.spines.right': False,
            'savefig.dpi': 600,
            'savefig.format': 'pdf',
        },
        'chinese': {
            'font.family': 'sans-serif',
            'font.sans-serif': [CHINESE_FONT, 'DejaVu Sans'],
            'font.serif': ['Times New Roman', 'DejaVu Serif'],
            'font.size': 10.5,
            'axes.titlesize': 14,
            'axes.labelsize': 12,
            'xtick.labelsize': 10.5,
            'ytick.labelsize': 10.5,
            'legend.fontsize': 10.5,
            'figure.figsize': (7.5, 5.625),
            'figure.dpi': 300,
            'lines.linewidth': 1.5,
            'lines.markersize': 7,
            'axes.linewidth': 1.0,
            'xtick.major.width': 1.0,
            'ytick.major.width': 1.0,
            'xtick.major.size': 5,
            'ytick.major.size': 5,
            'xtick.direction': 'in',
            'ytick.direction': 'in',
            'axes.grid': True,
            'grid.color': '#D0D0D0',
            'grid.linestyle': '--',
            'grid.alpha': 0.4,
            'axes.spines.top': False,
            'axes.spines.right': False,
            'savefig.dpi': 300,
            'savefig.format': 'png',
        },
    }

    FIGURE_SIZES = {
        'sci': {
            'single': (3.5, 2.625),
            'double': (7.0, 5.25),
            'full': (7.0, 9.0),
        },
        'nature': {
            'single': (3.50, 2.63),
            'double': (7.20, 5.40),
            'full': (7.20, 9.0),
        },
        'chinese': {
            'single': (7.5, 5.625),
            'double': (16.0, 12.0),
            'full': (16.0, 16.0),
        },
    }

    _current_style = 'sci'

    @classmethod
    def apply(cls, style_name='sci'):
        """应用期刊风格预设"""
        if style_name not in cls.PRESETS:
            raise ValueError(f"Unknown style: {style_name}. Choose from {list(cls.PRESETS.keys())}")

        # 先重置基础样式
        set_plot_style()

        # 尝试使用SciencePlots
        if _HAS_SCIENCEPLOTS and style_name in ('sci', 'nature'):
            try:
                plt.style.use(['science', style_name])
            except Exception:
                pass

        # 叠加项目专属设置
        rcParams.update(cls.PRESETS[style_name])
        cls._current_style = style_name

    @classmethod
    def figure_size(cls, layout='single', style=None):
        """获取指定布局的图尺寸"""
        style = style or cls._current_style
        return cls.FIGURE_SIZES.get(style, cls.FIGURE_SIZES['sci']).get(layout, (7.0, 5.25))

    @classmethod
    def get_palette(cls, style=None):
        """获取当前风格推荐的配色方案"""
        style = style or cls._current_style
        if style == 'nature':
            return [
                '#0072B2', '#E69F00', '#009E73', '#CC79A7',
                '#D55E00', '#56B4E9', '#F0E442', '#000000',
            ]
        elif style == 'chinese':
            return list(TABLEAU_10)
        else:
            return list(OKABE_ITO.values())


# ============================================================================
# AutoRecommender - 数据驱动图表推荐
# ============================================================================
class AutoRecommender:
    """分析DataFrame特征，自动推荐最适合的图表类型"""

    def __init__(self, df):
        self.df = df
        self.profile = self._profile_data()

    def _profile_data(self):
        """数据画像"""
        df = self.df
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

        # 检测分组列
        group_cols = [c for c in cat_cols if df[c].nunique() <= 10 and df[c].nunique() >= 2]

        # 检测时间列
        time_cols = [c for c in df.columns if any(k in str(c).lower() for k in ['时间', '日期', 'date', 'time', 'month', 'season', '季节'])]

        # 检测空间列
        spatial_cols = [c for c in df.columns if any(k in str(c).lower() for k in ['采样点', '位置', 'location', 'point', 'site', 'distance', '管口', '中段', '末端'])]

        # 检测相态列
        phase_keywords = ['CH4', 'CO2', 'TOC', 'COD', 'DO', '气相', '液相', '固相', 'NH4', 'TN', 'TP']
        phase_cols = [c for c in numeric_cols if any(k in str(c) for k in phase_keywords)]

        return {
            'n_rows': len(df),
            'n_cols': len(df.columns),
            'numeric_cols': numeric_cols,
            'cat_cols': cat_cols,
            'group_cols': group_cols,
            'time_cols': time_cols,
            'spatial_cols': spatial_cols,
            'phase_cols': phase_cols,
        }

    def recommend(self, top_n=5):
        """推荐图表类型列表，按分数排序"""
        p = self.profile
        recs = []

        # 箱线图/小提琴图：有分组 + 数值列
        if p['group_cols'] and p['numeric_cols']:
            score = 0.90 if len(p['numeric_cols']) <= 6 else 0.75
            recs.append({
                'chart_type': 'multivariate',
                'score': score,
                'reason': f"检测到{len(p['group_cols'])}个分组列 + {len(p['numeric_cols'])}个数值列，适合分组对比",
                'kwargs': {'variables': p['numeric_cols'][:6], 'group_col': p['group_cols'][0]},
            })

        # PCA：≥3数值列 + ≥10行
        if len(p['numeric_cols']) >= 3 and p['n_rows'] >= 10:
            score = 0.85
            recs.append({
                'chart_type': 'pca_hca',
                'score': score,
                'reason': f"{len(p['numeric_cols'])}个数值变量适合降维分析(PCA)",
                'kwargs': {'cols': p['numeric_cols'], 'mode': 'biplot'},
            })

        # 相关性热图：≥5数值列
        if len(p['numeric_cols']) >= 5:
            recs.append({
                'chart_type': 'heatmap',
                'score': 0.80,
                'reason': f"{len(p['numeric_cols'])}个数值变量适合相关性分析",
                'kwargs': {'method': 'pearson'},
            })

        # 时空分布：有空间+时间列
        if p['spatial_cols'] and (p['time_cols'] or p['group_cols']):
            recs.append({
                'chart_type': 'spatiotemporal',
                'score': 0.80,
                'reason': '检测到空间和时间维度，适合时空分布图',
                'kwargs': {'mode': 'line'},
            })

        # 多相态耦合：有相态列
        if len(p['phase_cols']) >= 3:
            recs.append({
                'chart_type': 'multiphase_coupling',
                'score': 0.75,
                'reason': f"检测到{len(p['phase_cols'])}个碳相关指标，适合多相态耦合图",
                'kwargs': {},
            })

        # 碳流/Sankey：有相态列
        if len(p['phase_cols']) >= 2:
            recs.append({
                'chart_type': 'carbon_flow',
                'score': 0.70,
                'reason': '适合碳流/物质流向可视化',
                'kwargs': {},
            })

        # Sankey桑基图
        if len(p['phase_cols']) >= 3:
            recs.append({
                'chart_type': 'sankey',
                'score': 0.65,
                'reason': '适合桑基图展示碳在相态间流转',
                'kwargs': {},
            })

        # 散点回归：2个连续变量
        if len(p['numeric_cols']) >= 2 and p['n_rows'] >= 10:
            recs.append({
                'chart_type': 'regression_scatter',
                'score': 0.70,
                'reason': f"数值变量间可做回归分析",
                'kwargs': {'x_col': p['numeric_cols'][0], 'y_col': p['numeric_cols'][1]},
            })

        # 聚类热图：≥5数值列
        if len(p['numeric_cols']) >= 5 and p['n_rows'] >= 8:
            recs.append({
                'chart_type': 'heatmap',
                'score': 0.68,
                'reason': '数值变量多，聚类热图可发现分组模式',
                'kwargs': {'clustered': True},
            })

        # 按分数排序
        recs.sort(key=lambda x: x['score'], reverse=True)
        return recs[:top_n]

    def suggest_layout(self):
        """推荐多图布局"""
        n_recs = len(self.recommend())
        if n_recs <= 1:
            return 'single'
        elif n_recs <= 2:
            return '1x2'
        elif n_recs <= 4:
            return '2x2'
        else:
            return '2x3'

    def suggest_palette(self):
        """根据数据特征推荐配色"""
        p = self.profile
        if '季节' in p['group_cols'] or 'season' in [c.lower() for c in p['group_cols']]:
            return dict(SEASON_COLORS)
        if any('气相' in c or '液相' in c or '固相' in c for c in p['phase_cols']):
            return dict(PHASE_COLORS)
        return dict(OKABE_ITO)


# ============================================================================
# MultiPanelComposer - 多图排版引擎
# ============================================================================
class MultiPanelComposer:
    """将多个子图组合成一个论文级多面板图"""

    @staticmethod
    def compose(plot_funcs, layout=None, style='sci',
                shared_x=False, shared_y=False,
                panel_labels=True, figsize=None,
                hspace=0.3, wspace=0.3):
        """
        组合多个绘图函数为一个多面板图

        Parameters
        ----------
        plot_funcs : list of callable
            每个函数签名: func(ax) -> metadata_dict
        layout : tuple (nrows, ncols) or None
        style : str
        shared_x, shared_y : bool
        panel_labels : bool
        figsize : tuple or None
        hspace, wspace : float

        Returns
        -------
        fig : matplotlib Figure
        metadata_list : list of dict
        """
        n = len(plot_funcs)
        if layout is None:
            if n <= 2:
                layout = (1, n)
            elif n <= 4:
                layout = (2, 2)
            elif n <= 6:
                layout = (2, 3)
            else:
                ncols = 3
                nrows = int(np.ceil(n / ncols))
                layout = (nrows, ncols)

        nrows, ncols = layout
        if figsize is None:
            base_w, base_h = StylePresets.figure_size('single', style)
            figsize = (base_w * ncols, base_h * nrows)

        fig, axes = plt.subplots(nrows, ncols, figsize=figsize,
                                  sharex=shared_x, sharey=shared_y,
                                  squeeze=False)

        metadata_list = []
        for i, func in enumerate(plot_funcs):
            row, col = divmod(i, ncols)
            ax = axes[row][col]
            try:
                meta = func(ax)
                metadata_list.append(meta if meta else {})
            except Exception as e:
                ax.text(0.5, 0.5, f'Error: {e}', ha='center', va='center',
                        transform=ax.transAxes, fontsize=8)
                metadata_list.append({'error': str(e)})

        # 隐藏多余的子图
        for i in range(n, nrows * ncols):
            row, col = divmod(i, ncols)
            axes[row][col].set_visible(False)

        # 添加子图标号
        if panel_labels:
            MultiPanelComposer._add_panel_labels(axes, nrows, ncols, style)

        plt.subplots_adjust(hspace=hspace, wspace=wspace)
        return fig, metadata_list

    @staticmethod
    def _add_panel_labels(axes, nrows, ncols, style='sci'):
        """添加(a)(b)(c)(d)标号"""
        label_size = 12 if style == 'chinese' else 10
        labels = 'abcdefghijklmnopqrstuvwxyz'
        idx = 0
        for row in range(nrows):
            for col in range(ncols):
                ax = axes[row][col]
                if ax.get_visible():
                    ax.text(-0.08, 1.08, f'({labels[idx]})',
                            transform=ax.transAxes,
                            fontsize=label_size, fontweight='bold',
                            va='bottom', ha='right')
                    idx += 1

    @staticmethod
    def align_y_axes(axes):
        """同步同一列的y轴范围"""
        if axes.ndim == 1:
            axes = axes.reshape(1, -1)
        for col in range(axes.shape[1]):
            ymin, ymax = np.inf, -np.inf
            for row in range(axes.shape[0]):
                ax = axes[row][col]
                if ax.get_visible():
                    ylim = ax.get_ylim()
                    ymin = min(ymin, ylim[0])
                    ymax = max(ymax, ylim[1])
            for row in range(axes.shape[1]):
                axes[row][col].set_ylim(ymin, ymax)


# ============================================================================
# VisualizationAgent - 主绘图类
# ============================================================================
class VisualizationAgent:
    """论文级自动绘图系统，支持10种图表类型"""

    def __init__(self, df, output_dir, style='sci', language='zh'):
        """
        Parameters
        ----------
        df : pd.DataFrame
            数据
        output_dir : str
            输出目录
        style : str
            'sci' / 'nature' / 'chinese'
        language : str
            'zh' / 'en'
        """
        self.df = df.copy()
        self.output_dir = output_dir
        self.style = style
        self.language = language
        os.makedirs(output_dir, exist_ok=True)

        self._recommender = AutoRecommender(self.df)
        self._legacy_plotter = ThesisPlotter(self.df, output_dir)
        self._caption_gen = EnhancedCaptionGenerator()
        StylePresets.apply(style)

    # ==================== 风格切换 ====================

    def plot_with_style(self, method_name, style=None, **kwargs):
        """以指定风格调用任意绘图方法"""
        old_style = self.style
        target_style = style or self.style
        StylePresets.apply(target_style)
        self.style = target_style
        try:
            result = getattr(self, method_name)(**kwargs)
        finally:
            StylePresets.apply(old_style)
            self.style = old_style
        return result

    # ==================== 自动绘图 ====================

    def auto_plot(self, top_n=5):
        """自动推荐并绘制最适合的图表"""
        recs = self._recommender.recommend(top_n)
        results = []
        for i, rec in enumerate(recs, 1):
            chart_type = rec['chart_type']
            kwargs = rec.get('kwargs', {})
            print(f"[自动绘图 {i}/{len(recs)}] {chart_type} (分数: {rec['score']:.2f}) - {rec['reason']}")
            try:
                method = getattr(self, f'plot_{chart_type}', None)
                if method:
                    fig, meta = method(**kwargs)
                    results.append({'chart_type': chart_type, 'fig': fig, 'metadata': meta, 'recommendation': rec})
                elif chart_type == 'regression_scatter':
                    x = kwargs.get('x_col', '')
                    y = kwargs.get('y_col', '')
                    fig, meta = self.plot_regression(x, y)
                    results.append({'chart_type': 'regression', 'fig': fig, 'metadata': meta, 'recommendation': rec})
                else:
                    print(f"  跳过: 未实现的方法 plot_{chart_type}")
            except Exception as e:
                print(f"  错误: {e}")
        return results

    # ==================== 需求1-3: 风格绘图 ====================

    def plot_sci(self, method_name='multivariate', **kwargs):
        """SCI/ES&T风格绘图"""
        return self.plot_with_style(method_name, style='sci', **kwargs)

    def plot_nature(self, method_name='multivariate', **kwargs):
        """Nature风格绘图"""
        return self.plot_with_style(method_name, style='nature', **kwargs)

    def plot_chinese_style(self, method_name='multivariate', **kwargs):
        """中文论文风格绘图"""
        return self.plot_with_style(method_name, style='chinese', **kwargs)

    # ==================== 需求4: 多变量统计图 ====================

    def plot_multivariate(self, variables=None, group_col=None, kind='raincloud'):
        """
        多变量统计图: violin / box / strip / raincloud

        Parameters
        ----------
        variables : list of str, 数值列名
        group_col : str, 分组列名
        kind : str, 'violin'|'box'|'strip'|'raincloud'

        Returns
        -------
        (fig, metadata_dict)
        """
        df = self.df
        if variables is None:
            variables = self._recommender.profile['numeric_cols'][:6]
        if group_col is None:
            groups = self._recommender.profile['group_cols']
            group_col = groups[0] if groups else None

        # 过滤存在的列
        variables = [v for v in variables if v in df.columns]
        if not variables:
            print("  警告: 无有效数值列")
            return None, {}

        n_vars = len(variables)
        fig_w = StylePresets.figure_size('double' if n_vars > 3 else 'single', self.style)[0]
        fig_h = StylePresets.figure_size('single', self.style)[1]
        fig, axes = plt.subplots(1, n_vars, figsize=(fig_w, fig_h * 0.8),
                                  sharey=False, squeeze=False)
        axes = axes[0]

        palette = StylePresets.get_palette()
        metadata = {'variables': variables, 'group_col': group_col, 'kind': kind}

        for i, var in enumerate(variables):
            ax = axes[i]
            if group_col and group_col in df.columns:
                data_plot = df[[var, group_col]].dropna()
                groups_list = data_plot[group_col].unique()

                if kind in ('violin', 'raincloud'):
                    sns.violinplot(data=data_plot, x=group_col, y=var, ax=ax,
                                   palette=palette[:len(groups_list)], inner=None,
                                   alpha=0.3, linewidth=0.5)
                if kind in ('box', 'raincloud'):
                    sns.boxplot(data=data_plot, x=group_col, y=var, ax=ax,
                                palette=palette[:len(groups_list)],
                                width=0.3 if kind == 'raincloud' else 0.6,
                                linewidth=0.8, fliersize=2)
                if kind in ('strip', 'raincloud'):
                    sns.stripplot(data=data_plot, x=group_col, y=var, ax=ax,
                                  palette=palette[:len(groups_list)],
                                  size=3, alpha=0.6, jitter=True)

                # 显著性标注
                if len(groups_list) == 2:
                    g1 = data_plot[data_plot[group_col] == groups_list[0]][var].dropna()
                    g2 = data_plot[data_plot[group_col] == groups_list[1]][var].dropna()
                    if len(g1) > 2 and len(g2) > 2:
                        _, p_val = scipy_stats.mannwhitneyu(g1, g2, alternative='two-sided')
                        y_max = data_plot[var].max()
                        add_significance_bars(ax, 0, 1, y_max * 1.05, p_value=p_val)
                        metadata.setdefault('tests', {})[var] = {'p_value': p_val, 'method': 'Mann-Whitney U'}

                label = get_label(var)
                ax.set_ylabel(label)
                ax.set_xlabel('')
            else:
                sns.violinplot(data=df, y=var, ax=ax, color=palette[0], inner=None, alpha=0.3)
                sns.boxplot(data=df, y=var, ax=ax, color=palette[0], width=0.3, linewidth=0.8)

            ax.set_title(get_label(var) if n_vars <= 4 else '')

        plt.tight_layout()
        filename = 'multivariate_' + kind
        save_figure(fig, filename, self.output_dir)
        caption = self._caption_gen.generate('multivariate', metadata, language=self.language)
        return fig, metadata

    # ==================== 需求5: PCA/HCA图 ====================

    def plot_pca_hca(self, cols=None, mode='biplot', group_col=None):
        """
        PCA/HCA增强图

        mode: 'biplot' | 'scores' | 'loadings' | 'clustermap'
        """
        df = self.df
        if cols is None:
            cols = self._recommender.profile['numeric_cols']
        cols = [c for c in cols if c in df.columns]

        numeric_df = df[cols].dropna()
        if len(numeric_df) < 5:
            print("  警告: PCA数据不足(需要≥5行)")
            return None, {}

        # 标准化 + PCA
        scaler = StandardScaler()
        scaled = scaler.fit_transform(numeric_df.values)
        pca = PCA(n_components=min(len(cols), 2))
        pca.fit(scaled)
        scores = pca.transform(scaled)
        loadings = pca.components_.T * np.sqrt(pca.explained_variance_ratio_)

        # 分组列
        if group_col is None:
            groups = self._recommender.profile['group_cols']
            group_col = groups[0] if groups else None

        if mode == 'clustermap':
            return self._plot_clustermap(numeric_df, cols, group_col)
        elif mode == 'scores':
            return self._plot_pca_scores(scores, pca, df, group_col, numeric_df.index)
        elif mode == 'loadings':
            return self._plot_pca_loadings(loadings, pca, cols)
        else:  # biplot
            return self._plot_pca_biplot(scores, loadings, pca, df, group_col,
                                          numeric_df.index, cols)

    def _plot_pca_biplot(self, scores, loadings, pca, df, group_col, index, cols):
        """PCA双标图 + 95%CI椭圆 + adjustText标签"""
        fig, ax = plt.subplots(figsize=StylePresets.figure_size('single', self.style))
        palette = StylePresets.get_palette()

        if group_col and group_col in df.columns:
            groups = df.loc[index, group_col].unique()
            for i, g in enumerate(groups):
                mask = df.loc[index, group_col] == g
                color = palette[i % len(palette)]
                ax.scatter(scores[mask, 0], scores[mask, 1], c=color, s=30,
                          alpha=0.7, label=str(g), edgecolors='white', linewidth=0.5)
                # 95% CI 椭圆
                if mask.sum() >= 3:
                    from matplotlib.patches import Ellipse
                    mean_x, mean_y = scores[mask, 0].mean(), scores[mask, 1].mean()
                    std_x, std_y = scores[mask, 0].std(), scores[mask, 1].std()
                    ellipse = Ellipse((mean_x, mean_y), 4*std_x, 4*std_y,
                                     fill=False, color=color, linewidth=1,
                                     linestyle='--', alpha=0.6)
                    ax.add_patch(ellipse)
            ax.legend(frameon=True, fontsize=8)
        else:
            ax.scatter(scores[:, 0], scores[:, 1], c=palette[0], s=30,
                      alpha=0.7, edgecolors='white', linewidth=0.5)

        # 载荷箭头
        texts = []
        scale = np.abs(scores).max() / np.abs(loadings).max() * 0.8
        for j, col in enumerate(cols):
            ax.annotate('', xy=(loadings[j, 0]*scale, loadings[j, 1]*scale),
                       xytext=(0, 0),
                       arrowprops=dict(arrowstyle='->', color='#CC0000', lw=1.2))
            txt = ax.text(loadings[j, 0]*scale*1.15, loadings[j, 1]*scale*1.15,
                         get_label(col), fontsize=7, color='#CC0000', ha='center')
            texts.append(txt)

        # adjustText防重叠
        if _HAS_ADJUSTTEXT and texts:
            adjust_text(texts, arrowprops=dict(arrowstyle='->', color='gray', lw=0.5))

        var_ratio = pca.explained_variance_ratio_
        ax.set_xlabel(f'PC1 ({var_ratio[0]*100:.1f}%)')
        ax.set_ylabel(f'PC2 ({var_ratio[1]*100:.1f}%)')
        ax.axhline(y=0, color='gray', linewidth=0.5, linestyle='--')
        ax.axvline(x=0, color='gray', linewidth=0.5, linestyle='--')

        plt.tight_layout()
        meta = {'variance_ratio': var_ratio, 'loadings_cols': cols}
        save_figure(fig, 'pca_biplot', self.output_dir)
        return fig, meta

    def _plot_pca_scores(self, scores, pca, df, group_col, index):
        """PCA得分图"""
        fig, ax = plt.subplots(figsize=StylePresets.figure_size('single', self.style))
        palette = StylePresets.get_palette()
        var_ratio = pca.explained_variance_ratio_

        if group_col and group_col in df.columns:
            groups = df.loc[index, group_col].unique()
            for i, g in enumerate(groups):
                mask = df.loc[index, group_col] == g
                ax.scatter(scores[mask, 0], scores[mask, 1],
                          c=palette[i % len(palette)], s=40, alpha=0.7,
                          label=str(g), edgecolors='white', linewidth=0.5)
            ax.legend(frameon=True)
        else:
            ax.scatter(scores[:, 0], scores[:, 1], c=palette[0], s=40, alpha=0.7)

        ax.set_xlabel(f'PC1 ({var_ratio[0]*100:.1f}%)')
        ax.set_ylabel(f'PC2 ({var_ratio[1]*100:.1f}%)')
        ax.axhline(0, color='gray', linewidth=0.5, linestyle='--')
        ax.axvline(0, color='gray', linewidth=0.5, linestyle='--')
        plt.tight_layout()
        meta = {'variance_ratio': var_ratio}
        save_figure(fig, 'pca_scores', self.output_dir)
        return fig, meta

    def _plot_pca_loadings(self, loadings, pca, cols):
        """PCA载荷图"""
        fig, ax = plt.subplots(figsize=StylePresets.figure_size('single', self.style))
        palette = StylePresets.get_palette()

        texts = []
        for j, col in enumerate(cols):
            ax.scatter(loadings[j, 0], loadings[j, 1], c=palette[j % len(palette)],
                      s=50, edgecolors='black', linewidth=0.5, zorder=3)
            txt = ax.text(loadings[j, 0]*1.1, loadings[j, 1]*1.1,
                         get_label(col), fontsize=8, ha='center')
            texts.append(txt)

        if _HAS_ADJUSTTEXT and texts:
            adjust_text(texts, arrowprops=dict(arrowstyle='->', color='gray', lw=0.5))

        theta = np.linspace(0, 2*np.pi, 100)
        ax.plot(np.cos(theta), np.sin(theta), 'k--', linewidth=0.5, alpha=0.5)
        ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)')
        ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)')
        ax.set_aspect('equal')
        plt.tight_layout()
        meta = {'variance_ratio': pca.explained_variance_ratio_}
        save_figure(fig, 'pca_loadings', self.output_dir)
        return fig, meta

    def _plot_clustermap(self, numeric_df, cols, group_col):
        """聚类热图 (HCA + Heatmap)"""
        # 标准化
        scaler = StandardScaler()
        scaled = pd.DataFrame(
            scaler.fit_transform(numeric_df.values),
            columns=[get_label(c) for c in cols],
            index=numeric_df.index
        )

        if group_col and group_col in self.df.columns:
            row_colors = self.df.loc[numeric_df.index, group_col].map(
                {g: TABLEAU_10[i % len(TABLEAU_10)]
                 for i, g in enumerate(self.df[group_col].unique())}
            )
        else:
            row_colors = None

        g = sns.clustermap(scaled, cmap='RdBu_r', center=0,
                           row_colors=row_colors,
                           figsize=StylePresets.figure_size('double', self.style),
                           linewidths=0.3, annot=False,
                           dendrogram_ratio=(0.15, 0.15),
                           cbar_pos=(0.02, 0.8, 0.03, 0.15))
        plt.suptitle('Hierarchical Cluster Analysis', y=1.02)

        meta = {'method': 'Ward', 'distance': 'Euclidean'}
        g.savefig(os.path.join(self.output_dir, 'clustermap.png'),
                  dpi=300, bbox_inches='tight')
        return g.fig, meta

    # ==================== 需求6: 热力图 ====================

    def plot_heatmap(self, data=None, method='pearson', clustered=False,
                     significance_threshold=0.05, mask_upper=True):
        """
        相关性热力图 / 聚类热力图

        Parameters
        ----------
        data : DataFrame or None (使用self.df的数值列)
        method : 'pearson' | 'spearman'
        clustered : bool, 是否使用聚类排序
        significance_threshold : float
        mask_upper : bool, 是否遮蔽上三角
        """
        df = data if data is not None else self.df
        numeric_cols = self._recommender.profile['numeric_cols']
        numeric_cols = [c for c in numeric_cols if c in df.columns]

        if len(numeric_cols) < 3:
            print("  警告: 数值列不足(需要≥3)")
            return None, {}

        corr_df = df[numeric_cols].corr(method=method)

        if clustered:
            return self._plot_clustered_heatmap(corr_df, numeric_cols, method)
        else:
            return self._plot_correlation_heatmap(corr_df, numeric_cols, method, mask_upper)

    def _plot_correlation_heatmap(self, corr_df, cols, method, mask_upper):
        """标准相关性热力图"""
        fig_w, fig_h = StylePresets.figure_size('single', self.style)
        n = len(cols)
        fig_size = max(fig_w, fig_h) * n / 6
        fig, ax = plt.subplots(figsize=(fig_size, fig_size))

        mask = np.triu(np.ones_like(corr_df, dtype=bool), k=1) if mask_upper else None
        labels = [get_label(c) for c in cols]

        sns.heatmap(corr_df, mask=mask, annot=True, fmt='.2f',
                    cmap='RdBu_r', center=0, vmin=-1, vmax=1,
                    xticklabels=labels, yticklabels=labels,
                    square=True, linewidths=0.5,
                    annot_kws={'fontsize': 7},
                    cbar_kws={'shrink': 0.8, 'label': f'{method.capitalize()} r'},
                    ax=ax)

        ax.set_title(f'{method.capitalize()} Correlation Matrix', fontsize=10)
        plt.tight_layout()

        meta = {'method': method, 'n_vars': n}
        save_figure(fig, f'heatmap_{method}', self.output_dir)
        caption = self._caption_gen.generate('heatmap', meta, language=self.language)
        return fig, meta

    def _plot_clustered_heatmap(self, corr_df, cols, method):
        """聚类排序热力图"""
        labels = [get_label(c) for c in cols]
        g = sns.clustermap(corr_df, annot=True, fmt='.2f',
                           cmap='RdBu_r', center=0, vmin=-1, vmax=1,
                           xticklabels=labels, yticklabels=labels,
                           linewidths=0.5, figsize=StylePresets.figure_size('double', self.style),
                           dendrogram_ratio=(0.15, 0.15),
                           cbar_kws={'label': f'{method.capitalize()} r'})

        meta = {'method': method, 'clustered': True}
        g.savefig(os.path.join(self.output_dir, f'heatmap_{method}_clustered.png'),
                  dpi=300, bbox_inches='tight')
        return g.fig, meta

    # ==================== 需求7: Sankey桑基图 ====================

    def plot_sankey(self, sources=None, targets=None, values=None,
                    labels=None, title='Sankey Diagram'):
        """
        桑基图 (碳流可视化)

        自动模式: 从数据推断碳流
        手动模式: 指定sources/targets/values/labels
        """
        if _HAS_PLOTLY:
            return self._plot_sankey_plotly(sources, targets, values, labels, title)
        else:
            return self._plot_sankey_mpl(sources, targets, values, labels, title)

    def _plot_sankey_plotly(self, sources, targets, values, labels, title):
        """plotly桑基图"""
        # 自动推断碳流
        if sources is None:
            sources, targets, values, labels = self._infer_carbon_flows()

        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15, thickness=20,
                label=labels,
                color=[TABLEAU_10[i % len(TABLEAU_10)] for i in range(len(labels))],
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color='rgba(150,150,150,0.4)',
            )
        )])
        fig.update_layout(title_text=title, font_size=12, width=800, height=500)

        # 保存HTML
        html_path = os.path.join(self.output_dir, 'sankey.html')
        fig.write_html(html_path)

        # 保存PNG (需要kaleido)
        if _HAS_KALEIDO:
            png_path = os.path.join(self.output_dir, 'sankey.png')
            fig.write_image(png_path, width=800, height=500, scale=3)

        meta = {'labels': labels, 'n_links': len(sources), 'html_path': html_path}
        return fig, meta

    def _plot_sankey_mpl(self, sources, targets, values, labels, title):
        """matplotlib回退: 简化的流向图"""
        if sources is None:
            sources, targets, values, labels = self._infer_carbon_flows()

        fig, ax = plt.subplots(figsize=StylePresets.figure_size('double', self.style))
        n = len(labels)
        node_y = np.linspace(0.9, 0.1, n)
        node_x = [0.1] * n  # 简化: 单列

        # 绘制节点
        for i, label in enumerate(labels):
            ax.add_patch(FancyBboxPatch((node_x[i] - 0.04, node_y[i] - 0.02),
                                        0.08, 0.04,
                                        boxstyle="round,pad=0.01",
                                        facecolor=TABLEAU_10[i % len(TABLEAU_10)],
                                        edgecolor='black', linewidth=0.5,
                                        alpha=0.8, transform=ax.transAxes))
            ax.text(node_x[i], node_y[i], label, ha='center', va='center',
                   fontsize=7, transform=ax.transAxes)

        # 绘制链接
        max_val = max(values) if values else 1
        for s, t, v in zip(sources, targets, values):
            lw = v / max_val * 5 + 0.5
            ax.annotate('', xy=(node_x[t] + 0.04, node_y[t]),
                       xytext=(node_x[s] + 0.12, node_y[s]),
                       arrowprops=dict(arrowstyle='->', color='#888888',
                                      lw=lw, connectionstyle='arc3,rad=0.2'),
                       transform=ax.transAxes)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        ax.set_title(title, fontsize=10)

        meta = {'labels': labels, 'n_links': len(sources), 'fallback': 'matplotlib'}
        save_figure(fig, 'sankey', self.output_dir)
        return fig, meta

    def _infer_carbon_flows(self):
        """从数据推断碳流"""
        df = self.df
        sources, targets, values = [], [], []
        labels = ['Input Carbon']

        # 气相碳
        if 'CH4平均值' in df.columns:
            ch4_mean = pd.to_numeric(df['CH4平均值'], errors='coerce').mean()
            if not np.isnan(ch4_mean) and ch4_mean > 0:
                sources.append(0)
                targets.append(len(labels))
                values.append(ch4_mean)
                labels.append('CH4')

        if 'CO2' in df.columns:
            co2_mean = pd.to_numeric(df['CO2'], errors='coerce').mean()
            if not np.isnan(co2_mean) and co2_mean > 0:
                sources.append(0)
                targets.append(len(labels))
                values.append(co2_mean)
                labels.append('CO2')

        # 液相碳
        if 'TOC（mg/L)' in df.columns:
            toc_mean = pd.to_numeric(df['TOC（mg/L)'], errors='coerce').mean()
            if not np.isnan(toc_mean) and toc_mean > 0:
                sources.append(0)
                targets.append(len(labels))
                values.append(toc_mean)
                labels.append('TOC')

        if 'IC(mg/L)' in df.columns:
            ic_mean = pd.to_numeric(df['IC(mg/L)'], errors='coerce').mean()
            if not np.isnan(ic_mean) and ic_mean > 0:
                sources.append(0)
                targets.append(len(labels))
                values.append(ic_mean)
                labels.append('IC')

        # 固相碳
        if '固总碳（g/kg)' in df.columns:
            solid_mean = pd.to_numeric(df['固总碳（g/kg)'], errors='coerce').mean()
            if not np.isnan(solid_mean) and solid_mean > 0:
                sources.append(0)
                targets.append(len(labels))
                values.append(solid_mean)
                labels.append('Solid C')

        if not values:
            sources = [0, 0, 0]
            targets = [1, 2, 3]
            values = [50, 30, 20]
            labels = ['Input', 'Gas', 'Liquid', 'Solid']

        return sources, targets, values, labels

    # ==================== 需求8: 碳流图 ====================

    def plot_carbon_flow(self, phase_data=None, fluxes=None):
        """
        碳流图 (增强版碳平衡示意图)

        Parameters
        ----------
        phase_data : dict, {'gas': val, 'liquid': val, 'solid': val}
        fluxes : list of dict, [{'source': str, 'target': str, 'value': float}]
        """
        if _HAS_PLOTLY and fluxes:
            return self._plot_carbon_flow_sankey(phase_data, fluxes)
        return self._plot_carbon_flow_schematic(phase_data)

    def _plot_carbon_flow_sankey(self, phase_data, fluxes):
        """碳流Sankey图"""
        labels = list(set(f['source'] for f in fluxes) | set(f['target'] for f in fluxes))
        label_map = {l: i for i, l in enumerate(labels)}
        sources = [label_map[f['source']] for f in fluxes]
        targets = [label_map[f['target']] for f in fluxes]
        values = [f['value'] for f in fluxes]
        return self._plot_sankey_plotly(sources, targets, values, labels, 'Carbon Flow')

    def _plot_carbon_flow_schematic(self, phase_data):
        """碳流示意图 (增强版matplotlib)"""
        df = self.df
        if phase_data is None:
            phase_data = {}
            for key, col in [('gas', '气相碳'), ('liquid', '液相碳'), ('solid', '固相碳')]:
                if col in df.columns:
                    phase_data[key] = pd.to_numeric(df[col], errors='coerce').mean()

        fig, ax = plt.subplots(figsize=StylePresets.figure_size('single', self.style))

        # 节点
        node_props = {
            'Input':   {'pos': (0.5, 0.85), 'color': '#333333'},
            'CH4+CO2': {'pos': (0.2, 0.55), 'color': PHASE_COLORS.get('气相', '#4E79A7')},
            'TOC/COD': {'pos': (0.5, 0.55), 'color': PHASE_COLORS.get('液相', '#F28E2B')},
            'Sediment': {'pos': (0.8, 0.55), 'color': PHASE_COLORS.get('固相', '#E15759')},
        }

        total = sum(phase_data.values()) if phase_data else 1
        for name, props in node_props.items():
            ax.add_patch(FancyBboxPatch(
                (props['pos'][0] - 0.1, props['pos'][1] - 0.04),
                0.2, 0.08, boxstyle="round,pad=0.01",
                facecolor=props['color'], edgecolor='black',
                linewidth=1, alpha=0.8, transform=ax.transAxes))
            ax.text(props['pos'][0], props['pos'][1], name,
                   ha='center', va='center', fontsize=9, fontweight='bold',
                   color='white', transform=ax.transAxes)

        # 比例标签
        phase_labels = {'CH4+CO2': phase_data.get('gas', 0),
                        'TOC/COD': phase_data.get('liquid', 0),
                        'Sediment': phase_data.get('solid', 0)}
        for name, val in phase_labels.items():
            if val > 0:
                pct = val / total * 100
                props = node_props[name]
                ax.text(props['pos'][0], props['pos'][1] - 0.08,
                       f'{pct:.1f}%', ha='center', va='top',
                       fontsize=8, transform=ax.transAxes)

        # 箭头
        for target in ['CH4+CO2', 'TOC/COD', 'Sediment']:
            start = node_props['Input']['pos']
            end = node_props[target]['pos']
            ax.annotate('', xy=(end[0], end[1] + 0.04),
                       xytext=(start[0], start[1] - 0.04),
                       arrowprops=dict(arrowstyle='->', color='#555555', lw=1.5),
                       transform=ax.transAxes)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        meta = {'phase_data': phase_data}
        save_figure(fig, 'carbon_flow', self.output_dir)
        return fig, meta

    # ==================== 需求9: 时空分布图 ====================

    def plot_spatiotemporal(self, variables=None, mode='line', x_col=None, group_col=None):
        """
        时空分布图

        mode: 'line' | 'heatmap' | 'contour'
        """
        df = self.df
        if variables is None:
            variables = self._recommender.profile['phase_cols'][:4]
        variables = [v for v in variables if v in df.columns]

        if not variables:
            print("  警告: 无有效变量")
            return None, {}

        if mode == 'heatmap':
            return self._plot_spatial_heatmap(variables, x_col)
        else:
            return self._plot_spatial_lines(variables, x_col, group_col)

    def _plot_spatial_lines(self, variables, x_col, group_col):
        """沿程折线图 (增强版)"""
        df = self.df
        fig, ax = plt.subplots(figsize=StylePresets.figure_size('single', self.style))
        palette = StylePresets.get_palette()

        if x_col and x_col in df.columns:
            x = df[x_col]
        else:
            x = range(len(df))

        if group_col and group_col in df.columns:
            groups = df[group_col].unique()
            for i, var in enumerate(variables):
                for j, g in enumerate(groups):
                    mask = df[group_col] == g
                    color = palette[(i * len(groups) + j) % len(palette)]
                    label = f'{get_label(var)} ({g})'
                    x_vals = x[mask] if hasattr(x, '__getitem__') else np.arange(len(df))[mask]
                    ax.plot(x_vals, df.loc[mask, var], marker='o', markersize=4,
                           linewidth=1.2, color=color, label=label, alpha=0.8)
        else:
            for i, var in enumerate(variables):
                color = palette[i % len(palette)]
                ax.plot(x, df[var], marker='o', markersize=4,
                       linewidth=1.2, color=color, label=get_label(var), alpha=0.8)

        ax.set_xlabel(get_label(x_col) if x_col else 'Sample')
        ax.set_ylabel('Concentration')
        ax.legend(frameon=True, fontsize=7, ncol=min(2, len(variables)))
        plt.tight_layout()

        meta = {'variables': variables, 'mode': 'line', 'x_col': x_col}
        save_figure(fig, 'spatiotemporal_line', self.output_dir)
        return fig, meta

    def _plot_spatial_heatmap(self, variables, x_col):
        """空间×时间热力图"""
        df = self.df
        data_matrix = df[variables].T
        data_matrix.index = [get_label(v) for v in variables]

        fig_h = max(3, len(variables) * 0.6)
        fig_w = StylePresets.figure_size('single', self.style)[0]
        fig, ax = plt.subplots(figsize=(fig_w, fig_h))

        sns.heatmap(data_matrix, cmap='YlOrRd', annot=True, fmt='.1f',
                    linewidths=0.5, ax=ax,
                    cbar_kws={'shrink': 0.8, 'label': 'Concentration'})

        if x_col and x_col in df.columns:
            ax.set_xticklabels(df[x_col], rotation=45, ha='right', fontsize=7)
        ax.set_xlabel('Sample')
        ax.set_ylabel('')
        plt.tight_layout()

        meta = {'variables': variables, 'mode': 'heatmap'}
        save_figure(fig, 'spatiotemporal_heatmap', self.output_dir)
        return fig, meta

    # ==================== 需求10: 多相态耦合图 ====================

    def plot_multiphase_coupling(self, panels=None):
        """
        多相态耦合图 (多面板 + 共享x轴)

        Parameters
        ----------
        panels : list of dict or None
            [{'type': 'box'|'line', 'variables': [...], 'phase': 'gas'|'liquid'|'solid'}]
        """
        df = self.df

        if panels is None:
            panels = []
            phase_configs = [
                ('gas', ['CH4平均值', 'CO2'], 'Boxplot'),
                ('liquid', ['TOC（mg/L)', 'COD（mg/L)', 'DO(mg/L)'], 'Boxplot'),
                ('solid', ['固总碳（g/kg)', '有机碳（g/kg)'], 'Bar'),
            ]
            for phase, candidates, ptype in phase_configs:
                found = [v for v in candidates if v in df.columns]
                if found:
                    panels.append({'type': ptype.lower(), 'variables': found, 'phase': phase})

        if not panels:
            print("  警告: 无有效面板数据")
            return None, {}

        n_panels = len(panels)
        fig_h = StylePresets.figure_size('single', self.style)[1]
        fig, axes = plt.subplots(n_panels, 1,
                                  figsize=StylePresets.figure_size('double', self.style),
                                  sharex=True, squeeze=False)
        axes = axes[:, 0]
        palette = StylePresets.get_palette()

        metadata = {'panels': [], 'n_panels': n_panels}

        for i, panel in enumerate(panels):
            ax = axes[i]
            ptype = panel.get('type', 'box')
            variables = [v for v in panel.get('variables', []) if v in df.columns]
            phase = panel.get('phase', '')
            phase_color = PHASE_COLORS.get(phase, palette[0])

            if not variables:
                continue

            if ptype == 'box':
                plot_data = df[variables].melt(var_name='Variable', value_name='Value')
                plot_data['Variable'] = plot_data['Variable'].map(get_label)
                sns.boxplot(data=plot_data, x='Variable', y='Value', ax=ax,
                           color=phase_color, width=0.6, linewidth=0.8, fliersize=2)
            elif ptype == 'bar':
                means = df[variables].mean()
                stds = df[variables].std()
                labels = [get_label(v) for v in variables]
                x_pos = range(len(variables))
                ax.bar(x_pos, means, yerr=stds, color=phase_color,
                      capsize=3, linewidth=0.8, edgecolor='black', alpha=0.8)
                ax.set_xticks(x_pos)
                ax.set_xticklabels(labels, rotation=0)
            elif ptype == 'line':
                for j, var in enumerate(variables):
                    ax.plot(range(len(df)), df[var], marker='o', markersize=3,
                           color=palette[j % len(palette)],
                           label=get_label(var), linewidth=1)
                ax.legend(fontsize=7, frameon=True)

            phase_label = {'gas': 'Gas Phase', 'liquid': 'Liquid Phase',
                          'solid': 'Solid Phase'}.get(phase, phase)
            ax.set_ylabel(f'{phase_label}\n({variables[0]})' if variables else phase_label)
            ax.set_xlabel('')

            metadata['panels'].append({
                'phase': phase, 'type': ptype,
                'variables': variables, 'n_obs': len(df)
            })

        axes[-1].set_xlabel('Variable')

        # 子图标号
        MultiPanelComposer._add_panel_labels(axes.reshape(-1, 1), n_panels, 1, self.style)

        plt.subplots_adjust(hspace=0.1)
        save_figure(fig, 'multiphase_coupling', self.output_dir)
        caption = self._caption_gen.generate('multiphase', metadata, language=self.language)
        return fig, metadata

    # ==================== 回归散点图 ====================

    def plot_regression(self, x_col, y_col, group_col=None, ci=True):
        """散点+回归线+95%CI"""
        df = self.df
        if x_col not in df.columns or y_col not in df.columns:
            print(f"  警告: 列不存在 ({x_col}, {y_col})")
            return None, {}

        data = df[[x_col, y_col]].dropna()
        if group_col and group_col in df.columns:
            data[group_col] = df.loc[data.index, group_col]
        data[x_col] = pd.to_numeric(data[x_col], errors='coerce')
        data[y_col] = pd.to_numeric(data[y_col], errors='coerce')
        data = data.dropna()

        if len(data) < 5:
            print("  警告: 回归数据不足")
            return None, {}

        fig, ax = plt.subplots(figsize=StylePresets.figure_size('single', self.style))
        palette = StylePresets.get_palette()

        if group_col and group_col in data.columns:
            groups = data[group_col].unique()
            for i, g in enumerate(groups):
                sub = data[data[group_col] == g]
                ax.scatter(sub[x_col], sub[y_col], c=palette[i % len(palette)],
                          s=30, alpha=0.7, label=str(g), edgecolors='white', linewidth=0.5)
            ax.legend(fontsize=7, frameon=True)
        else:
            ax.scatter(data[x_col], data[y_col], c=palette[0], s=30,
                      alpha=0.7, edgecolors='white', linewidth=0.5)

        # 回归线 + CI
        x_vals = data[x_col].values.astype(float)
        y_vals = data[y_col].values.astype(float)
        lr = LinearRegression()
        lr.fit(x_vals, y_vals)
        x_pred = np.linspace(x_vals.min(), x_vals.max(), 100)
        y_pred = lr.predict(x_pred)

        ax.plot(x_pred, y_pred, color='#CC0000', linewidth=1.2, label='Fit')

        if ci and len(data) > 3:
            n = len(data)
            y_hat = lr.predict(x_vals)
            se = np.sqrt(np.sum((y_vals - y_hat)**2) / (n - 2))
            x_mean = x_vals.mean()
            sx = np.sum((x_vals - x_mean)**2)
            t_val = scipy_stats.t.ppf(0.975, n - 2)
            ci_band = t_val * se * np.sqrt(1/n + (x_pred - x_mean)**2 / sx)
            ax.fill_between(x_pred, y_pred - ci_band, y_pred + ci_band,
                           alpha=0.15, color='#CC0000', label='95% CI')

        r2 = r2_score(y_vals, y_hat)
        _, p_value = scipy_stats.pearsonr(x_vals, y_vals)
        eq_str = f'y = {lr.coef_[0]:.3f}x + {lr.intercept_:.3f}'

        stats_text = f'R² = {r2:.3f}\np = {p_value:.4f}\n{eq_str}'
        ax.text(0.05, 0.95, stats_text, transform=ax.transAxes,
               fontsize=7, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        ax.set_xlabel(get_label(x_col))
        ax.set_ylabel(get_label(y_col))
        plt.tight_layout()

        meta = {'x': x_col, 'y': y_col, 'r2': r2, 'p': p_value, 'equation': eq_str}
        save_figure(fig, f'regression_{x_col}_{y_col}', self.output_dir)
        return fig, meta

    # ==================== 委托原ThesisPlotter ====================

    def legacy(self):
        """委托调用原ThesisPlotter的全部12种图"""
        self._legacy_plotter.generate_all_figures()


# ============================================================================
# EnhancedCaptionGenerator - 数据驱动图注
# ============================================================================
class EnhancedCaptionGenerator:
    """增强版图注生成器：支持数据驱动 + 中英文 + 自动编号"""

    def generate(self, fig_type, fig_data, stats_results=None,
                 language='zh', figure_number=None):
        """
        生成图注

        Parameters
        ----------
        fig_type : str
        fig_data : dict
        stats_results : dict, 可选的统计结果
        language : 'zh' | 'en'
        figure_number : int or None
        """
        num = f'{figure_number}' if figure_number else 'X'
        stats = stats_results or fig_data.get('tests', {})

        generators = {
            'multivariate': self._caption_multivariate,
            'pca_biplot': self._caption_pca,
            'heatmap': self._caption_heatmap,
            'sankey': self._caption_sankey,
            'carbon_flow': self._caption_carbon_flow,
            'spatiotemporal': self._caption_spatiotemporal,
            'multiphase': self._caption_multiphase,
            'regression': self._caption_regression,
        }

        gen = generators.get(fig_type)
        if gen:
            return gen(fig_data, stats, language, num)
        return ''

    @staticmethod
    def _caption_multivariate(data, stats, lang, num):
        variables = data.get('variables', [])
        group_col = data.get('group_col', '')
        kind = data.get('kind', 'box')
        var_names = ', '.join([get_label(v) for v in variables[:4]])
        kind_zh = {'violin': '小提琴图', 'box': '箱线图', 'strip': '散点图', 'raincloud': '云雨图'}
        kind_en = {'violin': 'Violin plot', 'box': 'Box plot', 'strip': 'Strip plot', 'raincloud': 'Raincloud plot'}

        test_info = ''
        for var, s in stats.items():
            p = s.get('p_value', 1)
            method = s.get('method', 'Mann-Whitney U')
            stars = significance_stars(p)
            test_info += f'{get_label(var)}: {method}, p={p:.4f} ({stars}). '

        if lang == 'zh':
            return (f'图{num} {var_names}的{kind_zh.get(kind, "统计图")}\n'
                    f'按{group_col}分组比较。样本量n={data.get("n_obs", "X")}。'
                    f'{test_info}')
        return (f'Fig. {num} {kind_en.get(kind, "Statistical plot")} of {var_names}\n'
                f'Grouped by {group_col}. n={data.get("n_obs", "X")}. {test_info}')

    @staticmethod
    def _caption_pca(data, stats, lang, num):
        var_ratio = data.get('variance_ratio', [0, 0])
        if lang == 'zh':
            return (f'图{num} 主成分分析(PCA)双标图\n'
                    f'PC1和PC2分别解释了{var_ratio[0]*100:.1f}%和'
                    f'{var_ratio[1]*100:.1f}%的方差。'
                    f'箭头表示变量载荷方向和大小。')
        return (f'Fig. {num} PCA biplot\n'
                f'PC1 and PC2 explain {var_ratio[0]*100:.1f}% and '
                f'{var_ratio[1]*100:.1f}% of variance. '
                f'Arrows indicate variable loadings.')

    @staticmethod
    def _caption_heatmap(data, stats, lang, num):
        method = data.get('method', 'Pearson')
        if lang == 'zh':
            return (f'图{num} {method.capitalize()}相关性矩阵\n'
                    f'颜色深浅表示相关系数大小，红色为正相关，蓝色为负相关。')
        return (f'Fig. {num} {method.capitalize()} correlation matrix\n'
                f'Color intensity indicates correlation magnitude. '
                f'Red=positive, blue=negative.')

    @staticmethod
    def _caption_sankey(data, stats, lang, num):
        n_links = data.get('n_links', 0)
        if lang == 'zh':
            return f'图{num} 碳流桑基图\n共{n_links}条流线，展示碳在不同相态间的分配。'
        return f'Fig. {num} Carbon flow Sankey diagram\n{n_links} flows showing carbon distribution.'

    @staticmethod
    def _caption_carbon_flow(data, stats, lang, num):
        if lang == 'zh':
            return f'图{num} 碳平衡示意图\n展示气相、液相、固相碳的相对比例。'
        return f'Fig. {num} Carbon balance schematic\nShowing relative proportions of gas/liquid/solid carbon.'

    @staticmethod
    def _caption_spatiotemporal(data, stats, lang, num):
        variables = data.get('variables', [])
        var_names = ', '.join([get_label(v) for v in variables[:4]])
        mode = data.get('mode', 'line')
        if lang == 'zh':
            mode_zh = {'line': '沿程变化趋势', 'heatmap': '时空分布热力图'}
            return f'图{num} {var_names}的{mode_zh.get(mode, "时空分布")}\n展示沿采样点的浓度变化。'
        mode_en = {'line': 'spatial variation', 'heatmap': 'spatiotemporal heatmap'}
        return f'Fig. {num} {mode_en.get(mode, "distribution")} of {var_names}\n'

    @staticmethod
    def _caption_multiphase(data, stats, lang, num):
        n_panels = data.get('n_panels', 0)
        panels = data.get('panels', [])
        if lang == 'zh':
            desc = '；'.join([f"({chr(97+i)}){p.get('phase','')}" for i, p in enumerate(panels)])
            return (f'图{num} 多相态碳污染物耦合图\n'
                    f'共{n_panels}个子面板：{desc}。共享x轴便于对比。')
        desc = '; '.join([f"({chr(97+i)}){p.get('phase','')}" for i, p in enumerate(panels)])
        return (f'Fig. {num} Multi-phase carbon pollutant coupling\n'
                f'{n_panels} panels: {desc}. Shared x-axis.')

    @staticmethod
    def _caption_regression(data, stats, lang, num):
        x_var = get_label(data.get('x', 'X'))
        y_var = get_label(data.get('y', 'Y'))
        r2 = data.get('r2', 0)
        p = data.get('p', 1)
        eq = data.get('equation', '')
        if lang == 'zh':
            return (f'图{num} {x_var}与{y_var}的线性回归关系\n'
                    f'实线为拟合线，阴影为95%置信区间。'
                    f'R²={r2:.3f}，p={p:.4f}，{eq}')
        return (f'Fig. {num} Linear regression: {x_var} vs {y_var}\n'
                f'Solid line: fit. Shaded: 95% CI. '
                f'R²={r2:.3f}, p={p:.4f}, {eq}')


# ============================================================================
# CodeGenerator - Origin/R代码模板
# ============================================================================
class CodeGenerator:
    """生成Origin和R代码模板"""

    @staticmethod
    def generate_origin_code(chart_type, columns, group_col=None, **kwargs):
        """生成Origin LabTalk脚本"""
        templates = {
            'boxplot': CodeGenerator._origin_boxplot,
            'scatter': CodeGenerator._origin_scatter,
            'regression': CodeGenerator._origin_regression,
            'heatmap': CodeGenerator._origin_heatmap,
            'bar': CodeGenerator._origin_bar,
            'line': CodeGenerator._origin_line,
            'violin': CodeGenerator._origin_violin,
        }
        gen = templates.get(chart_type, CodeGenerator._origin_generic)
        return gen(columns, group_col, **kwargs)

    @staticmethod
    def generate_r_code(chart_type, columns, group_col=None, **kwargs):
        """生成R ggplot2代码"""
        templates = {
            'boxplot': CodeGenerator._r_boxplot,
            'scatter': CodeGenerator._r_scatter,
            'regression': CodeGenerator._r_regression,
            'heatmap': CodeGenerator._r_heatmap,
            'bar': CodeGenerator._r_bar,
            'line': CodeGenerator._r_line,
            'violin': CodeGenerator._r_violin,
        }
        gen = templates.get(chart_type, CodeGenerator._r_generic)
        return gen(columns, group_col, **kwargs)

    @staticmethod
    def export_csv_for_origin(data, filepath):
        """导出为Origin兼容的CSV"""
        data.to_csv(filepath, index=False, encoding='utf-8-sig')
        return filepath

    # ==================== Origin模板 ====================

    @staticmethod
    def _origin_boxplot(columns, group_col, **kw):
        cols_str = ', '.join(columns)
        gc = group_col or 'Group'
        return f'''// Origin LabTalk - Boxplot
// 1. 导入数据
impASC;  // File > Import > ASCII

// 2. 创建箱线图
// 选择数据列: {cols_str}
// 分组列: {gc}
worksheet -a 1;  // 激活第1个工作表
layer -g boxplot plot_type:=box;
layer -g boxplot group:={gc};
layer -g boxplot columns:=({cols_str});

// 3. 格式化
layer -g boxplot whisker_type:=SD;
layer -g boxplot outlier_symbol:=circle;
layer -g boxplot median_line:=solid;

// 4. 坐标轴标签
 xlabel$("Variable");
 ylabel$("Concentration");

// 5. 添加显著性标注
// 手动添加文本框: *, **, ***

// 6. 导出
// File > Export Graphs > PDF (300 DPI)
'''

    @staticmethod
    def _origin_scatter(columns, group_col, **kw):
        x_col = kw.get('x_col', columns[0] if columns else 'X')
        y_col = kw.get('y_col', columns[1] if len(columns) > 1 else 'Y')
        return f'''// Origin LabTalk - Scatter Plot
// 1. 导入数据
impASC;

// 2. 创建散点图
worksheet -a 1;
layer -g scatter x:={x_col} y:={y_col};

// 3. 添加回归线
layer -g scatter fit:=linear;
layer -g scatter conf_band:=95;
layer -g scatter show_equation:=1;
layer -g scatter show_r2:=1;

// 4. 格式化
layer -g scatter symbol_size:=8;
layer -g scatter symbol_color:=blue;

// 5. 坐标轴
 xlabel$("{x_col}");
 ylabel$("{y_col}");
'''

    @staticmethod
    def _origin_regression(columns, group_col, **kw):
        return CodeGenerator._origin_scatter(columns, group_col, **kw)

    @staticmethod
    def _origin_heatmap(columns, **kw):
        cols_str = ', '.join(columns)
        return f'''// Origin LabTalk - Heatmap
// 1. 计算相关矩阵
// Data > Statistics > Correlation
// 选择列: {cols_str}
// 方法: Pearson

// 2. 创建热图
// 选择相关矩阵结果
worksheet -a 2;  // 激活结果表
layer -g heatmap;

// 3. 颜色映射
layer -g heatmap colormap:=red_blue;  // 红蓝发散
layer -g heatmap range:=-1 1;
layer -g heatmap show_values:=1;

// 4. 格式化
 layer -g heatmap annotation_fmt:=.2f;
'''

    @staticmethod
    def _origin_bar(columns, group_col, **kw):
        cols_str = ', '.join(columns)
        return f'''// Origin LabTalk - Bar Chart
// 1. 导入数据
impASC;

// 2. 创建柱状图
worksheet -a 1;
layer -g bar columns:=({cols_str});
layer -g bar errorbar:=SD;
layer -g bar cap_size:=5;

// 3. 格式化
 layer -g bar border:=solid;
 layer -g bar pattern:=none;

// 4. 坐标轴
 xlabel$("Category");
 ylabel$("Value");
'''

    @staticmethod
    def _origin_line(columns, group_col, **kw):
        x_col = kw.get('x_col', 'X')
        cols_str = ', '.join(columns)
        return f'''// Origin LabTalk - Line Plot
// 1. 导入数据
impASC;

// 2. 创建折线图
worksheet -a 1;
layer -g line x:={x_col} y:=({cols_str});
layer -g line symbol:=circle;
layer -g line symbol_size:=5;

// 3. 格式化
 layer -g line connect:=straight;
 layer -g line width:=1.5;
'''

    @staticmethod
    def _origin_violin(columns, group_col, **kw):
        cols_str = ', '.join(columns)
        return f'''// Origin LabTalk - Violin Plot (Origin 2022+)
// 1. 导入数据
impASC;

// 2. 创建小提琴图
// 需要Origin 2022或更高版本
worksheet -a 1;
layer -g violin columns:=({cols_str});
layer -g violin bandwidth:=auto;
layer -g violin show_box:=1;
layer -g violin show_median:=1;
'''

    @staticmethod
    def _origin_generic(columns, group_col, **kw):
        return '// Origin LabTalk - 通用图表\n// 请手动创建图表并设置格式\n'

    # ==================== R ggplot2模板 ====================

    @staticmethod
    def _r_boxplot(columns, group_col, **kw):
        gc = group_col or 'Group'
        cols_r = '", "'.join(columns)
        return f'''# R ggplot2 - Boxplot
library(ggplot2)

df <- read.csv("data.csv", fileEncoding="UTF-8")

# 转换为长格式
library(tidyr)
df_long <- pivot_longer(df, cols = c("{cols_r}"),
                        names_to = "Variable", values_to = "Value")

ggplot(df_long, aes(x = {gc}, y = Value, fill = {gc})) +
  geom_boxplot(width = 0.6, outlier.size = 1.5) +
  facet_wrap(~Variable, scales = "free_y") +
  theme_bw() +
  theme(
    text = element_text(family = "Arial", size = 10),
    panel.grid.minor = element_blank(),
    legend.position = "none"
  ) +
  labs(x = "", y = "Concentration")

ggsave("boxplot.pdf", width = 7, height = 5, dpi = 600)
'''

    @staticmethod
    def _r_scatter(columns, group_col, **kw):
        x_col = kw.get('x_col', columns[0] if columns else 'X')
        y_col = kw.get('y_col', columns[1] if len(columns) > 1 else 'Y')
        color_aes = f', color = {group_col}' if group_col else ''
        return f'''# R ggplot2 - Scatter Plot
library(ggplot2)

df <- read.csv("data.csv", fileEncoding = "UTF-8")

ggplot(df, aes(x = {x_col}, y = {y_col}{color_aes})) +
  geom_point(size = 3, alpha = 0.7) +
  theme_bw() +
  theme(
    text = element_text(family = "Arial", size = 10),
    panel.grid.minor = element_blank()
  ) +
  labs(x = "{x_col}", y = "{y_col}")

ggsave("scatter.pdf", width = 5, height = 4, dpi = 600)
'''

    @staticmethod
    def _r_regression(columns, group_col, **kw):
        x_col = kw.get('x_col', columns[0] if columns else 'X')
        y_col = kw.get('y_col', columns[1] if len(columns) > 1 else 'Y')
        color_aes = f', color = {group_col}' if group_col else ''
        return f'''# R ggplot2 - Regression
library(ggplot2)

df <- read.csv("data.csv", fileEncoding = "UTF-8")

ggplot(df, aes(x = {x_col}, y = {y_col}{color_aes})) +
  geom_point(size = 3, alpha = 0.7) +
  geom_smooth(method = "lm", se = TRUE, alpha = 0.15) +
  stat_regline_equation(label.x = 0.05, label.y = 0.95) +
  theme_bw() +
  theme(
    text = element_text(family = "Arial", size = 10),
    panel.grid.minor = element_blank()
  ) +
  labs(x = "{x_col}", y = "{y_col}")

ggsave("regression.pdf", width = 5, height = 4, dpi = 600)
'''

    @staticmethod
    def _r_heatmap(columns, **kw):
        cols_r = '", "'.join(columns)
        return f'''# R ggplot2 - Correlation Heatmap
library(ggplot2)
library(reshape2)

df <- read.csv("data.csv", fileEncoding = "UTF-8")
cor_mat <- cor(df[, c("{cols_r}")], use = "complete.obs")
cor_melt <- melt(cor_mat)

ggplot(cor_melt, aes(x = Var1, y = Var2, fill = value)) +
  geom_tile(color = "white") +
  geom_text(aes(label = sprintf("%.2f", value)), size = 3) +
  scale_fill_gradient2(low = "#2166AC", mid = "white", high = "#B2182B",
                       midpoint = 0, limits = c(-1, 1)) +
  theme_bw() +
  theme(
    text = element_text(family = "Arial", size = 10),
    axis.text.x = element_text(angle = 45, hjust = 1),
    panel.grid = element_blank()
  ) +
  labs(x = "", y = "", fill = "r")

ggsave("heatmap.pdf", width = 6, height = 5, dpi = 600)
'''

    @staticmethod
    def _r_bar(columns, group_col, **kw):
        cols_r = '", "'.join(columns)
        gc = group_col or 'Group'
        return f'''# R ggplot2 - Bar Chart with Error Bars
library(ggplot2)
library(dplyr)
library(tidyr)

df <- read.csv("data.csv", fileEncoding = "UTF-8")

df_summary <- df %>%
  group_by({gc}) %>%
  summarise(across(c("{cols_r}"), list(mean = mean, sd = sd), .names = "{{.col}}_{{.fn}}"))

ggplot(df_summary, aes(x = {gc}, y = {columns[0]}_mean, fill = {gc})) +
  geom_col(width = 0.6) +
  geom_errorbar(aes(ymin = {columns[0]}_mean - {columns[0]}_sd,
                    ymax = {columns[0]}_mean + {columns[0]}_sd),
                width = 0.2) +
  theme_bw() +
  theme(
    text = element_text(family = "Arial", size = 10),
    legend.position = "none"
  ) +
  labs(x = "", y = "{columns[0]}")

ggsave("barplot.pdf", width = 5, height = 4, dpi = 600)
'''

    @staticmethod
    def _r_line(columns, group_col, **kw):
        x_col = kw.get('x_col', 'X')
        cols_r = '", "'.join(columns)
        return f'''# R ggplot2 - Line Plot
library(ggplot2)
library(tidyr)

df <- read.csv("data.csv", fileEncoding = "UTF-8")
df_long <- pivot_longer(df, cols = c("{cols_r}"),
                        names_to = "Variable", values_to = "Value")

ggplot(df_long, aes(x = {x_col}, y = Value, color = Variable)) +
  geom_line(linewidth = 0.8) +
  geom_point(size = 2) +
  theme_bw() +
  theme(
    text = element_text(family = "Arial", size = 10),
    panel.grid.minor = element_blank()
  ) +
  labs(x = "{x_col}", y = "Concentration", color = "")

ggsave("lineplot.pdf", width = 7, height = 4, dpi = 600)
'''

    @staticmethod
    def _r_violin(columns, group_col, **kw):
        gc = group_col or 'Group'
        cols_r = '", "'.join(columns)
        return f'''# R ggplot2 - Violin + Box + Strip (Raincloud)
library(ggplot2)
library(tidyr)

df <- read.csv("data.csv", fileEncoding = "UTF-8")
df_long <- pivot_longer(df, cols = c("{cols_r}"),
                        names_to = "Variable", values_to = "Value")

ggplot(df_long, aes(x = {gc}, y = Value, fill = {gc})) +
  geom_violin(alpha = 0.3, linewidth = 0.5) +
  geom_boxplot(width = 0.2, linewidth = 0.5, outlier.size = 1) +
  geom_jitter(width = 0.1, size = 1, alpha = 0.5) +
  facet_wrap(~Variable, scales = "free_y") +
  theme_bw() +
  theme(
    text = element_text(family = "Arial", size = 10),
    panel.grid.minor = element_blank(),
    legend.position = "none"
  ) +
  labs(x = "", y = "Value")

ggsave("violin.pdf", width = 7, height = 5, dpi = 600)
'''

    @staticmethod
    def _r_generic(columns, group_col, **kw):
        return '# R ggplot2 - 通用图表\n# 请根据数据手动调整\n'


# ============================================================================
# 便捷入口函数
# ============================================================================
def visualize(data_path, output_dir='./figures', style='sci', language='zh'):
    """
    一键自动绘图

    Parameters
    ----------
    data_path : str, CSV/Excel文件路径
    output_dir : str, 输出目录
    style : str, 'sci'|'nature'|'chinese'
    language : str, 'zh'|'en'
    """
    # 加载数据
    if data_path.endswith('.csv'):
        df = pd.read_csv(data_path, encoding='utf-8-sig')
    elif data_path.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(data_path)
    else:
        raise ValueError(f"不支持的文件格式: {data_path}")

    agent = VisualizationAgent(df, output_dir, style=style, language=language)

    print(f"\n{'='*60}")
    print(f"Scientific Visualization Agent")
    print(f"风格: {style} | 语言: {language}")
    print(f"数据: {len(df)}行 × {len(df.columns)}列")
    print(f"输出: {output_dir}")
    print(f"{'='*60}\n")

    # 自动推荐+绘图
    results = agent.auto_plot(top_n=5)

    # 生成R代码
    code_dir = os.path.join(output_dir, 'code')
    os.makedirs(code_dir, exist_ok=True)
    cg = CodeGenerator()

    recs = agent._recommender.recommend(top_n=3)
    for rec in recs:
        ct = rec['chart_type']
        if ct in ('regression_scatter',):
            ct = 'scatter'
        cols = rec.get('kwargs', {}).get('variables', agent._recommender.profile['numeric_cols'][:3])
        gc = rec.get('kwargs', {}).get('group_col')
        r_code = cg.generate_r_code(ct, cols, gc)
        r_path = os.path.join(code_dir, f'{ct}.R')
        with open(r_path, 'w', encoding='utf-8') as f:
            f.write(r_code)
        origin_code = cg.generate_origin_code(ct, cols, gc)
        origin_path = os.path.join(code_dir, f'{ct}.ogs')
        with open(origin_path, 'w', encoding='utf-8') as f:
            f.write(origin_code)

    print(f"\n[完成] 共生成 {len(results)} 张图表")
    print(f"[完成] R代码已保存至 {code_dir}/")
    print(f"[完成] Origin代码已保存至 {code_dir}/")

    return agent, results
