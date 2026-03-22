# -*- coding: utf-8 -*-
"""
Java API Analyzer - Improved Version
专门用于分析 Java Spring MVC Controller 的 API
"""
import re
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class JavaAPIAnalyzer:
    """Java API 分析器（改进版）"""

    def __init__(self, controller_file: str):
        self.controller_file = Path(controller_file)
        self.content = self.controller_file.read_text(encoding='utf-8')

    def analyze(self) -> Dict[str, Any]:
        """分析 Java controller 文件"""
        # 提取类信息
        class_info = self._extract_class_info()

        # 提取 APIs
        apis = self._extract_apis()

        return {
            'controller': class_info,
            'apis': apis,
            'file_path': str(self.controller_file)
        }

    def _extract_class_info(self) -> Dict[str, str]:
        """提取类信息"""
        # 提取类名
        class_match = re.search(r'public\s+class\s+(\w+)', self.content)
        class_name = class_match.group(1) if class_match else 'Unknown'

        # 提取类注释（紧邻 @RestController 之前的注释）
        class_comment_pattern = r'/\*\*\s*\n\s*\*\s*([^\n]+).*?\*/\s*(?:@\w+.*?\n)*\s*@RestController'
        class_comment_match = re.search(class_comment_pattern, self.content, re.DOTALL)
        class_comment = class_comment_match.group(1).strip() if class_comment_match else ''

        # 提取 package
        package_match = re.search(r'package\s+([\w.]+);', self.content)
        package = package_match.group(1) if package_match else ''

        return {
            'name': class_name,
            'comment': class_comment,
            'package': package
        }

    def _extract_apis(self) -> List[Dict[str, Any]]:
        """提取 API 方法（改进版）"""
        apis = []

        # 改进的正则表达式：更准确地提取方法注释
        # 匹配：方法注释 + 注解 + 方法签名
        method_pattern = r'/\*\*\s*\n\s*\*\s*([^\n]+).*?\*/\s*((?:@\w+(?:\([^)]*\))?\s*\n\s*)*?)@(GetMapping|PostMapping|PutMapping|DeleteMapping)\s*\("([^"]+)"\)\s*public\s+Result<[^>]+>\s+(\w+)\s*\(([^)]*)\)'

        for match in re.finditer(method_pattern, self.content, re.DOTALL):
            comment = match.group(1).strip()
            annotations_block = match.group(2)
            http_method_annotation = match.group(3)
            url = match.group(4)
            method_name = match.group(5)
            params = match.group(6)

            # 提取注解
            annotations = self._extract_annotations(annotations_block)

            # 解析参数（改进版）
            param_list = self._parse_parameters(params)

            # 确定 HTTP 方法
            http_method_map = {
                'GetMapping': 'GET',
                'PostMapping': 'POST',
                'PutMapping': 'PUT',
                'DeleteMapping': 'DELETE'
            }
            http_method = http_method_map.get(http_method_annotation, 'UNKNOWN')

            apis.append({
                'comment': comment,
                'http_method': http_method,
                'url': url,
                'method_name': method_name,
                'parameters': param_list,
                'annotations': annotations
            })

        return apis

    def _extract_annotations(self, annotations_block: str) -> List[str]:
        """提取方法注解"""
        annotations = []
        annotation_pattern = r'@(\w+)(?:\([^)]*\))?'

        for match in re.finditer(annotation_pattern, annotations_block):
            annotation = match.group(1)
            # 排除映射注解
            if annotation not in ['GetMapping', 'PostMapping', 'PutMapping', 'DeleteMapping',
                                 'RestController', 'RequiredArgsConstructor']:
                annotations.append(annotation)

        return list(set(annotations))  # 去重

    def _parse_parameters(self, params_str: str) -> List[Dict[str, str]]:
        """解析方法参数（改进版）"""
        if not params_str.strip():
            return []

        params = []

        # 处理 @RequestParam 注解的参数
        request_param_pattern = r'@RequestParam\s*(?:\([^)]*value\s*=\s*"([^"]+)"[^)]*\))?\s+(\w+)\s+(\w+)'
        for match in re.finditer(request_param_pattern, params_str):
            param_name = match.group(1) if match.group(1) else match.group(3)
            param_type = match.group(2)
            params.append({
                'name': param_name,
                'type': param_type,
                'annotation': 'RequestParam'
            })

        # 处理 @RequestBody 注解的参数
        request_body_pattern = r'@RequestBody\s+(\w+)\s+(\w+)'
        for match in re.finditer(request_body_pattern, params_str):
            param_type = match.group(1)
            param_name = match.group(2)
            params.append({
                'name': param_name,
                'type': param_type,
                'annotation': 'RequestBody'
            })

        # 处理 @PathVariable 注解的参数
        path_variable_pattern = r'@PathVariable\s*(?:\([^)]*\))?\s+(\w+)\s+(\w+)'
        for match in re.finditer(path_variable_pattern, params_str):
            param_type = match.group(1)
            param_name = match.group(2)
            params.append({
                'name': param_name,
                'type': param_type,
                'annotation': 'PathVariable'
            })

        return params


