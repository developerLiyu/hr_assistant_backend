


def parse_optional_int(value: str | None) -> int | None:
    """
    处理整数参数为""方法：将空字符串转换为 None
    :param value:
    :return:
    """
    if value is None or value == "" or value == "None":
        return None
    return int(value)