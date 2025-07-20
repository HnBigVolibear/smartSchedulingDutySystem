import logging
from collections import defaultdict
from datetime import datetime, timedelta
import os
import sys
# import chinese_calendar as calendar
import pandas as pd
import pulp
import random

from api_get_holidays import get_holidays 
pulp_all_holiday_list = []
pulp_condition1_list = []

logger = logging.getLogger(__name__)  # 会自动继承主模块的配置


class ShiftScheduler:
    def __init__(self):
        self.employees = []
        self.unavailable_dates = defaultdict(list)
    
    def set_employees(self, employee_names):
        """设置团队成员"""
        self.employees = employee_names
    
    def add_unavailable_date(self, employee_name, date_str):
        """添加不可值班日期"""
        if employee_name not in self.employees:
            # self.unavailable_dates[employee_name] = []
            logger.warning(f"成员 {employee_name} 不在团队中，本条个性化不排班需求 -> 作废！")
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        self.unavailable_dates[employee_name].append(date)
        logger.info(f"成员 {employee_name} 的本条个性化不排班需求 -> 插入成功！")
    
    def is_holiday(self, date):
        """判断是否是节假日或周末"""
        # 如果date是字符串类型，则将其转换为日期类型
        if isinstance(date, str):
            date = datetime.strptime(date, "%Y-%m-%d").date()
        # 如果date在pulp_condition1_list中，则返回True
        if date in pulp_condition1_list:
            return True
        res = False
        try:
            res = date in pulp_all_holiday_list
            return res
        except Exception as e:
            # 此时代表确实没有更新到所需的日期，直接判断是否周六周日即可！(周一是0)
            return date.weekday() >= 5
    
    def generate_schedule(self, start_date_str, end_date_str):
        """生成排班表"""
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        # 创建日期列表
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date)
            current_date += timedelta(days=1)
        
        # 随机打乱员工顺序以增加随机性
        shuffled_employees = self.employees.copy()
        random.shuffle(shuffled_employees)
        
        # 创建问题实例
        prob = pulp.LpProblem("Shift_Scheduling", pulp.LpMinimize)
        
        # 创建决策变量
        shifts = pulp.LpVariable.dicts(
            'shift', 
            [(e, d) for e in shuffled_employees for d in dates],  # 使用打乱后的顺序
            cat='Binary'
        )
        
        # 添加随机权重以增加解的多样性
        weights = {(e, d): random.uniform(0.9, 1.1) for e in shuffled_employees for d in dates}
        
        # 目标函数：最小化加权总值班次数（引入随机性）
        prob += pulp.lpSum([shifts[(e, d)] * weights[(e, d)] for e in shuffled_employees for d in dates])
        
        # 约束条件
        
        # 1. 每天必须有一人值班
        for d in dates:
            prob += pulp.lpSum([shifts[(e, d)] for e in shuffled_employees]) == 1, f"daily_coverage_{d}"
        
        # 2. 不能安排到不可值班的日期
        for e in shuffled_employees:
            if e in self.unavailable_dates:
                for d in self.unavailable_dates[e]:
                    if d in dates:
                        prob += shifts[(e, d)] == 0, f"unavailable_{e}_{d}"
        
        # 3. 避免连续两天值班（严格约束）
        for e in shuffled_employees:
            for i in range(len(dates)-1):
                d1 = dates[i]
                d2 = dates[i+1]
                prob += shifts[(e, d1)] + shifts[(e, d2)] <= 1, f"no_consecutive_{e}_{d1}"
        
        # 4. 更严格的公平分配
        total_days = len(dates)
        min_shifts = total_days // len(shuffled_employees)
        max_shifts = min_shifts + 1
        
        # 确保每个人值班次数差异不超过1天
        for e in shuffled_employees:
            prob += pulp.lpSum([shifts[(e, d)] for d in dates]) >= min_shifts, f"min_shifts_{e}"
            prob += pulp.lpSum([shifts[(e, d)] for d in dates]) <= max_shifts, f"max_shifts_{e}"
        
        # 5. 节假日更公平分配
        holiday_dates = [d for d in dates if self.is_holiday(d)]
        if holiday_dates:
            holiday_min = len(holiday_dates) // len(shuffled_employees)
            holiday_max = holiday_min + 1
            for e in shuffled_employees:
                prob += pulp.lpSum([shifts[(e, d)] for d in holiday_dates]) >= holiday_min, f"min_holiday_{e}"
                prob += pulp.lpSum([shifts[(e, d)] for d in holiday_dates]) <= holiday_max, f"max_holiday_{e}"
        
        # 求解问题
        # 指定 CBC 求解器的路径（适用于打包后）
        solver = None
        try:
            cbc_path = os.path.join(sys._MEIPASS, "pulp", "solverdir", "cbc", "win", "i64", "cbc.exe")
            solver = pulp.PULP_CBC_CMD(path=cbc_path, mip=True, msg=True, timeLimit=20)
        except Exception as e:
            solver=pulp.PULP_CBC_CMD(mip=True, msg=True, timeLimit=20)
        prob.solve(solver)
        
        # 检查解的状态
        if pulp.LpStatus[prob.status] != 'Optimal':
            logger.error(f"警告：未找到最优解，当前状态：{str(pulp.LpStatus[prob.status])}")
        
        # 提取结果
        schedule = {}
        for d in dates:
            for e in shuffled_employees:
                if pulp.value(shifts[(e, d)]) > 0.9:
                    schedule[d] = e
                    break
        
        return schedule
    
    def save_to_excel(self, schedule, filename):
        """保存排班表到Excel"""
        schedule_data = []
        holiday_counts = {e: 0 for e in self.employees}
        workday_counts = {e: 0 for e in self.employees}
        total_counts = {e: 0 for e in self.employees}
        
        for date, employee in sorted(schedule.items()):
            weekday = ["一", "二", "三", "四", "五", "六", "日"][date.weekday()]
            day_type = "节假日" if self.is_holiday(date) else "工作日"
            
            if day_type == "节假日":
                holiday_counts[employee] += 1
            else:
                workday_counts[employee] += 1
            total_counts[employee] += 1
            
            schedule_data.append({
                "日期": date.strftime("%Y-%m-%d"),
                "星期": f"星期{weekday}",
                "类型": day_type,
                "值班人员": employee
            })
        
        # 统计信息
        stats_data = []
        for employee in self.employees:
            stats_data.append({
                "姓名": employee,
                "总值班次数": total_counts[employee],
                "工作日值班": workday_counts[employee],
                "节假日值班": holiday_counts[employee]
            })
        
        # 创建Excel文件
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # 排班表
            schedule_df = pd.DataFrame(schedule_data)
            schedule_df.to_excel(writer, sheet_name='排班表', index=False)
            
            # 统计信息
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='值班统计', index=False)
            
            # 调整列宽
            for sheet in writer.sheets.values():
                sheet.column_dimensions['A'].width = 12
                sheet.column_dimensions['B'].width = 10
                sheet.column_dimensions['C'].width = 10
                sheet.column_dimensions['D'].width = 12
        
        logger.info(f"排班表已保存到 {filename}")


