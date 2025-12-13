#!/usr/bin/env python3
"""
类型提示一致性检查脚本

检查代码中的类型提示覆盖率和一致性，帮助提高代码质量。

使用方法:
    python /app/scripts/check_type_hints.py [--fix]
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Any
from loguru import logger


class TypeHintChecker(ast.NodeVisitor):
    """AST 访问器，检查类型提示"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.issues: List[Dict[str, Any]] = []
        self.stats = {
            "total_functions": 0,
            "functions_with_return_hint": 0,
            "total_params": 0,
            "params_with_hint": 0,
        }

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """访问函数定义"""
        self.stats["total_functions"] += 1

        # 跳过测试文件中的某些函数
        if node.name.startswith("test_"):
            self.generic_visit(node)
            return

        # 跳过魔法方法（除了 __init__）
        if node.name.startswith("__") and node.name != "__init__":
            self.generic_visit(node)
            return

        # 检查返回类型提示
        if node.returns is None:
            # __init__ 方法可以没有返回类型（或应该是 None）
            if node.name != "__init__":
                self.issues.append({
                    "type": "missing_return_type",
                    "function": node.name,
                    "line": node.lineno,
                    "severity": "medium",
                    "message": f"Function '{node.name}' missing return type hint"
                })
        else:
            self.stats["functions_with_return_hint"] += 1

        # 检查参数类型提示
        for arg in node.args.args:
            self.stats["total_params"] += 1

            # 跳过 self 和 cls
            if arg.arg in ("self", "cls"):
                continue

            if arg.annotation is None:
                self.issues.append({
                    "type": "missing_param_type",
                    "function": node.name,
                    "parameter": arg.arg,
                    "line": node.lineno,
                    "severity": "low",
                    "message": f"Parameter '{arg.arg}' in '{node.name}' missing type hint"
                })
            else:
                self.stats["params_with_hint"] += 1

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """访问异步函数定义（与普通函数类似）"""
        self.visit_FunctionDef(node)


def check_file(filepath: Path) -> Tuple[List[Dict], Dict]:
    """
    检查单个文件的类型提示

    Returns:
        (issues, stats) 元组
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()

        tree = ast.parse(source, filename=str(filepath))
        checker = TypeHintChecker(str(filepath))
        checker.visit(tree)

        return checker.issues, checker.stats

    except SyntaxError as e:
        logger.error(f"Syntax error in {filepath}: {e}")
        return [], {}
    except Exception as e:
        logger.error(f"Error checking {filepath}: {e}")
        return [], {}


def check_directory(directory: Path, exclude_patterns: List[str] = None) -> Dict:
    """
    递归检查目录中的所有 Python 文件

    Args:
        directory: 目录路径
        exclude_patterns: 排除的路径模式

    Returns:
        检查结果汇总
    """
    if exclude_patterns is None:
        exclude_patterns = [
            "__pycache__",
            ".venv",
            "venv",
            "migrations",
            "alembic",
            ".git",
        ]

    all_issues = []
    total_stats = {
        "total_files": 0,
        "total_functions": 0,
        "functions_with_return_hint": 0,
        "total_params": 0,
        "params_with_hint": 0,
    }

    # 遍历所有 .py 文件
    for py_file in directory.rglob("*.py"):
        # 检查是否应该排除
        should_exclude = False
        for pattern in exclude_patterns:
            if pattern in str(py_file):
                should_exclude = True
                break

        if should_exclude:
            continue

        total_stats["total_files"] += 1

        issues, stats = check_file(py_file)

        # 添加文件路径到每个问题
        for issue in issues:
            issue["file"] = str(py_file.relative_to(directory.parent))
            all_issues.append(issue)

        # 累加统计
        for key in ["total_functions", "functions_with_return_hint", "total_params", "params_with_hint"]:
            total_stats[key] += stats.get(key, 0)

    return {
        "issues": all_issues,
        "stats": total_stats
    }


def print_report(results: Dict):
    """打印检查报告"""
    issues = results["issues"]
    stats = results["stats"]

    logger.info("=" * 70)
    logger.info("📊 Type Hint Coverage Report")
    logger.info("=" * 70)

    # 统计信息
    logger.info(f"\n📁 Files checked: {stats['total_files']}")
    logger.info(f"🔧 Functions checked: {stats['total_functions']}")

    if stats['total_functions'] > 0:
        return_coverage = (stats['functions_with_return_hint'] / stats['total_functions']) * 100
        logger.info(f"   └─ Return type hints: {stats['functions_with_return_hint']}/{stats['total_functions']} ({return_coverage:.1f}%)")

    if stats['total_params'] > 0:
        param_coverage = (stats['params_with_hint'] / stats['total_params']) * 100
        logger.info(f"📝 Parameters checked: {stats['total_params']}")
        logger.info(f"   └─ Type hints: {stats['params_with_hint']}/{stats['total_params']} ({param_coverage:.1f}%)")

    # 按严重程度分组
    issues_by_severity = {}
    for issue in issues:
        severity = issue["severity"]
        if severity not in issues_by_severity:
            issues_by_severity[severity] = []
        issues_by_severity[severity].append(issue)

    logger.info(f"\n⚠️  Total issues found: {len(issues)}")

    # 按严重程度显示
    for severity in ["high", "medium", "low"]:
        if severity in issues_by_severity:
            count = len(issues_by_severity[severity])
            icon = "🔴" if severity == "high" else "🟡" if severity == "medium" else "🟢"
            logger.info(f"   {icon} {severity.upper()}: {count}")

    # 显示前 10 个问题（示例）
    if issues:
        logger.info("\n" + "=" * 70)
        logger.info("📝 Sample Issues (first 10):")
        logger.info("=" * 70)

        for issue in issues[:10]:
            logger.info(
                f"\n  {issue['file']}:{issue['line']}"
            )
            logger.info(f"    ⚠️  {issue['message']}")

    # 按文件统计问题最多的文件
    if issues:
        files_with_issues = {}
        for issue in issues:
            file = issue["file"]
            files_with_issues[file] = files_with_issues.get(file, 0) + 1

        top_files = sorted(files_with_issues.items(), key=lambda x: x[1], reverse=True)[:5]

        logger.info("\n" + "=" * 70)
        logger.info("📂 Files with most issues (top 5):")
        logger.info("=" * 70)

        for file, count in top_files:
            logger.info(f"  {count:3d} issues: {file}")

    logger.info("\n" + "=" * 70)


def main():
    """主函数"""
    logger.info("🚀 Starting type hint consistency check...")

    # 检查目录
    app_dir = Path("/app/app")

    if not app_dir.exists():
        logger.error(f"Directory {app_dir} not found!")
        return 1

    # 运行检查
    results = check_directory(app_dir)

    # 打印报告
    print_report(results)

    # 返回码：如果有高严重度问题，返回 1
    high_issues = [i for i in results["issues"] if i["severity"] == "high"]
    if high_issues:
        logger.warning(f"\n⚠️  Found {len(high_issues)} high-severity issues")
        return 1

    logger.info("\n✅ Type hint check completed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
