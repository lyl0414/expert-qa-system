import streamlit as st
import streamlit.components.v1 as components
from qa_sys import KnowledgeQA
import plotly.graph_objects as go
import networkx as nx
import json

# 确保QA系统已初始化
if "qa_system" not in st.session_state:
    st.session_state.qa_system = KnowledgeQA(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="123456"
    )

def create_network_graph(nodes, edges, title):
    """创建网络图"""
    G = nx.Graph()
    
    # 添加节点和边
    for node in nodes:
        G.add_node(node['name'])
    for edge in edges:
        G.add_edge(edge['source'], edge['target'])
    
    # 使用 spring_layout 布局
    pos = nx.spring_layout(G)
    
    # 创建边的追踪
    edge_trace = go.Scatter(
        x=[], y=[],
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines')

    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_trace['x'] += (x0, x1, None)
        edge_trace['y'] += (y0, y1, None)

    # 创建节点的追踪
    node_trace = go.Scatter(
        x=[], y=[],
        text=[],
        mode='markers+text',
        hoverinfo='text',
        marker=dict(
            showscale=True,
            colorscale='YlOrRd',
            size=20,
            colorbar=dict(
                thickness=15,
                title='节点连接数',
                xanchor='left',
                titleside='right'
            )
        ),
        textposition="bottom center"
    )

    # 添加节点位置和属性
    for node in G.nodes():
        x, y = pos[node]
        node_trace['x'] += (x,)
        node_trace['y'] += (y,)
        node_trace['text'] += (node,)
    
    # 设置节点颜色基于连接数
    node_adjacencies = []
    for node, adjacencies in enumerate(G.adjacency()):
        node_adjacencies.append(len(adjacencies[1]))
    node_trace.marker.color = node_adjacencies

    # 创建图形
    fig = go.Figure(data=[edge_trace, node_trace],
                   layout=go.Layout(
                       title=title,
                       showlegend=False,
                       hovermode='closest',
                       margin=dict(b=20,l=5,r=5,t=40),
                       xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                       yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                   )
    
    return fig

def main():
    st.set_page_config(
        page_title="关系分析 - 知识图谱问答系统",
        page_icon="🔗",
        layout="wide"
    )

    st.title("🔗 关系分析")

    # 创建两个选项卡
    tab1, tab2 = st.tabs(["👥 专家合作网络", "🌐 研究领域网络"])

    # 专家合作网络
    with tab1:
        st.markdown("### 专家合作网络分析")
        expert_name = st.text_input("输入专家姓名", key="expert_name")
        depth = st.slider("选择网络深度", 1, 3, 2, help="设置要显示的合作关系网络层级")
        
        if st.button("分析合作网络", use_container_width=True):
            if expert_name:
                network_data = st.session_state.qa_system.get_collaboration_network(
                    expert_name, depth
                )
                if network_data['nodes']:
                    fig = create_network_graph(
                        network_data['nodes'],
                        network_data['links'],
                        f"{expert_name}的合作网络"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("未找到相关的合作网络")
            else:
                st.warning("请输入专家姓名")

    # 研���领域网络
    with tab2:
        st.markdown("### 研究领域关系网络")
        field = st.text_input("输入研究领域", key="field_name")
        if st.button("分析领域网络", use_container_width=True):
            if field:
                network_data = st.session_state.qa_system.get_field_network(field)
                if network_data['nodes']:
                    fig = create_network_graph(
                        network_data['nodes'],
                        network_data['links'],
                        f"{field}相关领域网络"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("未找到相关的领域网络")
            else:
                st.warning("请输入研究领域")

if __name__ == "__main__":
    main() 