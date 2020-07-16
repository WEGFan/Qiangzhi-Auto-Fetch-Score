# -*- coding: utf-8 -*-
import base64
import datetime
import logging
import platform
import random
import sys
import time
import urllib.parse
from typing import Dict, List

import getch
import requests
from pyquery import PyQuery

__version__ = '1.0.0'

logger = logging.getLogger(__name__)

try:
    import config_local as config
except ImportError as outer_err:
    try:
        import config
    except ImportError as outer_err:
        logger.error('无法找到配置文件，请确认当前目录是否存在 config.py')
        sys.exit(1)


def is_windows_10() -> bool:
    """检测当前系统是否为 Windows 10"""
    return platform.system() == 'Windows' and platform.release() == '10'


# 如果是 Windows 10 的话导入桌面推送通知相关的模块
if is_windows_10():
    import win10toast


class Error(Exception):
    def __init__(self, message=''):
        self.message = message

    def __str__(self):
        return self.message


class LoginError(Error):
    """登录错误"""
    pass


class FetchScoreError(Error):
    """获取成绩错误"""
    pass


class PushNotificationError(Error):
    """推送通知错误"""
    pass


class ScoreFetcher(object):
    __slots__ = ('username', 'password', 'score', '_session')

    username: str
    password: str
    score: List[Dict[str, str]]
    _session: requests.Session

    __request_header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/81.0.4044.92 Safari/537.36'
    }

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.score = []
        self._session = requests.session()

    def login(self) -> None:
        """登录"""
        self._session = requests.session()
        try:
            url = urllib.parse.urljoin(config.host, '/jsxsd/xk/LoginToXk')
            response = self._session.post(url, data={
                'encoded': f'{base64.b64encode(self.username.encode()).decode()}%%%'
                           f'{base64.b64encode(self.password.encode()).decode()}'
            }, headers=self.__request_header, timeout=5)
        except requests.Timeout as err:
            raise LoginError('登录超时，请稍后再试')
        except requests.RequestException as err:
            raise LoginError(str(err))

        doc = PyQuery(response.text, parser='html')
        if '学生个人中心' in doc('title').text():
            logger.info('登录成功')
            return
        raise LoginError(doc('.dlmi font[color=red]').text())  # 页面上显示错误的红字

    def check_login(self) -> bool:
        """检查是否登录

        :return: 是否登录
        """
        try:
            url = urllib.parse.urljoin(config.host, '/jsxsd/framework/main.jsp')
            response = self._session.get(url, headers=self.__request_header, timeout=5)
            if '请先登录系统' in response.text:
                return False
            return True
        except Exception as err:
            logger.exception(err)
            return False

    def get_score(self) -> List[Dict[str, str]]:
        """获取分数列表

        :return: 根据页面解析后的分数列表，列表里每个字典对象对应一行，key 对应表格列，value 对应每行的值
        """
        try:
            url = urllib.parse.urljoin(config.host, '/jsxsd/kscj/cjcx_list')
            response = self._session.get(url, headers=self.__request_header, timeout=5)
            logger.debug(response.text)
            return parse_score_list(response.text)
        except requests.Timeout as err:
            raise FetchScoreError('获取成绩超时')
        except requests.RequestException as err:
            raise FetchScoreError(str(err))
        except Exception as err:
            raise err

    def get_score_local(self, file: str) -> List[dict]:
        """从本地文件获取分数列表

        :param file: 文件路径
        :return: 根据页面解析后的分数列表，列表里每个字典对象对应一行，key 对应表格列，value 对应每行的值
        """
        with open(file, 'r', encoding='utf-8') as f:
            return parse_score_list(f.read())


def parse_score_list(html: str) -> List[Dict[str, str]]:
    """将 html 文档的分数表格解析成包含多个字典对象的列表

    :param html: html 文档内容
    :return: 解析后的分数列表，列表里每个字典对象对应一行，key 对应表格列，value 对应每行的值
    """
    doc = PyQuery(html)
    table_rows = doc('#dataList td').parent()  # 选择除标题行外的所有行
    table_column_list = [i.text() for i in doc('#dataList th').items()]  # 表格列
    score_list = []
    if doc('#dataList td:nth-child(1)').text() == '未查询到数据':  # 没有数据时只有一个 td，且内容为“未查询到数据”
        return score_list
    for row in table_rows.items():
        score = dict(zip(
            table_column_list,
            [cell.text() for cell in row.items('td')]  # 当前行每一列的值的列表
        ))
        score.pop('序号', None)  # 如果有序号的话删除，防止因为顺序变动造成成绩被当成是新成绩
        score_list.append(score)
    return score_list


def get_console_message(score_list: List[Dict[str, str]]) -> str:
    """获取要打印到控制台上的内容，格式为： ::

        课程名称：{课程名称1}    {列名1}：{值1}    {列名2}：{值2}
        课程名称：{课程名称2}    {列名1}：{值1}    {列名2}：{值2}
        ...

    :param score_list: 分数列表
    :return: 要打印到控制台上的内容字符串
    """
    message_list = [
        '    '.join(f'{i}：{score[i]}' for i in config.display_columns)
        for score in score_list
    ]
    return '\n'.join(message_list)


