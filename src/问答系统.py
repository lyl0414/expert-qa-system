import streamlit as st
from qa_sys import KnowledgeQA
import re
import os
import tempfile
import json
import streamlit.components.v1 as components
import random

# 在最开始就初始化session_state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "您好！我是专家知识图谱助手。我可以帮您查询专家信息、研究领域、论文等。请问有什么我可以帮您的？"}
    ]
if "qa_system" not in st.session_state:
    st.session_state.qa_system = KnowledgeQA(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="123456"
    )
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

def handle_input():
    """处理用户输入"""
    if st.session_state.user_input:
        question = st.session_state.user_input
        st.session_state.messages.append({"role": "user", "content": question})
        answer = st.session_state.qa_system.answer(question)
        
        # 创建一个新的容器来显示图谱
        graph_container = st.empty()
        
        st.session_state.messages.append({
            "role": "assistant", 
            "content": answer,
            "has_graph": True,
            "question": question,
            "graph_container": graph_container
        })
        st.session_state.user_input = ""

def search_experts(field=None, h_index_range=None, paper_keyword=None):
    """搜索专家"""
    query_conditions = []
    params = {}
    
    if field:
        query_conditions.append("(e)-[:belongs_to|interested_in]->(i:Interest {name: $field})")
        params["field"] = field
    
    if h_index_range:
        min_h, max_h = h_index_range
        query_conditions.append("e.h_index >= $min_h AND e.h_index <= $max_h")
        params.update({"min_h": min_h, "max_h": max_h})
    
    if paper_keyword:
        query_conditions.append("(e)-[:authored]->(p:Publication) WHERE p.title CONTAINS $keyword")
        params["keyword"] = paper_keyword
    
    if not query_conditions:
        return []
    
    query = f"""
    MATCH (e:Expert)
    WHERE {' AND '.join(query_conditions)}
    RETURN DISTINCT e.name as name, e.h_index as h_index
    ORDER BY e.h_index DESC
    LIMIT 10
    """
    
    return st.session_state.qa_system.graph.run(query, params).data()

