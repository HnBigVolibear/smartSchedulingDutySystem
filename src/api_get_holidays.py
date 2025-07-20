from datetime import datetime
import requests
import json

import logging
logger = logging.getLogger(__name__)  # 会自动继承主模块的配置


def get_years_in_range(start_date_str, end_date_str, date_format="%Y-%m-%d"):
    """
    获取起止日期时段内涉及的所有年份
    
    参数:
        start_date_str: 开始日期字符串 (例如: "2020-01-15")
        end_date_str: 结束日期字符串 (例如: "2023-12-31")
        date_format: 日期字符串的格式 (默认为 "%Y-%m-%d")
    
    返回:
        包含时段内所有年份的列表，按升序排列
    """
    try:
        # 将字符串转换为日期对象
        start_date = datetime.strptime(start_date_str, date_format)
        end_date = datetime.strptime(end_date_str, date_format)
        # 确保开始日期不大于结束日期
        if start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期")
        # 获取年份范围
        start_year = start_date.year
        end_year = end_date.year
        # 生成年份列表
        years = list(range(start_year, end_year + 1))
        return years
    except ValueError as e:
        raise ValueError(f"日期格式错误或无效: {e}")
    

def get_non_zero_type_dates(data):
    # 解析出里面所有的假期日期
    return [
        day_info["date"].strip()
        for day_info in data["holiday"].values() 
        if day_info.get("holiday") is True
    ]
    
def get_holidays(start_date_str, end_date_str):
    year_list = get_years_in_range(start_date_str, end_date_str)
    holiday_list = []
    for year in year_list:
        api_url = f"https://timor.tech/api/holiday/year/{year}?type=Y&week=Y"
        # 关键：添加浏览器标头
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://timor.tech/"
        }
        try:
            response = requests.get(api_url, headers=headers, timeout=8)
            response.raise_for_status()
            logger.info(f"成功从接口获取到了{year}的节假日信息：")
            new_data = get_non_zero_type_dates(response.json())
            logger.info("成功解析出里面的假期日期列表。")
            # 将节假日信息添加到result列表中
            holiday_list = holiday_list + new_data
        except Exception as e:
            logger.error(f"{year}获取节假日信息失败: {e}")
    if holiday_list:
        holiday_list = list(set(holiday_list))
        # 将假期日期列表，转换为真正的日期对象列表：
        holiday_list = [datetime.strptime(date_str, "%Y-%m-%d").date() for date_str in holiday_list]
    logger.info("获取假期列表api_get_holidays.get_holidays执行完毕。")
    return holiday_list

if __name__ == '__main__':
    print(get_holidays(start_date_str="2024-07-01", end_date_str="2026-01-14"))
    # print(get_years_in_range(start_date_str="2024-07-01", end_date_str="2026-01-14"))