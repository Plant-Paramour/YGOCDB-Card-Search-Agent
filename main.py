"""
游戏王查卡代理程序 (Python 3.12) - LLM多轮查询版
用户输入 → LLM search ID列表 → LLM选ID get详情 → 打印
"""
import json
import sys
import requests
import logging
from typing import Dict, List, Any, Optional

from mcp_client import MCPClient
from card_query import simple_search, get_detail
from output_renderer import render_card, render_baige_results

# 配置日志（全局）- 只显示错误信息
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(r'C:\code\ygocdb-agent\agent.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class YGOCDBAgent:
    """游戏王卡片查询代理类 - LLM驱动多轮ID选择"""

    def __init__(self, config_path: str = r"C:\code\ygocdb-agent\config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.api_url = self.config["api_url"]
        self.api_key = self.config["api_key"]
        self.model = self.config["model"]
        self.mcp_client = MCPClient(self.config)
        # logger.info(f'✅ 配置加载成功，使用模型: {self.model}')

    def load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if not config.get("api_key") or not config.get("api_url"):
                    raise ValueError("config.json 缺少必要字段：api_key 或 api_url")
                return config
        except Exception as e:
            raise ValueError(f"配置加载失败: {e}")

    def call_llm(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        # logger.debug(f'LLM调用: {len(messages)}消息')
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        data = {"model": self.model, "messages": messages, "temperature": 0.1}
        if tools: data.update({"tools": tools, "tool_choice": "auto"})

        resp = requests.post(f"{self.api_url}/chat/completions", headers=headers, json=data, timeout=60)
        resp.raise_for_status()
        # logger.debug(f'LLM成功: {resp.json()["choices"][0]["finish_reason"]}')
        return resp.json()

    def search_cards(self, keyword: str) -> List[Dict[str, Any]]:
        """工具: 根据关键词搜索，获取单卡完整详情"""
        # logger.debug(f'search_cards: {keyword}')
        return simple_search(self.mcp_client, keyword)

    def get_card_by_id(self, card_id: str) -> Dict[str, Any]:
        """工具: 根据ID搜索，获取单卡完整详情"""
        # logger.debug(f'get_card_by_id: {card_id}')
        try:
            result = get_detail(self.mcp_client, card_id)
            # logger.debug(f'get_card_by_id: 返回数据包含字段: {list(result.keys()) if result else []}')
            return result
        except Exception as e:
            logger.error(f'get_card_by_id 失败: {e}')
            return {'error': str(e)}

    def print_card_by_id(self, card_id: str) -> None:
        """工具: 根据ID直接在控制台打印卡片完整信息（集成output_renderer.render_card）"""
        # logger.debug(f'print_card_by_id: {card_id}')
        try:
            card = self.get_card_by_id(card_id)
            # logger.debug(f'print_card_by_id: 成功获取卡片数据: {len(str(card)) if card else 0} characters')
            rendered = render_card(card)
            # logger.debug(f'print_card_by_id: 成功渲染卡片，内容长度: {len(rendered) if rendered else 0} characters')
            print(rendered)
        except Exception as e:
            logger.error(f'print_card_by_id 失败: {e}')
            print(f'❌ 打印卡片信息失败: {e}')

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_cards",
                    "description": "根据卡名或关键词搜索卡片，获取官方原始卡片数据（含标准卡名、准确的效果文本、官方字段名）。用于回答卡片效果、数值或查找特定卡片。",
                    "parameters": {
                        "type": "object",
                        "properties": {"keyword": {"type": "string", "description": "搜索关键词，如'铁兽'、'死狱乡'"}},
                        "required": ["keyword"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_card_by_id",
                    "description": "根据卡片ID，精确获取唯一的卡片详情数据。",
                    "parameters": {
                        "type": "object",
                        "properties": {"card_id": {"type": "string", "description": "ID，如'44146295'"}},
                        "required": ["card_id"]
                    }
                }
            }
        ]

    def execute_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        func_name = tool_call["function"]["name"]
        args = json.loads(tool_call["function"]["arguments"])
        # logger.debug(f'执行: {func_name} {args}')

        if func_name == "search_cards":
            cards = self.search_cards(args["keyword"])[:10]  # 限10
            # 使用百鸽服务渲染器，输出详细信息，不是简单列表
            result = render_baige_results(cards)
            print("\n📄 百鸽查卡结果:")
            print(result)
            # logger.info(f'搜索返回 {len(cards)} 候选')
            return {"candidates": cards, "summary": result}

        elif func_name == "get_card_by_id":
            card = self.get_card_by_id(args["card_id"])
            formatted = render_card(card)
            # logger.info(f'详情: {card.get("name", "?")}')
            return {"detail": formatted}

    def agent_chat(self, query: str) -> str:
        # logger.debug(f'查询: {query}')
        messages = [
                {
                    "role": "system",
                    "content": """你是一位【资深卡牌游戏分析师】。你的核心职责是为用户提供精炼、直击要点的卡牌效果解说。

                    ### 核心准则 (Core Principles)
                    1. **隐式数据处理**：工具返回的 JSON 数据（如ID、攻守、原始文本）仅供你内部理解使用。**严禁**在回复中罗列这些原始参数，**严禁**输出“属性：xx”、“攻击力：xx”等面板信息，除非这些数值与特定战术直接相关（如“攻击力0导致可以被xx检索”）。
                    2. **纯粹解读**：不要复述原文！不要复述原文！直接告诉用户这张卡“强在哪里”、“怎么用”、“有什么限制”。
                    3. **节省篇幅**：直接进入正题，去除所有客套话和格式化的数据块。
                    4. **尊重卡面文本**：只要用户问题中涉及卡名，你都**应该使用工具函数查询该卡**(除非在前几轮对话中已确认卡片效果)。

                    ### 交互流程
                    1. **工具调用**：
                       - 收到用户查询 -> 调用 `search_cards` 或 `get_card_by_id` 获取真实数据。

                    2. **思维链 (由你自己执行，不输出)**：
                       - 阅读 `description`，将“游戏王长难句”转化为逻辑点。
                       - 提炼核心：这张卡是展开点？阻抗？还是解场卡？
                       - 检查自肃：是否有严重的种族/属性限制？是否存在自肃？是发动后自肃，还是全回合自肃？

                    3. **输出规范 (仅输出解读内容)**：
                       请直接输出针对该卡牌的分析，包含如下方面的内容：

                       1. 卡名使用md_name字段。
                       2. **核心定位**：(一句话概括，如：本家核心初动 / 强力泛用康)
                       3. **效果解析**：
                           - 🎯 **(功能1)**：(用大白话解释效果。例如：召唤就能从卡组拿一张本家魔陷，赚卡点。)
                           - 🛡️ **(功能2)**：(例如：在墓地还能自跳挡刀。)
                           - ⚠️ **注意！区分自肃**：(发动后自肃：发效后只能出融合怪。全回合自肃：发动的回合自己不是融合怪兽就不能从额外卡组特殊召唤。)

                       (结束回复，不要附带原文)
                    """
                },            {"role": "user", "content": query}
        ]
        tools = self.get_tools()
        # 执行多轮对话
        for round_num in range(5):
            resp = self.call_llm(messages, tools)
            if "error" in resp: return f"❌ {resp['error']}"

            msg = resp["choices"][0]["message"]
            messages.append(msg)

            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    result = self.execute_tool(tc)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(result)
                    })
            else:
                # logger.info('LLM最终回复')
                return msg["content"]

    def chat_loop(self):
        print("\n🎮 === LLM多轮查卡代理 ===\n💡 示例: '烙印融合这张卡强大的原因？'\n🚪 quit退出")
        while True:
            try:
                q = input("🃏 你: ").strip()
                if q.lower() in ['quit', 'q']: break
                print("🤖 代理: ", end="", flush=True)
                print(self.agent_chat(q))
                print()
            except (KeyboardInterrupt, Exception) as e:
                logger.error(str(e))
                print("\n👋 再见！")
                break

