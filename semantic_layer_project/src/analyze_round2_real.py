# -*- coding: utf-8 -*-
"""
第二轮分析脚本 - 使用扩展的v2代码
直接在v2基础上添加Service和Util支持
"""
import sys
import re
from pathlib import Path
from datetime import datetime

# 直接导入v2的函数
sys.path.insert(0, str(Path(__file__).parent))
from java_api_analyzer_v2 import (
    _determine_business_domain,
    _determine_semantic_role,
    _analyze_side_effects,
    _assess_risk_level,
    _explain_risk,
    _generate_responsibility
)


def analyze_java_class(file_path: str):
    """分析Java类（Controller/Service/Util）"""
    file_obj = Path(file_path)
    content = file_obj.read_text(encoding='utf-8')

    # 检测类型
    if 'Controller' in file_obj.name:
        class_type = 'Controller'
    elif 'Service' in file_obj.name:
        class_type = 'Service'
    elif 'Util' in file_obj.name:
        class_type = 'Util'
    else:
        class_type = 'Unknown'

    # 提取类信息
    class_match = re.search(r'(?:public\s+)?(?:interface|class)\s+(\w+)', content)
    class_name = class_match.group(1) if class_match else 'Unknown'

    class_comment_pattern = r'/\*\*\s*\n\s*\*\s*([^\n]+).*?\*/\s*(?:@\w+.*?\n)*\s*(?:public\s+)?(?:interface|class)'
    class_comment_match = re.search(class_comment_pattern, content, re.DOTALL)
    class_comment = class_comment_match.group(1).strip() if class_comment_match else ''

    package_match = re.search(r'package\s+([\w.]+);', content)
    package = package_match.group(1) if package_match else ''

    class_info = {
        'name': class_name,
        'comment': class_comment,
        'package': package
    }

    # 根据类型提取方法
    if class_type == 'Controller':
        methods = extract_controller_methods(content)
    elif class_type == 'Service':
        methods = extract_service_methods(content)
    elif class_type == 'Util':
        methods = extract_util_methods(content)
    else:
        methods = []

    return {
        'class_info': class_info,
        'class_type': class_type,
        'methods': methods,
        'file_path': str(file_path)
    }


def extract_controller_methods(content: str):
    """提取Controller方法（复用v2逻辑）"""
    methods = []
    pattern = r'/\*\*\s*\n\s*\*\s*([^\n]+).*?\*/\s*((?:@\w+(?:\([^)]*\))?\s*\n\s*)*?)@(GetMapping|PostMapping|PutMapping|DeleteMapping)\s*\("([^"]+)"\)\s*public\s+\S+\s+(\w+)\s*\(([^)]*)\)'

    for match in re.finditer(pattern, content, re.DOTALL):
        methods.append({
            'comment': match.group(1).strip(),
            'http_method': {'GetMapping': 'GET', 'PostMapping': 'POST', 'PutMapping': 'PUT', 'DeleteMapping': 'DELETE'}[match.group(3)],
            'url': match.group(4),
            'method_name': match.group(5),
            'parameters': [],
            'annotations': []
        })

    return methods


def extract_service_methods(content: str):
    """提取Service接口方法"""
    methods = []
    pattern = r'/\*\*\s*\n\s*\*\s*([^\n]+).*?\*/\s*(\w+(?:<[^>]+>)?)\s+(\w+)\s*\(([^)]*)\);'

    for match in re.finditer(pattern, content, re.DOTALL):
        methods.append({
            'comment': match.group(1).strip(),
            'method_name': match.group(3),
            'return_type': match.group(2),
            'parameters': [],
            'annotations': []
        })

    return methods


def extract_util_methods(content: str):
    """提取Util静态方法"""
    methods = []
    pattern = r'/\*\*\s*\n\s*\*\s*([^\n]+).*?\*/\s*public\s+static\s+(\w+(?:<[^>]+>)?)\s+(\w+)\s*\('

    for match in re.finditer(pattern, content, re.DOTALL):
        methods.append({
            'comment': match.group(1).strip(),
            'method_name': match.group(3),
            'return_type': match.group(2),
            'parameters': [],
            'annotations': [],
            'is_static': True
        })

    return methods


