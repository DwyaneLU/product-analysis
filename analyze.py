from dashscope import MultiModalConversation
from config import API_KEY

def get_sell_points_from_all_images(image_paths):
    """对一组拼图图像统一识别出卖点关键词维度"""
    messages = [
        {
            "role": "user",
            "content": [
                *[{"image": path} for path in image_paths],
                {"text": "请你首先确定这些图片是属于什么种类的商品，然后对这些图片中的商品进行统一卖点归纳分析，总结它们所具备的合理的商品卖点维度（如 TSA密码锁、万向轮、扩容层、USB接口等），返回精炼且合理的中文关键词列表，"
                         "关键词不超过7个且每个关键字长度不超过5个字，勿返回句子。"}
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
        # ✅ 新增对中文分号 "；" 的拆分支持
        result = result.replace("；", "\n").replace("。", "\n").replace("，", "\n").replace(",", "\n")
        lines = [line.strip("- ").strip() for line in result.splitlines() if line.strip()]
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