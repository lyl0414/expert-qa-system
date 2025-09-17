from py2neo import Graph, Node, Relationship
import json
from typing import Dict, Any
import logging
from pathlib import Path

class Neo4jImporter:
    def __init__(self, uri: str = "bolt://localhost:7687", 
                 user: str = "neo4j", 
                 password: str = "password"):
        """
        初始化Neo4j连接
        
        Args:
            uri: Neo4j服务器地址
            user: 用户名
            password: 密码
        """
        self.graph = Graph(uri, auth=(user, password))
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    def import_data(self, json_file: str):
        """
        导入JSON数据到Neo4j
        
        Args:
            json_file: JSON文件路径
        """
        try:
            # 读取JSON文件
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 清空现有数据库(可选)
            self.graph.run("MATCH (n) DETACH DELETE n")
            
            # 创建主题节点
            self._create_topic_node(data)
            
            # 创建专家节点及关系
            self._create_expert_nodes(data)
            
            # 创建出版物节点及关系
            self._create_publication_nodes(data)
            
            self.logger.info("数据导入完成")
            
        except Exception as e:
            self.logger.error(f"导入过程中出错: {str(e)}")
            raise

    def _create_topic_node(self, data: Dict[str, Any]):
        """创建主题节点"""
        topic = Node("Topic",
                    id=data['id'],
                    name=data['name'],
                    name_zh=data['name_zh'],
                    level=data['level'])
        self.graph.create(topic)
        self.logger.info(f"创建主题节点: {data['name']}")
        return topic

    def _create_expert_nodes(self, data: Dict[str, Any]):
        """创建专家节点及其关系"""
        topic = self.graph.nodes.match("Topic", id=data['id']).first()
        
        for expert_data in data['experts']:
            # 创建专家节点
            expert = Node("Expert",
                        id=expert_data['id'],
                        name=expert_data['name'],
                        name_zh=expert_data.get('name_zh', ''),
                        position=expert_data.get('position', ''),
                        h_index=expert_data.get('h_index', 0))
            self.graph.create(expert)
            
            # 创建专家与主题的关系
            research_in = Relationship(expert, "RESEARCH_IN", topic)
            self.graph.create(research_in)
            
            # 创建研究兴趣节点及关系
            for interest in expert_data.get('interests', []):
                interest_node = Node("Interest", name=interest)
                self.graph.merge(interest_node, "Interest", "name")
                
                interested_in = Relationship(expert, "INTERESTED_IN", interest_node)
                self.graph.create(interested_in)
            
            self.logger.info(f"创建专家节点: {expert_data['name']}")

    def _create_publication_nodes(self, data: Dict[str, Any]):
        """创建出版物节点及其关系"""
        for pub_data in data['publications']:
            # 创建出版物节点
            publication = Node("Publication",
                             id=pub_data['id'],
                             title=pub_data['title'],
                             year=pub_data.get('year', 0))  # 添加year属性，如果没有则默认为0
            self.graph.create(publication)
            
            # 创建作者与出版物的关系
            for author in pub_data['authors']:
                # 查找或创建作者节点
                expert = self.graph.nodes.match("Expert", id=author['id']).first()
                if not expert:
                    # 如果作者节点不存在，创建新的作者节点
                    expert = Node("Expert",
                                id=author['id'] if author['id'] else author['name'],  # 如果没有id则使用name作为id
                                name=author['name'])
                    self.graph.create(expert)
                
                # 创建作者与论文的关系
                authored = Relationship(expert, "AUTHORED", publication)
                self.graph.create(authored)
            
            self.logger.info(f"创建出版物节点: {pub_data['title'][:50]}...")

def main():
    # Neo4j连接配置
    config = {
        "uri": "bolt://localhost:7687",
        "user": "neo4j",
        "password": "123456"  # 替换为你的密码
    }
    
    # JSON文件路径
    json_file = "data/demo-time.json"
    
    # 创建导入器并执行导入
    importer = Neo4jImporter(**config)
    importer.import_data(json_file)

if __name__ == "__main__":
    main() 