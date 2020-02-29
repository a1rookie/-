__author__ = 'zhangenmin'
__date__ = '2019/2/26 13:39'

from flask import Blueprint
from flask_cors import CORS

# 创建蓝图对象
api = Blueprint("api", __name__)

# 导入蓝图的视图
from . import users, admin, teacher
from . import student, get_access_token
from . import instructor
# 导入蓝图的视图