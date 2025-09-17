import streamlit as st
from qa_sys import KnowledgeQA

# 确保QA系统已初始化
if "qa_system" not in st.session_state:
    st.session_state.qa_system = KnowledgeQA(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="123456"
    )

def main():
    st.set_page_config(
        page_title="专家搜索 - 知识图谱问答系统",
        page_icon="🔍",
        layout="wide"
    )

    # 页面标题
    st.title("🔍 专家搜索")
    
    # 使用tabs来分隔不同的搜索方式
    tab1, tab2, tab3 = st.tabs([
        "🎯 按研究领域搜索",
        "📊 按h指数搜索",
        "📚 按论文关键词搜索"
    ])
    
    # 按研究领域搜索
    with tab1:
        st.markdown("### 按研究领域搜索专家")
        field = st.text_input("输入研究领域（如：自然语言处理、机器学习等）")
        if st.button("搜索", key="field_search", use_container_width=True):
            if field:
                results = st.session_state.qa_system.search_experts_by_interest(field)
                display_results(results)
            else:
                st.warning("请输入研究领域")
    
    # 按h指数搜索
    with tab2:
        st.markdown("### 按h指数范围搜索专家")
        h_index_range = st.slider(
            "选择h指数范围",
            0, 100, (20, 80)
        )
        if st.button("搜索", key="h_index_search", use_container_width=True):
            results = st.session_state.qa_system.search_experts_by_h_index(
                h_index_range[0], h_index_range[1]
            )
            display_results(results)
    
    # 按论文关键词搜索
    with tab3:
        st.markdown("### 按论文关键词搜索专家")
        keyword = st.text_input("输入论文关键词")
        if st.button("搜索", key="paper_search", use_container_width=True):
            if keyword:
                query = f"""
                MATCH (e:Expert)-[:AUTHORED]->(p:Publication)
                WHERE p.title CONTAINS $keyword
                RETURN DISTINCT e.name as name, e.h_index as h_index
                ORDER BY e.h_index DESC
                """
                results = st.session_state.qa_system.graph.run(
                    query, keyword=keyword
                ).data()
                display_results(results)
            else:
                st.warning("请输入论文关键词")

def display_results(results):
    """统一的结果显示函数"""
    if not results:
        st.warning("未找到匹配的专家")
        return
        
    st.markdown("## 搜索结果")
    
    # 创建结果网格
    cols = st.columns(3)
    for idx, expert in enumerate(results):
        with cols[idx % 3]:
            name_display = expert['name_zh'] if expert.get('name_zh') else expert['name']
            position_display = f"职位：{expert['position']}" if expert.get('position') else ""
            
            st.markdown(f"""
            <div style="
                background-color: #FFF8E1;
                padding: 1.5rem;
                margin: 0.5rem 0;
                border-radius: 15px;
                border: 2px solid #FFB74D;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            ">
                <h3 style="color: #F57C00; margin: 0 0 0.5rem 0;">{name_display}</h3>
                <p style="color: #5D4037; margin: 0;">
                    <strong>h指数:</strong> {expert.get('h_index', '未知')}
                </p>
                {f'<p style="color: #5D4037; margin: 0.5rem 0 0 0;">{position_display}</p>' if position_display else ''}
            </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 