from appLogger import AppLogger

app_log = AppLogger(__name__, "logs/app.log")
logger = app_log.get_logger()

logger.info("测试日志内容")