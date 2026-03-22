"""
行为分析器 - 识别执行模式和副作用
"""
from typing import List, Dict, Any
import re


class BehaviorAnalyzer:
    """行为分析器"""

    def analyze(self, symbols: List[Dict], calls: List[Dict]) -> Dict[str, Any]:
        """分析代码行为"""
        # 识别执行模式
        patterns = self._identify_patterns(symbols)

        # 分析副作用
        side_effects = self._analyze_side_effects(symbols)

        return {
            'patterns': patterns,
            'side_effects': side_effects
        }

    def _identify_patterns(self, symbols: List[Dict]) -> List[Dict]:
        """识别执行模式"""
        patterns = []

        for symbol in symbols:
            # 识别 API 端点
            if self._is_api_endpoint(symbol):
                pattern = {
                    'id': f"pattern_{symbol['uid']}",
                    'type': 'API_ENDPOINT',
                    'entry_point': symbol['name'],
                    'file_path': symbol['file_path'],
                    'line': symbol['start_line'],
                    'description': f"API 端点: {symbol['name']}"
                }
                patterns.append(pattern)

            # 识别事件处理器
            elif self._is_event_handler(symbol):
                pattern = {
                    'id': f"pattern_{symbol['uid']}",
                    'type': 'EVENT_HANDLER',
                    'entry_point': symbol['name'],
                    'file_path': symbol['file_path'],
                    'line': symbol['start_line'],
                    'description': f"事件处理器: {symbol['name']}"
                }
                patterns.append(pattern)

        return patterns

    def _is_api_endpoint(self, symbol: Dict) -> bool:
        """判断是否为 API 端点"""
        name = symbol['name'].lower()
        # 简单的启发式规则
        return any(keyword in name for keyword in [
            'handle', 'endpoint', 'route', 'api'
        ])

    def _is_event_handler(self, symbol: Dict) -> bool:
        """判断是否为事件处理器"""
        name = symbol['name'].lower()
        return any(keyword in name for keyword in [
            'on_', 'handle_event', 'listener'
        ])

    def _analyze_side_effects(self, symbols: List[Dict]) -> List[Dict]:
        """分析副作用"""
        side_effects = []

        for symbol in symbols:
            # 基于命名推断副作用
            effects = self._infer_side_effects(symbol)
            side_effects.extend(effects)

        return side_effects

    def _infer_side_effects(self, symbol: Dict) -> List[Dict]:
        """推断副作用"""
        effects = []
        name = symbol['name'].lower()

        # 数据库操作
        if any(kw in name for kw in ['save', 'create', 'update', 'delete', 'insert']):
            effects.append({
                'symbol': symbol['uid'],
                'type': 'DB_WRITE',
                'description': f"{symbol['name']} 可能执行数据库写操作",
                'risk_level': 'HIGH'
            })

        # API 调用
        if any(kw in name for kw in ['fetch', 'request', 'call_api', 'http']):
            effects.append({
                'symbol': symbol['uid'],
                'type': 'API_CALL',
                'description': f"{symbol['name']} 可能调用外部 API",
                'risk_level': 'MEDIUM'
            })

        # 文件操作
        if any(kw in name for kw in ['write', 'read_file', 'save_file']):
            effects.append({
                'symbol': symbol['uid'],
                'type': 'FILE_IO',
                'description': f"{symbol['name']} 可能执行文件操作",
                'risk_level': 'MEDIUM'
            })

        return effects
