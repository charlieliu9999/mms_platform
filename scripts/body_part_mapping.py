"""
P2任务：统一部位字典映射

问题：
- 引擎归一化：盆腔 → 盆腔及盆底结构
- 标准库字段：body_part_l2 = '盆腔'
- 结果：即使扫描方式匹配，部位也对不上

解决方案：
在 standard_lookup_service 查询时建立等价映射
"""

# 部位等价映射表
BODY_PART_EQUIVALENTS = {
    # 引擎归一化名称 -> 标准库可能的变体
    "盆腔及盆底结构": ["盆腔及盆底结构", "盆腔"],
    "四肢及关节": ["四肢及关节", "四肢", "关节"],
    "颅脑": ["颅脑", "脑", "头颅"],
    "全腹部": ["全腹部", "腹部"],

    # 反向映射（标准库 -> 引擎归一化）
    "盆腔": ["盆腔", "盆腔及盆底结构"],
    "四肢": ["四肢", "四肢及关节"],
    "关节": ["关节", "四肢及关节"],
    "脑": ["脑", "颅脑"],
    "腹部": ["腹部", "全腹部"],
}

def get_body_equivalents(body_name: str) -> list:
    """
    获取部位的所有等价名称

    Args:
        body_name: 部位名称

    Returns:
        包含该部位所有等价名称的列表（包含自身）
    """
    if body_name in BODY_PART_EQUIVALENTS:
        return BODY_PART_EQUIVALENTS[body_name]
    return [body_name]


# 测试
if __name__ == "__main__":
    test_cases = [
        "盆腔及盆底结构",
        "盆腔",
        "四肢及关节",
        "颅脑",
        "肝脏",  # 无映射
    ]

    print("部位等价映射测试:")
    for body in test_cases:
        equivalents = get_body_equivalents(body)
        print(f"{body:15s} -> {equivalents}")
