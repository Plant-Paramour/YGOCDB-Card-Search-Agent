import logging
import re
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def render_card(card: Dict[str, Any]) -> str:
    """根据类型渲染卡片信息"""
    if 'error' in card:
        return f'❌ {card.get("error", "未知错误")}'

    name = card.get('name', '未知')
    id_ = card.get('id', '?')
    type_ = card.get('type', '?')
    desc = card.get('desc', '无')
    if len(desc) > 800:
        desc = desc[:800] + '...'
    image = f'https://cdn.233.momobako.com/ygopro/pics/{id_}.jpg' if id_ != '?' else ''

    # logger.debug(f'渲染卡片: {name}, 类型: {type_}')

    if '怪兽' in type_ or 'Monster' in type_:
        race = card.get('race', '?')
        attr = card.get('attribute', '?')
        level = card.get('level', '?')
        atk = card.get('atk', '?')
        def_ = card.get('def', '?')
        return f'''🃏 **{name}**
```
ID: {id_} | 类型: {type_}
种族: {race} | 属性: {attr}
等级: {level} | ATK/DEF: {atk}/{def_}
```
![卡片图片]({image})

**效果：**
{desc}'''
    else:
        return f'''🃏 **{name}**
```
ID: {id_} | 类型: {type_}
```
![卡片图片]({image})

**效果：**
{desc}'''

def render_baige_card(card: Dict[str, Any]) -> str:
    """百鸽服务专用渲染，按指定格式，支持灵摆（安全group无unpack）"""
    if 'error' in card:
        return f'❌ {card.get("error", "未知错误")}'

    md_name = card.get('md_name', card.get('cn_name', '未知'))
    aliases_parts = []
    cn_name = card.get('cn_name')
    if cn_name:
        aliases_parts.append(f"cn: {cn_name}")
    sc_name = card.get('sc_name')
    if sc_name:
        aliases_parts.append(f"sc: {sc_name}")
    nwbbs_n = card.get('nwbbs_n')
    if nwbbs_n:
        aliases_parts.append(f"nwbbs: {nwbbs_n}")
    cnocg_n = card.get('cnocg_n')
    if cnocg_n:
        aliases_parts.append(f"cnocg: {cnocg_n}")
    aliases = ', '.join(aliases_parts) if aliases_parts else '无'

    en_name = card.get('en_name', '无')
    jp_name = card.get('jp_name', '无')
    jp_ruby = card.get('jp_ruby', '')
    jp_info = f"{jp_name} ({jp_ruby})" if jp_ruby else jp_name

    id_ = card.get('id', '?')
    image = f'https://cdn.233.momobako.com/ygopro/pics/{id_}.jpg'

    text = card.get('text', {})
    types_str = text.get('types', '?').strip()
    desc = text.get('desc', '无效果').replace('\\r', '').replace('\\n', '\n')
    pdesc = text.get('pdesc', '').replace('\\r', '').replace('\\n', '\n')
    if len(desc) > 1000:
        desc = desc[:1000] + '...'
    if len(pdesc) > 1000:
        pdesc = pdesc[:1000] + '...'

    data = card.get('data', {})
    is_monster = '怪兽' in types_str
    # 从types_str解析属性、种族、等级（替换原来的data获取）
    lines = [line.strip() for line in types_str.split('\n') if line.strip()]
    attr_name = '?'
    race_name = '?'
    level_str = ''
    if len(lines) >= 1:
        first_line_parts = lines[0].split(maxsplit=2)
        if len(first_line_parts) >= 2:
            race_attr_str = first_line_parts[1]
            if '/' in race_attr_str:
                race_part, attr_part = race_attr_str.split('/', 1)
                race_part_clean = race_part.rstrip()
                attr_part_clean = attr_part.rstrip()
                race_name = race_part_clean + '族' if not race_part_clean.endswith('族') else race_part_clean
                attr_name = attr_part_clean + '属性' if not attr_part_clean.endswith('属性') else attr_part_clean
            else:
                # 无/时，假设为种族
                race_part_clean = race_attr_str.rstrip()
                race_name = race_part_clean + '族' if not race_part_clean.endswith('族') else race_part_clean
    if len(lines) >= 2:
        second_line = lines[1]
        level_match = re.search(r'\[★(\d+)\]', second_line)
        if level_match:
            level_str = f'[★{level_match.group(1)}]'

    atk = data.get('atk', '?')
    def_ = data.get('def', '?')

    # 灵摆安全解析（group(1)/group(2)无unpack）
    is_pendulum = '灵摆' in types_str
    scale_left = '？'
    scale_right = '？'
    if is_pendulum:
        match = re.search(r'(\d+)/(\d+)\s*$', types_str)
        if match:
            scale_left = match.group(1)
            scale_right = match.group(2)

    output = f"""# {md_name}
**别名**: {aliases}
**英语名**:{en_name}
**平假名&假名**:{jp_info}
**卡图**({image})

**基本信息**
- **ID**: {id_}
- **类型**: {types_str}
"""

    if is_monster:
        output += f"- **属性**: {attr_name} / **种族**: {race_name} / **等级/阶级**: {level_str}\n"
        output += f"- **攻击力**: {atk} / **守备力**: {def_}\n"
        if is_pendulum:
            output += f"- **灵摆刻度**: {scale_left}/{scale_right}\n"
    else:
        output += "(注: 魔法/陷阱卡请省略攻守/等级信息)\n"

    if is_pendulum and pdesc.strip():
        output += f"""
**灵摆效果**
{pdesc}

"""

    output += f"**效果文本**{desc}"

    return output


def render_baige_results(results: List[Dict[str, Any]]) -> str:
    """批量渲染搜索结果，最多10张"""
    if not results:
        return "❌ 无匹配卡片"
    rendered = []
    for i, card in enumerate(results[:10], 1):
        rendered.append(f"**第{i}匹配:**\n{render_baige_card(card)}\n{'─' * 60}")
    return '\n\n'.join(rendered)
