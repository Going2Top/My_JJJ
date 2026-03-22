"""
语义层生成系统 - 主程序
"""
import sys
import argparse
from pathlib import Path
from typing import Optional
import json

from analyzer import CodeAnalyzer
from semantic_enricher import SemanticEnricher
from behavior_analyzer import BehaviorAnalyzer
from context_extractor import ContextExtractor
from md_generator import MarkdownGenerator


class SemanticLayerGenerator:
    """语义层生成器"""

    def __init__(self, repo_path: str, use_gitnexus: bool = False):
        self.repo_path = Path(repo_path)
        self.use_gitnexus = use_gitnexus

        # 初始化各个组件
        self.analyzer = CodeAnalyzer(repo_path, use_gitnexus)
        self.semantic_enricher = SemanticEnricher()
        self.behavior_analyzer = BehaviorAnalyzer()
        self.context_extractor = ContextExtractor()
        self.md_generator = MarkdownGenerator()

    def generate(self, output_path: Optional[str] = None) -> str:
        """Generate semantic layer document"""
        print("Starting semantic layer generation...")

        # 1. Code analysis
        print("\nPhase 1/5: Analyzing code structure...")
        analysis_result = self.analyzer.analyze()
        print(f"   [OK] Found {len(analysis_result['symbols'])} symbols")
        print(f"   [OK] Found {len(analysis_result['calls'])} call relationships")
        print(f"   [OK] Found {len(analysis_result['clusters'])} code clusters")

        # 2. Semantic enrichment
        print("\nPhase 2/5: Semantic enrichment...")
        semantic_data = self.semantic_enricher.enrich(
            analysis_result['symbols'],
            analysis_result['clusters']
        )
        print(f"   [OK] Identified {len(semantic_data['domains'])} business domains")
        print(f"   [OK] Annotated {len(semantic_data['entities'])} entities")

        # 3. Behavior analysis
        print("\nPhase 3/5: Behavior analysis...")
        behavior_data = self.behavior_analyzer.analyze(
            analysis_result['symbols'],
            analysis_result['calls']
        )
        print(f"   [OK] Identified {len(behavior_data['patterns'])} execution patterns")
        print(f"   [OK] Found {len(behavior_data['side_effects'])} side effects")

        # 4. Context extraction
        print("\nPhase 4/5: Context extraction...")
        context_data = self.context_extractor.extract(
            semantic_data['entities'],
            behavior_data['patterns']
        )
        print(f"   [OK] Extracted {len(context_data['constraints'])} constraints")
        print(f"   [OK] Collected {len(context_data['examples'])} examples")

        # 5. Generate Markdown
        print("\nPhase 5/5: Generating Markdown document...")
        markdown_content = self.md_generator.generate(
            semantic_data=semantic_data,
            behavior_data=behavior_data,
            context_data=context_data,
            repo_info={
                'path': str(self.repo_path),
                'name': self.repo_path.name
            }
        )

        # Save file
        if output_path is None:
            output_path = "F:/semantic_layer_project/output/SEMANTIC_LAYER.md"

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(markdown_content, encoding='utf-8')

        print(f"\n[SUCCESS] Semantic layer generated!")
        print(f"[OUTPUT] File: {output_file}")

        # 生成统计信息
        stats = {
            'symbols': len(analysis_result['symbols']),
            'domains': len(semantic_data['domains']),
            'patterns': len(behavior_data['patterns']),
            'constraints': len(context_data['constraints']),
            'examples': len(context_data['examples'])
        }

        stats_file = output_file.parent / "stats.json"
        stats_file.write_text(json.dumps(stats, indent=2), encoding='utf-8')

        return str(output_file)


def main():
    parser = argparse.ArgumentParser(
        description="生成代码仓库的语义层文档"
    )
    parser.add_argument(
        'command',
        choices=['analyze', 'update'],
        help='命令：analyze（全量分析）或 update（增量更新）'
    )
    parser.add_argument(
        'repo_path',
        help='代码仓库路径'
    )
    parser.add_argument(
        '--output', '-o',
        help='输出文件路径（默认：F:/semantic_layer_project/output/SEMANTIC_LAYER.md）'
    )
    parser.add_argument(
        '--use-gitnexus',
        action='store_true',
        help='使用 GitNexus 进行分析（需要先运行 npx gitnexus analyze）'
    )

    args = parser.parse_args()

    try:
        generator = SemanticLayerGenerator(
            args.repo_path,
            use_gitnexus=args.use_gitnexus
        )
        output_file = generator.generate(args.output)

        print(f"\n[SUCCESS] Semantic layer generated to: {output_file}")
        return 0

    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
