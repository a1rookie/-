# -*- coding:utf-8 -*-
import datetime

__author__ = 'zdt'
__date__ = '2019/3/5 12:12'


def check_time(start_time, end_time):
    # 范围时间
    start_time = datetime.datetime.strptime(str(datetime.datetime.now().date()) + '{}'.format(start_time), '%Y-%m-%d%H:%M:%S')
    end_time = datetime.datetime.strptime(str(datetime.datetime.now().date()) + '{}'.format(end_time), '%Y-%m-%d%H:%M:%S')

    # 当前时间
    n_time = datetime.datetime.now()

    # 判断当前时间是否在范围时间内
    if start_time < n_time < end_time:
        return 1
    else:
        return 0
