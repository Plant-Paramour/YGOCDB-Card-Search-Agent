import logging
import json
import requests
from typing import Dict, List, Any

# 配置日志
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(r'C:\code\ygocdb-agent\agent.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MCPClient:
    """简化版的卡片查询客户端 - 直接调用YGOCDB API"""

    def __init__(self, config: Dict[str, Any]):
        self.api_base = 'https://ygocdb.com/api/v0'
        # logger.info('MCPClient初始化成功 (使用直接API模式)')

    def search_cards(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索卡片 - 直接调用YGOCDB API"""
        # logger.debug(f'search_cards keyword: {keyword}')

        # 直接调用API，不需要MCP中间层
        # logger.info('使用直接API搜索卡片')
        # URL编码可能需要处理中文字符
        url = f'{self.api_base}/?search={keyword}'
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            # logger.debug(f'API搜索响应: {data}')
            return data.get('result', [])
        except Exception as e:
            logger.error(f'API搜索失败: {e}')
            return []

    def get_card_by_id(self, card_id: str) -> Dict[str, Any]:
        """根据卡片ID获取详情 - 直接调用YGOCDB API"""
        # logger.debug(f'get_card_by_id: {card_id}')
        url = f'{self.api_base}/?id={card_id}'
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            # print(url)
            data = resp.json()
            return data.get('result', {})
        except Exception as e:
            logger.error(f'API详情查询失败: {e}')
            return {}