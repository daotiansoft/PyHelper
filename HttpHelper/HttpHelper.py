# -*- coding: utf-8 -*-
import logging
from enum import Enum
import requests
import time
from typing import Optional, Dict, Any, Union, Callable, List
from dataclasses import dataclass, asdict
from threading import Lock
import random
import os


# 设置日志
try:
    os.makedirs('./logs', exist_ok=True)
except Exception as e:
    pass

log_filename = './logs/HttpHelper_%s.log' % (time.strftime("%Y%m%d%H", time.localtime()))
logging.basicConfig(
    filename = log_filename,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HttpStatus(Enum):
    """响应状态枚举"""
    SUCCESS = "success"
    HTTP_ERROR = "http_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    UNKNOWN_ERROR = "unknown_error"

@dataclass
class HttpResponse:
    """API响应数据类"""
    status: HttpStatus
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    status_code: Optional[int] = None
    url: Optional[str] = None
    elapsed_time: Optional[float] = None
    retry_count: int = 0
    response: requests.Response = None
    
    @property
    def is_success(self) -> bool:
        return self.status == HttpStatus.SUCCESS
    
    @property
    def should_retry(self) -> bool:
        """判断是否需要重试"""
        retryable_statuses = [
            HttpStatus.NETWORK_ERROR,
            HttpStatus.TIMEOUT,
            HttpStatus.RATE_LIMIT
        ]
        return self.status in retryable_statuses
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            **asdict(self),
            'is_success': self.is_success,
            'should_retry': self.should_retry
        }
class RateLimiter:
    """速率限制器"""
    def __init__(self, max_calls: int = 60, period: int = 60):
        """
        Args:
            max_calls: 时间窗口内最大调用次数
            period: 时间窗口（秒）
        """
        self.max_calls = max_calls
        self.period = period
        self.calls: List[float] = []
        self.lock = Lock()
    
    def wait_if_needed(self):
        """如果需要等待，则阻塞直到可以继续调用"""
        with self.lock:
            now = time.time()
            # 移除超过时间窗口的记录
            self.calls = [call for call in self.calls if now - call < self.period]
            
            if len(self.calls) >= self.max_calls:
                # 计算需要等待的时间
                oldest_call = self.calls[0]
                wait_time = self.period - (now - oldest_call)
                if wait_time > 0:
                    logger.info(f"速率限制，等待 {wait_time:.2f} 秒")
                    time.sleep(wait_time)
                    # 等待后重新计算
                    now = time.time()
                    self.calls = [call for call in self.calls if now - call < self.period]
            
            self.calls.append(now)

class RetryStrategy:
    """重试策略配置"""
    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        backoff_max: float = 60.0,
        retry_status_codes: List[int] = None
    ):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.backoff_max = backoff_max
        self.retry_status_codes = retry_status_codes or [429, 500, 502, 503, 504]
    
    def get_wait_time(self, retry_count: int) -> float:
        """计算退避等待时间"""
        # 指数退避 + 随机抖动
        wait_time = min(
            self.backoff_factor * (2 ** (retry_count - 1)),
            self.backoff_max
        )
        # 添加随机抖动 (±10%)
        jitter = wait_time * 0.1 * random.uniform(-1, 1)
        return max(0.1, wait_time + jitter)
    

