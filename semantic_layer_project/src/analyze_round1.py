# -*- coding: utf-8 -*-
"""
第一轮分析：TicketOrderController + OrderService + JWTUtil
"""
import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent))

from java_api_analyzer_v2 import JavaAPIAnalyzer, generate_class_semantic_layer


def main():
    print("=" * 60)
    print("第一轮分析：Controller + Service + Util")
    print("=" * 60)

    # 定义要分析的文件
    files_to_analyze = [
        ("F:/12306/services/order-service/src/main/java/org/opengoofy/index12306/biz/orderservice/controller/TicketOrderController.java", "Controller"),
        ("F:/12306/services/order-service/src/main/java/org/opengoofy/index12306/biz/orderservice/service/OrderService.java", "Service"),
        ("F:/12306/frameworks/bizs/user/src/main/java/org/opengoofy/index12306/frameworks/starter/user/toolkit/JWTUtil.java", "Util")
    ]

    # 创建输出目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path(f"F:/semantic_layer_project/output/round1_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n输出目录：{output_dir}\n")

    results = []

    for idx, (file_path, class_type) in enumerate(files_to_analyze, 1):
        file_obj = Path(file_path)
        print(f"[{idx}/3] 分析 {class_type}: {file_obj.name}")

        try:
            analyzer = JavaAPIAnalyzer(file_path)
            result = analyzer.analyze()

            class_name = result['controller']['name']
            method_count = len(result['apis'])

            print(f"       类名：{class_name}")
            print(f"       方法数量：{method_count}")

            # 生成文档
            md_content = generate_class_semantic_layer(
                result['controller'],
                result['apis'],
                result['file_path'],
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

    # 生成准确度分析报告
    if results:
        analysis_file = output_dir / "00_准确度分析.md"
        analysis_content = generate_accuracy_analysis(results, timestamp)
        analysis_file.write_text(analysis_content, encoding='utf-8')
        print(f"[完成] 准确度分析：{analysis_file.name}")

    print(f"\n输出目录：{output_dir}")
    return 0


def generate_accuracy_analysis(results: list, timestamp: str) -> str:
    """生成准确度分析报告"""
    md = f"""# 第一轮分析 - 准确度评估报告

> 生成时间：{timestamp.replace('_', ' ')}
> 分析类数量：{len(results)}

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

### 当前代码的问题

#### 1. Service类分析不准确
- **问题**：当前代码只能分析Controller类的@GetMapping/@PostMapping等注解
- **影响**：Service类的public方法无法被正确识别
- **准确率**：预计 20%

#### 2. Util类分析不准确
- **问题**：Util类通常是静态工具方法，没有Spring注解
- **影响**：无法识别静态方法和工具方法
- **准确率**：预计 10%

#### 3. 方法注释提取
- **问题**：正则表达式专门针对Controller的REST API模式
- **影响**：Service和Util的方法注释可能无法提取
- **准确率**：预计 30%

#### 4. 语义角色判断
- **问题**：语义角色判断基于HTTP方法和URL
- **影响**：Service和Util类没有HTTP方法，无法正确分类
- **准确率**：预计 20%

#### 5. 副作用分析
- **问题**：副作用分析基于URL和HTTP方法
- **影响**：Service和Util的副作用无法准确识别
- **准确率**：预计 30%

---

## 📊 总体评估

| 类型 | 预期准确率 | 主要问题 |
|------|-----------|---------|
| Controller | 92% | 基本准确 |
| Service | 25% | 无法识别业务方法 |
| Util | 15% | 无法识别静态工具方法 |

**平均准确率**：约 44%

---

## 🎯 改进建议

### 优先级1：支持Service类分析
1. 识别@Service注解
2. 提取public方法（不依赖HTTP注解）
3. 分析方法参数和返回值
4. 识别@Transactional等业务注解
5. 根据方法名推断业务语义

### 优先级2：支持Util类分析
1. 识别静态方法（static关键字）
2. 提取工具方法的注释
3. 分析方法签名和参数
4. 识别工具类的用途（JWT、Cache、Date等）

### 优先级3：改进通用分析能力
1. 统一方法提取逻辑
2. 改进注释提取（支持多种格式）
3. 增强语义推断（基于方法名和类型）
4. 优化副作用分析（不依赖HTTP）

---

## 📝 下一步行动

1. **修改代码**：实现上述改进建议
2. **第二轮分析**：使用改进后的代码分析新的3个类
3. **对比评估**：比较改进前后的准确率
4. **持续优化**：根据第二轮结果继续改进

---

*由 AI Agent 语义层生成系统生成*
"""

    return md


if __name__ == '__main__':
    sys.exit(main())
