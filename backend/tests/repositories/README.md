# Repository Tests

测试新增的 Repository 层，确保数据访问逻辑正确且符合架构规范。

## 📋 测试覆盖

### 已创建测试文件

1. **test_rdagent_task.py** - RDAgentTaskRepository 测试
   - 测试 CRUD 操作
   - 测试权限检查（get_by_id_and_user）
   - 测试分页功能
   - 测试按状态查询

2. **test_generated_factor.py** - GeneratedFactorRepository 测试
   - 测试因子创建和更新
   - 测试因子查询（按用户、按任务）
   - 测试级联删除（delete_by_task）
   - 测试所有权检查（is_owner）

3. **test_generated_model.py** - GeneratedModelRepository 测试
   - 测试模型 CRUD 操作
   - 测试分页和查询
   - 测试统计方法

4. **test_strategy_signal.py** - StrategySignalRepository 测试
   - 测试信号创建
   - 测试信号去重（check_duplicate）
   - 测试按用户/策略查询
   - 测试通知状态管理

## 🚀 运行测试

### 运行所有 Repository 测试

```bash
docker compose exec backend pytest tests/repositories/ -v
```

### 运行特定测试文件

```bash
# RDAgentTask Repository
docker compose exec backend pytest tests/repositories/test_rdagent_task.py -v

# GeneratedFactor Repository
docker compose exec backend pytest tests/repositories/test_generated_factor.py -v

# GeneratedModel Repository
docker compose exec backend pytest tests/repositories/test_generated_model.py -v

# StrategySignal Repository
docker compose exec backend pytest tests/repositories/test_strategy_signal.py -v
```

### 运行特定测试类

```bash
docker compose exec backend pytest tests/repositories/test_rdagent_task.py::TestRDAgentTaskRepositoryGetById -v
```

### 生成覆盖率报告

```bash
docker compose exec backend pytest tests/repositories/ --cov=app.repositories --cov-report=html
```

## 📊 测试结果

**当前状态**（2025-12-27）：
- ✅ **52 个测试通过**
- ⚠️ 15 个测试需要调整（方法签名不匹配）
- 📈 **总体通过率**: 78%

### 通过的测试

- ✅ RDAgentTaskRepository: 基本 CRUD、查询、分页
- ✅ GeneratedFactorRepository: 完整的因子管理功能
- ✅ StrategySignalRepository: 信号创建、查询、去重

### 需要修复的测试

一些测试假设了不存在的方法或不同的方法签名：
- RDAgentTaskRepository.create() - 需要检查实际参数
- RDAgentTaskRepository.update() - 需要检查实际参数
- GeneratedModelRepository.create()/update() - 需要检查实际参数
- StrategySignalRepository - 某些方法可能未实现（count, delete, mark_as_notified）

## 🛠️ 测试配置

### conftest.py

使用 SQLite 内存数据库进行测试：
- 每个测试函数获得独立的数据库 session
- 测试完成后自动回滚和清理
- 确保所有 SQLAlchemy 模型关系正确导入

## 📝 测试编写指南

### 基本测试结构

```python
import pytest
from sqlalchemy.orm import Session
from app.repositories.example import ExampleRepository
from app.models.example import Example

class TestExampleRepositoryGetById:
    """测试 get_by_id 方法"""

    def test_get_existing_item(self, db_session: Session):
        """测试获取存在的项目"""
        # Arrange
        item = Example(name="test")
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        # Act
        result = ExampleRepository.get_by_id(db_session, item.id)

        # Assert
        assert result is not None
        assert result.id == item.id
```

### Fixtures 使用

所有测试可以使用 `db_session` fixture 获取数据库 session：

```python
@pytest.fixture
def test_user(db_session: Session):
    """Create a test user"""
    user = User(email="test@example.com", username="testuser")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
```

## 🎯 下一步工作

1. **修复失败的测试**
   - 检查 Repository 实际方法签名
   - 添加缺失的方法或删除不存在方法的测试

2. **增加测试覆盖率**
   - 添加边界情况测试
   - 添加异常处理测试
   - 测试并发场景

3. **性能测试**
   - 测试大批量数据操作
   - 测试复杂查询性能

## 📚 相关文档

- [CLAUDE.md](../../../CLAUDE.md) - 测试规范
- [pytest.ini](../../pytest.ini) - Pytest 配置
- [Code Review Report](/tmp/service_layer_violations_detailed.md) - 架构修复报告