def generate_simple_doc(class_info, class_type, methods, file_path):
    """生成简化的文档"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    domain = _determine_business_domain(file_path)

    md = f"""# {class_info['name']} - 语义层文档

> 类型：{class_type}
> 生成时间：{timestamp}
> 文件路径：`{file_path}`

---

## 类概览

- **类名**：{class_info['name']}
- **类型**：{class_type}
- **描述**：{class_info['comment']}
- **包路径**：{class_info['package']}
- **业务域**：{domain}
- **方法数量**：{len(methods)}

## 方法列表

"""

    for idx, method in enumerate(methods, 1):
        md += f"\n### {idx}. {method['method_name']}\n\n"
        md += f"- **描述**：{method['comment']}\n"

        if class_type == 'Controller':
            md += f"- **HTTP方法**：{method['http_method']}\n"
            md += f"- **URL**：`{method['url']}`\n"
        else:
            md += f"- **返回类型**：{method.get('return_type', 'void')}\n"

        if method.get('is_static'):
            md += f"- **静态方法**：是\n"

        md += "\n"

    md += "\n---\n\n*由 AI Agent 语义层生成系统生成*\n"

    return md


def main():
    print("=" * 60)
    print("第二轮分析：使用扩展的v2代码")
    print("=" * 60)

    files = [
        ("F:/12306/services/pay-service/src/main/java/org/opengoofy/index12306/biz/payservice/controller/PayController.java", "Controller"),
        ("F:/12306/services/pay-service/src/main/java/org/opengoofy/index12306/biz/payservice/service/PayService.java", "Service"),
        ("F:/12306/frameworks/cache/src/main/java/org/opengoofy/index12306/framework/starter/cache/toolkit/CacheUtil.java", "Util")
    ]

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path(f"F:/semantic_layer_project/output/round2_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n输出目录：{output_dir}\n")

    results = []

    for idx, (file_path, expected_type) in enumerate(files, 1):
        file_obj = Path(file_path)
        print(f"[{idx}/3] 分析 {expected_type}: {file_obj.name}")

        try:
            result = analyze_java_class(file_path)
            class_name = result['class_info']['name']
            method_count = len(result['methods'])

            print(f"       类名：{class_name}")
            print(f"       方法数量：{method_count}")

            md_content = generate_simple_doc(
                result['class_info'],
                result['class_type'],
                result['methods'],
                result['file_path']
            )

            output_file = output_dir / f"{idx:02d}_{class_name}.md"
            output_file.write_text(md_content, encoding='utf-8')

            print(f"       [完成] {output_file.name}\n")

            results.append({
                'index': idx,
                'class_name': class_name,
                'class_type': result['class_type'],
                'method_count': method_count,
                'expected_type': expected_type,
                'success': method_count > 0
            })

        except Exception as e:
            print(f"       [错误] {e}\n")
            import traceback
            traceback.print_exc()

    # 生成分析报告
    analysis_file = output_dir / "00_分析报告.md"
    analysis_content = f"""# 第二轮分析报告

> 生成时间：{timestamp.replace('_', ' ')}

## 分析结果

"""

    for r in results:
        status = "✅ 成功" if r['success'] else "❌ 失败"
        analysis_content += f"\n### {r['index']}. {r['class_name']} ({r['expected_type']})\n\n"
        analysis_content += f"- **状态**：{status}\n"
        analysis_content += f"- **方法数量**：{r['method_count']}\n"
        analysis_content += f"- **实际类型**：{r['class_type']}\n\n"

    success_count = sum(1 for r in results if r['success'])
    analysis_content += f"\n## 总结\n\n成功分析：{success_count}/3\n"

    analysis_file.write_text(analysis_content, encoding='utf-8')
    print(f"[完成] 分析报告：{analysis_file.name}")
    print(f"\n输出目录：{output_dir}")


if __name__ == '__main__':
    main()
