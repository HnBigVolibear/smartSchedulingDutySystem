import flet as ft
from datetime import timedelta, datetime, date

import json
import os
import sys
import math

import warnings
warnings.filterwarnings("ignore", category=UserWarning) # 禁用pip的警告

import mode_self as mode1
import mode_pulp as mode2

import logging
logging.basicConfig(
    level=logging.INFO,  # 设置日志级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # 设置日志格式
    handlers=[
        logging.FileHandler('Smart_Scheduling_Duty_System_use_api_log.txt', encoding='utf-8'),  # 输出到文件
        logging.StreamHandler()         # 同时输出到控制台（可选）
    ]
)
# 获取 logger 实例
logger = logging.getLogger(__name__)

APP_NAME = "智能随机排班系统"
APP_VERSION = "V1.0.1 API版" # 特别说明：API版是使用API接口获取数据的版本，非API版是使用本地文件获取数据的版本


# #####################################################
# 打包须知：
# 1. 务必使用Python虚拟环境（推荐venv），否则你打包出来的exe文件会非常大（可能高达2GB以上），因为会包含所有库的文件（包括Flet依赖的flutter框架。。。）；
# 2. 打包前请确保已经安装了pyinstaller，并且已经安装了flet、pandas、pulp、requests等库；
# 3. 请务必：在Flet项目的 < src > 文件夹里调出cmd来打包！！！
# 4. 打包时需要使用pyinstaller的--onefile参数，否则会生成多个文件；
# 5. 打包时需要使用pyinstaller的--add-data参数，否则不会复制资源文件！必须包含以下资源文件：
#     - ../.venv/Lib/site-packages/pulp;pulp
#     - assets
# 6. 示例打包命令：
# pyinstaller --windowed --onefile --name "智能随机排班系统" --add-data "../.venv/Lib/site-packages/pulp;pulp" --add-data "assets;assets" main.py --icon bear.ico --noconfirm --clean       
# #####################################################


def get_resource_path(relative_path):
    """获取资源文件的正确路径，适配开发环境和打包环境"""
    if hasattr(sys, '_MEIPASS'):
        # 打包后的环境
        base_path = sys._MEIPASS
        return os.path.join(base_path, relative_path)
    else:
        # 开发环境
        return "src/"+relative_path


def save_to_file(key, value):
    if not os.path.exists('voli_bear_config.json'):
        logger.info("检测到voli_bear_config.json本地配置文件不存在，现在自动创建新配置文件")
    # 保存数据到本地文件
    config = load_from_file()
    config[key] = value
    with open('voli_bear_config.json', 'w') as f:
        json.dump(config, f)
    logger.info(f"保存配置项：{key} = {value} 到本地配置文件")

def load_from_file():
    # 从本地文件加载数据
    if not os.path.exists('voli_bear_config.json'):
        return {}
    with open('voli_bear_config.json', 'r') as f:
        return json.load(f)



