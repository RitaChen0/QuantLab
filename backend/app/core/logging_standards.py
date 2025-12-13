"""
日志级别使用标准

本文件定义 QuantLab 项目的日志级别使用规范，确保日志的一致性和可读性。

## 日志级别定义

### DEBUG - 详细诊断信息
用途：开发调试、追踪程序执行流程
示例：
  - logger.debug(f"Function called with args: {args}")
  - logger.debug(f"Query result: {result}")
  - logger.debug(f"Cache key: {cache_key}")

### INFO - 重要业务事件
用途：记录正常的业务操作、系统状态变化
示例：
  - logger.info(f"User {user_id} logged in")
  - logger.info(f"Strategy {strategy_id} created successfully")
  - logger.info(f"Sync completed: {count} records")
  - logger.info(f"Celery task started: {task_name}")

### WARNING - 可恢复的异常情况
用途：需要注意但不影响功能的情况
示例：
  - logger.warning(f"Cache miss for key: {key}")
  - logger.warning(f"API rate limit approaching: {current}/{limit}")
  - logger.warning(f"Deprecated function used: {func_name}")
  - logger.warning(f"Lock acquisition timeout, retrying...")

### ERROR - 功能失败但系统继续运行
用途：操作失败、异常捕获、需要人工介入
示例：
  - logger.error(f"Failed to fetch data from API: {error}")
  - logger.error(f"Database query failed: {error}")
  - logger.error(f"Strategy validation failed: {error}")
  - logger.error(f"Backtest execution error: {error}")

### CRITICAL - 系统级严重错误
用途：系统无法继续运行、数据损坏
示例：
  - logger.critical(f"Database connection lost")
  - logger.critical(f"Unable to initialize required service")
  - logger.critical(f"Data corruption detected")

## 使用原则

1. **生产环境日志级别**：INFO
   - 只记录 INFO 及以上级别
   - DEBUG 日志不会输出

2. **开发环境日志级别**：DEBUG
   - 记录所有级别日志
   - 便于调试和追踪

3. **异常记录**：
   ```python
   try:
       risky_operation()
   except Exception as e:
       logger.error(f"Operation failed: {e}")
       logger.exception(e)  # 自动记录堆栈跟踪
   ```

4. **避免过度日志**：
   - 不要在循环内使用 INFO 级别
   - 使用 DEBUG 或定期汇总

   ```python
   # ❌ 错误
   for item in items:
       logger.info(f"Processing {item}")

   # ✅ 正确
   logger.info(f"Processing {len(items)} items...")
   for item in items:
       logger.debug(f"Processing {item}")
   logger.info(f"Completed processing {len(items)} items")
   ```

5. **敏感信息脱敏**：
   ```python
   # ❌ 错误
   logger.info(f"User password: {password}")

   # ✅ 正确
   logger.info(f"User authenticated: {username}")
   logger.debug(f"Password hash: {password_hash[:8]}...")
   ```

## 日志格式建议

```python
# 操作日志
logger.info(f"✅ {operation} completed: {details}")
logger.error(f"❌ {operation} failed: {error}")
logger.warning(f"⚠️  {operation} warning: {details}")

# 性能日志
logger.info(f"⏱️  {operation} took {duration:.2f}s")

# 数据统计
logger.info(f"📊 {metric}: {value}")
```
"""
