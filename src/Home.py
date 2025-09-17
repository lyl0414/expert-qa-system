import streamlit as st
from qa_sys import KnowledgeQA

# 初始化session_state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "您好！我是芝士问答助手。我可以帮您查询专家信息、研究领域、论文等。请问有什么我可以帮您的？"}
    ]
if "qa_system" not in st.session_state:
    st.session_state.qa_system = KnowledgeQA(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="123456"
    )
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

def main():
    st.set_page_config(
        page_title="芝士问答",
        page_icon="🧀",
        layout="wide"
    )

    # 主标题
    st.title("🧀 芝士问答")
    
    # 设置页面样式
    st.markdown("""
    <style>
        .chat-message {
            padding: 1.5rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            display: flex;
            flex-direction: column;
        }
        .chat-message.user {
            background-color: #F0F2F6;
        }
        .chat-message.assistant {
            background-color: #FFF8E1;
        }
        .chat-message .content {
            margin-top: 0.5rem;
            white-space: pre-wrap;
        }
    </style>
    """, unsafe_allow_html=True)

    # 侧边栏
    with st.sidebar:
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
                {"role": "assistant", "content": "您好！我是芝士问答助手。我可以帮您查询专家信息、研究领域、论文等。请问有什么我可以帮您的？"}
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
                    <div style="color: #8E8EA0">芝士助手</div>
                    <div class="content">{message["content"]}</div>
                </div>
                """, unsafe_allow_html=True)

    # 输入框
    st.text_input(
        label="用户输入",
        value="",
        placeholder="输入您的问题...",
        key="user_input",
        on_change=handle_input,
        label_visibility="collapsed"
    )

if __name__ == "__main__":
    main() 