# 使用示例
def pulp_main( start_date, end_date, staff_list, condition_list1, condition_list2):
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
    
    global pulp_condition1_list
    global pulp_all_holiday_list
    pulp_all_holiday_list = get_holidays(start_date,end_date)
    
    # 1. 初始化排班系统
    scheduler = ShiftScheduler()
    # 2. 自定义团队成员
    scheduler.set_employees(staff_list)
    # 3. 设置自定义的额外非工作日
    pulp_condition1_list = [datetime.strptime(d, "%Y-%m-%d").date() for d in condition_list1]
    # 4. 设置不可值班日期
    for item in condition_list2:
        scheduler.add_unavailable_date(item[1], item[0])
        # scheduler.add_unavailable_date("张三", "2025-12-25")
    # 5. 生成排班表并保存到Excel
    schedule = scheduler.generate_schedule(start_date, end_date)
    now_str = datetime.now().strftime("%Y%m%d%H%M%S")
    scheduler.save_to_excel(schedule, f"duty_result_type2_{now_str}.xlsx") 
    logger.info("pulp_main排班完成")
    return f"duty_result_type2_{now_str}.xlsx"



# 算法说明：
# PuLP 是一个 Python 线性规划库，用于解决 数学优化问题（特别是线性规划、整数规划和混合整数规划问题）。它提供了一个高级接口，可以方便地定义优化模型、添加约束条件，并调用求解器（如 CBC、GLPK 等）进行计算。

# PuLP 的核心功能
# 定义优化问题

# 可以定义 最大化（Maximize） 或 最小化（Minimize） 的目标函数。

# 支持 线性约束（如 a*x + b*y <= c）。

# 支持 整数变量（Integer） 和 二进制变量（Binary）（适用于排班、调度等离散优化问题）。

# 调用求解器

# 支持多种求解器（如 CBC、GLPK、CPLEX、Gurobi 等）。

# 默认自带 CBC（无需额外安装，但性能较弱）。

# 也可以使用更强大的商业求解器（如 Gurobi、CPLEX）。

# 适用于排班、资源分配、物流优化等问题

# 特别适合 排班系统（如您的需求：每天安排 1 人值班，避免连续排班，节假日公平分配）。

# 也适用于 生产调度、投资组合优化、运输问题 等。

# PuLP 在您的排班系统中的作用
# 您的需求：

# 每天 1 人值班 → 用 二进制变量（Binary）表示某天某人是否值班。

# 避免连续值班 → 用 约束条件 限制 shift[张三, 周一] + shift[张三, 周二] <= 1。

# 节假日公平分配 → 用 目标函数 最小化节假日值班次数的方差。

# 不可值班日期 → 直接固定某些变量为 0。

# PuLP 让您可以用 数学表达式 描述这些规则，并自动计算最优排班表。
    

# 提示词：

# 使用python实现一个自动智能排班程序，场景是我们部门有二十几个人，每天需要有一位同事值班。要尽可能平均分配，并且一般情况一个人原则上不要连续值班2天。同时整体上大家在节假日（包括周六周日）的值班天数要是几乎相等的，是否工作日需要使用chinese_calendar这个库来判断。最后，如果有人提前说明未来某一天他无法值班，则排班时自动考虑这个因素。
# 我还需要可以指定团队成员，指定排班的起止日期。
# 我不需要调度，不需要每7天按周管控。我只要运行后就得到起止日期内所有日期的排班情况，保存在excel里。
# 以上这个排班功能，如何实现，给我完整的代码。最好是能使用一些高级的算法，让排班更优雅，效果更完美。