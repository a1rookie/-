# coding:utf-8

from werkzeug.routing import BaseConverter
from flask import session, jsonify, g
from attendance.utils.response_code import RET
import functools
from functools import wraps
from flask_jwt_extended import get_jwt_claims,get_jwt_identity,verify_jwt_in_request


# 定义正则转换器
class ReConverter(BaseConverter):
    """"""
    def __init__(self, url_map, regex):
        # 调用父类的初始化方法
        super(ReConverter, self).__init__(url_map)
        # 保存正则表达式
        self.regex = regex


def limit_role(roles=list):
    def check_user(func):
        @wraps(func)
        def user_index(*args,**kwargs):
            user_role = get_jwt_claims()['role']
            if user_role in roles:
                return func(*args, **kwargs)
            else:
                # 身份错误
                return jsonify(errno=RET.ROLEERR, errmsg="无权限，拒绝访问!")

        return user_index

    return check_user


def auth_token(view_func):
    @functools.wraps(view_func)
    def wrapper(*args,**kwargs):
        username = get_jwt_claims()
        user_id = get_jwt_claims()['id']
        user_role = get_jwt_claims()['role']

        if user_id is not None:
            g.user_id = user_id
            return view_func(*args, **kwargs)
        else:
            # 如果未登录，返回未登录的信息
            return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    return wrapper


# 定义的验证登录状态的装饰器
def login_required(view_func):
    # wraps函数的作用是将wrapper内层函数的属性设置为被装饰函数view_func的属性
    @functools.wraps(view_func)
    def wrapper(*args, **kwargs):
        # 判断用户的登录状态
        user_id = session.get("user_id")

        # 如果用户是登录的， 执行视图函数
        if user_id is not None:
            # 将user_id保存到g对象中，在视图函数中可以通过g对象获取保存数据
            g.user_id = user_id
            return view_func(*args, **kwargs)
        else:
            # 如果未登录，返回未登录的信息
            return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    return wrapper