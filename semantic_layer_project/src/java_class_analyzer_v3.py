# -*- coding: utf-8 -*-
"""
Java Class Analyzer - Version 3
支持分析 Controller、Service、Util 三种类型的 Java 类
"""
import re
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class JavaClassAnalyzer:
    """Java 类分析器 - 支持多种类型"""

    def __init__(self, java_file: str):
        self.java_file = Path(java_file)
        self.content = self.java_file.read_text(encoding='utf-8')
        self.class_type = self._detect_class_type()

    def _detect_class_type(self) -> str:
        """检测类类型"""
        if 'Controller' in self.java_file.name:
            return 'Controller'
        elif 'Service' in self.java_file.name:
            return 'Service'
        elif 'Util' in self.java_file.name:
            return 'Util'
        else:
            return 'Unknown'

    def analyze(self) -> Dict[str, Any]:
        """分析 Java 类文件"""
        class_info = self._extract_class_info()

        # 根据类型选择不同的方法提取策略
        if self.class_type == 'Controller':
            methods = self._extract_controller_methods()
        elif self.class_type == 'Service':
            methods = self._extract_service_methods()
        elif self.class_type == 'Util':
            methods = self._extract_util_methods()
        else:
            methods = []

        return {
            'class_info': class_info,
            'methods': methods,
