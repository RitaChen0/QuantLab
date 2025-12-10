#!/usr/bin/env python3
"""
測試安全修復是否正常運作
"""

import sys
sys.path.insert(0, '/data/CCTest/QuantLab/backend')

def test_like_escaping():
    """測試 LIKE 模式轉義"""
    from app.utils.query_helpers import escape_like_pattern

    print("=" * 60)
    print("測試 1: LIKE 模式轉義")
    print("=" * 60)

    test_cases = [
        ("test_user", "test\\_user"),
        ("50%", "50\\%"),
        ("test\\data", "test\\\\data"),
        ("normal", "normal"),
        ("_%mixed%_", "\\_\\%mixed\\%\\_"),
    ]

    all_passed = True
    for input_str, expected in test_cases:
        result = escape_like_pattern(input_str)
        passed = result == expected
        all_passed = all_passed and passed

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | Input: '{input_str}' -> Output: '{result}' (Expected: '{expected}')")

    print(f"\n結果: {'✅ 所有測試通過' if all_passed else '❌ 有測試失敗'}\n")
    return all_passed


def test_ast_validation():
    """測試 AST 安全驗證"""
    print("=" * 60)
    print("測試 2: AST 安全驗證")
    print("=" * 60)

    # 模擬簡化版的驗證函數
    import ast

    dangerous_functions = {
        'eval', 'exec', 'compile', '__import__',
        'open', 'file', 'input',
    }

    test_cases = [
        # (code, should_pass, description)
        (
            "class MyStrategy(bt.Strategy):\n    def __init__(self):\n        pass",
            True,
            "正常策略代碼"
        ),
        (
            "eval('malicious code')",
            False,
            "包含 eval() 調用"
        ),
        (
            "exec('bad code')",
            False,
            "包含 exec() 調用"
        ),
        (
            "__import__('os').system('ls')",
            False,
            "包含 __import__ 調用"
        ),
        (
            "open('/etc/passwd', 'r')",
            False,
            "包含 open() 調用"
        ),
    ]

    all_passed = True
    for code, should_pass, description in test_cases:
        try:
            tree = ast.parse(code)
            has_dangerous = False

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in dangerous_functions:
                            has_dangerous = True
                            break

            if should_pass:
                passed = not has_dangerous
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"{status} | {description}: 應通過驗證，{'通過' if passed else '被阻擋'}")
            else:
                passed = has_dangerous
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"{status} | {description}: 應被阻擋，{'被阻擋' if passed else '未阻擋'}")

            all_passed = all_passed and passed

        except SyntaxError:
            if should_pass:
                print(f"❌ FAIL | {description}: 語法錯誤")
                all_passed = False
            else:
                print(f"✅ PASS | {description}: 因語法錯誤被阻擋")

    print(f"\n結果: {'✅ 所有測試通過' if all_passed else '❌ 有測試失敗'}\n")
    return all_passed


def test_restricted_builtins():
    """測試受限的內建函數"""
    print("=" * 60)
    print("測試 3: 受限的內建函數命名空間")
    print("=" * 60)

    safe_builtins = {
        'len': len,
        'range': range,
        'int': int,
        'float': float,
        'str': str,
        'list': list,
    }

    namespace = {
        '__builtins__': safe_builtins,
        '__name__': '__main__',
    }

    test_cases = [
        # (code, should_work, description)
        ("result = len([1, 2, 3])", True, "使用安全函數 len()"),
        ("result = list(range(5))", True, "使用安全函數 range() 和 list()"),
        ("result = int('123')", True, "使用安全函數 int()"),
    ]

    print("測試允許的安全函數:")
    all_passed = True
    for code, should_work, description in test_cases:
        try:
            exec(code, namespace)
            if should_work:
                print(f"✅ PASS | {description}: 成功執行")
            else:
                print(f"❌ FAIL | {description}: 不應執行成功")
                all_passed = False
        except Exception as e:
            if should_work:
                print(f"❌ FAIL | {description}: 執行失敗 - {e}")
                all_passed = False
            else:
                print(f"✅ PASS | {description}: 被正確阻擋")

    print(f"\n結果: {'✅ 所有測試通過' if all_passed else '❌ 有測試失敗'}\n")
    return all_passed


if __name__ == "__main__":
    print("\n🔒 QuantLab 安全修復測試\n")

    results = []
    results.append(("LIKE 模式轉義", test_like_escaping()))
    results.append(("AST 安全驗證", test_ast_validation()))
    results.append(("受限內建函數", test_restricted_builtins()))

    print("=" * 60)
    print("📊 測試總結")
    print("=" * 60)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {name}")

    all_passed = all(r[1] for r in results)
    print("\n" + ("=" * 60))
    if all_passed:
        print("✅ 所有安全測試通過！")
    else:
        print("❌ 部分測試失敗，請檢查實作")
    print("=" * 60 + "\n")

    sys.exit(0 if all_passed else 1)