def generate_class_semantic_layer(controller_info: Dict[str, str], apis: List[Dict[str, Any]],
                                  file_path: str, output_dir: Path) -> str:
    """为整个 Controller 类生成语义层文档"""

    controller = controller_info

    # 确定业务域
    domain = _determine_business_domain(file_path)

    # 生成时间戳
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 生成 Markdown
    md = f"""# {controller['name']} - API 语义层文档

> 自动生成的 API 语义层文档
>
> 生成时间：{timestamp}
>
> 文件路径：`{file_path}`

---

## 📋 类概览

### 基本信息
- **类名**：{controller['name']}
- **描述**：{controller['comment']}
- **包路径**：{controller['package']}
- **业务域**：{domain}
- **API 数量**：{len(apis)}

### API 列表

"""

    for idx, api in enumerate(apis, 1):
        md += f"{idx}. **{api['method_name']}** - {api['http_method']} `{api['url']}`\n"
        md += f"   - 描述：{api['comment']}\n"
        md += f"   - 语义角色：{_determine_semantic_role(api)}\n\n"

    md += """
---

## 📊 统计信息

"""

    # 统计 HTTP 方法
    http_methods = {}
    for api in apis:
        method = api['http_method']
        http_methods[method] = http_methods.get(method, 0) + 1

    md += "### HTTP 方法分布\n\n"
    for method, count in sorted(http_methods.items()):
        md += f"- **{method}**：{count} 个\n"

    # 统计语义角色
    semantic_roles = {}
    for api in apis:
        role = _determine_semantic_role(api)
        semantic_roles[role] = semantic_roles.get(role, 0) + 1

    md += "\n### 语义角色分布\n\n"
    for role, count in sorted(semantic_roles.items(), key=lambda x: x[1], reverse=True):
        md += f"- **{role}**：{count} 个\n"

    md += "\n---\n\n"

    # 为每个 API 生成详细文档
    for idx, api in enumerate(apis, 1):
        md += _generate_single_api_doc(api, controller, domain, idx)
        md += "\n---\n\n"

    # 附录
    md += f"""
## 📚 附录

### 架构模式
- **模式**：Spring MVC Controller-Service 架构
- **层级**：Controller 层（API 入口点）
- **职责**：处理 HTTP 请求，委托给 Service 层

### 命名规范
- **Controller**：PascalCase，以 'Controller' 结尾
- **方法**：camelCase，动词开头
- **URL**：kebab-case，RESTful 风格

### 响应格式
- 统一包装在 `Result<T>` 中
- 使用 `Results.success()` 辅助方法构造响应

---

*由 AI Agent 语义层生成系统生成*
"""

    return md


