


'''
#删除无关数据
from openai import OpenAI
import json

# 1. 初始化七牛云AI客户端
openai_base_url = ' '#替换为自己的链接
openai_api_key = ' '  # 替换为你的API密钥
client = OpenAI(
    base_url=openai_base_url,
    api_key=openai_api_key
)


# 2. 加载知识图谱实体（从entities.json读取，返回{实体: ID}字典和实体列表）
def load_kg_entities(kg_json_path):
    """
    读取entities.json中的实体-ID映射
    返回：(entity_id_map, entity_list)，其中entity_list是所有实体名称的列表
    """
    with open(kg_json_path, 'r', encoding='utf-8') as f:
        entity_id_map = json.load(f)  # 格式：{"肺泡蛋白质沉积症": "MED_001", ...}
    entity_list = list(entity_id_map.keys())  # 提取所有实体名称
    return entity_id_map, entity_list


# 3. 通用医学实体关联判断（部分匹配筛选）
def filter_partial_match(mention, linked_entity, text, entity_list):
    """
    通用逻辑：判断任意医学实体提及与知识图谱实体的关联性
    适用于所有医学领域实体（疾病、病毒、解剖部位等）
    """
    prompt = f"""
    任务：基于医学专业知识，判断以下两个实体是否存在明确关联（如包含、从属、病因、症状、解剖关联等医学逻辑关系）。

    关键信息：
    - 文本语境：{text}（实体出现的上下文，辅助判断）
    - 待判断实体提及：{mention}（从文本中提取的实体）
    - 知识图谱部分匹配实体：{linked_entity}（知识图谱中名称部分重叠的实体）
    - 知识图谱实体类型参考（部分）：{entity_list[:30]}（仅展示部分实体，用于理解图谱领域）

    判断标准：
    1. 若存在医学逻辑上的关联（例如：
       - 疾病与病因：“肺炎”与“肺炎链球菌”
       - 解剖部位与疾病：“肺”与“肺炎”
       - 病原体与相关疾病：“冠状病毒”与“冠状病毒感染”
       - 别名与正式名：“伤风”与“普通感冒”），返回“保留”；
    2. 若仅名称部分重叠但无医学关联（例如：
       - “伤风”与“破伤风”
       - “鼻病毒”与“鼻窦炎”（无直接关联）
       - “鼻咽部”与“咽部肿瘤”（无明确关联）），返回“删除”；
    3. 输出格式严格限定为“保留”或“删除”，不添加任何解释文字。
    """
    response = client.chat.completions.create(
        model="deepseek-v3",
        messages=[{"role": "user", "content": prompt}],
        stream=False,
        max_tokens=10
    )
    result = response.choices[0].message.content.strip()
    return result == "保留"


# 4. 优化：纯中文无匹配实体处理（兼容中英文，强化中文场景）
def complement_no_match(mention, entity_id_map, entity_list):
    """
    通用逻辑：为无匹配的医学实体（含纯中文、英文）生成同义词/标准名并匹配知识图谱
    重点优化纯中文实体场景：若实体已是标准名则直接匹配，非标准名则生成别名
    """
    prompt_synonym = f"""
    任务：处理医学实体“{mention}”，生成其中文标准医学名称及所有可能的同义词/别名（含通用俗称、医学简称）。

    处理规则（优先针对中文场景，兼顾英文）：
    1. 若输入为中文：
       - 先判断是否为“标准医学名称”（如“胸膜炎”“肺部感染”是标准名，“肺痨”“伤风”是非标准名）；
       - 若是标准名：直接返回该标准名（无需额外添加别名，避免冗余）；
       - 若是非标准名（如俗称、简称）：先返回对应的中文标准名，再补充1-3个常见同义词/别名；
    2. 若输入为英文（如“pneumonia”“coronavirus”）：
       - 先翻译为准确的中文标准医学名称，再补充1-2个中文同义词/别名；
    3. 覆盖范围：疾病名称（如“胸膜疾病”“小儿胸膜疾病”）、病原体、解剖部位、医学术语等；
    4. 输出格式：仅返回中文名称，用逗号分隔（示例：
       - 输入“胸膜疾病”（中文标准名）→ 输出“胸膜疾病”
       - 输入“小儿胸膜疾病”（中文标准名）→ 输出“小儿胸膜疾病”
       - 输入“肺痨”（中文非标准名）→ 输出“肺结核,肺痨,肺痨病”
       - 输入“common cold”（英文）→ 输出“普通感冒,感冒,伤风”）；
    5. 严格限制：不添加任何解释、标点（除逗号外）、多余文字，确保输出可直接用于匹配。
    """
    response_syn = client.chat.completions.create(
        model="deepseek-v3",
        messages=[{"role": "user", "content": prompt_synonym}],
        stream=False,
        max_tokens=100
    )

    # 清洗同义词列表（处理纯中文场景的冗余，保留有效名称）
    synonyms = response_syn.choices[0].message.content.strip().split(",")
    synonyms = [
        s.strip() for s in synonyms
        if s.strip() and len(s) > 1  # 过滤空值、单个字符（如“病”“炎”）
           and s not in ["无", "无匹配", "暂无"]  # 过滤无效值
    ]
    synonyms = list(set(synonyms))  # 去重（避免LLM生成重复别名）

    # 匹配知识图谱：优先匹配标准名，再匹配别名
    matched_entity = None
    for syn in synonyms:
        if syn in entity_list:
            matched_entity = syn
            break  # 取第一个匹配的实体（优先标准名）

    # 若匹配成功，返回补全结果；若未匹配，返回None（表示知识图谱中无对应实体）
    if matched_entity:
        return {
            "mention": mention,
            "linked_entity": matched_entity,
            "linked_id": entity_id_map[matched_entity],
            "match_type": "LLM补全-同义匹配"
        }
    return None

# 5. 处理单条数据
def process_single_item(item, entity_id_map, entity_list):
    """处理单条JSON数据，更新linked_results"""
    processed_links = []
    for link in item["linked_results"]:
        # 处理部分匹配
        if link["match_type"] == "部分匹配":
            if filter_partial_match(
                    mention=link["mention"],
                    linked_entity=link["linked_entity"],
                    text=item["text"],
                    entity_list=entity_list
            ):
                processed_links.append(link)  # 保留有关联的
            continue

        # 处理无匹配（补全）
        if link["match_type"] == "无匹配":
            complement_result = complement_no_match(
                mention=link["mention"],
                entity_id_map=entity_id_map,
                entity_list=entity_list
            )
            if complement_result:
                processed_links.append(complement_result)  # 补全成功则添加
            continue

        # 完全匹配直接保留
        if link["match_type"] == "完全匹配":
            processed_links.append(link)

    item["linked_results"] = processed_links
    return item


# 6. 主流程：从文件读取并批量处理
def main():
    # 配置文件路径（根据实际情况修改）
    input_json_path = "data/CMeEE-V2-train_update_linked1_test.json"  # 输入JSON文件路径（包含多条数据）
    output_json_path = "data/CMeEE-V2-train_update_linked1_test1.json"  # 输出结果文件路径
    kg_json_path = "data/kg_entity_id_map.json"  # 知识图谱实体JSON文件路径（格式：{"实体": "ID", ...}）

    # 加载知识图谱实体（获取映射表和实体列表）
    entity_id_map, entity_list = load_kg_entities(kg_json_path)
    print(f"已加载知识图谱实体 {len(entity_list)} 个")

    # 从文件读取JSON数据（支持单条对象或多条数组）
    with open(input_json_path, "r", encoding="utf-8") as f:
        input_data = json.load(f)
    # 确保数据是列表（若为单条对象，转为列表）
    if isinstance(input_data, dict):
        input_data = [input_data]

    # 批量处理每条数据
    processed_data = []
    for i, item in enumerate(input_data, 1):
        print(f"正在处理第 {i}/{len(input_data)} 条数据...")
        processed_item = process_single_item(item, entity_id_map, entity_list)
        processed_data.append(processed_item)

    # 保存处理结果
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=2)
    print(f"所有数据处理完成，结果已保存至 {output_json_path}")


if __name__ == "__main__":
    main()
'''



