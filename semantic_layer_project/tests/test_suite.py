# -*- coding: utf-8 -*-
"""
Test Suite - Three Round Testing
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from main import SemanticLayerGenerator


def test_round_1_runability():
    """Round 1: Runability Test"""
    print("=" * 60)
    print("Round 1: Runability Test")
    print("=" * 60)

    try:
        # Create test repository
        test_repo = Path("F:/semantic_layer_project/tests/test_repo")
        test_repo.mkdir(parents=True, exist_ok=True)

        # Create test files
        (test_repo / "user_service.py").write_text("""
class UserService:
    '''User service'''

    def validate_user(self, username, password):
        '''Validate user credentials'''
        return True

    def create_user(self, username, email):
        '''Create new user'''
        pass
""", encoding='utf-8')

        (test_repo / "auth_controller.py").write_text("""
from user_service import UserService

class AuthController:
    '''Authentication controller'''

    def __init__(self):
        self.user_service = UserService()

    def handle_login(self, username, password):
        '''Handle login request'''
        return self.user_service.validate_user(username, password)
""", encoding='utf-8')

        print(f"[OK] Test repository created: {test_repo}")

        # Run generator
        generator = SemanticLayerGenerator(str(test_repo), use_gitnexus=False)
        output_file = generator.generate(
            "F:/semantic_layer_project/tests/output/test_semantic_layer.md"
        )

        print(f"[OK] Semantic layer generated: {output_file}")

        # Verify output file exists
        if Path(output_file).exists():
            print("[OK] Output file exists")
            file_size = Path(output_file).stat().st_size
            print(f"[OK] File size: {file_size} bytes")

            if file_size > 100:
                print("\n[PASS] Round 1: System runs successfully")
                return True
            else:
                print("\n[FAIL] Round 1: Output file too small")
                return False
        else:
            print("\n[FAIL] Round 1: Output file does not exist")
            return False

    except Exception as e:
        print(f"\n[FAIL] Round 1: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_round_2_accuracy():
    """Round 2: Accuracy Test"""
    print("\n" + "=" * 60)
    print("Round 2: Accuracy Test")
    print("=" * 60)

    try:
        output_file = Path("F:/semantic_layer_project/tests/output/test_semantic_layer.md")
        if not output_file.exists():
            print("[FAIL] Output file does not exist, run Round 1 first")
            return False

        content = output_file.read_text(encoding='utf-8')

        # Check key sections
        checks = {
            "Title exists": "# Semantic Layer" in content,
            "Business Domains": "## Business Domains" in content,
            "Code Entity Semantics": "## Code Entity Semantics" in content,
            "Execution Patterns": "## Execution Patterns" in content,
            "Side Effects": "## Side Effects" in content,
            "Coding Constraints": "## Coding Constraints" in content,
            "Code Examples": "## Code Examples" in content,
            "Statistics": "## Statistics" in content,
        }

        passed = 0
        total = len(checks)

        for check_name, result in checks.items():
            status = "[OK]" if result else "[FAIL]"
            print(f"{status} {check_name}: {'Pass' if result else 'Fail'}")
            if result:
                passed += 1

        # Check semantic recognition
        semantic_checks = {
            "Recognize UserService": "UserService" in content,
            "Recognize AuthController": "AuthController" in content,
            "Recognize validate_user": "validate_user" in content,
            "Recognize handle_login": "handle_login" in content,
        }

        print("\nSemantic Recognition:")
        for check_name, result in semantic_checks.items():
            status = "[OK]" if result else "[FAIL]"
            print(f"{status} {check_name}: {'Pass' if result else 'Fail'}")
            if result:
                passed += 1

        total += len(semantic_checks)
        accuracy = (passed / total) * 100

        print(f"\nAccuracy: {accuracy:.1f}% ({passed}/{total})")

        if accuracy >= 80:
            print("\n[PASS] Round 2: Accuracy meets requirements")
            return True
        else:
            print("\n[FAIL] Round 2: Accuracy insufficient")
            return False

    except Exception as e:
        print(f"\n[FAIL] Round 2: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_round_3_effectiveness():
    """Round 3: Effectiveness Test"""
    print("\n" + "=" * 60)
    print("Round 3: Effectiveness Test")
    print("=" * 60)

    try:
        output_file = Path("F:/semantic_layer_project/tests/output/test_semantic_layer.md")
        if not output_file.exists():
            print("[FAIL] Output file does not exist, run Round 1 first")
            return False

        content = output_file.read_text(encoding='utf-8')

        # Evaluate if it helps Agent understand code
        effectiveness_checks = {
            "Provides business semantics": any(keyword in content for keyword in ["Business", "Semantic", "Responsibility"]),
            "Describes execution behavior": any(keyword in content for keyword in ["Execution", "Side Effects", "Risk"]),
            "Provides coding conventions": any(keyword in content for keyword in ["Constraints", "Convention", "Pattern"]),
            "Contains code examples": "Examples" in content or "Location" in content,
            "Clear structure": content.count("##") >= 5,
            "Complete information": len(content) > 1000,
            "Good readability": "Table of Contents" in content or "Usage" in content,
        }

        passed = 0
        total = len(effectiveness_checks)

        for check_name, result in effectiveness_checks.items():
            status = "[OK]" if result else "[FAIL]"
            print(f"{status} {check_name}: {'Pass' if result else 'Fail'}")
            if result:
                passed += 1

        effectiveness = (passed / total) * 100

        print(f"\nEffectiveness: {effectiveness:.1f}% ({passed}/{total})")

        # Additional evaluation
        print("\nAgent Usability:")

        has_usage = "Usage" in content or "How to Use" in content
        print(f"[{'OK' if has_usage else 'FAIL'}] Contains usage guide")

        has_confidence = "Confidence" in content
        print(f"[{'OK' if has_confidence else 'FAIL'}] Contains confidence info")

        has_location = "Location" in content or "file_path" in content
        print(f"[{'OK' if has_location else 'FAIL'}] Contains code location info")

        if effectiveness >= 70:
            print("\n[PASS] Round 3: Effectively helps Agent understand code")
            return True
        else:
            print("\n[FAIL] Round 3: Effectiveness insufficient")
            return False

    except Exception as e:
        print(f"\n[FAIL] Round 3: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("AI Agent Semantic Layer System - Three Round Testing")
    print("=" * 60 + "\n")

    results = []

    # Round 1: Runability
    result1 = test_round_1_runability()
    results.append(("Runability", result1))

    if result1:
        # Round 2: Accuracy
        result2 = test_round_2_accuracy()
        results.append(("Accuracy", result2))

        # Round 3: Effectiveness
        result3 = test_round_3_effectiveness()
        results.append(("Effectiveness", result3))
    else:
        print("\n[WARN] Round 1 failed, skipping subsequent tests")
        results.append(("Accuracy", False))
        results.append(("Effectiveness", False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{test_name}: {status}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\nOverall Pass Rate: {(passed/total)*100:.1f}% ({passed}/{total})")

    if passed == total:
        print("\n[SUCCESS] All tests passed! System ready for use.")
        return 0
    else:
        print("\n[WARN] Some tests failed, needs improvement.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
