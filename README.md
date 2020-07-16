# 强智教务系统自动查分

强智教务系统自动查分，支持 Windows 10 桌面通知和 Server 酱推送  
（只在自己学校的教务系统上测试过，理应通用，如果不行的话欢迎开 issue 反馈）

## 安装

1. 下载源码
   - 直接下载：<https://github.com/WEGFan/Qiangzhi-Auto-Fetch-Score/archive/master.zip>
   - 克隆仓库：`git clone https://github.com/WEGFan/Qiangzhi-Auto-Fetch-Score`
2. 安装 [Python 3.6](https://www.python.org/downloads/) 或以上版本
3. 在源码目录下运行 `pip install -r requirements.txt` 安装依赖

## 使用方法

1. 打开 `config.py`，根据注释配置教务系统网址、帐号密码等设置
2. （可选）注册 [Server 酱](http://sc.ftqq.com/) 并配置 SCKEY 实现微信推送功能
3. 在源码目录下运行 `python auto_fetch_score.py` 开始定时查分
