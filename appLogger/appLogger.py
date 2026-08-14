# -*- coding: utf-8 -*-
import logging
import sys
from pathlib import Path

class AppLogger:
    """
    全局单例日志器，自动检测并修复被覆盖的问题
    """
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, name="my_app", log_file="logs/app.log", level=logging.INFO):
        if self._initialized:
            return
        
        self.name = name
        self.log_file = log_file
        self.level = level
        
        # 获取或创建日志器
        self.logger = logging.getLogger(name)
        
        # 强制重置
        self._reset_logger()
        
        self._initialized = True
    
    def _reset_logger(self):
        """重置日志器配置"""
        # 清除所有处理器
        self.logger.handlers.clear()
        
        # 阻止传播
        self.logger.propagate = False
        
        # 设置级别
        self.logger.setLevel(self.level)
        
        # 创建日志目录
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
        
        # 文件处理器
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(self.level)
        
        # 控制台处理器
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(self.level)
        
        # 格式化
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console)
    
    def get_logger(self):
        return self.logger
    
    def reset(self):
        """重置日志器（当发现被覆盖时调用）"""
        self._reset_logger()
        self.logger.info("日志器已重置")