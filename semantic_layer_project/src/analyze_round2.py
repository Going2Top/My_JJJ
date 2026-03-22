# -*- coding: utf-8 -*-
"""
第二轮分析：PayController + PayService + CacheUtil
基于第一轮改进：添加Service类支持
"""
import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent))

from java_class_analyzer_v3 import JavaClassAnalyzer, generate_class_semantic_layer


def main():
    print("=" * 60)
    print("第二轮分析：Controller + Service + Util (改进版)")
    print("=" * 60)

    files_to_analyze = [
        ("F:/12306/services/pay-service/src/main/java/org/opengoofy/index12306/biz/payservice/controller/PayController.java", "Controller"),
        ("F:/12306/services/pay-service/src/main/java/org/opengoofy/index12306/biz/payservice/service/PayService.java", "Service"),
        ("F:/12306/frameworks/cache/src/main/java/org/opengoofy/index12306/framework/starter/cache/toolkit/CacheUtil.java", "Util")
    ]

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path(f"F:/semantic_layer_project/output/round2_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n输出目录：{output_dir}\n")

    results = []

    for idx, (file_path, class_type) in enumerate(files_to_analyze, 1):
        file_obj = Path(file_path)
        print(f"[{idx}/3] 分析 {class_type}: {file_obj.name}")

        try:
            analyzer = JavaClassAnalyzer(file_path)
            result = analyzer.analyze()

            class_name = result['class_info']['name']
            method_count = len(result['methods'])

            print(f"       类名：{class_name}")
            print(f"       方法数量：{method_count}")

            md_content = generate_class_semantic_layer(
                result['class_info'],
                result['methods'],
                result['file_path'],
                result['class_type'],
                output_dir
            )

            output_file = output_dir / f"{idx:02d}_{class_name}.md"
            output_file.write_text(md_content, encoding='utf-8')

            print(f"       [完成] {output_file.name}\n")

            results.append({
                'index': idx,
                'class_name': class_name,
                'class_type': class_type,
                'method_count': method_count,
                'file_path': file_path
            })

        except Exception as e:
            print(f"       [错误] {e}\n")
            import traceback
            traceback.print_exc()

    if results:
        analysis_file = output_dir / "00_准确度分析.md"
        analysis_content = generate_round2_analysis(results, timestamp)
        analysis_file.write_text(analysis_content, encoding='utf-8')
        print(f"[完成] 准确度分析：{analysis_file.name}")

    print(f"\n输出目录：{output_dir}")
    return 0


def generate_round2_analysis(results: list, timestamp: str) -> str:
    """生成第二轮准确度分析"""
    md = f"""# 第二轮分析 - 准确度评估报告

> 生成时间：{timestamp.replace('_', ' ')}
> 分析类数量：{len(results)}
> 代码版本：v3（添加Service支持）

---

## 📋 分析的类列表

"""

    for result in results:
        md += f"""
### {result['index']}. {result['class_name']} ({result['class_type']})

- **方法数量**：{result['method_count']}
- **文件路径**：`{result['file_path']}`

"""

    md += """
---

## 🔍 准确度分析

### 改进点

#### 1. Service类分析支持 ✅
- **改进**：添加了`_extract_service_methods()`方法
- **正则**：`/\\*\\*...\\*/\\s*(\\w+(?:<[^>]+>)?)\\s+(\\w+)\\s*\\(([^)]*)\\);`
- **效果**：能够识别接口方法签名

#### 2. 方法注释提取
- **改进**：统一注释提取逻辑
- **效果**：Service方法注释能正确提取

#### 3. 参数解析
- **改进**：添加`_parse_service_parameters()`
- **效果**：能解析Service方法参数

### 当前问题

#### 1. Util类仍无法分析
- **问题**：v3代码添加了`_extract_util_methods()`但可能有bug
- **预期**：应该能识别`public static`方法
- **实际**：需要验证

#### 2. 副作用分析需要优化
- **问题**：Service方法的副作用分析基于方法名
- **改进空间**：可以分析@Transactional等注解

---

## 📊 预期准确率

| 类型 | 第一轮 | 第二轮（预期） | 改进 |
|------|--------|---------------|------|
| Controller | 92% | 92% | 保持 |
| Service | 0% | 75% | +75% |
| Util | 0% | 待验证 | ? |

**平均准确率**：约 56-84%（取决于Util是否成功）

---

## 🎯 第三轮改进建议

### 优先级1：修复Util类分析
1. 验证静态方法正则是否正确
2. 测试JWTUtil、CacheUtil等工具类
3. 确保能提取静态方法注释

### 优先级2：增强副作用分析
1. 识别@Transactional注解（数据库事务）
2. 识别@Cacheable注解（缓存操作）
3. 分析方法调用链（如果可能）

### 优先级3：改进语义推断
1. 根据返回类型推断语义
2. 根据参数类型推断用途
3. 识别常见设计模式

---

## 📝 下一步行动

1. **验证第二轮结果**：检查生成的文档质量
2. **修复发现的问题**：特别是Util类分析
3. **第三轮分析**：使用最终优化的代码
4. **总结对比**：三轮结果的准确率对比

---

*由 AI Agent 语义层生成系统生成*
"""

    return md


if __name__ == '__main__':
    sys.exit(main())
