"""
上下文提取器 - 提取编码约束和示例
"""
from typing import List, Dict, Any
from collections import Counter
import re


class ContextExtractor:
    """上下文提取器"""

    def extract(self, entities: List[Dict], patterns: List[Dict]) -> Dict[str, Any]:
        """提取上下文信息"""
        # 提取编码约束
        constraints = self._extract_constraints(entities)

        # 收集代码示例
        examples = self._collect_examples(entities, patterns)

        return {
            'constraints': constraints,
            'examples': examples
        }

    def _extract_constraints(self, entities: List[Dict]) -> List[Dict]:
        """提取编码约束"""
        constraints = []

        # 命名规范
        naming_constraint = self._analyze_naming_convention(entities)
        constraints.append(naming_constraint)

        # 架构模式
        architecture_constraint = self._analyze_architecture_pattern(entities)
        constraints.append(architecture_constraint)

        return constraints

    def _analyze_naming_convention(self, entities: List[Dict]) -> Dict:
        """分析命名规范"""
        # 统计命名风格
        styles = []
        for entity in entities:
            name = entity['name']
            if re.match(r'^[a-z][a-zA-Z0-9]*$', name):
                styles.append('camelCase')
            elif re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
                styles.append('PascalCase')
            elif re.match(r'^[a-z_]+$', name):
                styles.append('snake_case')

        most_common = Counter(styles).most_common(1)
        dominant_style = most_common[0][0] if most_common else 'mixed'

        return {
            'type': 'naming_convention',
            'description': f"主要使用 {dominant_style} 命名风格",
            'enforcement': 'SHOULD',
            'examples': [
                f"函数: {dominant_style}",
                f"类: PascalCase"
            ]
        }

    def _analyze_architecture_pattern(self, entities: List[Dict]) -> Dict:
        """分析架构模式"""
        # 统计语义角色
        roles = [e.get('semantic_role', 'unknown') for e in entities]
        role_counts = Counter(roles)

        # 判断是否使用分层架构
        has_layers = all(role in role_counts for role in ['controller', 'service'])

        if has_layers:
            pattern = "分层架构 (Controller → Service → Repository)"
        else:
            pattern = "未识别明确的架构模式"

        return {
            'type': 'architecture_pattern',
            'description': pattern,
            'enforcement': 'SHOULD',
            'details': dict(role_counts)
        }

    def _collect_examples(self, entities: List[Dict], patterns: List[Dict]) -> List[Dict]:
        """收集代码示例"""
        examples = []

        # 为每种语义角色收集一个示例
        role_examples = {}
        for entity in entities:
            role = entity.get('semantic_role', 'unknown')
            if role not in role_examples and role != 'unknown':
                role_examples[role] = entity

        for role, entity in role_examples.items():
            examples.append({
                'title': f"{role.title()} 示例",
                'symbol': entity['name'],
                'file_path': entity['file_path'],
                'line': entity['start_line'],
                'description': entity.get('responsibility', ''),
                'role': role
            })

        return examples