class HttpClient:
    """
    HTTP客户端
    
    特性：
    1. 完整的异常处理
    2. 自动重试机制
    3. 速率限制
    4. 请求超时控制
    5. 连接池管理
    6. 详细的日志记录
    7. 响应验证
    """
    
    def __init__(
        self,
        base_url: str = "",
        default_timeout: int = 30,
        retry_strategy: Optional[RetryStrategy] = None,
        rate_limiter: Optional[RateLimiter] = None,
        verify_ssl: bool = True,
        default_headers: Optional[Dict[str, str]] = None
    ):
        """
        初始化客户端
        
        Args:
            base_url: 基础URL
            default_timeout: 默认超时时间（秒）
            retry_strategy: 重试策略
            rate_limiter: 速率限制器
            verify_ssl: 是否验证SSL证书
            default_headers: 默认请求头
        """
        self.base_url = base_url.rstrip('/')
        self.default_timeout = default_timeout
        self.verify_ssl = verify_ssl
        
        # 使用默认重试策略
        self.retry_strategy = retry_strategy or RetryStrategy()
        
        # 使用默认速率限制器（每分钟60次）
        self.rate_limiter = rate_limiter or RateLimiter(max_calls=60, period=60)
        
        # 创建会话，启用连接池
        self.session = requests.Session()
        
        # 配置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        if default_headers:
            self.session.headers.update(default_headers)
        
        # 配置适配器，优化连接性能
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=100,
            max_retries=0  # 我们自己实现重试逻辑
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # 统计数据
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_retries': 0,
            'total_time': 0.0
        }
    
    def _make_url(self, endpoint: str) -> str:
        """构建完整的URL"""
        if self.base_url:
            return f"{self.base_url}/{endpoint.lstrip('/')}"
        return endpoint
    
    def _handle_exception(self, exception: Exception, url: str) -> HttpResponse:
        """处理异常并返回适当的HttpResponse"""
        
        # 更新统计
        self.stats['failed_requests'] += 1
        
        if isinstance(exception, requests.exceptions.Timeout):
            logger.warning(f"请求超时: {url}")
            return HttpResponse(
                status=HttpStatus.TIMEOUT,
                error_message="请求超时",
                url=url
            )
        
        elif isinstance(exception, requests.exceptions.ConnectionError):
            logger.warning(f"连接错误: {url}")
            return HttpResponse(
                status=HttpStatus.NETWORK_ERROR,
                error_message="网络连接错误",
                url=url
            )
        
        elif isinstance(exception, requests.exceptions.HTTPError):
            response = exception.response
            status_code = response.status_code if response else None
            
            if status_code == 429:
                logger.warning(f"速率限制: {url}")
                return HttpResponse(
                    status=HttpStatus.RATE_LIMIT,
                    error_message="请求过于频繁，被限流",
                    status_code=status_code,
                    url=url
                )
            else:
                logger.error(f"HTTP错误 {status_code}: {url}")
                return HttpResponse(
                    status=HttpStatus.HTTP_ERROR,
                    error_message=f"HTTP错误: {str(exception)}",
                    status_code=status_code,
                    url=url
                )
        else:
            logger.error(f"未知错误: {url} - {type(exception).__name__}: {str(exception)}")
            return HttpResponse(
                status=HttpStatus.UNKNOWN_ERROR,
                error_message=f"未知错误: {str(exception)}",
                url=url
            )
    
    def _send_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> HttpResponse:
        """发送单个请求（无重试）"""
        start_time = time.time()
        
        try:
            # 应用速率限制
            self.rate_limiter.wait_if_needed()
            
            # 发送请求
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.default_timeout,
                verify=self.verify_ssl,
                **kwargs
            )
            
            elapsed = time.time() - start_time
            
            # 更新统计
            self.stats['total_requests'] += 1
            self.stats['total_time'] += elapsed
            
            # 检查HTTP状态码
            response.raise_for_status()

            data = response.text
            
            # 更新成功统计
            self.stats['successful_requests'] += 1
            
            return HttpResponse(
                status=HttpStatus.SUCCESS,
                data=data,
                status_code=response.status_code,
                url=url,
                elapsed_time=elapsed,
                response=response
            )
            
        except Exception as e:
            elapsed = time.time() - start_time
            api_response = self._handle_exception(e, url)
            api_response.elapsed_time = elapsed
            return api_response
    
    def request(
        self,
        method: str,
        endpoint: str,
        retry_on_failure: bool = True,
        **kwargs
    ) -> HttpResponse:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE等)
            endpoint: API端点
            retry_on_failure: 是否启用重试
            **kwargs: 传递给requests的额外参数
            
        Returns:
            HttpResponse
        """
        url = self._make_url(endpoint)
        logger.debug(f"发送请求: {method} {url}")
        
        retry_count = 0
        max_retries = self.retry_strategy.max_retries if retry_on_failure else 0
        
        while retry_count <= max_retries:
            # 发送请求
            response = self._send_request(method, url, **kwargs)
            response.retry_count = retry_count
            
            # 如果成功或不需要重试，直接返回
            if response.is_success or not response.should_retry:
                return response
            
            # 检查是否达到最大重试次数
            if retry_count >= max_retries:
                logger.warning(f"达到最大重试次数 ({max_retries}): {url}")
                return response
            
            # 计算等待时间并重试
            retry_count += 1
            self.stats['total_retries'] += 1
            
            wait_time = self.retry_strategy.get_wait_time(retry_count)
            logger.info(f"请求失败，第 {retry_count}/{max_retries} 次重试，等待 {wait_time:.2f} 秒: {url}")
            
            time.sleep(wait_time)
        
        return response
    
    def get(self, endpoint: str, **kwargs) -> HttpResponse:
        """发送GET请求"""
        return self.request('GET', endpoint, **kwargs)
    
    def post(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> HttpResponse:
        """发送POST请求"""
        kwargs['data'] = data
        return self.request('POST', endpoint, **kwargs)
    
    def put(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> HttpResponse:
        """发送PUT请求"""
        kwargs['data'] = data
        return self.request('PUT', endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> HttpResponse:
        """发送DELETE请求"""
        return self.request('DELETE', endpoint, **kwargs)
    
    def get_safe(
        self,
        endpoint: str,
        key_path: str = "",
        default: Any = None,
        **kwargs
    ) -> Any:
        """
        安全获取数据，支持嵌套键路径
        
        Args:
            endpoint: API端点
            key_path: 键路径，用点号分隔，如 "data.user.name"
            default: 默认值
            **kwargs: 传递给get的额外参数
            
        Returns:
            获取到的值或默认值
        """
        response = self.get(endpoint, **kwargs)
        
        if not response.is_success or not response.data:
            return default
        
        if not key_path:
            return response.data
        
        # 支持嵌套键路径访问
        try:
            keys = key_path.split('.')
            value = response.data
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                elif isinstance(value, list) and key.isdigit():
                    index = int(key)
                    if 0 <= index < len(value):
                        value = value[index]
                    else:
                        return default
                else:
                    return default
            
            return value
            
        except (KeyError, TypeError, AttributeError, ValueError):
            return default
    
    def batch_request(
        self,
        requests_list: List[Dict[str, Any]],
        max_concurrent: int = 5,
        delay_between_batches: float = 0.1
    ) -> List[HttpResponse]:
        """
        批量发送请求
        
        Args:
            requests_list: 请求列表，每个元素是包含method, endpoint和其他参数的字典
            max_concurrent: 最大并发数
            delay_between_batches: 批次间延迟（秒）
            
        Returns:
            响应列表
        """
        import concurrent.futures
        
        responses = []
        total = len(requests_list)
        
        logger.info(f"开始批量处理 {total} 个请求，最大并发数: {max_concurrent}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # 提交所有任务
            future_to_request = {}
            for i, req in enumerate(requests_list):
                method = req.pop('method', 'GET')
                endpoint = req.pop('endpoint', '')
                future = executor.submit(self.request, method, endpoint, **req)
                future_to_request[future] = (i, method, endpoint)
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_request):
                i, method, endpoint = future_to_request[future]
                try:
                    response = future.result()
                    responses.append((i, response))
                except Exception as e:
                    logger.error(f"批量请求异常: {method} {endpoint} - {str(e)}")
                    responses.append((i, HttpResponse(
                        status=HttpStatus.UNKNOWN_ERROR,
                        error_message=str(e),
                        url=endpoint
                    )))
                
                # 添加批次间延迟，避免突发请求
                time.sleep(delay_between_batches)
        
        # 按原始顺序排序
        responses.sort(key=lambda x: x[0])
        return [resp for _, resp in responses]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        if stats['total_requests'] > 0:
            stats['success_rate'] = stats['successful_requests'] / stats['total_requests']
            stats['avg_response_time'] = stats['total_time'] / stats['total_requests']
        else:
            stats['success_rate'] = 0.0
            stats['avg_response_time'] = 0.0
        return stats
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_retries': 0,
            'total_time': 0.0
        }
    
    def close(self):
        """关闭会话，释放资源"""
        self.session.close()
        logger.info("API客户端已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()