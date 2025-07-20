import logging
import random
from datetime import datetime, timedelta
from collections import defaultdict
# import chinese_calendar as calendar
import pandas as pd
from api_get_holidays import get_holidays
self_all_holiday_list = []
self_condition1_list = []

logger = logging.getLogger(__name__)  # 会自动继承主模块的配置


class SimpleSchedulingSystem:
    def __init__(self, members=None):
        # 初始化成员列表
        self.members = members
        # 初始化数据结构
        self.schedule = {}  # 存储排班结果 {日期: 人员}
        self.unavailable_dates = defaultdict(list)  # 存储不可值班日期 {人员: [日期]}
        self.day_off_counts = defaultdict(int)  # 节假日值班次数
        self.workday_counts = defaultdict(int)  # 工作日值班次数
        self.total_counts = defaultdict(int)  # 总值班次数
    
    def set_members(self, members):
        """设置团队成员"""
        self.members = members
    
    def add_unavailable_date(self, member, date_str):
        """添加不可值班日期"""
        if member not in self.members:
            logger.warning(f"成员 {member} 不在团队中，本条个性化不排班需求 -> 作废！")
        # date = datetime.strptime(date_str, "%Y-%m-%d").date()
        self.unavailable_dates[member].append(date_str)
        logger.info(f"成员 {member} 的本条个性化不排班需求 -> 插入成功！")
    
    def is_holiday(self, date):
        """判断是否是节假日或周末"""
        if isinstance(date, str):
            date = datetime.strptime(date, "%Y-%m-%d").date()
        if date in self_condition1_list:
            return True
        res = False
        try:
            res = date in self_all_holiday_list
            return res
        except Exception as e:
            # 此时代表确实没有更新到所需的日期，直接判断是否周六周日即可！(周一是0)
            return date.weekday() >= 5
        
    
    def get_available_members(self, date, last_member=None):
        """获取可值班的人员列表"""
        date_str = date if isinstance(date, str) else date.strftime("%Y-%m-%d")
        available_members = []
        
        for member in self.members:
            # 检查是否是不可值班日期
            if date_str in self.unavailable_dates[member]:
                continue
            
            # 检查是否连续两天值班
            if member == last_member:
                continue
                
            available_members.append(member)
        
        return available_members
    
    def select_member(self, date, candidates):
        """从候选人员中选择最合适的值班人员"""
        if not candidates:
            return None
            
        # 按总值班次数排序，选择值班次数最少的人
        candidates.sort(key=lambda x: self.total_counts[x])
        
        # 获取最小值班次数
        min_count = self.total_counts[candidates[0]]
        
        # 筛选出值班次数最少的人员
        min_count_members = [m for m in candidates if self.total_counts[m] == min_count]
        
        # 如果是节假日，优先选择节假日值班少的人
        if self.is_holiday(date):
            min_count_members.sort(key=lambda x: self.day_off_counts[x])
            min_holiday_count = self.day_off_counts[min_count_members[0]]
            min_count_members = [m for m in min_count_members 
                              if self.day_off_counts[m] == min_holiday_count]
        else:
            # 如果是工作日，优先选择工作日值班少的人
            min_count_members.sort(key=lambda x: self.workday_counts[x])
            min_workday_count = self.workday_counts[min_count_members[0]]
            min_count_members = [m for m in min_count_members 
                               if self.workday_counts[m] == min_workday_count]
        
        # 如果还有多个候选，随机选择
        return random.choice(min_count_members)
    
    def generate_schedule(self, start_date, end_date):
        """
        生成指定日期范围内的排班表
        参数:
            start_date: 开始日期(YYYY-MM-DD格式或date对象)
            end_date: 结束日期(YYYY-MM-DD格式或date对象)
        返回:
            pandas DataFrame格式的排班表
        """
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        # 重置计数
        self.day_off_counts = defaultdict(int)
        self.workday_counts = defaultdict(int)
        self.total_counts = defaultdict(int)
        self.schedule = {}
        
        last_member = None
        current_date = start_date
        schedule_data = []
        
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            
            # 获取可值班人员
            available_members = self.get_available_members(date_str, last_member)
            if not available_members:
                # 如果没有可用人员，放宽连续值班的限制
                available_members = self.get_available_members(date_str, None)
                if not available_members:
                    raise ValueError(f"无法为 {date_str} 安排值班，所有人员都不可用")
            
            # 选择值班人员
            selected_member = self.select_member(date_str, available_members)
            self.schedule[date_str] = selected_member
            last_member = selected_member
            
            # 更新计数
            self.total_counts[selected_member] += 1
            if self.is_holiday(date_str):
                self.day_off_counts[selected_member] += 1
            else:
                self.workday_counts[selected_member] += 1
            
            # 准备输出数据
            weekday = ["一", "二", "三", "四", "五", "六", "日"][current_date.weekday()]
            day_type = "节假日" if self.is_holiday(date_str) else "工作日"
            
            schedule_data.append({
                "日期": date_str,
                "星期": f"星期{weekday}",
                "类型": day_type,
                "值班人员": selected_member
            })
            
            current_date += timedelta(days=1)
        
        # 创建DataFrame
        df = pd.DataFrame(schedule_data)
        
        # 添加统计信息
        stats_data = []
        for member in sorted(self.members):
            stats_data.append({
                "姓名": member,
                "总值班次数": self.total_counts[member],
                "工作日值班": self.workday_counts[member],
                "节假日值班": self.day_off_counts[member]
            })
        
        stats_df = pd.DataFrame(stats_data)
        
        return df, stats_df
    
    def save_to_excel(self, start_date, end_date, filename="排班表.xlsx"):
        """
        生成排班表并保存到Excel文件
        参数:
            start_date: 开始日期(YYYY-MM-DD格式或date对象)
            end_date: 结束日期(YYYY-MM-DD格式或date对象)
            filename: 输出的Excel文件名
        """
        # 生成排班表
        schedule_df, stats_df = self.generate_schedule(start_date, end_date)
        
        # 创建Excel writer
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # 写入排班表
            schedule_df.to_excel(writer, sheet_name='排班表', index=False)
            
            # 写入统计信息
            stats_df.to_excel(writer, sheet_name='值班统计', index=False)
            
            # 调整列宽
            for sheet in writer.sheets.values():
                sheet.column_dimensions['A'].width = 12
                sheet.column_dimensions['B'].width = 10
                sheet.column_dimensions['C'].width = 10
                sheet.column_dimensions['D'].width = 12
        
        logger.info(f"排班表已保存到 {filename}")