from openai import OpenAI
import json

# 1. 初始化七牛云AI客户端
openai_base_url = ' '#替换为自己的链接
openai_api_key = ' '  # 替换为你的API密钥
client = OpenAI(
    base_url=openai_base_url,
    api_key=openai_api_key
)


# 2. 加载知识图谱实体（从entities.json读取）
def load_kg_entities(kg_json_path):
    """读取entities.json，返回{实体: ID}字典和实体列表"""
    with open(kg_json_path, 'r', encoding='utf-8') as f:
        entity_id_map = json.load(f)
    entity_list = list(entity_id_map.keys())
    return entity_id_map, entity_list


# 3. 部分匹配实体判断（添加保留/删掉标记，不实际删除）
def filter_partial_match(mention, linked_entity, text, entity_list):
    """
    对部分匹配实体判断关联性，返回添加状态标记的原始数据
    status为"保留"或"删掉"，供人工复查
    """
    prompt = f"""
    任务：基于医学专业知识，判断以下两个实体是否存在明确关联（如包含、从属、病因、症状、解剖关联等医学逻辑关系）。

    关键信息：
    - 文本语境：{text}（实体出现的上下文，辅助判断）
    - 待判断实体提及：{mention}（从文本中提取的实体）
    - 知识图谱部分匹配实体：{linked_entity}（知识图谱中名称部分重叠的实体）
    - 知识图谱实体类型参考（部分）：{entity_list[:30]}（仅展示部分实体，用于理解图谱领域）

    判断标准：
    1. 若存在医学逻辑上的关联（例如：
       - 疾病与病因：“肺炎”与“肺炎链球菌”
       - 解剖部位与疾病：“肺”与“肺炎”
       - 病原体与相关疾病：“冠状病毒”与“冠状病毒感染”
       - 别名与正式名：“伤风”与“普通感冒”“肺脓疡”与“肺脓肿”），返回“保留”；
    2. 若仅名称部分重叠但无医学关联（例如：
       - “伤风”与“破伤风”
       - “鼻病毒”与“鼻窦炎”（无直接关联）
       - “鼻咽部”与“咽部肿瘤”（无明确关联）），返回“删除”；
    3. 输出格式严格限定为“保留”或“删除”，不添加任何解释文字。
    """
    response = client.chat.completions.create(
        model="deepseek-v3",
        messages=[{"role": "user", "content": prompt}],
        stream=False,
        max_tokens=10
    )
    result = response.choices[0].message.content.strip()

    # 返回添加状态标记的原始数据（不删除，仅标记）
    return {
        "mention": mention,
        "linked_entity": linked_entity,
        "linked_id": linked_entity,  # 保留原始linked_id
        "match_type": "部分匹配",
        "status": "保留" if result == "保留" else "删掉"  # 核心：添加状态标记
    }


