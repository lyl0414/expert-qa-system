import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from qa_sys import KnowledgeQA
import pandas as pd

# 确保QA系统已初始化
if "qa_system" not in st.session_state:
    st.session_state.qa_system = KnowledgeQA(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="123456"
    )

def plot_h_index_distribution():
    """绘制h指数分布图"""
    h_indices = st.session_state.qa_system.get_h_index_distribution()
    
    # 创建DataFrame
    df = pd.DataFrame({'h_index': h_indices})
    
    # 创建直方图
    fig = px.histogram(
        df, 
        x='h_index',
        nbins=30,
        title='专家h指数分布',
        labels={'h_index': 'h指数', 'count': '专家数量'},
        color_discrete_sequence=['#FF9800']
    )
    
    # 添加均值线
    mean_h = df['h_index'].mean()
    fig.add_vline(
        x=mean_h, 
        line_dash="dash", 
        line_color="red",
        annotation_text=f"平均值: {mean_h:.1f}"
    )
    
    # 更新布局
    fig.update_layout(
        showlegend=False,
        xaxis_title="h-指数",
        yaxis_title="专家数量",
        bargap=0.1
    )
    
    return fig

def plot_field_distribution():
    """绘制研究领域分布图"""
    field_dist = st.session_state.qa_system.get_field_distribution()
    
    # 创建DataFrame
    df = pd.DataFrame(
        list(field_dist.items()), 
        columns=['field', 'count']
    ).sort_values('count', ascending=True)
    
    # 创建水平条形图
    fig = px.bar(
        df,
        x='count',
        y='field',
        orientation='h',
        title='热门研究领域分布',
        color='count',
        color_continuous_scale='Oranges'
    )
    
    # 更新布局
    fig.update_layout(
        xaxis_title="专家数量",
        yaxis_title="研究领域",
        showlegend=False,
        yaxis={'categoryorder':'total ascending'}
    )
    
    return fig

def plot_yearly_publications():
    """绘制年度论文发表趋势"""
    yearly_stats = st.session_state.qa_system.get_yearly_publication_stats()
    
    # 创建完整的年份范围（1950-2024）
    all_years = list(range(1950, 2025))
    
    # 创建DataFrame，确保包含所有年份
    df = pd.DataFrame(
        [(year, yearly_stats.get(year, 0)) for year in all_years],
        columns=['year', 'count']
    )
    
    # 创建图形对象
    fig = go.Figure()
    
    # 添加实际数据线（蓝色）
    fig.add_trace(
        go.Scatter(
            x=df['year'],
            y=df['count'],
            mode='lines+markers',
            name='实际发表量',
            line=dict(color='#1f77b4'),  # 蓝色
            hovertemplate="年份: %{x}<br>论文数量: %{y}<extra></extra>"
        )
    )
    
    # 添加趋势线（红色）
    from scipy.signal import savgol_filter
    # 使用Savitzky-Golay滤波器计算趋势线
    window = 11  # 必须是奇数
    trend = savgol_filter(df['count'], window, 3)
    
    fig.add_trace(
        go.Scatter(
            x=df['year'],
            y=trend,
            mode='lines',
            name='发展趋势',
            line=dict(color='red', dash='dash'),
            hovertemplate="年份: %{x}<br>趋势值: %{y:.0f}<extra></extra>"
        )
    )
    
    # 更新布局
    fig.update_layout(
        title='论文发表年度趋势 (1950-2024)',
        xaxis=dict(
            title="年份",
            tickmode='linear',
            tick0=1950,
            dtick=5,  # 每5年显示一个刻度
            range=[1950, 2024]  # 固定x轴范围
        ),
        yaxis_title="论文数量",
        hovermode='x unified',
        plot_bgcolor='white',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor='rgba(255, 255, 255, 0.8)'
        ),
        showlegend=True
    )
    
    # 添加网格线
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    
    return fig

def main():
    st.set_page_config(
        page_title="统计分析 - 知识图谱问答系统",
        page_icon="📊",
        layout="wide"
    )

    st.title("📊 统计分析")
    
    # 创建三个选项卡
    tab1, tab2, tab3 = st.tabs([
        "📈 h指数分布", 
        "🎯 研究领域分布",
        "📅 论文发表趋势"
    ])

    # h指数分布
    with tab1:
        st.markdown("### h指数分布分析")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            h_index_fig = plot_h_index_distribution()
            st.plotly_chart(h_index_fig, use_container_width=True)
        
        with col2:
            h_indices = pd.Series(st.session_state.qa_system.get_h_index_distribution())
            st.markdown("#### 统计指标")
            st.markdown(f"""
            - **平均值**: {h_indices.mean():.1f}
            - **中位数**: {h_indices.median():.1f}
            - **最大值**: {h_indices.max()}
            - **最小值**: {h_indices.min()}
            - **标准差**: {h_indices.std():.1f}
            """)

    # 研究领域分布
    with tab2:
        st.markdown("### 研究领域分布分析")
        field_fig = plot_field_distribution()
        st.plotly_chart(field_fig, use_container_width=True)
        
        # 添加领域统计信息
        field_dist = st.session_state.qa_system.get_field_distribution()
        total_experts = sum(field_dist.values())
        st.markdown(f"""
        #### 领域统计
        - **总计领域数**: {len(field_dist)}
        - **涉及专家总数**: {total_experts}
        - **平均每个领域专家数**: {total_experts/len(field_dist):.1f}
        """)

    # 论文发表趋势
    with tab3:
        st.markdown("### 论文发表趋势分析")
        pub_fig = plot_yearly_publications()
        st.plotly_chart(pub_fig, use_container_width=True)

if __name__ == "__main__":
    main() 