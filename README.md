# expert-qa-system
# 专家知识图谱问答系统

基于Neo4j图数据库的专家知识图谱问答系统，支持多轮对话和中英文混合查询。

## 知识图谱结构

### 实体类型
1. Expert (专家)
   - name: 英文名
   - name_zh: 中文名
   - h_index: h指数
   - position: 职位

2. Publication (论文)
   - title: 论文标题
   - year: 发表年份
   - venue: 发表venue
   - citation: 引用次数

3. Interest (研究领域)
   - name: 领域名称（支持中英文）
   - description: 领域描述

### 关系类型
- 专家-领域
  - belongs_to: 专家属于某领域
  
- 专家-研究兴趣
  - interested_in: 专家的研究兴趣

- 专家-论文
  - authored: 作者关系

- 论文-领域
  - published_in: 发表在某领域

## 支持的问题类型

### 1. 专家查询
- 查询领域专家
  ```
  谁研究了自然语言生成领域？
  谁研究Natural Language Generation？
  自然语言处理领域最强的专家有哪些？
  机器学习方向的专家？
  NLP领域排名前的专家？
  ```

- 查询专家信息
  ```
  Kees Van Deemter的研究领域是什么？
  Albert Gatt的h指数是多少？
  Ehud Reiter发表了什么论文？
  特别说明，对重名做了如下处理：
    请输入您的问题: Robert Dale的h指数是多少？
    找到多位相关专家：
    1. Robert Dale，研究领域：Software Architecture, Language Technology, Virtual Environments，h指数：25
    2. Robert Dale，研究领域：Temporal Expressions, Anaphora Resolution, Supervised Machine Learning，h指数：12
  ```

### 2. 论文查询
- 查询领域论文
  ```
  自然语言生成领域的论文有哪些？
  Natural Language Generation领域的相关论文有哪些？
  自然语言处理最近的研究论文？
  自然语言方向的论文有哪些？
  ```

- 查询论文信息
  ```
  General and reference这篇论文的作者是谁？
  General and reference这篇论文发表在哪一年？
  ```

### 3. 合作关系查询
Ehud Reiter和Robert Dale有什么合作关系吗？
Ehud Reiter和Robert Dale有合作吗？
Ehud Reiter和Robert Dale合作发表了哪些论文？

## 多轮对话支持

系统支持多种形式的追问，包括：

### 1. 专家相关追问
用户: 谁研究自然语言生成领域？
系统: [返回专家列表]
用户: 他的研究领域是什么？
用户: 他的h指数是多少？
用户: 他发表了什么论文？

### 2. 多专家追问
用户: 谁研究自然语言生成领域？
系统: [返回专家列表]

用户: 他们之间有合作吗？
用户: 他们发表过什么论文？
用户: 他们是什么时候开始合作的？
用户: 他们一共合作了多少次？

### 3. 领域相关追问
用户: 自然语言生成领域的专家有哪些？
系统: [返回专家列表]

用户: 这个领域的论文有哪些？
用户: 这个领域还有其他专家吗？
用户: 这个领域最新的论文有哪些？

### 4. 请求更多信息
用户: [任意上述问题]
系统: [返回结果]

用户: 还有吗？
用户: 更多
用户: 继续
用户: 其他的

### 运行
所需依赖（可能不全，你们自己看着再补充）：
pip install -r requirements.txt
运行
streamlit run src/问答系统.py
>>>>>>> 29a7a9c (first commit)
