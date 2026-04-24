"""WorldQuant BRAIN API 异常层次"""


class BrainAPIError(Exception):
    """BRAIN API基础异常"""
    pass


class AuthenticationError(BrainAPIError):
    """认证失败"""
    pass


class SimulationTimeoutError(BrainAPIError):
    """模拟超时"""
    pass


class RateLimitError(BrainAPIError):
    """速率限制"""
    pass


class SimulationError(BrainAPIError):
    """模拟创建/执行错误"""
    pass


class AlphaNotFoundError(BrainAPIError):
    """Alpha不存在"""
    pass


class DataFieldError(BrainAPIError):
    """数据集字段错误"""
    pass