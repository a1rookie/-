# -*- coding:utf-8 -*-
import base64
import urllib
import urllib.request
import urllib.parse

from attendance.models import TokenKey

__author__ = 'zdt'
__date__ = '2019/2/28 15:30'

KEY_NUM = 0


def check(url, params):
    """
    请求百度人脸识别
    :param url:
    :param params:
    :return:
    """
    request = urllib.request.Request(url=url, data=params)
    request.add_header('Content-Type', 'application/json')
    response = urllib.request.urlopen(request)
    content = response.read()

    return content


def img_bs(file_path):
    """
    图片处理
    :param file_path:
    :return:
    """
    try:
        f = open(file_path, 'rb')
    except OSError:
        print("打开照片文件失败")
        return 1
    img = base64.b64encode(f.read())
    f.close()

    return img


def face_m():
    """
    启用多个access_token
    :param KEY_NUM:
    :return:
    """
    global KEY_NUM
    access_token_list = TokenKey.query.all()
    if KEY_NUM == len(access_token_list):
        KEY_NUM = 0
    access_token = access_token_list[KEY_NUM].access_token
    KEY_NUM += 1
    print(access_token)

    return access_token