# 使用示例
def self_main( start_date, end_date, staff_list, condition_list1, condition_list2):
    # 入参示例：
    # start_date = "2025-07-01"
    # end_date="2026-01-14"
    # staff_list = [
    #     "张三", "李四", "王五", "赵六", "钱七", "孙八", "周九", "吴十",
    #     "郑十一", "王十二", "冯十三", "陈十四", "褚十五", "卫十六", 
    #     "蒋十七", "沈十八", "韩十九", "杨二十", "朱一", "秦二"
    # ]
    # condition_list1 = ["2025-07-01", "2025-07-02", "2025-09-01"]
    # condition_list2 = [  [2025-07-01, 张三], [2025-07-09, 李四]  ]
    logger.info(start_date+"  "+end_date)
    logger.info(staff_list)
    logger.info(condition_list1)
    logger.info(condition_list2)
    
    global self_condition1_list
    global self_all_holiday_list
    self_all_holiday_list = get_holidays(start_date,end_date)
    
    # 1. 初始化排班系统
    scheduler = SimpleSchedulingSystem()
    # 2. 自定义团队成员
    scheduler.set_members(staff_list)
    # 3. 设置自定义的额外非工作日
    self_condition1_list = [datetime.strptime(d, "%Y-%m-%d").date() for d in condition_list1]
    # 4. 设置不可值班日期
    for item in condition_list2:
        scheduler.add_unavailable_date(item[1], item[0])
        # scheduler.add_unavailable_date("张三", "2025-12-25")
    # 5. 生成排班表并保存到Excel
    now_str = datetime.now().strftime("%Y%m%d%H%M%S")
    scheduler.save_to_excel(start_date, end_date, f"duty_result_type1_{now_str}.xlsx") 
    logger.info("self_main排班完成")
    return f"duty_result_type1_{now_str}.xlsx"