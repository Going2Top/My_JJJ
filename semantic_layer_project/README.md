# AI Agent 语义层生成系统

一个自动化系统，能够分析代码仓库并生成高质量的语义层文档（Markdown 格式），帮助 AI Agent 深入理解代码。

## 快速开始

### 安装依赖

```bash
cd F:/semantic_layer_project
pip install -e .
```

### 生成语义层

```bash
# 分析代码仓库并生成语义层
python src/main.py analyze /path/to/your/repo

# 输出文件：F:/semantic_layer_project/output/SEMANTIC_LAYER.md
```

### 运行测试

```bash
# 运行三轮测试
python tests/test_suite.py
```

## 项目结构

```
F:/semantic_layer_project/
├── docs/
│   └── 方案文档.md          # 详细的设计方案
├── src/
│   ├── main.py              # 主程序入口
│   ├── analyzer.py          # 代码分析器
│   ├── semantic_enricher.py # 语义推断器
│   ├── behavior_analyzer.py # 行为分析器
│   ├── context_extractor.py # 上下文提取器
│   └── md_generator.py      # Markdown 生成器
├── tests/
│   ├── test_suite.py        # 测试套件
│   ├── test_repo/           # 测试代码仓库
│   └── output/              # 测试输出
├── output/
│   └── SEMANTIC_LAYER.md    # 生成的语义层文档
└── pyproject.toml           # 项目配置

```

## 功能特性

### 三层语义架构

1. **语义层**：理解"代码是什么"
   - 业务域划分
   - 语义角色识别
   - 职责描述

2. **行为层**：理解"代码做什么"
   - 执行模式识别
   - 副作用分析
   - 影响评估

3. **上下文层**：提供"任务相关上下文"
   - 编码约束
   - 代码示例
   - 最佳实践

### 输出格式

生成的语义层文档（Markdown 格式）包含：

- 📖 使用说明
- 📑 目录结构
- 🏢 业务域划分
- 🔍 代码实体语义
- ⚡ 执行模式
- 🔧 副作用分析
- 📝 编码约束
- 💡 代码示例
- 📊 统计信息

## 使用场景

### 1. 为 AI Agent 提供上下文

```python
# 读取语义层
with open("SEMANTIC_LAYER.md") as f:
    semantic_layer = f.read()

# 作为系统提示词
system_prompt = f"""
你是一个代码助手。以下是代码仓库的语义层：

{semantic_layer}

请基于这个语义层理解代码并生成准确的代码。
"""
```

### 2. 代码审查

使用语义层快速了解代码的业务语义和架构模式。

### 3. 新人入职

帮助新人快速理解代码仓库的结构和规范。

## 配置选项

### 使用 GitNexus（可选）

如果你的项目已经使用 GitNexus 索引：

```bash
# 先运行 GitNexus 分析
npx gitnexus analyze

# 然后使用 GitNexus 数据生成语义层
python src/main.py analyze /path/to/repo --use-gitnexus
```

### 自定义输出路径

```bash
python src/main.py analyze /path/to/repo --output /custom/path/semantic_layer.md
```

## 测试说明

系统包含三轮测试：

### 第一轮：可运行性测试
- 验证系统能否正常运行
- 检查是否能生成输出文件
- 确认文件大小合理

### 第二轮：准确度测试
- 检查文档结构完整性
- 验证关键元素识别准确性
- 评估语义标注质量

### 第三轮：目的达成度测试
- 评估是否能帮助 Agent 理解代码
- 检查文档可读性
- 验证信息完整性

## 质量指标

| 指标 | 目标值 |
|------|--------|
| Agent 代码准确率 | ≥ 90% |
| 语义覆盖率 | ≥ 85% |
| 语义准确率 | ≥ 90% |
| 生成速度 | < 5min/1000文件 |

## 技术栈

- Python 3.10+
- AST 解析（内置 ast 模块）
- GitNexus（可选）
- Markdown 生成

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 联系方式

如有问题，请提交 Issue。
