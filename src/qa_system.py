# 调试语句版本
from py2neo import Graph
import jieba
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

@dataclass
class DialogContext:
    """对话上下文"""
    last_question: str = ""
    last_answer: str = ""
    last_entities: List[str] = field(default_factory=list)  # 存储上一轮提到的专家名字
    last_topic: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def is_valid(self) -> bool:
        """检查上下文是否仍然有效（默认5分钟内）"""
        return datetime.now() - self.timestamp < timedelta(minutes=5)

    def update(self, question: str, answer: str, entities: List[str], topic: str):
        """更新上下文"""
        self.last_question = question
        self.last_answer = answer
        self.last_entities = entities
        self.last_topic = topic
        self.timestamp = datetime.now()

class KnowledgeQA:
    def __init__(self, uri: str = "bolt://localhost:7687", 
                 user: str = "neo4j", 
                 password: str = "password"):
        """初始化问答系统"""
        self.graph = Graph(uri, auth=(user, password))
        self.question_patterns = self._init_patterns()
        self.context = DialogContext()
        self.follow_up_patterns = self._init_follow_up_patterns()
        # 添加领域名称映射字典
        self.field_mapping = {
            "自然语言生成": "Natural Language Generation",
            "自然语言": "Natural Language",
            "自然语言处理": "Natural Language Processing",
            "NLP": "Natural Language Processing",
            "机器学习": "Machine Learning",
            "ML": "Machine Learning",
            "深度学习": "Deep Learning",
            "DL": "Deep Learning",
            "计算机视觉": "Computer Vision",
            "CV": "Computer Vision",
            "NLG": "Natural Language Generation"
        }

    def _map_field_name(self, field: str) -> str:
        """统一的领域名称映射方法"""
        print(f"正在映射领域名称: {field}")
        # 如果输入的是英文，就不进行映射
        if any(field.lower() == en.lower() for en in self.field_mapping.values()):
            field_en = field
            print(f"检测到英文输入，保持原样: {field_en}")
        else:
            # 获取英��领域名称
            field_en = self.field_mapping.get(field, field)
            print(f"映射结果: {field} -> {field_en}")
        return field_en

    def _init_patterns(self) -> Dict[str, Dict[str, Any]]:
        """初始化问题模式"""
        return {
            # 专家相关问题
            r"谁研究(了)?([^领域？]+?)(领域)?[\?？]?$": {
                "type": "expert_by_interest",
                "extract": lambda m: m.group(2).strip()
            },
            r"(.*?)的(研究)?领域(是什么|有哪些)?": {
                "type": "expert_interests",
                "extract": lambda m: m.group(1).strip()
            },
            r"(.*?)的h指数是多少": {
                "type": "expert_h_index",
                "extract": lambda m: m.group(1).strip()
            },
            
            # 论文相关问题
            r"(.*?)发表了(什么|哪些)论文": {
                "type": "expert_publications",
                "extract": lambda m: m.group(1).strip()
            },
            r"(.*?)这篇论文的作者是谁": {
                "type": "publication_authors",
                "extract": lambda m: m.group(1).strip()
            },
            # 领域论文查询模式
            r"(.*?)(领域|方向)(的)?(关)?(���文|文章)(有哪些|是什么)?[\?？]?$": {
                "type": "field_publications",
                "extract": lambda m: m.group(1).strip()
            },
            
            # 合作关系问题
            r"(.*?)和(.*?)有(什么)?合作(关系)?吗?": {
                "type": "cooperation",
                "extract": lambda m: (m.group(1).strip(), m.group(2).strip())
            },
            
            # 领域专家排名
            r"(.*?)(领域|方向|研究).*?(最强|排名|指数|专家|学|研究员).*?": {
                "type": "top_experts_in_field",
                "extract": lambda m: m.group(1).strip()
            },
            
            # 修改最近论文查询模式，使其更灵活
            r"(.*?)(领域|方向)?(最近|近期|最新)的?(研究)?论文": {
                "type": "recent_field_publications",
                "extract": lambda m: m.group(1).strip()
            },
            
            # 添加一个更宽松的模式
            r"(.*?)(领域|方向)?的?(最近|近期|最新)(研究)?论文": {
                "type": "recent_field_publications",
                "extract": lambda m: m.group(1).strip()
            },
            
            # 添加论文发表年份查询模式
            r"(.*?)(这篇)?论���(发表)?在哪(一)?年": {
                "type": "publication_year",
                "extract": lambda m: m.group(1).strip()
            },
            
            # 添加论文领域查询模式
            r"(.*?)(这篇)?论文属于(什么|哪个|哪些)领域": {
                "type": "publication_field",
                "extract": lambda m: m.group(1).strip()
            }
        }

    def _init_follow_up_patterns(self) -> Dict[str, Dict[str, Any]]:
        """初始化追问模式"""
        return {
            # 关于多个专家的追问
            r"(他们)(之间)?(的|还有|是|有)?(.*?)(吗)?[\?？]?$": {
                "type": "experts_follow_up",
                "extract": lambda m: m.group(4).strip()
            },
            # 关于单个专家的追问
            r"(他|她|这个专家)(的|还有|是|有)?([^？?]*)(吗)?[\?？]?$": {
                "type": "expert_follow_up",
                "extract": lambda m: (self.context.last_entities[-1] if self.context.last_entities else None, m.group(3).strip())
            },
            # 关于领域的追问 - 修改这里
            r"(这个领域|该领域|这一领域)(的|还有|是|有)?(.*?)(有哪些|是什么)?(吗)?[\?？]?$": {
                "type": "field_follow_up",
                "extract": lambda m: (self.context.last_topic, self._extract_question_type(m.group(3)))
            },
            # 请求更多信息
            r"(还有吗|更多|继续|其他的)": {
                "type": "more_info",
                "extract": lambda m: self.context.last_topic
            }
        }

    def _extract_question_type(self, text: str) -> str:
        """从问题中提取核心问题类型"""
        # 去除可的后缀
        text = text.replace("有哪些", "").replace("是什么", "").strip()
        # 提取核心词
        for core_type in ["论文", "专家", "合作"]:
            if core_type in text:
                return core_type
        return text

    def answer(self, question: str) -> str:
        """处理问题并返回答案"""
        print("\n" + "="*50)
        print(f"问题: {question}")
        print(f"当前上下文状态:")
        print(f"- 上一个问题: {self.context.last_question}")
        print(f"- 上一个话题: {self.context.last_topic}")
        print(f"- 上一轮提到的专家: {self.context.last_entities}")
        print(f"- 上下文是否有效: {self.context.is_valid()}")
        
        # 尝试处理追问
        if self.context.is_valid():
            print("\n尝试匹配追问模式...")
            for pattern, config in self.follow_up_patterns.items():
                match = re.match(pattern, question)
                if match:
                    print(f"匹配到追问模式: {pattern}")
                    extracted = config["extract"](match)
                    print(f"提取的信息: {extracted}")
                    answer = self._handle_follow_up(config["type"], extracted)
                    print(f"追问处理结果: {answer}")
                    return answer
            print("没有匹配到追问模式")
        
        # 处理新问题
        print("\n尝试匹配新问题模式...")
        for pattern, config in self.question_patterns.items():
            match = re.match(pattern, question)
            if match:
                try:
                    print(f"匹配到模式: {pattern}")
                    extracted = config["extract"](match)
                    print(f"提取的信息: {extracted}")
                    if not extracted:
                        print("提取的信息为空，继续尝试其他模式")
                        continue
                    
                    # 更新上下文
                    answer = getattr(self, f"_handle_{config['type']}")(extracted)
                    print(f"处理结果: {answer}")
                    return answer
                    
                except Exception as e:
                    print(f"处理出错: {str(e)}")
                    return f"抱歉,处理您的问题时出现错误: {str(e)}"
        
        print("没有匹配到任何模式")
        return "抱歉,还不能理解这个问题"

    def _handle_follow_up(self, follow_up_type: str, extracted_info: Any) -> str:
        """处理追问"""
        print(f"\n处理追问:")
        print(f"- 类型: {follow_up_type}")
        print(f"- 提取的信息: {extracted_info}")
        
        if follow_up_type == "experts_follow_up":
            question_type = extracted_info
            print(f"- 处理多专家追问，问题类型: {question_type}")
            if "合作" in question_type and len(self.context.last_entities) >= 2:
                print(f"- 检测到合作相关问题，专家列表: {self.context.last_entities}")
                # 检查所有专家对之间的合作关系
                response = []
                for i in range(len(self.context.last_entities)):
                    for j in range(i + 1, len(self.context.last_entities)):
                        expert1 = self.context.last_entities[i]
                        expert2 = self.context.last_entities[j]
                        collaboration = self._handle_cooperation((expert1, expert2))
                        if "未发现" not in collaboration:  # 只添加有合作的结果
                            response.append(collaboration)
                
                if response:
                    return "\n\n".join(response)
                return "在这些专家之间未发现直接的合作论文"
            
            return f"抱歉，我不太理解您想了解这些专家的什么信息"
            
        elif follow_up_type == "expert_follow_up":
            expert_name, question_type = extracted_info
            print(f"- 处理单个专家追问，专家: {expert_name}, 问题类型: {question_type}")
            if not expert_name:
                return "抱歉，我不确定您指的是哪位专家"
            
            if "研究领域" in question_type or "领域" in question_type:
                return self._handle_expert_interests(expert_name)
            elif "论文" in question_type:  # 简化判断条件
                return self._handle_expert_publications(expert_name)
            elif "h指数" in question_type:
                return self._handle_expert_h_index(expert_name)
                
        elif follow_up_type == "field_follow_up":
            field, question_type = extracted_info
            print(f"- 处理领域追问，领域: {field}, 问题类型: {question_type}")
            if not field:
                return "抱歉，我不确定您指的是哪个领域"
            
            if "专家" in question_type:
                return self._handle_expert_by_interest(field)
            elif "论文" in question_type:  # 简化判断条件
                return self._handle_field_publications(field)
                
        elif follow_up_type == "more_info":
            print(f"- 处理更多���息请求，当前话题: {self.context.last_topic}")
            if self.context.last_topic:
                return self._get_more_information(self.context.last_topic)
        
        return "抱歉，我不理解您的追问"

    def _get_more_information(self, topic: str) -> str:
        """获取更多相关信息"""
        # 这里可以根据上下文返回更多相关信息
        query = """
        MATCH (e:Expert)-[:INTERESTED_IN]->(i:Interest)
        WHERE i.name CONTAINS $topic
        WITH e
        MATCH (e)-[:AUTHORED]->(p:Publication)
        RETURN e.name, p.title
        LIMIT 5
        """
        results = self.graph.run(query, topic=topic).data()
        
        if not results:
            return f"抱歉，没有找到更多关于{topic}的信息"
            
        response = f"这里是一些相关的额外信息:\n"
        for r in results:
            response += f"- {r['e.name']} 发表的论文: {r['p.title']}\n"
        return response

    def _handle_expert_by_interest(self, interest: str) -> str:
        """查找研究某领域的专家"""
        field_en = self._map_field_name(interest)
        # 添加调信息
        print(f"正在查找领域: {field_en}")
        
        # 改查询语句 - 使用小写不敏感的匹配
        query = """
        MATCH (e:Expert)-[:INTERESTED_IN]->(i:Interest)
        WHERE toLower(i.name) = toLower($field_en)
        RETURN DISTINCT e.name, e.name_zh, e.h_index, e.position
        ORDER BY e.h_index DESC
        """
        
        results = self.graph.run(query, field_en=field_en).data()
        
        if not results:
            # 如果没有结果，尝试模糊匹配
            query_fuzzy = """
            MATCH (e:Expert)-[:INTERESTED_IN]->(i:Interest)
            WHERE toLower(i.name) CONTAINS toLower($field_en)
            RETURN DISTINCT e.name, e.name_zh, e.h_index, e.position
            ORDER BY e.h_index DESC
            """
            results = self.graph.run(query_fuzzy, field_en=field_en).data()
            
            if not results:
                similar_fields = self._find_similar_fields(field_en)
                if similar_fields:
                    return f"抱歉,没有找到完全匹配的专家。您是不是想找这些领域?\n{', '.join(similar_fields)}"
                return f"抱歉,没有找到研究{interest}的专家"
        
        # 判断是否使用中文显示
        is_chinese_query = interest in self.field_mapping
        field_display = f"{interest} ({field_en})" if is_chinese_query else field_en
        
        response = f"研究{field_display}的主要专家有:\n"
        seen_experts = set()
        experts_list = []
        for r in results:
            name = r['e.name_zh'] if r['e.name_zh'] else r['e.name']
            if name not in seen_experts:
                seen_experts.add(name)
                experts_list.append(name)
                position = f"({r['e.position']})" if r.get('e.position') else ""
                # 如果是中文查询且有英文名，显示中英文对照
                if is_chinese_query and r['e.name']:
                    name_display = f"{name} ({r['e.name']})"
                else:
                    name_display = name
                response += f"- {name_display} {position} h指数: {r['e.h_index']}\n"
        
        # 更新上下文
        self.context.update(
            question=f"查询{interest}领域专家",
            answer=response,
            entities=experts_list,
            topic=interest
        )
        
        return response

    def _handle_expert_interests(self, expert_name: str) -> str:
        """查找专家的研究领域"""
        query = """
        MATCH (e:Expert {name: $name})-[:INTERESTED_IN]->(i:Interest)
        RETURN i.name
        """
        results = self.graph.run(query, name=expert_name).data()
        
        if not results:
            return f"抱歉,没有找到{expert_name}的研究领域信息"
            
        interests = [r["i.name"] for r in results]
        return f"{expert_name}的研究领域包括: {', '.join(interests)}"

    def _handle_expert_h_index(self, expert_name: str) -> str:
        """查询专家的h指数"""
        query = """
        MATCH (e:Expert {name: $name})
        RETURN e.h_index
        """
        result = self.graph.run(query, name=expert_name).data()
        
        if not result:
            return f"抱歉,没有找到{expert_name}的h指数信息"
            
        return f"{expert_name}的h指数为: {result[0]['e.h_index']}"

    def _handle_expert_publications(self, expert_name: str) -> str:
        """查询专家发表的论文"""
        query = """
        MATCH (e:Expert {name: $name})-[:AUTHORED]->(p:Publication)
        RETURN p.title
        """
        results = self.graph.run(query, name=expert_name).data()
        
        if not results:
            return f"抱歉,没有找到{expert_name}发表的论文"
            
        response = f"{expert_name}发表的论文包括:\n"
        for r in results:
            response += f"- {r['p.title']}\n"
        return response

    def _handle_publication_authors(self, title: str) -> str:
        """查��论文的作者"""
        query = """
        MATCH (e:Expert)-[:AUTHORED]->(p:Publication)
        WHERE p.title CONTAINS $title
        RETURN e.name
        """
        results = self.graph.run(query, title=title).data()
        
        if not results:
            return f"抱歉,没有找到论文《{title}》的作者信息"
            
        authors = [r["e.name"] for r in results]
        return f"论文《{title}》的作者是: {', '.join(authors)}"

    def _handle_cooperation(self, experts: tuple) -> str:
        """查询两位专家的合作关系"""
        try:
            expert1, expert2 = experts
            print(f"- 正在查询 {expert1} 和 {expert2} 的合作关系")
            
            query = """
            MATCH (e1:Expert)-[:AUTHORED]->(p:Publication)<-[:AUTHORED]-(e2:Expert)
            WHERE e1.name CONTAINS $name1 AND e2.name CONTAINS $name2
            RETURN p.title, p.year
            ORDER BY p.year DESC
            """
            results = self.graph.run(query, name1=expert1, name2=expert2).data()
            
            if not results:
                return f"未发现{expert1}和{expert2}有直接的合作论文"
            
            response = f"{expert1}和{expert2}合作发表的论文:\n"
            for r in results:
                year = f"({r['p.year']})" if r.get('p.year') else ""
                response += f"- {r['p.title']} {year}\n"
            return response
            
        except Exception as e:
            return f"抱歉,查询合作关系时出现错误: {str(e)}"

    def _handle_top_experts_in_field(self, field: str) -> str:
        """查询某领域最具影响力的专家"""
        field_en = self._map_field_name(field)
        # 使用与_handle_expert_by_interest相同的查询逻辑
        return self._handle_expert_by_interest(field_en)

    def _find_similar_fields(self, field: str) -> List[str]:
        """查找相似的研究领域"""
        field_en = self._map_field_name(field)
        query = """
        MATCH (i:Interest)
        RETURN DISTINCT i.name as name
        """
        all_fields = [r['name'] for r in self.graph.run(query).data()]
        print(f"正在查找与 {field_en} 相似的领域")
        
        # 使用简单的包含关系查找相似领域
        similar = []
        for f in all_fields:
            if (field_en.lower() in f.lower() or 
                f.lower() in field_en.lower() or 
                any(word in f.lower() for word in field_en.lower().split())):
                similar.append(f)
                print(f"找到相似领域: {f}")
        
        return similar[:5]  # 只返回前5个相似领域

    def _handle_field_publications(self, field: str) -> str:
        """查询领域相关的论文"""
        field_en = self._map_field_name(field)
        print(f"正在查找{field}领域的论文")
        
        # 修改查询语句，使用与最近论文查询相同的去重逻辑
        query = """
        MATCH (p:Publication)<-[:AUTHORED]-(e:Expert)-[:INTERESTED_IN]->(i:Interest)
        WHERE toLower(i.name) = toLower($field_en)
        WITH DISTINCT p.title as title, p.year as year, p.id as id
        MATCH (p:Publication {id: id})<-[:AUTHORED]-(e:Expert)
        WITH title, year, id, 
             COLLECT(DISTINCT {name: e.name, name_zh: e.name_zh}) as authors
        RETURN title, year, authors
        ORDER BY year DESC, title
        LIMIT 10
        """
        
        results = self.graph.run(query, field_en=field_en).data()
        
        if not results:
            # 如果精确匹配没有结果，尝试模糊匹配
            query_fuzzy = """
            MATCH (p:Publication)<-[:AUTHORED]-(e:Expert)-[:INTERESTED_IN]->(i:Interest)
            WHERE toLower(i.name) CONTAINS toLower($field_en)
            WITH DISTINCT p.title as title, p.year as year, p.id as id
            MATCH (p:Publication {id: id})<-[:AUTHORED]-(e:Expert)
            WITH title, year, id, 
                 COLLECT(DISTINCT {name: e.name, name_zh: e.name_zh}) as authors
            RETURN title, year, authors
            ORDER BY year DESC, title
            LIMIT 10
            """
            results = self.graph.run(query_fuzzy, field_en=field_en).data()
            
        if not results:
            return f"抱歉，没有找到{field}领域的相关论文"
        
        # 判断是否使用中文显示
        is_chinese_query = field in self.field_mapping
        field_display = f"{field} ({field_en})" if is_chinese_query else field_en
        
        response = f"{field_display}领域的相关论文包括:\n"
        
        # 使用集合来跟踪已处理的论文
        seen_titles = set()
        
        for r in results:
            # 如果论文标题已经处理过，跳过
            if r['title'] in seen_titles:
                continue
            seen_titles.add(r['title'])
            
            year = f"({r['year']})" if r.get('year') else ""
            
            # 处理多个作者的显示
            author_displays = []
            for author in r['authors']:
                if is_chinese_query and author['name'] and author['name_zh']:
                    author_displays.append(f"{author['name_zh']} ({author['name']})")
                else:
                    author_displays.append(author['name_zh'] if author['name_zh'] else author['name'])
            
            authors = f" - 作者: {', '.join(author_displays)}" if author_displays else ""
            response += f"- {r['title']} {year}{authors}\n"
        
        return response

    def _handle_recent_field_publications(self, field: str) -> str:
        """查询领域最近的论文"""
        field_en = self._map_field_name(field)
        print(f"正在查找{field}领域最近的论文")
        
        # 修改查询语句，先聚合论文信息再处理作者
        query = """
        MATCH (p:Publication)<-[:AUTHORED]-(e:Expert)-[:INTERESTED_IN]->(i:Interest)
        WHERE toLower(i.name) = toLower($field_en) AND p.year IS NOT NULL
        WITH DISTINCT p.title as title, p.year as year, p.id as id
        MATCH (p:Publication {id: id})<-[:AUTHORED]-(e:Expert)
        WITH title, year, id, 
             COLLECT(DISTINCT {name: e.name, name_zh: e.name_zh}) as authors
        RETURN title, year, authors
        ORDER BY year DESC, title
        LIMIT 5
        """
        
        results = self.graph.run(query, field_en=field_en).data()
        
        if not results:
            # 如果精确匹配没有结果，尝试模糊匹配
            query_fuzzy = """
            MATCH (p:Publication)<-[:AUTHORED]-(e:Expert)-[:INTERESTED_IN]->(i:Interest)
            WHERE toLower(i.name) CONTAINS toLower($field_en) AND p.year IS NOT NULL
            WITH DISTINCT p.title as title, p.year as year, p.id as id
            MATCH (p:Publication {id: id})<-[:AUTHORED]-(e:Expert)
            WITH title, year, id, 
                 COLLECT(DISTINCT {name: e.name, name_zh: e.name_zh}) as authors
            RETURN title, year, authors
            ORDER BY year DESC, title
            LIMIT 5
            """
            results = self.graph.run(query_fuzzy, field_en=field_en).data()
            
        if not results:
            return f"抱歉，没有找到{field}领域的相关论文"
        
        # 判断是否使用中文显示
        is_chinese_query = field in self.field_mapping
        field_display = f"{field} ({field_en})" if is_chinese_query else field_en
        
        # 获取最新年份
        latest_year = results[0]['year']
        response = f"{field_display}领域最近({latest_year}年)的研究论文包括:\n"
        
        # 使用集合来跟踪已处理的论文
        seen_titles = set()
        
        for r in results:
            # 如果论文标题已经处理过，跳过
            if r['title'] in seen_titles:
                continue
            seen_titles.add(r['title'])
            
            year = f"({r['year']})" if r.get('year') else ""
            
            # 处理多个作者的显示
            author_displays = []
            for author in r['authors']:
                if is_chinese_query and author['name'] and author['name_zh']:
                    author_displays.append(f"{author['name_zh']} ({author['name']})")
                else:
                    author_displays.append(author['name_zh'] if author['name_zh'] else author['name'])
            
            authors = f" - 作者: {', '.join(author_displays)}" if author_displays else ""
            response += f"- {r['title']} {year}{authors}\n"
        
        return response

    def _handle_publication_year(self, title: str) -> str:
        """查询论文发表年份"""
        print(f"正在查找论文 {title} 的发表年份")
        
        # 查询论文信息
        query = """
        MATCH (p:Publication)
        WHERE p.title CONTAINS $title
        WITH DISTINCT p.title as title, p.year as year, p.id as id
        MATCH (p:Publication {id: id})<-[:AUTHORED]-(e:Expert)
        WITH title, year, 
             COLLECT(DISTINCT {name: e.name, name_zh: e.name_zh}) as authors
        RETURN title, year, authors
        """
        
        results = self.graph.run(query, title=title).data()
        
        if not results:
            return f"抱歉，没有找到标题包含 '{title}' 的论文"
        
        response = ""
        seen_titles = set()
        
        for r in results:
            if r['title'] in seen_titles:
                continue
            seen_titles.add(r['title'])
            
            # 处理作者显示
            author_displays = []
            for author in r['authors']:
                if author['name_zh']:
                    author_displays.append(f"{author['name_zh']} ({author['name']})")
                else:
                    author_displays.append(author['name'])
            
            authors = f"作者: {', '.join(author_displays)}" if author_displays else ""
            year = r['year'] if r.get('year') else "未知"
            
            response += f"论文 '{r['title']}' 发表于 {year}年\n"
            if authors:
                response += f"{authors}\n"
        
        return response.strip()

    def _handle_publication_field(self, title: str) -> str:
        """查询论文所属领域"""
        print(f"正在查找论文 {title} 的研究领域")
        
        # 查询论文相关的领域信息
        query = """
        MATCH (p:Publication)<-[:AUTHORED]-(e:Expert)-[:INTERESTED_IN]->(i:Interest)
        WHERE p.title CONTAINS $title
        WITH DISTINCT p.title as title, p.year as year,
             COLLECT(DISTINCT i.name) as interest_names,
             COLLECT(DISTINCT {name: e.name, name_zh: e.name_zh}) as authors
        RETURN title, year, interest_names, authors
        """
        
        results = self.graph.run(query, title=title).data()
        
        if not results:
            return f"抱歉，没有找到标题包含 '{title}' 的论文"
        
        response = ""
        seen_titles = set()
        
        for r in results:
            if r['title'] in seen_titles:
                continue
            seen_titles.add(r['title'])
            
            # 处理作者显示
            author_displays = []
            for author in r['authors']:
                if author['name_zh']:
                    author_displays.append(f"{author['name_zh']} ({author['name']})")
                else:
                    author_displays.append(author['name'])
            
            # 处理领域显示
            fields = r['interest_names']
            fields_display = ', '.join(fields) if fields else "未知"
            
            year = f" ({r['year']}年)" if r.get('year') else ""
            authors = f"\n作者: {', '.join(author_displays)}" if author_displays else ""
            
            response += f"论文 '{r['title']}'{year} 的研究领域包括:\n"
            response += f"- {fields_display}{authors}\n"
        
        return response.strip()

    def search_experts_by_field(self, field: str) -> list:
        """按研究领域搜索专家"""
        return self._handle_expert_by_interest(field)

    def search_experts_by_h_index(self, min_h: int, max_h: int) -> list:
        """按h指数范围搜索专家"""
        query = """
        MATCH (e:Expert)
        WHERE e.h_index >= $min_h AND e.h_index <= $max_h
        RETURN e.name as name, e.name_zh as name_zh, e.h_index as h_index
        ORDER BY e.h_index DESC
        """
        results = self.graph.run(query, min_h=min_h, max_h=max_h).data()
        return results

    def search_experts_by_interest(self, interest: str) -> list:
        """按研究兴趣搜索专家"""
        return self._handle_expert_by_interest(interest)

    def get_collaboration_network(self, expert_name: str, depth: int = 2) -> dict:
        """获取专家合作网络"""
        query = f"""
        MATCH path = (e1:Expert)-[:AUTHORED*1..{depth}]-(e2:Expert)
        WHERE e1.name CONTAINS $name
        WITH DISTINCT e1, e2
        RETURN e1.name as source, e2.name as target
        LIMIT 50
        """
        results = self.graph.run(query, name=expert_name).data()
        
        # 构建网络数据
        nodes = set()
        links = []
        for r in results:
            nodes.add(r['source'])
            nodes.add(r['target'])
            links.append({"source": r['source'], "target": r['target']})
        
        return {
            "nodes": [{"name": name} for name in nodes],
            "links": links
        }

    def get_h_index_distribution(self) -> list:
        """获取h指数分布数据"""
        query = """
        MATCH (e:Expert)
        WHERE e.h_index IS NOT NULL
        RETURN e.h_index as h_index
        """
        results = self.graph.run(query).data()
        return [r['h_index'] for r in results]

    def get_field_distribution(self) -> dict:
        """获取研究领域分布数据"""
        query = """
        MATCH (i:Interest)<-[:INTERESTED_IN]-(e:Expert)
        WITH i.name as field, COUNT(DISTINCT e) as count
        RETURN field, count
        ORDER BY count DESC
        LIMIT 10
        """
        results = self.graph.run(query).data()
        return {r['field']: r['count'] for r in results}

def main():
    # 创建问答系统实例
    qa = KnowledgeQA(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="123456"  # 替换为你的密码
    )
    
    print("欢迎使用专家知识图谱问答系统!")
    print("您可以询问关于专家、研究领域、论文的问题")
    print("输入'退出'结束对话")
    
    while True:
        question = input("\n请输入您的问题: ").strip()
        if question in ['退出', 'quit', 'exit']:
            break
            
        answer = qa.answer(question)
        print(f"\n{answer}")

if __name__ == "__main__":
    main() 