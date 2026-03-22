"""
语义推断器 - 为代码添加业务语义
"""
from typing import List, Dict, Any
import re


class SemanticEnricher:
    """语义推断器"""

    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm

    def enrich(self, symbols: List[Dict], clusters: List[Dict]) -> Dict[str, Any]:
        """语义推断"""
        # 识别业务域
        domains = self._identify_domains(clusters)

        # 为每个符号添加语义信息
        entities = []
        for symbol in symbols:
            entity = self._enrich_symbol(symbol, domains)
            entities.append(entity)

        return {
            'domains': domains,
            'entities': entities
        }

    def _identify_domains(self, clusters: List[Dict]) -> List[Dict]:
        """识别业务域"""
        domains = []

        for cluster in clusters:
            # 基于聚类名称推断业务域
            domain_name = self._infer_domain_name(cluster['name'])
            domain = {
                'id': cluster['id'],
                'name': domain_name,
                'description': f"{domain_name} 相关功能",
                'members': cluster['members']
            }
            domains.append(domain)

        return domains

    def _infer_domain_name(self, cluster_name: str) -> str:
        """推断业务域名称"""
        # 简单的关键词匹配
        keywords = {
            'auth': 'Authentication',
            'user': 'User Management',
            'api': 'API',
            'db': 'Database',
            'model': 'Data Model',
            'service': 'Business Service',
            'util': 'Utilities',
            'test': 'Testing',
            'config': 'Configuration'
        }

        cluster_lower = cluster_name.lower()
        for keyword, domain in keywords.items():
            if keyword in cluster_lower:
                return domain

        return cluster_name.title()

    def _enrich_symbol(self, symbol: Dict, domains: List[Dict]) -> Dict:
        """为符号添加语义信息"""
        # 推断语义角色
        semantic_role = self._infer_semantic_role(symbol)

        # 找到所属业务域
        business_domain = self._find_domain(symbol, domains)

        # 生成职责描述
        responsibility = self._generate_responsibility(symbol, semantic_role)

        return {
            **symbol,
            'semantic_role': semantic_role,
            'business_domain': business_domain,
            'responsibility': responsibility,
            'confidence': 0.8  # 基于规则的置信度
        }

    def _infer_semantic_role(self, symbol: Dict) -> str:
        """推断语义角色"""
        name = symbol['name'].lower()

        # 基于命名模式推断
        if 'controller' in name or 'handler' in name:
            return 'controller'
        elif 'service' in name:
            return 'service'
        elif 'model' in name or 'entity' in name:
            return 'model'
        elif 'repository' in name or 'dao' in name:
            return 'repository'
        elif 'validator' in name or 'validate' in name:
            return 'validator'
        elif 'util' in name or 'helper' in name:
            return 'utility'
        elif 'middleware' in name:
            return 'middleware'
        else:
            return 'unknown'

    def _find_domain(self, symbol: Dict, domains: List[Dict]) -> str:
        """找到符号所属的业务域"""
        for domain in domains:
            if symbol['uid'] in domain['members']:
                return domain['name']
        return 'Unknown'

    def _generate_responsibility(self, symbol: Dict, role: str) -> str:
        """生成职责描述"""
        name = symbol['name']

        # 基于 docstring
        if symbol.get('docstring'):
            return symbol['docstring'].split('\n')[0]

        # 基于命名和角色
        if role == 'validator':
            return f"验证 {name} 的有效性"
        elif role == 'controller':
            return f"处理 {name} 相关的请求"
        elif role == 'service':
            return f"提供 {name} 相关的业务逻辑"
        elif role == 'model':
            return f"表示 {name} 数据模型"
        elif role == 'repository':
            return f"管理 {name} 的数据访问"
        else:
            return f"{symbol['kind']}: {name}"
