from dashscope import MultiModalConversation
from config import API_KEY
import re

def get_sell_points_from_all_images(image_paths):
    """对一组拼图图像统一识别出卖点关键词维度"""
    messages = [
        {
            "role": "user",
            "content": [
                *[{"image": path} for path in image_paths],
                {"text": "你是一位专业的 Amazon 商品图片卖点提炼专家。\n\n"
        "请依次完成以下任务：\n"
        "1. 根据所提供的多张商品图片，判断它们是否属于同一类商品（如行李箱、耳机、电脑包等）；\n"
        "2. 统一对这类商品的图片进行分析，从图中总结出清晰可见、显著体现的卖点维度（如 TSA锁、万向轮、扩容层、USB接口等）；\n"
        "3. 仅返回这类商品图片中反复出现、共同具备、且在图像中视觉上容易识别的卖点关键词。\n\n"
        "⚠️ 要求：\n"
        "- 返回 **不超过7个** 的中文关键词；\n"
        "- 每个关键词 **不超过8个字**；\n"
        "- 不要返回句子、解释或编号；\n"
        "- 输出格式仅为关键词组成的列表（用顿号或逗号分隔）。\n\n"
        "示例输出格式（仅示例）：USB接口、万向轮、加厚杆、扩容层"}
            ]
        }
    ]
    try:
        response = MultiModalConversation.call(
            api_key=API_KEY,
            model="qwen-vl-plus",
            messages=messages
        )
        result = response.output.choices[0].message.content[0]["text"]

        # ✅ 使用正则分隔关键词（支持顿号、逗号、中英文逗号）
        lines = re.split(r"[，,、\s]+", result)
        lines = [line.strip() for line in lines if line.strip()]

        return lines

    except Exception as e:
        print(f"❌ 多图卖点维度分析失败: {e}")
        return []


def classify_image_by_points(image_path, point_list):
    """根据统一卖点维度，判断某个子图是否匹配相关卖点，仅返回关键词"""
    prompt = (
            "你是一个电商图像分析专家。"
            "现在请你判断以下这张商品图片中，是否有清晰展示、显著体现以下关键词中的某些卖点。"
            "只有在图中**明显可见、突出呈现**该卖点特征的情况下，才返回对应关键词。"
            "不要因为推测、模糊存在、间接关联而返回关键词。"
            "只返回关键词本身，用顿号或逗号分隔，不要返回解释内容。\n关键词列表：" + "，".join(point_list)
    )
    messages = [
        {
            "role": "user",
            "content": [
                {"image": image_path},
                {"text": prompt}
            ]
        }
    ]
    try:
        response = MultiModalConversation.call(
            api_key=API_KEY,
            model="qwen-vl-plus",
            messages=messages
        )
        result = response.output.choices[0].message.content[0]["text"]

        # ✅ 清洗和过滤返回
        result = result.replace("关键词：", "").replace("关键词:", "")
        result = result.replace("。", "\n").replace("，", "\n").replace(",", "\n")
        lines = [line.strip("- ").strip() for line in result.splitlines() if line.strip()]
        # 只保留模型识别出的、在关键词维度列表中的词
        filtered = [kw for kw in lines if kw in point_list]
        return filtered

    except Exception as e:
        print(f"❌ 分类失败: {e}")
        return []