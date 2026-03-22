"""
代码分析器 - 提取代码结构
"""
import ast
from pathlib import Path
from typing import Dict, List, Any
import json


class CodeAnalyzer:
    """代码分析器"""

    def __init__(self, repo_path: str, use_gitnexus: bool = False):
        self.repo_path = Path(repo_path)
        self.use_gitnexus = use_gitnexus

    def analyze(self) -> Dict[str, Any]:
        """分析代码仓库"""
        if self.use_gitnexus:
            return self._analyze_with_gitnexus()
        else:
            return self._analyze_with_ast()

    def _analyze_with_gitnexus(self) -> Dict[str, Any]:
        """使用 GitNexus 分析（需要先运行 npx gitnexus analyze）"""
        # 读取 GitNexus 生成的索引
        gitnexus_dir = self.repo_path / '.gitnexus'
        if not gitnexus_dir.exists():
            raise FileNotFoundError(
                f"GitNexus 索引不存在。请先运行: npx gitnexus analyze"
            )

        # 这里简化处理，实际应该通过 MCP 协议访问
        # 或者直接读取 LadybugDB 数据库
        return {
            'symbols': [],
            'calls': [],
            'clusters': []
        }

    def _analyze_with_ast(self) -> Dict[str, Any]:
        """使用 AST 直接分析 Python 代码"""
        symbols = []
        calls = []
        clusters = []

        # 遍历所有 Python 文件
        python_files = list(self.repo_path.rglob('*.py'))

        for file_path in python_files:
            # 跳过虚拟环境和测试文件
            if any(p in file_path.parts for p in ['venv', 'env', '__pycache__']):
                continue

            try:
                content = file_path.read_text(encoding='utf-8')
                tree = ast.parse(content)

                # 提取符号
                file_symbols = self._extract_symbols(tree, file_path)
                symbols.extend(file_symbols)

                # 提取调用关系
                file_calls = self._extract_calls(tree, file_path)
                calls.extend(file_calls)

            except Exception as e:
                print(f"   [WARN] Skipping file {file_path}: {e}")

        # 简单聚类：按目录分组
        clusters = self._simple_clustering(symbols)

        return {
            'symbols': symbols,
            'calls': calls,
            'clusters': clusters
        }

    def _extract_symbols(self, tree: ast.AST, file_path: Path) -> List[Dict]:
        """提取符号（函数、类）"""
        symbols = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                symbols.append({
                    'uid': f"Function:{node.name}",
                    'name': node.name,
                    'kind': 'Function',
                    'file_path': str(file_path),
                    'start_line': node.lineno,
                    'docstring': ast.get_docstring(node)
                })
            elif isinstance(node, ast.ClassDef):
                symbols.append({
                    'uid': f"Class:{node.name}",
                    'name': node.name,
                    'kind': 'Class',
                    'file_path': str(file_path),
                    'start_line': node.lineno,
                    'docstring': ast.get_docstring(node)
                })

        return symbols

    def _extract_calls(self, tree: ast.AST, file_path: Path) -> List[Dict]:
        """提取函数调用关系"""
        calls = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append({
                        'caller': str(file_path),
                        'callee': node.func.id,
                        'line': node.lineno
                    })

        return calls

    def _simple_clustering(self, symbols: List[Dict]) -> List[Dict]:
        """简单聚类：按目录分组"""
        clusters_dict = {}

        for symbol in symbols:
            file_path = Path(symbol['file_path'])
            # 使用父目录作为聚类标识
            cluster_key = file_path.parent.name or 'root'

            if cluster_key not in clusters_dict:
                clusters_dict[cluster_key] = {
                    'id': cluster_key,
                    'name': cluster_key,
                    'members': []
                }

            clusters_dict[cluster_key]['members'].append(symbol['uid'])

        return list(clusters_dict.values())
