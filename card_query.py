import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def simple_search(client, keyword: str) -> List[Dict[str, Any]]:
    """简单搜索，只返回ID/name列表，让LLM选择"""
    # logger.debug(f'simple_search: keyword={keyword}')
    return client.search_cards(keyword)

def get_detail(client, card_id: str) -> Dict[str, Any]:
    """单卡详情"""
    # 直接调用YGOCDB API进行搜索
    # logger.info(f'搜索卡片: {keyword}')
    return client.get_card_by_id(card_id)