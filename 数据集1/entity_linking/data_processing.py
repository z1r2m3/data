'''
#分行展示每一个json数据
import json


def transform_json(input_file, output_file):
    # 读取原始JSON文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)  # 假设原始数据是JSON数组

    transformed_data = []
    for item in data:
        # 提取text字段
        text = item['text']
        # 提取所有实体的"entity"值，拼接成字符串
        entities = [ent['entity'] for ent in item['entities']]
        entities_str = ', '.join(entities)
        # 构造新格式字典
        transformed_item = {
            "text": text,
            "entities": entities_str
        }
        transformed_data.append(transformed_item)

    # 写入转换后的JSON文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(transformed_data, f, ensure_ascii=False, indent=2)


# 使用示例
if __name__ == "__main__":
    input_json = "data/test.json"  # 原始JSON文件路径
    output_json = "data/cmeee_transformed.json"  # 转换后输出文件路径
    transform_json(input_json, output_json)
    print(f"转换完成，结果已保存至 {output_json}")
'''
#每一条json数据占一行，方便统计数据量。处理CMeEE实体抽取数据，使其规范，去除不必要的字段
import json

'''
def transform_json(input_file, output_file):
    # 读取原始JSON文件（假设是JSON数组格式）
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    transformed_data = []
    # 先完成数据格式转换（和之前逻辑一致）
    for item in data:
        text = item['text']
        entities = [ent['entity'] for ent in item['entities']]
        entities_str = ', '.join(entities)
        transformed_item = {
            "text": text,
            "entities": entities_str
        }
        transformed_data.append(transformed_item)

    # 关键修改：逐行写入每条JSON数据，实现“一条占一行”
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('[\n')  # 先写入JSON数组的开头符号
        # 遍历转换后的数据，逐行写入
        for i, item in enumerate(transformed_data):
            # 将单条数据转为JSON字符串（无缩进，紧凑格式）
            item_str = json.dumps(item, ensure_ascii=False)
            # 最后一条数据后不加逗号，其他加逗号
            if i == len(transformed_data) - 1:
                f.write(f'  {item_str}\n')
            else:
                f.write(f'  {item_str},\n')
        f.write(']')  # 写入JSON数组的结尾符号


# 使用示例
if __name__ == "__main__":
    input_json = "data/CMeEE-V2_train.json"  # 原始文件路径
    output_json = "data/CMeEE-V2_train_update.json"  # 输出文件路径
    transform_json(input_json, output_json)
    print(f"转换完成，结果已保存至 {output_json}")

'''
'''
#为知识图谱当中的实体分配ID
import json

# 读取txt实体文件，生成带唯一ID的映射表
entity_id_map = {}  # 键：实体名，值：唯一ID
id_counter = 1  # ID起始值

# 读取原始实体txt（假设文件名为kg_entities.txt）
with open("data/entity.txt", "r", encoding="utf-8") as f:
    for line in f:
        entity_name = line.strip()  # 去除换行符和空格
        if entity_name and entity_name not in entity_id_map:  # 避免空行和重复实体
            # 生成唯一ID（格式：MED_001、MED_002...）
            entity_id = f"MED_{id_counter:03d}"  # 03d表示3位数字，不足补0
            entity_id_map[entity_name] = entity_id
            id_counter += 1

# 1. 保存“实体名→ID”的JSON映射表（后续复用）
with open("data/kg_entity_id_map.json", "w", encoding="utf-8") as f:
    json.dump(entity_id_map, f, ensure_ascii=False, indent=2)

# 2. 新增：将“实体名+ID”写入新的txt文件（原文件kg_entities.txt不变）
# 新文件名为kg_entities_with_id.txt（可自定义）
with open("data/kg_entities_with_id.txt", "w", encoding="utf-8") as f:
    for entity_name, entity_id in entity_id_map.items():
        # 按“实体名 + 分隔符 + ID”的格式写入，分隔符用逗号或制表符均可
        f.write(f"{entity_name},{entity_id}\n")

print(f"处理完成！")
print(f"- 原文件 kg_entities.txt 未修改")
print(f"- 已生成 JSON 映射表：kg_entity_id_map.json（共 {len(entity_id_map)} 个实体）")
print(f"- 已生成带ID的新txt文件：kg_entities_with_id.txt")
'''
'''
#实体映射
import json

# 加载知识图谱实体映射表和你的JSON数据集
with open("data/kg_entity_id_map.json", "r", encoding="utf-8") as f:
    kg_entity_map = json.load(f)
with open("data/CMeEE-V2_train_update.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)  # 你的JSON数据（含text和entities字段）

# 实体匹配函数（先完全匹配，再部分匹配）
def match_entity(mention, kg_map):
    matched_result = None
    # 1. 优先完全匹配（如“大叶性肺炎”直接匹配）
    if mention in kg_map:
        matched_result = {
            "mention": mention,
            "linked_entity": mention,
            "linked_id": kg_map[mention],
            "match_type": "完全匹配"
        }
    # 2. 部分匹配（如“肺炎”匹配“大叶性肺炎”，可选，根据需求开启）
    else:
        for kg_entity, kg_id in kg_map.items():
            if mention in kg_entity or kg_entity in mention:
                matched_result = {
                    "mention": mention,
                    "linked_entity": kg_entity,
                    "linked_id": kg_id,
                    "match_type": "部分匹配"
                }
                break  # 只取第一个匹配到的实体，后续可人工筛选
    # 3. 无匹配结果
    if not matched_result:
        matched_result = {
            "mention": mention,
            "linked_entity": "无匹配",
            "linked_id": "无",
            "match_type": "无匹配"
        }
    return matched_result

# 为JSON中每个实体提及匹配知识图谱实体
for item in json_data:
    # 拆分entities字符串为单个实体提及
    mentions = [m.strip() for m in item["entities"].split(",")]
    # 匹配每个提及并保存结果
    item["linked_results"] = [match_entity(mention, kg_entity_map) for mention in mentions]

# 保存带链接结果的中间文件（供人工审核）
with open("data/CMeEE-V2_train_update_linked.json", "w", encoding="utf-8") as f:
    json.dump(json_data, f, ensure_ascii=False, indent=2)

print("匹配完成！已生成带候选链接的中间文件")
'''
'''
#删除无匹配的字段
import json


def filter_no_match(input_file, output_file):
    # 读取带链接结果的JSON文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)  # 假设是JSON数组格式

    # 过滤每个item中的"无匹配"结果
    filtered_data = []
    for item in data:
        # 仅保留match_type为"完全匹配"或"部分匹配"的结果
        filtered_links = [
            link for link in item["linked_results"]
            if link["match_type"] in ["完全匹配", "部分匹配"]
        ]
        # 替换原linked_results为过滤后的结果
        item["linked_results"] = filtered_links
        filtered_data.append(item)

    # 保存过滤后的新文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=2)


# 使用示例
if __name__ == "__main__":
    input_json = "data/CMeEE-V2_train_update_linked.json"  # 输入文件路径
    output_json = "data/CMeEE-V2_train_update_linked1.json"  # 输出文件路径
    filter_no_match(input_json, output_json)
    print(f"过滤完成！已保存至 {output_json}")
'''
'''

import json

# 原文件路径
input_file = "data/CMeEE-V2_train_update_linked.json"
# 输出文件路径（包含前100条数据）
output_file = "data/100_data.json"

# 读取原文件数据
with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)  # 假设数据是JSON数组格式（如[{"key":...}, ...]）

# 截取前100条数据（如果原数据不足100条，则取全部）
top_100_data = data[3000:3500]

# 写入新文件
with open(output_file, 'w', encoding='utf-8') as f:
    # 保证中文正常显示，且格式美观（indent=2）
    json.dump(top_100_data, f, ensure_ascii=False, indent=2)

print(f"已成功将前100条数据复制到 {output_file}")
'''
'''
import json


# Function to filter linked results based on the status
def filter_linked_results(data):
    # Keep only the items where status is "保留"
    filtered_linked_results = [
        result for result in data["linked_results"] if result["status"] == "保留"
    ]

    # Update the original data with the filtered results
    data["linked_results"] = filtered_linked_results
    return data


# Load data from a.json
with open('data/CMeEE-V2_train_update_linked_100_LLM.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Apply the function to each entry in the JSON file
filtered_data = [filter_linked_results(entry) for entry in data]

# Save the filtered data to b.json
with open('data/1.json', 'w', encoding='utf-8') as file:
    json.dump(filtered_data, file, ensure_ascii=False, indent=4)

print("Filtered data has been saved to b.json")
'''
'''
import json

# Function to add the "kg_entities" field with the linked_entities
def add_kg_entities(data):
    for entry in data:
        # Extract linked_entity values from "linked_results" where status is "保留"
        kg_entities = ", ".join([result["linked_entity"] for result in entry["linked_results"] if result["status"] == "保留"])
        entry["kg_entities"] = kg_entities
    return data

# Load data from a.json
with open('data/1.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Apply the function to the data
updated_data = add_kg_entities(data)

# Save the updated data to b.json
with open('data/2.json', 'w', encoding='utf-8') as file:
    json.dump(updated_data, file, ensure_ascii=False, indent=4)

print("Data with 'kg_entities' added has been saved to b.json.")

'''
'''
import json

# Function to extract the required fields
def extract_fields(data):
    extracted_data = []
    for entry in data:
        extracted_data.append({
            "text": entry.get("text"),
            "entities": entry.get("entities"),
            "kg_entities": entry.get("kg_entities")
        })
    return extracted_data

# Load the original data from a JSON file (replace 'a.json' with your file name)
with open('data/2.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Extract the required fields
extracted_data = extract_fields(data)

# Save the extracted data to a new JSON file (each line contains one JSON object)
with open('data/3.json', 'w', encoding='utf-8') as file:
    for entry in extracted_data:
        json.dump(entry, file, ensure_ascii=False)
        file.write('\n')

print("Data has been extracted and saved to 'extracted_data.json'")
'''
'''
import json

# Function to filter out entries where "kg_entities" is empty
def filter_empty_kg_entities(data):
    # Keep only the entries where "kg_entities" is not empty
    return [entry for entry in data if entry.get("kg_entities")]

# Load data from a.json
with open('data/CMeEE-V2_link_LLM3.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Filter out entries with empty "kg_entities"
filtered_data = filter_empty_kg_entities(data)

# Save the filtered data to b.json
with open('data/CMeEE-V2_link_LLM4.json', 'w', encoding='utf-8') as file:
    json.dump(filtered_data, file, ensure_ascii=False, indent=4)

print("Data with non-empty 'kg_entities' has been saved to 'b.json'.")
'''
'''
import json

# Function to filter out entries where "kg_entities" is empty
def filter_empty_kg_entities(data):
    # Keep only the entries where "kg_entities" is empty
    return [entry for entry in data if not entry.get("kg_entities")]

# Load data from a.json
with open('data/CMeEE-V2_link_LLM3.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Filter out entries with empty "kg_entities"
empty_kg_entities_data = filter_empty_kg_entities(data)

# Save the filtered data to c.json
with open('data/CMeEE-V2_link_LLM5.json', 'w', encoding='utf-8') as file:
    json.dump(empty_kg_entities_data, file, ensure_ascii=False, indent=4)

print("Data with empty 'kg_entities' has been saved to 'c.json'.")
'''
'''
import json

# Function to filter and keep the entries where "match_type" is "完全匹配"
def filter_match_type(data, start_index=4000):
    # Keep only the entries from the start_index onward that have "match_type": "完全匹配"
    filtered_data = []
    for entry in data[start_index:]:
        if any(result.get("match_type") == "完全匹配" for result in entry.get("linked_results", [])):
            filtered_data.append(entry)
    return filtered_data

# Load data from m.json
with open('data/CMeEE-V2_train_update_linked.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Apply the function to filter data starting from the 4000th entry
filtered_data = filter_match_type(data)

# Save the filtered data to n.json
with open('data/6.json', 'w', encoding='utf-8') as file:
    json.dump(filtered_data, file, ensure_ascii=False, indent=4)

print("Filtered data has been saved to 'n.json'.")
'''
import json


# Function to process each entry and modify it according to the requirements
def process_data(data):
    for entry in data:
        # Extract all "linked_entity" with "match_type": "完全匹配"
        kg_entities = ", ".join([result["linked_entity"] for result in entry.get("linked_results", []) if
                                 result.get("match_type") == "完全匹配"])

        # Add "kg_entities" field
        entry["kg_entities"] = kg_entities

        # Remove the "linked_results" field
        if "linked_results" in entry:
            del entry["linked_results"]

    return data


# Load data from n.json
with open('data/6.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Process the data
processed_data = process_data(data)

# Save the processed data to x.json
with open('data/7.json', 'w', encoding='utf-8') as file:
    json.dump(processed_data, file, ensure_ascii=False, indent=4)

print("Data has been processed and saved to 'x.json'.")
