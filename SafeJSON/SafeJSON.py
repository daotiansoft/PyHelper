# -*- coding: utf-8 -*-

import json
from typing import Any, Optional, Dict, List, Union, Callable
from decimal import Decimal
from datetime import datetime, date
from enum import Enum
import re


class SafeJSON:
    """安全的JSON数据处理类"""
    
    @staticmethod
    def parse_safe(json_str: str, default: Any = None, 
                  strict: bool = False) -> Optional[Any]:
        """
        安全解析JSON字符串
        
        Args:
            json_str: JSON字符串
            default: 解析失败时的默认值
            strict: 是否严格模式（JSONDecodeError时抛出异常）
        
        Returns:
            解析后的对象或默认值
        """
        if not json_str or not isinstance(json_str, str):
            return default
        
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError, ValueError):
            if strict:
                raise
            return default
    
    @staticmethod
    def get_value(data: Any, *keys, default: Any = None) -> Any:
        """安全获取嵌套值（支持字典和列表）"""
        if not keys:
            return data if data is not None else default
        
        try:
            current = data
            for key in keys:
                if isinstance(current, dict):
                    current = current.get(key)
                elif isinstance(current, list):
                    if isinstance(key, int) and 0 <= key < len(current):
                        current = current[key]
                    else:
                        # 尝试在列表中查找字典的特定键
                        if isinstance(key, str):
                            for item in current:
                                if isinstance(item, dict) and key in item:
                                    current = item[key]
                                    break
                            else:
                                return default
                        else:
                            return default
                else:
                    return default
                
                if current is None:
                    return default
                    
            return current
        except (KeyError, TypeError, IndexError, AttributeError):
            return default
    
    @staticmethod
    def get_path(data: Any, path: str, default: Any = None, 
                separator: str = '.', array_pattern: str = r'\[(\d+)\]') -> Any:
        """
        通过路径表达式安全取值
        支持: user.name, items[0].id, data.0.name
        
        Args:
            data: JSON数据
            path: 路径表达式
            default: 默认值
            separator: 路径分隔符
            array_pattern: 数组索引的正则模式
        """
        if not path:
            return data if data is not None else default
        
        # 解析路径，处理数组索引
        parts = []
        for part in path.split(separator):
            # 检查是否有数组索引
            matches = re.findall(array_pattern, part)
            if matches:
                # 分离字段名和索引
                field_match = re.match(r'^([^\[]+)', part)
                if field_match:
                    field_name = field_match.group(1)
                    parts.append(field_name)
                    for idx in matches:
                        parts.append(int(idx))
                else:
                    # 纯索引情况，如 "0.name"
                    for idx in matches:
                        parts.append(int(idx))
            else:
                parts.append(part)
        
        return SafeJSON.get_value(data, *parts, default=default)
    
    @staticmethod
    def get_string(data: Any, *keys, default: str = "", 
                  strip: bool = True) -> str:
        """安全获取字符串值"""
        value = SafeJSON.get_value(data, *keys, default=default)
        if value is None:
            return default
        
        result = str(value)
        return result.strip() if strip else result
    
    @staticmethod
    def get_int(data: Any, *keys, default: int = 0,
               min_val: Optional[int] = None,
               max_val: Optional[int] = None) -> int:
        """安全获取整数值"""
        value = SafeJSON.get_value(data, *keys)
        if value is None:
            return default
        
        try:
            result = int(value)
            if min_val is not None:
                result = max(result, min_val)
            if max_val is not None:
                result = min(result, max_val)
            return result
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def get_float(data: Any, *keys, default: float = 0.0,
                 min_val: Optional[float] = None,
                 max_val: Optional[float] = None,
                 precision: Optional[int] = None) -> float:
        """安全获取浮点数值"""
        value = SafeJSON.get_value(data, *keys)
        if value is None:
            return default
        
        try:
            result = float(value)
            if min_val is not None:
                result = max(result, min_val)
            if max_val is not None:
                result = min(result, max_val)
            if precision is not None:
                result = round(result, precision)
            return result
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def get_bool(data: Any, *keys, default: bool = False,
                true_values: List[Any] = None,
                false_values: List[Any] = None) -> bool:
        """安全获取布尔值"""
        value = SafeJSON.get_value(data, *keys)
        if value is None:
            return default
        
        # 默认真值/假值列表
        if true_values is None:
            true_values = [True, 'true', 'True', 'TRUE', '1', 1, 'yes', 'Yes', 'YES', 'on', 'On', 'ON']
        if false_values is None:
            false_values = [False, 'false', 'False', 'FALSE', '0', 0, 'no', 'No', 'NO', 'off', 'Off', 'OFF']
        
        if value in true_values:
            return True
        elif value in false_values:
            return False
        else:
            return bool(value)
    
    @staticmethod
    def get_list(data: Any, *keys, default: Optional[List] = None,
                item_type: Optional[Callable] = None) -> List:
        """安全获取列表值"""
        value = SafeJSON.get_value(data, *keys)
        if value is None:
            return default if default is not None else []
        
        if not isinstance(value, (list, tuple)):
            return [value] if item_type is None else [item_type(value)]
        
        if item_type:
            try:
                return [item_type(item) for item in value]
            except (ValueError, TypeError):
                return default if default is not None else []
        
        return list(value)
    
    @staticmethod
    def get_dict(data: Any, *keys, default: Optional[Dict] = None) -> Dict:
        """安全获取字典值"""
        value = SafeJSON.get_value(data, *keys)
        if value is None or not isinstance(value, dict):
            return default if default is not None else {}
        return dict(value)
    
    @staticmethod
    def get_datetime(data: Any, *keys, default: Optional[datetime] = None,
                    format: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
        """安全获取日期时间值"""
        value = SafeJSON.get_value(data, *keys)
        if value is None:
            return default
        
        try:
            if isinstance(value, (int, float)):
                # 时间戳
                return datetime.fromtimestamp(value)
            elif isinstance(value, str):
                # 格式化字符串
                return datetime.strptime(value, format)
            elif isinstance(value, datetime):
                return value
            elif isinstance(value, date):
                return datetime.combine(value, datetime.min.time())
            else:
                return default
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def get_decimal(data: Any, *keys, default: Decimal = None) -> Optional[Decimal]:
        """安全获取Decimal值（用于精确计算）"""
        value = SafeJSON.get_value(data, *keys)
        if value is None:
            return default
        
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def extract(data: Any, mapping: Dict[str, Any], 
               default_values: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        根据映射关系提取数据
        
        Args:
            data: 原始数据
            mapping: 字段映射 {新字段名: 源路径}
            default_values: 各字段的默认值
        
        Returns:
            提取后的字典
        
        Example:
            >>> data = {"user": {"name": "Alice", "age": 30}}
            >>> mapping = {"username": "user.name", "userage": "user.age"}
            >>> SafeJSON.extract(data, mapping)
            {"username": "Alice", "userage": 30}
        """
        result = {}
        default_values = default_values or {}
        
        for new_key, source_path in mapping.items():
            if isinstance(source_path, str):
                value = SafeJSON.get_path(data, source_path)
            elif callable(source_path):
                value = source_path(data)
            else:
                value = SafeJSON.get_value(data, source_path)
            
            if value is None:
                value = default_values.get(new_key)
            
            result[new_key] = value
        
        return result
