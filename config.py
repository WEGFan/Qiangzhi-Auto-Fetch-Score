# -*- coding: utf-8 -*-
from typing import List, Tuple

# 教务系统域名
host: str = 'http://jwgl.xxxx.edu.cn/'
# 用户名
username: str = ''
# 密码
password: str = ''
# 获取间隔的时间区间，单位为分钟
fetch_interval_range: Tuple[int, int] = (5, 10)
# 要显示/推送的列名（与查询成绩页面的表格列名对应），推送时列表的第一项会作为每个成绩的标题显示
display_columns: List[str] = ['课程名称', '总成绩', '学分', '平时成绩', '期中成绩', '实验成绩', '期末成绩']

# 是否启用 Windows 10 桌面推送通知
win10_toast_enable: bool = False
# 是否启用 Server 酱推送
server_chan_enable: bool = False
# Server 酱推送的 SCKEY
server_chan_sckey: str = ''

# 是否启用调试日志输出
debug: bool = False