# 4. 无匹配实体补全（保持原逻辑，补全结果默认标记为"保留"）
def complement_no_match(mention, entity_id_map, entity_list):
    """为无匹配实体生成同义词并匹配知识图谱，补全结果添加"status": "保留"标记"""
    prompt_synonym = f"""
    任务：处理医学实体“{mention}”，生成其中文标准医学名称及所有可能的同义词/别名（含通用俗称、医学简称）。

    处理规则（优先针对中文场景，兼顾英文）：
    1. 若输入为中文：
       - 先判断是否为“标准医学名称”（如“胸膜炎”“肺部感染”是标准名，“肺痨”“伤风”是非标准名）；
       - 若是标准名：直接返回该标准名（无需额外添加别名，避免冗余）；
       - 若是非标准名（如俗称、简称）：先返回对应的中文标准名，再补充1-3个常见同义词/别名；
    2. 若输入为英文（如“pneumonia”“coronavirus”）：
       - 先翻译为准确的中文标准医学名称，再补充1-2个中文同义词/别名；
    3. 覆盖范围：疾病名称（如“胸膜疾病”“小儿胸膜疾病”）、病原体、解剖部位、医学术语等；
    4. 输出格式：仅返回中文名称，用逗号分隔（示例：
       - 输入“胸膜疾病”（中文标准名）→ 输出“胸膜疾病”
       - 输入“小儿胸膜疾病”（中文标准名）→ 输出“小儿胸膜疾病”
       - 输入“肺痨”（中文非标准名）→ 输出“肺结核,肺痨,肺痨病”
       - 输入“common cold”（英文）→ 输出“普通感冒,感冒,伤风”）；
    5. 严格限制：不添加任何解释、标点（除逗号外）、多余文字，确保输出可直接用于匹配。
    """
    response_syn = client.chat.completions.create(
        model="deepseek-v3",
        messages=[{"role": "user", "content": prompt_synonym}],
        stream=False,
        max_tokens=100
    )

    synonyms = response_syn.choices[0].message.content.strip().split(",")
    synonyms = [
        s.strip() for s in synonyms
        if s.strip() and len(s) > 1
           and s not in ["无", "无匹配", "暂无"]
    ]
    synonyms = list(set(synonyms))

    matched_entity = None
    for syn in synonyms:
        if syn in entity_list:
            matched_entity = syn
            break

    if matched_entity:
        return {
            "mention": mention,
            "linked_entity": matched_entity,
            "linked_id": entity_id_map[matched_entity],
            "match_type": "LLM补全-同义匹配",
            "status": "保留"  # 补全成功的实体默认标记为保留
        }
    # 无匹配的实体保留原始信息，标记为"未补全"
    return {
        "mention": mention,
        "linked_entity": "无匹配",
        "linked_id": "无",
        "match_type": "无匹配",
        "status": "未补全"
    }