def main():
    while True:
        print("\n🎮 === 游戏王查卡程序 === ")
        print("【1】百鸽查卡服务")
        print("【2】启用智能体查卡")
        print("【0】退出")
        print("-" * 30)

        choice = input("请选择选项 (1/2/0): ").strip()

        if choice == "1":
            try:
                config = json.load(open(r"C:\code\ygocdb-agent\config.json", 'r', encoding='utf-8'))
                client = MCPClient(config)
                print("\n🕊️ 【百鸽查卡服务(测试版)】已启用！输入关键词搜索，'quit'退出。")
                while True:
                    keyword = input("🔍 关键词: ").strip()
                    if keyword.lower() in ['quit', 'q']:
                        print("🕊️ 服务已退出，返回主菜单。")
                        break
                    if not keyword:
                        print("❌ 关键词不能为空！")
                        continue
                    results = client.search_cards(keyword)
                    print("\n📄 百鸽查卡结果:")
                    print(render_baige_results(results))
                    print()
            except FileNotFoundError:
                print("\n❌ config.json 文件不存在！请先创建它（即使空{}也行）。")
            except Exception as e:
                print(f"\n❌ 服务启动失败: {e}")
            continue
        elif choice == "2":
            try:
                agent = YGOCDBAgent()
                print("\n✅ 智能体查卡已启用！输入 'quit' 退出聊天模式。")
                agent.chat_loop()
            except ValueError as e:
                print(f"\n⚠️ 配置问题: {e}")
                print("请创建或修改配置文件 config.json，内容示例如下：")
                print('   {')
                print('     "api_url": "https://api.openai.com/v1/chat/completions",')
                print('     "api_key": "sk-你的key",')
                print('     "model": "gpt-4o"')
                print('   }')
                print("\n请在配置完成后重新选择【2】！")
            except KeyboardInterrupt:
                print("\n👋 操作中断！")
            except Exception as e:
                logger.error(f"未知错误: {e}")
                print(f"\n❌ 启动失败: {e}")
        elif choice == "0":
            print("\n👋 再见")
            break
        else:
            print("\n❌ 无效选项，请重新选择！")

if __name__ == "__main__":
    main()