def visualize_knowledge_graph(question: str, answer: str):
    return
    """使用D3.js生成交互式知识图谱可视化"""
    import json
    import streamlit.components.v1 as components
    
    # 根据问题类型构建查询
    query = None
    params = {}
    
    # 处理领域专家查询
    if "研究" in question and ("领域" in question or "方向" in question):
        field = None
        if "自然语言生成" in question:
            field = "Natural Language Generation"
        elif "自然语言处理" in question:
            field = "Natural Language Processing"
        
        if field:
            query = """
            MATCH (e:Expert)-[r:INTERESTED_IN]->(i:Interest)
            WHERE i.name = $field
            RETURN e, r, i
            """
            params["field"] = field
    
    # 处理专家信息查询
    elif any(name in question for name in ["Kees Van Deemter", "Albert Gatt", "Ehud Reiter"]):
        expert_name = next(name for name in ["Kees Van Deemter", "Albert Gatt", "Ehud Reiter"] if name in question)
        if "研究领域" in question or "方向" in question:
            query = """
            MATCH (e:Expert)-[r:INTERESTED_IN]->(i:Interest)
            WHERE e.name = $expert_name
            RETURN e, r, i
            """
        elif "论文" in question:
            query = """
            MATCH (e:Expert)-[r:AUTHORED]->(p:Publication)
            WHERE e.name = $expert_name
            RETURN e, r, p
            """
        params["expert_name"] = expert_name
    
    if not query:
        return None
    
    # 执行查询
    results = st.session_state.qa_system.graph.run(query, params).data()
    
    # 构建D3.js数据结构
    nodes = []
    links = []
    node_ids = {}
    current_id = 0
    
    # 处理查询结果，先创建所有节点
    for record in results:
        for key, value in record.items():
            if hasattr(value, 'labels'):  # 节点
                name = value.get('name_zh', '') or value.get('name', '')
                if name and name not in node_ids:
                    node_ids[name] = current_id
                    nodes.append({
                        "id": current_id,
                        "name": name,
                        "type": list(value.labels)[0]
                    })
                    current_id += 1
    
    # 处理关系
    link_id = 0
    for record in results:
        for key, value in record.items():
            if hasattr(value, 'type'):  # 关系
                source_name = value.start_node.get('name_zh', '') or value.start_node.get('name', '')
                target_name = value.end_node.get('name_zh', '') or value.end_node.get('name', '')
                if source_name in node_ids and target_name in node_ids:
                    # 使用正则表达式提取关系类型
                    relation_str = str(value)
                    # print('原始关系字符串:', relation_str)  # 调试输出
                    
                    # 尝试不同的正则表达式模式
                    match = re.search(r':(.*?)\s*{', relation_str)
                    if match:
                        relation_type = match.group(1).strip('[]')
                    else:
                        # 如果匹配失败，使用备用方案
                        relation_type = str(value.type)
                    
                    # print('提取的关系类型:', relation_type)  # 调试输出
                    
                    link_data = {
                        "id": link_id,
                        "source": int(node_ids[source_name]),
                        "target": int(node_ids[target_name]),
                        "relation": relation_type,
                        "value": 1
                    }
                    links.append(link_data)
                    link_id += 1
    
    # 打印调试信息
    # print("\n节点集:")
    # print(json.dumps(nodes, ensure_ascii=False, indent=2))
    # print("\n边集:")
    # print(json.dumps(links, ensure_ascii=False, indent=2))
    
    # 将数据转换为JSON字符串
    nodes_json = json.dumps(nodes)
    links_json = json.dumps(links)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script src="https://d3js.org/d3.v5.min.js"></script>
        <style>
            .link-active {{
                stroke-opacity: 1;
                stroke-width: 3;
            }}
        </style>
    </head>
    <body>
        <div style="border:1px solid #000;position: relative;">
            <svg width="800" height="600"></svg>

        </div>
        <script>
            let marge = {{ top: 60, bottom: 60, left: 60, right: 60 }}
            let svg = d3.select('svg')
            let width = svg.attr('width')
            let height = svg.attr('height')
            
            // 设置缩放
            svg.call(
                d3.zoom().on('zoom', function() {{
                    g.attr('transform', d3.event.transform)
                }})
            ).on('dblclick.zoom', null)
            
            let g = svg.append('g')
                .attr('transform', 'translate(' + marge.top + ',' + marge.left + ')')
                .attr('class', 'container')
            
            // 节点和边数据
            let nodes = {json.dumps(nodes, ensure_ascii=False)}
            let edges = {json.dumps(links, ensure_ascii=False)}
            
            // 创建力导向图
            let forceSimulation = d3.forceSimulation()
                .force('link', d3.forceLink().id(d => d.id).distance(200))
                .force('charge', d3.forceManyBody().strength(-2000))
                .force('center', d3.forceCenter(width / 2, height / 2))
                .force('collision', d3.forceCollide().radius(80))
            
            // 箭头
            let marker = g.append('marker')
                .attr('id', 'resolved')
                .attr('markerUnits', 'userSpaceOnUse')
                .attr('viewBox', '0 -5 10 10')
                .attr('refX', 44)
                .attr('refY', 0)
                .attr('markerWidth', 10)
                .attr('markerHeight', 10)
                .attr('orient', 'auto')
                .attr('stroke-width', 2)
                .append('path')
                .attr('d', 'M0,-5L10,0L0,5')
                .attr('fill', '#000000')
            
            // 绘制边
            let links = g.append('g')
                .selectAll('path')
                .data(edges)
                .enter()
                .append('path')
                .attr('id', d => 'edgepath' + d.id)
                .style('stroke', '#000')
                .style('stroke-width', 2)
                .attr('class', 'lines')
                .attr('marker-end', 'url(#resolved)')
            
            // 边上的文字
            let linksText = g.append('g')
                .selectAll('text')
                .data(edges)
                .enter()
                .append('text')
                .attr('class', 'linksText')
                .text(d => d.relation)
                .style('font-size', 14)
                .attr('fill-opacity', 0)
            
            // 创建节点
            let gs = g.append('g')
                .selectAll('.circleText')
                .data(nodes)
                .enter()
                .append('g')
                .attr('class', 'singleNode')
                .attr('id', d => 'singleNode' + d.id)
                .style('cursor', 'pointer')
            
            // 绘制节点圆圈
            gs.append('circle')
                .attr('r', 40)
                .attr('fill', 'orange')
                .attr('stroke', 'grey')
                .attr('stroke-width', 3)
            
            // 文字
            gs.append('text')
                .attr('y', -25)
                .attr('dy', 10)
                .attr('text-anchor', 'middle')
                .style('font-size', 14)
                .text(d => d.name)
            
            // 鼠标交互
            gs.on('mouseover', function(d) {{
                linksText.style('fill-opacity', e => e.source.id === d.id ? 1 : 0)
                links.style('opacity', 0.1)
                    .filter(e => e.source.id === d.id)
                    .style('opacity', 1)
                    .classed('link-active', true)
            }}).on('mouseout', function(d) {{
                linksText.style('fill-opacity', 0)
                links.style('opacity', 1)
                    .classed('link-active', false)
            }})
            
            // 拖拽行为
            gs.call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended))
            
            // 力导向图更新
            forceSimulation.nodes(nodes)
            forceSimulation.force('link').links(edges)
            
            forceSimulation.on('tick', () => {{
                links.attr('d', d => 'M' + d.source.x + ',' + d.source.y + ' L' + d.target.x + ',' + d.target.y)
                linksText.attr('x', d => (d.source.x + d.target.x) / 2)
                    .attr('y', d => (d.source.y + d.target.y) / 2)
                gs.attr('transform', d => 'translate(' + d.x + ',' + d.y + ')')
            }})
            
            function dragstarted(d) {{
                if (!d3.event.active) forceSimulation.alphaTarget(0.3).restart()
                d.fx = d.x
                d.fy = d.y
            }}
            
            function dragged(d) {{
                d.fx = d3.event.x
                d.fy = d3.event.y
            }}
            
            function dragended(d) {{
                if (!d3.event.active) forceSimulation.alphaTarget(0)
                d.fx = null
                d.fy = null
            }}
        </script>
    </body>
    </html>
    """
    
    components.html(html_content, height=600, width=800)
    
    return None

def main():
    st.set_page_config(
        page_title="计算机领域专家知识图谱问答系统",
        page_icon="🧀",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 自定义CSS样式
    st.markdown("""
        <style>
        /* 整体页面样式 */
        .main {
            background: linear-gradient(135deg, #FFF9C4 0%, #FFECB3 100%);
            font-family: 'Helvetica Neue', Arial, sans-serif;
        }
        
        /* 侧边栏样式 */
        .css-1d391kg {
            background-color: #FFE082;
            border-right: 2px solid #FFB74D;
        }
        
        /* 聊天消息样式 */
        .chat-message {
            padding: 1.5rem;
            margin: 1rem 2rem;
            border-radius: 15px;
            box-shadow: 0 2px 8px rgba(255, 167, 38, 0.1);
            position: relative;
        }
        .chat-message.user {
            background-color: #FFF8E1;
            margin-left: 4rem;
            border-left: 4px solid #FFB74D;
        }
        .chat-message.assistant {
            background-color: #FFFFFF;
            margin-right: 4rem;
            border-right: 4px solid #FFB74D;
        }
        .chat-message .content {
            color: #5D4037;
            font-size: 1rem;
            line-height: 1.6;
            margin-top: 0.5rem;
        }
        .chat-message .role {
            color: #FF8F00;
            font-weight: 600;
            font-size: 0.9rem;
        }
        
        /* 输入框样式 */
        .stTextInput {
            position: fixed;
            bottom: 2rem;
            left: 50%;
            transform: translateX(-50%);
            width: 60%;
            background: #FFFFFF;
            border-radius: 20px;
            padding: 0.5rem;
            box-shadow: 0 4px 12px rgba(255, 167, 38, 0.2);
        }
        .stTextInput > div > div {
            background-color: #FFFFFF;
            border-radius: 20px;
            border: 2px solid #FFB74D;
        }
        .stTextInput input {
            color: #5D4037 !important;
            font-size: 1rem;
            padding: 0.5rem 1rem !important;
        }
        .stTextInput input:focus {
            box-shadow: 0 0 0 2px rgba(255, 167, 38, 0.3);
        }
        
        /* 滚动条样式 */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #FFF8E1;
        }
        ::-webkit-scrollbar-thumb {
            background: #FFB74D;
            border-radius: 10px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #FF8F00;
        }
        
        /* 聊天容器 */
        #chat-container {
            height: calc(100vh - 180px);
            overflow-y: auto;
            padding: 2rem;
            padding-bottom: 100px;
            background: linear-gradient(180deg, #FFF8E1 0%, #FFECB3 100%);
            border-radius: 20px;
            margin: 1rem;
            box-shadow: inset 0 2px 10px rgba(255, 167, 38, 0.1);
        }
        
        /* 侧边栏内容样式 */
        .sidebar-content {
            padding: 1rem;
        }
        .sidebar-content h3 {
            color: #F57C00;
            margin-bottom: 1.5rem;
        }
        .sidebar-content h4 {
            color: #FF8F00;
            margin-top: 1.5rem;
        }
        
        /* 新对话按钮样式 */
        .stButton button {
            background-color: #FFB74D !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 20px !important;
            padding: 0.5rem 1.5rem !important;
            font-weight: 500 !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 2px 6px rgba(255, 167, 38, 0.2) !important;
        }
        .stButton button:hover {
            background-color: #FF8F00 !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(255, 167, 38, 0.3) !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # 侧边栏
    with st.sidebar:
        
        
        # 原有的示例问题部分
        st.markdown("### 💡 示例问题")
        st.markdown("""
        #### 🎯 专家查询
        - 谁研究了自然语言生成领域？
        - Albert Gatt的h指数是多少？
        
        #### 📚 论文查询
        - 自然语言生成领域的论文有哪些？
        - NLP最近的研究论文？
        
        #### 🤝 合作关系
        - Ehud Reiter和Robert Dale有合作吗？
        
        #### 🔄 多轮对话
        1. 用户: 谁研究自然语言生成？
        2. 用户: 他的研究领域是什么？
        3. 用户: 他的h指数是多少？
        """)
        
        if st.button("🔄 新对话", use_container_width=True):
            st.session_state.messages = [
                {"role": "assistant", "content": "您好！我是专家知识图谱助手。我可以帮您查询专家信息、研究领域、论文等。请问有什么我可以帮您的？"}
            ]
            st.experimental_rerun()

    # 主聊天界面
    for message in st.session_state.messages:
        with st.container():
            if message["role"] == "user":
                st.markdown(f"""
                <div class="chat-message user">
                    <div style="color: #8E8EA0">你</div>
                    <div class="content">{message["content"]}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message assistant">
                    <div style="color: #8E8EA0">助手</div>
                    <div class="content">{message["content"]}</div>
                </div>
                """, unsafe_allow_html=True)
                
                if message.get("has_graph"):
                    st.button("📊 查看知识图谱", key=f"graph_{random.randint(1, 100)}")
                    # col1, col2 = st.columns([1, 4])
                    # with col1:
                    #     if st.button("📊 查看知识图谱", key=f"graph_{len(st.session_state.messages)}"):
                    #         with col2:
                    #             visualize_knowledge_graph(
                    #                 message["question"],
                    #                 message["content"]
                    #             )

    # 输入框
    st.text_input(
        label="用户输入",
        label_visibility="collapsed",
        placeholder="输入您的问题...",
        key="user_input",
        on_change=handle_input
    )

if __name__ == "__main__":
    main() 