"""
Strategy service for business logic
"""

import ast
from typing import Optional, List, Set
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.strategy import Strategy, StrategyStatus
from app.schemas.strategy import StrategyCreate, StrategyUpdate
from app.repositories.strategy import StrategyRepository
from app.core.config import settings
from app.utils.cache import cached_method, cache


class StrategyService:
    """Service for strategy-related business logic"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = StrategyRepository()

    @cached_method(
        key_prefix="strategy:detail",
        expiry=300,
        key_func=lambda strategy_id, user_id: f"{strategy_id}:{user_id}"
    )
    def get_strategy(self, strategy_id: int, user_id: int) -> Strategy:
        """
        Get strategy by ID (cached for 5 minutes)

        Args:
            strategy_id: Strategy ID
            user_id: User ID (for ownership verification)

        Returns:
            Strategy object

        Raises:
            HTTPException: If strategy not found or user is not owner
        """
        strategy = self.repo.get_by_id(self.db, strategy_id)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found",
            )

        # Verify ownership
        if not self.repo.is_owner(self.db, strategy_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this strategy",
            )

        return strategy

    @cached_method(
        key_prefix="strategy:list",
        expiry=120,
        key_func=lambda user_id, status_filter=None, skip=0, limit=20: f"{user_id}:{status_filter}:{skip}:{limit}"
    )
    def get_user_strategies(
        self,
        user_id: int,
        status_filter: Optional[StrategyStatus] = None,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Strategy], int]:
        """
        Get strategies by user (cached for 2 minutes)

        Args:
            user_id: User ID
            status_filter: Filter by status (optional)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (strategies list, total count)
        """
        strategies = self.repo.get_by_user(
            self.db,
            user_id,
            status=status_filter,
            skip=skip,
            limit=limit
        )
        total = self.repo.count_by_user(self.db, user_id, status=status_filter)
        return strategies, total

    def search_strategies(
        self,
        user_id: int,
        keyword: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[Strategy]:
        """
        Search user's strategies by name

        Args:
            user_id: User ID
            keyword: Search keyword
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching strategies

        Raises:
            HTTPException: If keyword is empty
        """
        if not keyword or len(keyword.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search keyword cannot be empty",
            )

        return self.repo.search_by_user(
            self.db,
            user_id,
            keyword,
            skip=skip,
            limit=limit
        )

    def create_strategy(self, user_id: int, strategy_create: StrategyCreate) -> Strategy:
        """
        Create new strategy

        Args:
            user_id: User ID
            strategy_create: Strategy creation data

        Returns:
            Created strategy object

        Raises:
            HTTPException: If validation fails or quota exceeded
        """
        # Check quota
        self._check_strategy_quota(user_id)

        # Validate strategy code (basic validation)
        if strategy_create.code:
            engine_type = strategy_create.engine_type or 'backtrader'
            self._validate_strategy_code(strategy_create.code, engine_type=engine_type)

        # Validate parameters JSON structure
        if strategy_create.parameters:
            if not isinstance(strategy_create.parameters, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parameters must be a valid JSON object",
                )

        strategy = self.repo.create(self.db, user_id, strategy_create)

        # Invalidate list cache for this user
        cache.clear_pattern(f"strategy:list:{user_id}*")

        return strategy

    def update_strategy(
        self,
        strategy_id: int,
        user_id: int,
        strategy_update: StrategyUpdate
    ) -> Strategy:
        """
        Update strategy

        Args:
            strategy_id: Strategy ID
            user_id: User ID (for ownership verification)
            strategy_update: Update data

        Returns:
            Updated strategy object

        Raises:
            HTTPException: If strategy not found, user is not owner, or validation fails
        """
        strategy = self.repo.get_by_id(self.db, strategy_id)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found",
            )

        # Verify ownership
        if not self.repo.is_owner(self.db, strategy_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this strategy",
            )

        # Validate strategy code if being updated
        if strategy_update.code:
            engine_type = strategy_update.engine_type or strategy.engine_type or 'backtrader'
            self._validate_strategy_code(strategy_update.code, engine_type=engine_type)

        # Validate parameters JSON structure if being updated
        if strategy_update.parameters is not None:
            if not isinstance(strategy_update.parameters, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parameters must be a valid JSON object",
                )

        updated_strategy = self.repo.update(self.db, strategy, strategy_update)

        # Invalidate caches
        cache.delete(f"strategy:detail:{strategy_id}:{user_id}")
        cache.clear_pattern(f"strategy:list:{user_id}*")

        return updated_strategy

    def update_strategy_status(
        self,
        strategy_id: int,
        user_id: int,
        new_status: StrategyStatus
    ) -> Strategy:
        """
        Update strategy status

        Args:
            strategy_id: Strategy ID
            user_id: User ID (for ownership verification)
            new_status: New status

        Returns:
            Updated strategy object

        Raises:
            HTTPException: If strategy not found or user is not owner
        """
        strategy = self.repo.get_by_id(self.db, strategy_id)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found",
            )

        # Verify ownership
        if not self.repo.is_owner(self.db, strategy_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this strategy",
            )

        updated_strategy = self.repo.update_status(self.db, strategy, new_status)

        # Invalidate caches
        cache.delete(f"strategy:detail:{strategy_id}:{user_id}")
        cache.clear_pattern(f"strategy:list:{user_id}*")

        return updated_strategy

    def delete_strategy(self, strategy_id: int, user_id: int) -> None:
        """
        Delete strategy

        Args:
            strategy_id: Strategy ID
            user_id: User ID (for ownership verification)

        Raises:
            HTTPException: If strategy not found or user is not owner
        """
        strategy = self.repo.get_by_id(self.db, strategy_id)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found",
            )

        # Verify ownership
        if not self.repo.is_owner(self.db, strategy_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this strategy",
            )

        self.repo.delete(self.db, strategy)

        # Invalidate caches
        cache.delete(f"strategy:detail:{strategy_id}:{user_id}")
        cache.clear_pattern(f"strategy:list:{user_id}*")

    def validate_strategy_code(self, code: str, engine_type: str = 'backtrader') -> dict:
        """
        Validate strategy code (syntax and structure)

        Args:
            code: Strategy code to validate
            engine_type: Strategy engine type ('backtrader' or 'qlib')

        Returns:
            Validation result dictionary

        Raises:
            HTTPException: If code is invalid
        """
        try:
            self._validate_strategy_code(code, engine_type=engine_type)
            return {
                "valid": True,
                "message": "Strategy code is valid",
            }
        except HTTPException as e:
            return {
                "valid": False,
                "message": e.detail,
            }

    def _validate_strategy_code(self, code: str, engine_type: str = 'backtrader') -> None:
        """
        Secure validation of strategy code using AST parsing

        This method uses Abstract Syntax Tree (AST) analysis to validate
        strategy code without executing it. It checks for:
        - Valid Python syntax
        - Presence of required methods (for Backtrader strategies)
        - Dangerous function calls or imports
        - Unauthorized attribute access

        Args:
            code: Strategy code to validate
            engine_type: Strategy engine type ('backtrader' or 'qlib')

        Raises:
            HTTPException: If code is invalid or contains dangerous operations
        """
        if not code or len(code.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Strategy code cannot be empty",
            )

        # Parse code into AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Syntax error in strategy code: {str(e)}",
            )

        # Validate AST structure
        self._validate_ast_security(tree, engine_type=engine_type)

        # Only validate required methods for Backtrader strategies
        if engine_type == 'backtrader':
            self._validate_required_methods(tree)

    def _validate_ast_security(self, tree: ast.AST, engine_type: str = 'backtrader') -> None:
        """
        Validate AST for security concerns

        Args:
            tree: Parsed AST tree
            engine_type: Strategy engine type ('backtrader' or 'qlib')

        Raises:
            HTTPException: If dangerous operations detected
        """
        # Allowed safe imports (whitelist approach)
        allowed_imports = {
            'backtrader', 'bt',
            'pandas', 'pd',
            'numpy', 'np',
            'talib',
            'datetime', 'date', 'time',
            'typing',
            'decimal',
            'math',
            'statistics',
        }

        # Additional imports for Qlib/ML strategies
        if engine_type == 'qlib':
            allowed_imports.update({
                'qlib',
                'lightgbm', 'lgb',
                'sklearn',
                'xgboost', 'xgb',
                'torch', 'pytorch',
                'tensorflow', 'tf',
                'scipy',
                'collections',
                'itertools',
                'functools',
                'warnings',
            })

        # Dangerous function names (blacklist)
        dangerous_functions = {
            'eval', 'exec', 'compile', '__import__',
            'open', 'file', 'input',
            'globals', 'locals', 'vars', 'dir',
            'getattr', 'setattr', 'delattr', 'hasattr',
            'breakpoint', 'exit', 'quit',
        }

        # Dangerous attribute patterns
        dangerous_attributes = {
            '__globals__', '__code__', '__builtins__',
            '__dict__', '__class__', '__bases__',
            '__subclasses__', '__import__',
        }

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self._validate_import_node(node, allowed_imports)

            # Check function calls
            elif isinstance(node, ast.Call):
                self._validate_call_node(node, dangerous_functions)

            # Check attribute access
            elif isinstance(node, ast.Attribute):
                if node.attr in dangerous_attributes:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Dangerous attribute access not allowed: {node.attr}",
                    )

    def _validate_import_node(self, node: ast.AST, allowed_imports: Set[str]) -> None:
        """
        Validate import statements

        Args:
            node: AST import node
            allowed_imports: Set of allowed module names

        Raises:
            HTTPException: If unauthorized import detected
        """
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split('.')[0]
                if module not in allowed_imports:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Import '{alias.name}' is not allowed. "
                               f"Allowed imports: {', '.join(sorted(allowed_imports))}",
                    )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split('.')[0]
                if module not in allowed_imports:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Import from '{node.module}' is not allowed. "
                               f"Allowed imports: {', '.join(sorted(allowed_imports))}",
                    )

    def _validate_call_node(self, node: ast.Call, dangerous_functions: Set[str]) -> None:
        """
        Validate function calls

        Args:
            node: AST call node
            dangerous_functions: Set of dangerous function names

        Raises:
            HTTPException: If dangerous function call detected
        """
        func_name = None

        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            # For method calls like obj.method()
            func_name = node.func.attr

        if func_name and func_name in dangerous_functions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Function '{func_name}' is not allowed for security reasons",
            )

    def _validate_required_methods(self, tree: ast.AST) -> None:
        """
        Validate that required methods exist

        Args:
            tree: Parsed AST tree

        Raises:
            HTTPException: If required methods are missing
        """
        required_methods = {'next', 'on_data', '__init__'}
        found_methods = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check methods within class definitions
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        found_methods.add(item.name)

            elif isinstance(node, ast.FunctionDef):
                # Check top-level functions
                found_methods.add(node.name)

        # Check if at least one required method exists
        if not found_methods.intersection(required_methods):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Strategy code must contain at least one of these methods: "
                       f"{', '.join(sorted(required_methods))}",
            )

    def _check_strategy_quota(self, user_id: int) -> None:
        """
        Check if user has exceeded strategy quota

        Args:
            user_id: User ID

        Raises:
            HTTPException: If quota exceeded
        """
        current_count = self.repo.count_by_user(self.db, user_id)

        if current_count >= settings.MAX_STRATEGIES_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Strategy quota exceeded. Maximum {settings.MAX_STRATEGIES_PER_USER} strategies allowed per user. "
                       f"Current count: {current_count}. Please delete some strategies before creating new ones."
            )