def _generate_single_api_doc(api: Dict[str, Any], controller: Dict[str, str],
                             domain: str, index: int) -> str:
    """生成单个 API 的详细文档"""

    semantic_role = _determine_semantic_role(api)
    side_effects = _analyze_side_effects(api)
    risk_level = _assess_risk_level(api, side_effects, domain)
    is_idempotent = 'Idempotent' in api['annotations']

    md = f"""
## {index}. {api['method_name']}

### 基本信息
- **方法名**：`{api['method_name']}`
- **描述**：{api['comment']}
- **HTTP 方法**：{api['http_method']}
- **URL**：`{api['url']}`
- **语义角色**：{semantic_role}
- **业务域**：{domain}

### 语义层

**这个 API 做什么：**
{api['comment']}

**业务职责：**
{_generate_responsibility(api, semantic_role)}

**操作类型：**
{'读操作' if api['http_method'] == 'GET' else '写操作'}

**置信度：** 0.90
- 基于：URL 模式、HTTP 方法、方法名和注解

### 行为层

**执行模式：** REST API 端点

**入口点：**
- 方法：`{controller['name']}.{api['method_name']}()`
- HTTP：`{api['http_method']} {api['url']}`

**请求参数：**
"""

    if api['parameters']:
        for param in api['parameters']:
            md += f"- **{param['name']}** ({param['type']}) - @{param.get('annotation', 'Unknown')}\n"
    else:
        md += "- 无参数\n"

    md += f"""

**副作用：**
"""

    if side_effects:
        for effect in side_effects:
            md += f"- {effect}\n"
    else:
        md += "- 无副作用（只读操作）\n"

    md += f"""

**风险评估：**
- **风险级别**：{risk_level}
- **理由**：{_explain_risk(api, side_effects, risk_level, domain)}

**幂等性：**
- **是否幂等**：{'是' if is_idempotent else '否'}
"""

    if is_idempotent:
        md += "- 此 API 标记了 @Idempotent 注解，确保多次相同请求具有相同效果\n"

    md += f"""

### 上下文层

**注解：**
"""

    for annotation in api['annotations']:
        md += f"- @{annotation}\n"

    md += f"""

**使用指南：**

何时使用此 API：
"""

    if api['http_method'] == 'GET':
        md += f"- 当需要{api['comment']}时使用\n"
        md += "- 这是只读操作，不会修改数据\n"
    else:
        md += f"- 当需要{api['comment']}时使用\n"
        md += "- 这是写操作，会修改数据\n"

    md += f"""

**示例请求：**
```http
{api['http_method']} {api['url']}
Content-Type: application/json
```
"""

    if api['parameters'] and api['http_method'] in ['POST', 'PUT']:
        md += "\n**请求体：**\n```json\n{\n"
        for param in api['parameters']:
            if param.get('annotation') == 'RequestBody':
                md += f'  // {param["type"]} 对象\n'
        md += "}\n```\n"

    md += """

**响应示例：**
```json
{
  "code": "0",
  "message": "success",
  "data": { ... }
}
```

**重要提示：**
"""

    if is_idempotent:
        md += "- ✅ 此 API 是幂等的，失败时可以安全重试\n"

    if api['http_method'] != 'GET':
        md += "- ⚠️ 这是写操作，确保有适当的授权\n"
        md += "- ⚠️ 调用前验证所有输入参数\n"

    if 'ILog' in api['annotations']:
        md += "- 📝 此 API 启用了日志记录（@ILog）\n"

    if risk_level in ['HIGH', 'CRITICAL']:
        md += f"- 🚨 {risk_level} 风险操作，需要特别注意\n"

    return md


def _determine_business_domain(file_path: str) -> str:
    """确定业务域"""
    file_path_lower = file_path.lower()

    if 'order' in file_path_lower:
        return '订单管理'
    elif 'ticket' in file_path_lower:
        return '车票管理'
    elif 'user' in file_path_lower or 'passenger' in file_path_lower:
        return '用户管理'
    elif 'pay' in file_path_lower:
        return '支付管理'
    elif 'refund' in file_path_lower:
        return '退款管理'
    else:
        return '其他'


def _determine_semantic_role(api: Dict[str, Any]) -> str:
    """确定语义角色（改进版）"""
    url = api['url'].lower()
    method_name = api['method_name'].lower()
    http_method = api['http_method']

    # 认证相关
    if 'login' in url or 'login' in method_name:
        return '认证 API'
    if 'logout' in url or 'logout' in method_name:
        return '登出 API'
    if 'register' in url or 'register' in method_name:
        return '注册 API'

    # 购买/支付相关
    if 'purchase' in url or 'purchase' in method_name or 'buy' in url:
        return '购买 API'
    if 'pay' in url and http_method == 'POST':
        return '支付 API'
    if 'refund' in url or 'refund' in method_name:
        return '退款 API'

    # CRUD 操作
    if http_method == 'GET':
        if 'query' in url or 'get' in url or 'list' in url or 'page' in url:
            return '查询 API'
    elif http_method == 'POST':
        if 'create' in url or 'save' in url or 'add' in url:
            return '创建 API'
        if 'update' in url or 'modify' in url or 'edit' in url:
            return '更新 API'
        if 'delete' in url or 'remove' in url or 'cancel' in url or 'close' in url:
            return '删除 API'
    elif http_method == 'PUT':
        return '更新 API'
    elif http_method == 'DELETE':
        return '删除 API'

    return '操作 API'