def get_server_chan_push_content(score_list: List[Dict[str, str]]) -> str:
    """获取 Server 酱要发送的消息内容，格式为： ::

        #### {课程名称1}
        - **{列名1}：**{值1}
        - **{列名2}：**{值2}

        #### {课程名称2}
        - **{列名1}：**{值1}
        - **{列名2}：**{值2}
        ...

    :param score_list: 分数列表
    :return: 要发送的消息内容字符串
    """
    message_list = [
        f'#### {score[config.display_columns[0]]}\n' +
        '\n'.join(f'- **{i}：**{score[i]}' for i in config.display_columns[1:])
        for score in score_list
    ]
    return '\n\n'.join(message_list)


def push_notification(score_difference_list: List[Dict[str, str]]) -> None:
    """推送通知

    :param score_difference_list: 差异分数列表
    """
    # Windows 10 桌面推送
    if config.win10_toast_enable:
        toast = win10toast.ToastNotifier()
        toast.show_toast(title='出新成绩了', msg='快来看看你有没有挂科吧', duration=5, threaded=True)
    # Server 酱推送
    if config.server_chan_enable:
        detail_message = get_server_chan_push_content(score_difference_list)
        logger.debug(detail_message)
        try:
            response = requests.post(f'https://sc.ftqq.com/{config.server_chan_sckey}.send', data={
                'text': f'有 {len(score_difference_list)} 门课出新成绩了，快看看你挂科了吗',
                'desp': detail_message
            })
            response_json = response.json()
            logger.debug(response_json)
        except Exception as err:
            raise PushNotificationError(f'Server酱推送错误：{err}')
        else:
            if response_json['errno'] != 0:
                raise PushNotificationError(f"Server酱推送错误，服务器返回错误代码：{response_json['errno']}，"
                                            f"错误信息：{response_json['errmsg']}")


def main() -> None:
    logger.info(f'强智教务系统自动查分 v{__version__}', )

    if not is_windows_10():
        config.win10_toast_enable = False
        logger.warning('当前系统不为 Windows 10，系统通知已关闭')

    fetcher = ScoreFetcher(config.username, config.password)

    try:
        (interval_min, interval_max) = config.fetch_interval_range
        if interval_min > interval_max:
            raise ValueError('最小值大于最大值')
        if interval_min <= 0 or interval_max <= 0:
            raise ValueError('间隔分钟数必须为正数')
    except Exception as err:
        logger.error(f'设置获取成绩间隔失败，错误信息：{err}')
        getch.pause('按任意键退出...')
        sys.exit(1)

    first_run = True

    while True:
        interval = random.randint(interval_min * 60, interval_max * 60)
        next_fetch_time = datetime.datetime.now() + datetime.timedelta(seconds=interval)

        try:
            # 如果当前没有登录就先登录
            if not fetcher.check_login():
                fetcher.login()

            # 如果是第一次运行就只获取所有成绩
            if first_run:
                fetcher.score = fetcher.get_score()
                logger.debug(fetcher.score)
                logger.info(f'获取到 {len(fetcher.score)} 个成绩：\n{get_console_message(fetcher.score)}')
                first_run = False
                continue

            new_score_list = fetcher.get_score()
            score_difference = [i for i in new_score_list if i not in fetcher.score]
            if score_difference:
                logger.info(f'获取到 {len(new_score_list)} 个成绩，有 {len(score_difference)} 个新成绩：\n'
                            f'{get_console_message(score_difference)}')
                push_notification(score_difference)
            else:
                logger.info(f'获取到 {len(new_score_list)} 个成绩，没有新成绩')
            fetcher.score = new_score_list
        except LoginError as err:
            logger.exception(f'登录错误：{err}')
        except FetchScoreError as err:
            logger.exception(f'获取成绩错误：{err}')
        except PushNotificationError as err:
            logger.exception(f'推送错误：{err}')
        except Exception as err:
            logger.exception(f'其他错误：{err}')
        finally:
            print()
            logger.info(f"下次获取成绩时间在 {next_fetch_time.strftime('%H:%M:%S')}")
            time.sleep(interval)


if __name__ == '__main__':
    if config.debug:
        log_level = logging.DEBUG
        log_format = '[%(asctime)s] %(levelname)s - %(module)s [%(filename)s (L%(lineno)s)]: %(message)s'
    else:
        log_level = logging.INFO
        log_format = '[%(asctime)s] %(levelname)s: %(message)s'
    logging.basicConfig(level=log_level, format=log_format,
                        handlers=[logging.StreamHandler(), logging.FileHandler('app.log', encoding='utf-8')])

    try:
        main()
    except (EOFError, KeyboardInterrupt) as outer_error:
        sys.exit()
    except Exception as outer_error:
        logger.exception(f'程序运行错误：{outer_error}')
        getch.pause('按任意键退出...')
        sys.exit(1)
