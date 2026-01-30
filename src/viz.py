# src/viz.py
from __future__ import annotations
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px

# 配置中文字体（macOS 系统字体）
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

def plot_sales_vs_ads_static(df: pd.DataFrame, x: str = "ad_spend", y: str = "sales"):
    """
    静态散点图（Seaborn + Matplotlib）。在 Jupyter 中直接显示。
    
    参数：
        df: 包含 x 和 y 列的 DataFrame
        x: x 轴列名（默认："ad_spend"）
        y: y 轴列名（默认："sales"）
    
    返回：
        matplotlib.figure.Figure: 图表对象
    
    异常：
        ValueError: 如果 x 或 y 列不在 DataFrame 中
    """
    # 数据验证
    if x not in df.columns or y not in df.columns:
        raise ValueError(f"DataFrame 缺少列: {x} 或 {y}")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(data=df, x=x, y=y, ax=ax, s=100, alpha=0.7)
    sns.regplot(data=df, x=x, y=y, ax=ax, scatter=False, line_kws={'color': 'red', 'linewidth': 2})
    ax.set_title("广告投入与销量关系（静态）", fontsize=14, fontweight='bold')
    ax.set_xlabel(f"{x} (万元)", fontsize=12)
    ax.set_ylabel(f"{y} (万元)", fontsize=12)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig

def plot_sales_vs_ads_interactive(df: pd.DataFrame, x: str = "ad_spend", y: str = "sales"):
    """
    交互式散点图（Plotly）。返回 Plotly Figure 对象。
    
    参数：
        df: 包含 x、y 和 month 列的 DataFrame
        x: x 轴列名（默认："ad_spend"）
        y: y 轴列名（默认："sales"）
    
    返回：
        plotly.graph_objs._figure.Figure: 交互式图表对象
    
    异常：
        ValueError: 如果必要的列不在 DataFrame 中
    """
    # 数据验证
    if x not in df.columns or y not in df.columns:
        raise ValueError(f"DataFrame 缺少列: {x} 或 {y}")
    
    fig = px.scatter(
        df, x=x, y=y,
        size=y,
        hover_name="month" if "month" in df.columns else None,
        title="广告投入与销量关系（交互式）",
        trendline="ols"
    )
    return fig