def _analyze_side_effects(api: Dict[str, Any]) -> List[str]:
    """分析副作用（改进版）"""
    effects = []
    url = api['url'].lower()
    method_name = api['method_name'].lower()
    http_method = api['http_method']

    # GET 请求通常无副作用
    if http_method == 'GET':
        return []

    # 数据库写操作
    if any(kw in url or kw in method_name for kw in ['create', 'save', 'add', 'insert']):
        effects.append('数据库写入：创建新记录')

    if any(kw in url or kw in method_name for kw in ['update', 'modify', 'edit']):
        effects.append('数据库写入：更新现有记录')

    if any(kw in url or kw in method_name for kw in ['delete', 'remove', 'cancel', 'close']):
        effects.append('数据库写入：删除或标记删除记录')

    # 认证相关副作用
    if any(kw in url or kw in method_name for kw in ['login', 'signin']):
        effects.append('会话管理：创建用户会话')
        effects.append('缓存写入：存储认证令牌')

    if any(kw in url or kw in method_name for kw in ['logout', 'signout']):
        effects.append('会话管理：销毁用户会话')
        effects.append('缓存删除：清除认证令牌')

    # 购买/支付相关副作用
    if any(kw in url or kw in method_name for kw in ['purchase', 'buy']):
        effects.append('数据库写入：创建订单')
        effects.append('库存管理：扣减库存')
        effects.append('可能调用外部服务：库存系统')

    if 'pay' in url or 'pay' in method_name:
        effects.append('外部 API 调用：支付网关')
        effects.append('数据库写入：更新支付状态')

    if 'refund' in url or 'refund' in method_name:
        effects.append('外部 API 调用：支付网关退款')
        effects.append('数据库写入：更新退款状态')
        effects.append('库存管理：恢复库存')

    # 如果是 POST/PUT/DELETE 但没有识别到具体副作用，给出通用提示
    if not effects and http_method in ['POST', 'PUT', 'DELETE']:
        effects.append('数据库操作：可能修改数据')

    return effects


def _assess_risk_level(api: Dict[str, Any], side_effects: List[str], domain: str) -> str:
    """评估风险级别（改进版）"""
    url = api['url'].lower()
    method_name = api['method_name'].lower()
    http_method = api['http_method']

    # GET 请求通常是低风险
    if http_method == 'GET':
        return 'LOW'

    # CRITICAL 级别：涉及金额、库存、支付的操作
    critical_keywords = ['pay', 'refund', 'purchase', 'buy', 'order']
    if any(kw in url or kw in method_name for kw in critical_keywords):
        if domain in ['支付管理', '退款管理', '订单管理', '车票管理']:
            return 'CRITICAL'

    # HIGH 级别：认证、用户数据修改、删除操作
    high_keywords = ['login', 'register', 'delete', 'remove', 'cancel', 'update', 'modify']
    if any(kw in url or kw in method_name for kw in high_keywords):
        return 'HIGH'

    # MEDIUM 级别：创建操作
    if any(kw in url or kw in method_name for kw in ['create', 'save', 'add']):
        return 'MEDIUM'

    # 默认：有副作用的 POST 操作为 MEDIUM
    if side_effects:
        return 'MEDIUM'

    return 'LOW'


def _explain_risk(api: Dict[str, Any], side_effects: List[str], risk_level: str, domain: str) -> str:
    """解释风险级别"""
    reasons = []

    if api['http_method'] == 'GET':
        reasons.append('GET 操作，只读，不修改数据')
    else:
        reasons.append(f'{api["http_method"]} 操作，可能修改数据')

    if side_effects:
        reasons.append(f'识别到 {len(side_effects)} 个副作用')

    if risk_level == 'CRITICAL':
        reasons.append(f'涉及{domain}的关键业务操作')
    elif risk_level == 'HIGH':
        reasons.append('涉及敏感数据或重要操作')

    return '；'.join(reasons)


def _generate_responsibility(api: Dict, semantic_role: str) -> str:
    """生成职责描述"""
    comment = api['comment']

    if semantic_role == '查询 API':
        return f"检索并返回{comment}"
    elif semantic_role == '创建 API':
        return f"创建新的{comment}"
    elif semantic_role == '更新 API':
        return f"更新现有的{comment}"
    elif semantic_role == '删除 API':
        return f"删除或取消{comment}"
    elif semantic_role == '认证 API':
        return f"验证用户身份并{comment}"
    elif semantic_role == '购买 API':
        return f"处理购买请求：{comment}"
    elif semantic_role == '支付 API':
        return f"处理支付流程：{comment}"
    elif semantic_role == '退款 API':
        return f"处理退款请求：{comment}"
    else:
        return f"执行操作：{comment}"


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法: python java_api_analyzer_v2.py <controller_file>")
        sys.exit(1)

    controller_file = sys.argv[1]
    analyzer = JavaAPIAnalyzer(controller_file)
    result = analyzer.analyze()

    print(f"Controller: {result['controller']['name']}")
    print(f"发现 API: {len(result['apis'])}")

    for api in result['apis']:
        print(f"  - {api['http_method']} {api['url']} -> {api['method_name']}")