# 5. 处理单条数据（所有数据均保留，仅添加状态标记）
def process_single_item(item, entity_id_map, entity_list):
    processed_links = []
    for link in item["linked_results"]:
        # 处理部分匹配：添加保留/删掉标记，保留原始数据
        if link["match_type"] == "部分匹配":
            processed_link = filter_partial_match(
                mention=link["mention"],
                linked_entity=link["linked_entity"],
                text=item["text"],
                entity_list=entity_list
            )
            processed_links.append(processed_link)
            continue

        # 处理无匹配：补全或标记未补全，保留原始数据
        if link["match_type"] == "无匹配":
            processed_link = complement_no_match(
                mention=link["mention"],
                entity_id_map=entity_id_map,
                entity_list=entity_list
            )
            processed_links.append(processed_link)
            continue

        # 完全匹配：直接添加"保留"标记
        if link["match_type"] == "完全匹配":
            link_with_status = link.copy()
            link_with_status["status"] = "保留"  # 完全匹配默认保留
            processed_links.append(link_with_status)
            continue

    item["linked_results"] = processed_links
    return item


# 6. 主流程
def main():
    input_json_path = "data/100_data.json"  # 输入JSON文件路径（包含多条数据）
    output_json_path = "data/CMeEE-V2_train_update_linked_100_LLM.json"  # 输出结果文件路径
    kg_json_path = "data/kg_entity_id_map.json"  # 知识图谱实体JSON文件路径（格式：{"实体": "ID", ...}）

    entity_id_map, entity_list = load_kg_entities(kg_json_path)
    print(f"已加载知识图谱实体 {len(entity_list)} 个")

    with open(input_json_path, "r", encoding="utf-8") as f:
        input_data = json.load(f)
    if isinstance(input_data, dict):
        input_data = [input_data]

    processed_data = []
    for i, item in enumerate(input_data, 1):
        print(f"正在处理第 {i}/{len(input_data)} 条数据...")
        processed_item = process_single_item(item, entity_id_map, entity_list)
        processed_data.append(processed_item)

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=2)
    print(f"处理完成，结果保存至 {output_json_path}（所有数据均保留，已添加状态标记）")


if __name__ == "__main__":
    main()