def main(page: ft.Page):
    page.title = f"{APP_NAME} - {APP_VERSION}"
    # page.horizontal_alignment = 'CENTER'       # 水平居中
    # page.vertical_alignment = 'CENTER'         # 垂直居中
    page.adaptive = True
    page.padding = ft.padding.only(top=8,bottom=0,left=0,right=0)
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO
    
    page.window.bgcolor = ft.Colors.TRANSPARENT # 设置大窗口背景颜色
    page.bgcolor = '#FFF8DC' # 设置真正的本应用窗口的背景颜色
    # page.window.title_bar_color = '#BA55D3' # 设置标题栏背景颜色，好像不生效。。。
    page.window.title_bar_hidden = False # 是否隐藏标题栏
    # page.window.frameless = True
    page.window.left = 3 # 窗口出现的初始位置，左上角坐标x
    page.window.top = 6 # 窗口出现的初始位置，左上角坐标y
    page.window.width = 720 # 窗口宽度
    page.window.height = 830 # 窗口高度
    page.window.resizable = False # 是否可以调整应用程序窗口的大小
    page.window.shadow = True # 是否在应用程序窗口周围显示阴影
    page.window.movable = True  # 是否可以移动应用程序窗口
    page.update()
    
    
    top_title = ft.Text(
        value=APP_NAME, 
        tooltip=ft.Tooltip(message="^_^自己的工具自己造！"),
        color="green", font_family="楷体", size=56, 
        width=page.window.width,
        height=66,
        text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD,
    )
    author_title = ft.Text(
        value="出品方：湖南大白熊工作室", 
        color="#181818", size=16, 
        # width=282,
        height=23,
        text_align=ft.TextAlign.LEFT,
        badge=ft.Badge(
            text="^_^",
            text_color=ft.Colors.WHITE,
            bgcolor="#1e90ff",
            offset=ft.Offset(12, -4), # 设置角标位置
        ), # 添加角标
    )
    # page.add(
    #     top_title, 
    #     ft.Row(controls=[
    #             ft.Icon(name=ft.Icons.FAVORITE, color=ft.Colors.PINK), # 前缀图标
    #             author_title,
    #         ],
    #         alignment=ft.MainAxisAlignment.CENTER,  # 水平居中
    #     ), 
    #     ft.Divider(color="transparent", height=5),
    # )
    
    
    algorithm_type = [
        ["我手搓的普通线性规划算法", ft.Colors.RED],
        ["基于PuLP的高级规划算法", ft.Colors.BLUE],
    ]
    def get_options():
        options = []
        for option in algorithm_type:
            options.append(
                ft.DropdownOption(
                    key=option[0],
                    content=ft.Text(
                        value=option[0],
                        color=option[1],
                    ),
                )
            )
        return options
    
    def dropdown_changed(e):
        logger.info(f'选择了算法：{str(e.control.value)}')
        
    algorithm = ft.Dropdown(
        label="选择你想用的排班算法",
        color=ft.Colors.PURPLE_600,
        text_size=14,
        width=page.window.width,
        text_align=ft.TextAlign.CENTER,
        options=get_options(),
        
        on_change=dropdown_changed,
    )
    # page.add(algorithm)
    
    
    def is_need_hint_year(data_str):
        input_date = datetime.strptime(data_str, "%Y-%m-%d").date()
        current_date = datetime.now().date()
        # 获取年份和月份
        input_year = input_date.year
        current_year = current_date.year
        current_month = current_date.month
        if input_year <= current_year:
            return False
        else:  # 未来年份
            if current_month >= 11:
                return False
            else:
                return True
    def confirm_year_to_hint(data_str):
        is_need_hint = is_need_hint_year(data_str)
        if is_need_hint:
            snack = ft.SnackBar(
                content=ft.Text(f"【警告】您选择的日期在明年或更往后，但是当前月份还未到11月，python的节假日库可能暂时还未更新到明年，即可能会无法获取到准确的节假日。您可以忽略本条提示，程序会继续，只是可能明年的节假日会直接根据是否周末来判断了！"),
                duration=4000, # 持续时间，单位为毫秒
                behavior=ft.SnackBarBehavior.FLOATING,
                dismiss_direction=ft.DismissDirection.END_TO_START,
                margin=ft.margin.only(bottom=90),
                bgcolor = '#1e90ff',
                open = True
            )
            page.add(snack)
    def set_start_date(e):
        logger.info('设置了开始日期：'+e.data.replace("T00:00:00.000",""))
        date_button1.text = e.data.replace("T00:00:00.000","")
        # 同步设置 结束日期 不得 早于开始日期！
        date_obj = datetime.strptime(e.data.replace("T00:00:00.000",""), "%Y-%m-%d")
        date_picker2.first_date = date_obj + timedelta(days=1)
        page.update()
        confirm_year_to_hint(e.data.replace("T00:00:00.000",""))
    def set_end_date(e):
        logger.info('设置了结束日期：'+e.data.replace("T00:00:00.000",""))
        date_button2.text = e.data.replace("T00:00:00.000","")
        page.update()
        confirm_year_to_hint(e.data.replace("T00:00:00.000",""))
    date_picker1 = ft.DatePicker(
        help_text="值班开始日期",
        cancel_text="取消",confirm_text="确定",error_format_text="日期格式错误",error_invalid_text="无效的日期",
        field_hint_text="选择日期",field_label_text="日期",
        first_date=date(datetime.now().year-1, 1, 1),
        last_date=date(datetime.now().year+2, 1, 1) - timedelta(days=1), 
        on_change=set_start_date
    )
    date_picker2 = ft.DatePicker(
        help_text="值班结束日期",
        cancel_text="取消",confirm_text="确定",error_format_text="日期格式错误",error_invalid_text="无效的日期",
        field_hint_text="选择日期",field_label_text="日期",
        first_date=date(datetime.now().year-1, 1, 1),
        last_date=date(datetime.now().year+2, 1, 1) - timedelta(days=1),
        on_change=set_end_date
    )
    page.overlay.append(date_picker1)
    page.overlay.append(date_picker2)
    def open_date_picker1(e):
        logger.info('点击了开始日期按钮')
        date_picker1.open = True
        page.update()
    def open_date_picker2(e):
        logger.info('点击了结束日期按钮')
        date_picker2.open = True
        page.update()
    date_button1 = ft.ElevatedButton(
        "排班开始日期",
        icon=ft.Icons.CALENDAR_MONTH,
        on_click=open_date_picker1
    )
    date_button2 = ft.ElevatedButton(
        "排班结束日期",
        icon=ft.Icons.CALENDAR_MONTH,
        on_click=open_date_picker2
    )
    
    first_row = ft.Row(controls=[
        ft.Container(expand=4, content=ft.Text(
            value="请选择排班的时段范围:", 
            # weight=ft.FontWeight.BOLD,
            size=16,
            color="#424242"
        )),
        ft.Container(expand=5, content=date_button1),
        ft.Container(expand=5, content=date_button2)
    ])
    # page.add(ft.Container(
    #     content=first_row, 
    #     expand=True,
    #     height=50,
    #     padding=ft.padding.only(top=2,bottom=2, left=12,right=12), #内边距
    #     margin=ft.margin.only(top=8,bottom=8), #外边距
    #     border=ft.border.all(width=1, color="#202020"), #边框
    #     border_radius=4, #圆角
    #     clip_behavior=ft.ClipBehavior.HARD_EDGE, #裁剪行为
    #     opacity=0.99, # 透明度（0-1，越小越透明）
    #     # animate_opacity=300, #动画时间
        
    #     # 我自己学着试一试玩一玩渐变色！
    #     gradient=ft.LinearGradient(
    #         begin=ft.alignment.center_left,
    #         end=ft.alignment.center_right,
    #         colors=[
    #             "#ABF8FF",  # 浅蓝色
    #             "#F0F8FF",  # 更接近白色的浅蓝色
    #         ],
    #         tile_mode=ft.GradientTileMode.MIRROR, # 渐变平铺模式
    #         rotation=math.pi / 3,  # 旋转角度
    #     ),
    # ))
    
    
    
    def handle_team_members_change(e: ft.ControlEvent): # 保存当前输入的数据
        save_to_file("team_members_text", e.control.value)
    team_members = ft.TextField(
        label="请提供值班团队人员列表（多个人员之间用中文逗号隔开）",
        color=ft.Colors.PURPLE_600,
        width=page.window.width,
        hint_text="注：多个人员之间用中文逗号隔开",
        multiline=True,
        min_lines=3, max_lines=8,
        text_size=14,
        on_change=handle_team_members_change,
        # 高级用法：
        cursor_color="#1E90FF", # 光标颜色
        cursor_width=2, # 光标宽度
        # icon=ft.Icon(name=ft.Icons.FAVORITE, color=ft.Colors.PINK), # 前缀图标
    )
    # page.add(team_members)
    # 加载之前保存的数据
    team_members_text = load_from_file().get("team_members_text", "")
    if team_members_text: # 如果之前有保存的数据，则将其设置为文本框的值
        logger.info("配置参数【team_members_text】成功加载到之前保存的数据")
        team_members.value = team_members_text
        page.update()
    
    
    def handle_condition1_change(e: ft.ControlEvent): # 保存当前输入的数据
        save_to_file("condition1_text", e.control.value)
    condition1 = ft.TextField(
        label="自定义额外休息日（形如2025-07-01，多个日期用逗号隔开）",
        color=ft.Colors.PURPLE_600,
        multiline=True,
        min_lines=2, max_lines=5,
        text_size=14,
        on_change=handle_condition1_change,
        hint_text="多个日期用逗号隔开，形如：2025-07-01"
    )
    hint1 = ft.Text(
        value="注：本系统已自动识别国家所有法定节假日（包括调休补班都能识别哦^_^），但如果你的公司或部门还有其他额外的休息日，则请手动录入！（比如工会活动日啥的）\n另外，如果当前还未到11月，则排班结束日期尽量不要到明年！否则节假日获取可能小概率会失败！",
        tooltip=ft.Tooltip("特别鸣谢：@提莫的神秘小站 提供节假日接口数据！\n官网：https://timor.tech/api/holiday")
    )
    def handle_condition2_change(e: ft.ControlEvent): # 保存当前输入的数据
        save_to_file("condition2_text", e.control.value)
    condition2 = ft.TextField(
        label="个性化不排需求（形如2025-07-01:张三，多个要求用逗号隔开）",
        color=ft.Colors.PURPLE_600,
        multiline=True,
        min_lines=2, max_lines=5,
        text_size=14,
        on_change=handle_condition2_change,
        hint_text="多个需求用逗号隔开，形如：2025-07-01:张三，2025-11-01:李四"
    )
    hint2 = ft.Text(value="注：这里是用于供团队成员自行选择自己不想要值班的日期。如果某人某天明确表示不想值班，则请手动录入！")
    
    condition_card = ft.Card(
        content=ft.Container(
            content=ft.Column(controls=[
                ft.Text(value="高级选项：", size=20, weight=ft.FontWeight.BOLD),
                condition1, hint1,
                ft.Divider(color="transparent", height=2), 
                condition2, hint2,
            ]),
            padding=14,
        ),
        margin=ft.margin.only(top=8),
        elevation=10,
        color="#FEF2BD"
    )
    # page.add(condition_card)
    # 加载之前保存的数据
    condition1_text = load_from_file().get("condition1_text", "")
    if condition1_text: # 如果之前有保存的数据，则将其设置为文本框的值
        logger.info("配置参数【condition1_text】成功加载到之前保存的数据")
        condition1.value = condition1_text
        page.update()
    condition2_text = load_from_file().get("condition2_text", "")
    if condition2_text: # 如果之前有保存的数据，则将其设置为文本框的值
        logger.info("配置参数【condition2_text】成功加载到之前保存的数据")
        condition2.value = condition2_text
        page.update()
        
    
    
    def open_dialog(dlg_text):
        dlg.content = ft.Text(value=dlg_text, selectable=True)
        dlg.open = True
        page.update()
    def close_dialog(e):
        dlg.open = False
        page.update()
    dlg = ft.AlertDialog(
        title="提示", 
        content=ft.Text(value="默认对话框"),
        actions=[ ft.TextButton(text="确定", on_click=close_dialog) ],
    )
    page.overlay.append(dlg)
    
    
    def params_is_valid():
        if not date_button1.text or not date_button2.text or not team_members.value or len(date_button1.text) != 10 or len(date_button2.text) != 10 or len(team_members.value) < 3:
            return False
        return True
    # 至关重要的函数：
    def generate_schedule(e):
        if not algorithm.value:
            open_dialog('呵呵，第一行参数配置，你选了什么算法？')
            return None
        if not params_is_valid():
            open_dialog("参数校验不通过！请注意：开始日期、结束日期、排班团队列表，不能为空！")
            return None
        
        set_generate_btn_style(False)
        snack = ft.SnackBar(
            content=ft.Text("正在生成中，请耐心等待。。。"),
            duration=2800, # 持续时间，单位为毫秒
            behavior=ft.SnackBarBehavior.FLOATING,
            dismiss_direction=ft.DismissDirection.END_TO_START,
            margin=ft.margin.only(bottom=48),
            bgcolor = '#1e90ff',
            open = True
        )
        page.add(snack)
        
        logger.info('开始生成排版表。。。')
        try:
            p1 = date_button1.text
            p2 = date_button2.text
            p3 = [] if not team_members.value else list(set(
                team_members.value.replace(",","，").split("，")
            ))
            p4 = [] if not condition1.value else list(set(
                condition1.value.replace(",","，").split("，")
            ))
            p5 = [] if not condition2.value else [
                i.split("：") for i in 
                list(set(
                    condition2.value.replace(",","，").replace(":","：").split("，")
                ))
            ]
            logger.info("相关参数已整理完毕，开始调用排班算法。。。")
            
            file_name = None
            if algorithm.value == '我手搓的普通线性规划算法':
                logger.info('此时是第一种算法模式')
                file_name = mode1.self_main(p1,p2,p3,p4,p5)
            else:
                logger.info('此时是第二种算法模式')
                file_name = mode2.pulp_main(p1,p2,p3,p4,p5)
            
            # 生成完毕，弹出框提示用户已完毕！
            logger.info('【结束】排班执行完毕！')
            open_dialog(f"排班表已生成完毕！EXCEL默认生成在本工具所在文件夹。生成文件名：\n{file_name}")
        except Exception as e:
            logger.error(f"【崩溃】排班时发生错误：\n{str(e)}")
            open_dialog(f"【崩溃】排班时发生错误：\n{str(e)}\n\n部分严重错误，可能导致程序异常，可以考虑重启本程序再试！")
        # 生成完毕，恢复按钮状态
        set_generate_btn_style(True)
    
    generate_btn = ft.ElevatedButton(
        text="生成值班表", 
        disabled=False,
        on_click=generate_schedule,
        width=240,
        height=40,
        bgcolor='blue',
        color='white',
        style=ft.ButtonStyle(
            text_style=ft.TextStyle(
                size=22,
                font_family="华文彩云",
                # weight=ft.FontWeight.BOLD, # 粗体
                letter_spacing=5
            ),
            shape=ft.RoundedRectangleBorder(radius=18), #圆角
            elevation={"pressed": 14, "default": 7}, #阴影
            overlay_color=ft.Colors.BLUE_ACCENT, # 按钮按下时的颜色
            # alignment=ft.alignment.center, # 按钮文字居中
        ),
        # tooltip="提交表单", # 悬停提示
        # badge=ft.Badge(text="^_^"), # 添加角标
        icon=ft.Icons.BACK_HAND_ROUNDED, # 添加图标。图标大全：https://gallery.flet.dev/icons-browser/
        icon_color="white", # 图标颜色
        # url="https://github.com/HnBigVolibear", # 点击按钮跳转的链接
    )
    
    # 设置生成按钮的样式
    def set_generate_btn_style(type):
        if type:
            generate_btn.text = "生成值班表"
            generate_btn.disabled=False
            generate_btn.bgcolor='blue'
            page.update()
        else:
            generate_btn.text = "生成中。。。"
            generate_btn.disabled=True
            generate_btn.bgcolor='#808080'
            page.update()
    
    
    def handle_close(e):
        dlg_my_wechat.open = False
        page.update()
    dlg_my_wechat = ft.AlertDialog(
        modal=True,
        title=ft.Text("Sponsor Me~"),
        content=ft.Column(
            controls=[
                ft.Text("❤️如果你认可我的工作，这边可以让我买一杯咖啡继续创作下去呢"),  # 原有文字
                ft.Image(src=get_resource_path("assets/sponsor.png"), width=360, height=360),  # 微信二维码图片
                ft.Text("Buy Me a Coffee ^_^", size=12, color="#FF8C00")  # 说明文字
            ],
            tight=True,  # 紧凑布局
            spacing=10,  # 控件间距
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,  # 水平居中
        ),
        actions=[
            ft.TextButton("确定！", on_click=handle_close)
        ],
        actions_alignment=ft.MainAxisAlignment.END
    )
    def open_my_wechat(e):
        page.open(dlg_my_wechat)
    
    
    # 创建悬浮图片（带旋转和溢出）
    right_bottom_img = ft.Container( # 右下角图标
        content=ft.Image(
            src=get_resource_path("assets/wechat.png"),
            rotate=ft.Rotate(angle=-0.65, alignment=ft.alignment.bottom_center),
            width=64, height=64,
            fit=ft.ImageFit.COVER,
            repeat=ft.ImageRepeat.NO_REPEAT,
            opacity=0.94,
        ),
        right=-26,
        bottom=-8,
        
        on_click=open_my_wechat,
        # 交互增强
        tooltip=ft.Tooltip(message="一切Bug与技术支持，请联系我☝"),
        animate_scale=ft.Animation(duration=300, curve=ft.AnimationCurve.EASE_OUT),  # 缩放动画
        on_hover=lambda e: [
            setattr( e.control, "scale", 
                ft.Scale(1.3) if e.data == "true" else ft.Scale(1.0)  # 悬停放大1.2倍
            ),
            page.update()
        ],
    )
    left_bottom_img = ft.Container( # 左下角图标
        content=ft.Image(
            src=get_resource_path("assets/github.png"),
            rotate=ft.Rotate(angle=0.54, alignment=ft.alignment.center_left),
            width=64, height=64,
            fit=ft.ImageFit.COVER,
            repeat=ft.ImageRepeat.NO_REPEAT,
            opacity=0.94,
        ),
        left=-12,
        bottom=-2,
        
        url="https://github.com/HnBigVolibear",
        url_target="_blank",  # 在新标签页打开
        # 交互增强
        tooltip=ft.Tooltip(message="点击访问作者的个人主页^_^"),
        animate_scale=ft.Animation(duration=300, curve=ft.AnimationCurve.EASE_OUT),  # 缩放动画
        on_hover=lambda e: [
            setattr( e.control, "scale", 
                ft.Scale(1.3) if e.data == "true" else ft.Scale(1.0)  # 悬停放大1.2倍
            ),
            page.update()
        ],
    )
    
    # 整体排版 - 精妙布局结构（关键！）
    page.add(
        ft.Container(
            content=ft.Stack(
                controls=[
                    # 主内容层
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                # 标题
                                top_title, 
                                # 作者
                                ft.Row(controls=[
                                        ft.Icon(name=ft.Icons.FAVORITE, color=ft.Colors.PINK), # 前缀图标
                                        author_title,
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,  # 水平居中
                                ), 
                                ft.Divider(color="transparent", height=4),  # 分割线
                                # 算法模型选择
                                algorithm,
                                # 排版起止时间段选择
                                ft.Container(
                                    content=first_row, 
                                    expand=True,
                                    height=50,
                                    padding=ft.padding.only(top=2,bottom=2, left=12,right=12), #内边距
                                    margin=ft.margin.only(top=8,bottom=8), #外边距
                                    border=ft.border.all(width=1, color="#202020"), #边框
                                    border_radius=4, #圆角
                                    clip_behavior=ft.ClipBehavior.HARD_EDGE, #裁剪行为
                                    opacity=0.98, # 透明度（0-1，越小越透明）
                                    
                                    # 嘿嘿，我自己学着试一试玩一玩渐变色！
                                    gradient=ft.LinearGradient(
                                        begin=ft.alignment.center_left,
                                        end=ft.alignment.center_right,
                                        colors=[
                                            "#ABF8FF",  # 浅蓝色
                                            "#F0F8FF",  # 更接近白色的浅蓝色
                                        ],
                                        tile_mode=ft.GradientTileMode.MIRROR, # 渐变平铺模式
                                        rotation=math.pi / 3,  # 旋转角度
                                    ),
                                ),
                                
                                # 团队成员
                                team_members,
                                # 高级选项
                                condition_card,
                                
                                ft.Divider(color="transparent", height=8), 
                                # 最后的生成按钮
                                ft.Row(
                                    controls=[generate_btn],
                                    alignment=ft.MainAxisAlignment.CENTER,  # 水平居中
                                    vertical_alignment=ft.CrossAxisAlignment.START,  # 垂直贴顶
                                    expand=True,  # 确保行占满可用宽度
                                    height=60,
                                )
                            ],
                            spacing=9,
                            expand=True, # 确保列占满可用宽度
                        ),
                        padding=ft.padding.symmetric(horizontal=22),
                        expand=True   
                    ),
                    # 悬浮图片层
                    right_bottom_img,
                    left_bottom_img,
                ],
                expand=True,
            ),
            expand=True,
        )
    )



logger.info("ft.app -> 开始启动！")
ft.app(
    target=main, 
    view=ft.FLET_APP, 
    assets_dir="assets",
    name=APP_NAME,
)
