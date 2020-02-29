__author__ = 'zhangenmin'
__date__ = '2019/2/26 9:59'


from flask import Flask,current_app
from config import config_map
from flask_sqlalchemy import SQLAlchemy as _SQLAlchemy
from flask_session import Session
#from flask_wtf import CSRFProtect
from flask_cors import CORS
from flask import jsonify
import redis
import logging
from logging import Logger
from logging.handlers import RotatingFileHandler
from attendance.utils.commons import ReConverter
from flask_jwt_extended import JWTManager,get_jwt_claims
from datetime import timedelta
from contextlib import contextmanager
from flask_mail import Mail


class SQLAlchemy(_SQLAlchemy):
    """
    结合继承,利用contextmanager创建上下文管理器
    """
    @contextmanager
    def auto_commit(self):
        try:
            yield
            self.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            self.session.rollback()
            raise e

db = SQLAlchemy()
mail = Mail()

redis_store = None

revoked_store = None



class UserObject:
    def __init__(self,id,username, role):
        self.id = id
        self.username = username
        self.role = role
# 配置日志信息
# 设置日志的记录等级
logging.basicConfig(level=logging.INFO)

# 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
file_log_handler = RotatingFileHandler("logs/log",maxBytes=1024*1024*100,backupCount=10,encoding="utf-8")

# 创建日志记录的格式                 日志等级    输入日志信息的文件名 行数    日志信息
formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')

# 为全局的日志工具对象（flask app使用的）添加日记录器
logging.getLogger().addHandler(file_log_handler)


# 工厂模式
def create_app(config_name):
    """
    创建flask的应用对象
    :param config_name: str  配置模式的模式的名字 （"develop",  "product"）
    :return:
    """
    app = Flask(__name__,static_url_path='/api/v1.0/static', static_folder='static')

    # 根据配置模式的名字获取配置参数的类
    config_class = config_map.get(config_name)
    app.config.from_object(config_class)

    # 使用app初始化db
    db.init_app(app)
    mail.init_app(app)

    # 初始化redis工具
    global redis_store
    redis_store = redis.StrictRedis(host=config_class.REDIS_HOST,port=config_class.REDIS_PORT)

    # 利用flask-session，将session数据保存到redis中
    #Session(app)

    # 为flask补充csrf防护
    #CSRFProtect(app)
    CORS(app,supports_credentials=True,resources=r'/api/v1.0/*')

    #设置我们的redis连接以存储列入黑名单的令牌
    # global revoked_store
    # revoked_store = redis.StrictRedis(host=config_class.REDIS_HOST,port=config_class.REDIS_PORT,db=0,password=config_class.REDIS_pwd,
    # decode_responses = True)
    #jwt
    app.config['JWT_SECRET_KEY'] = 'jwt-secret-attendance'
    jwt = JWTManager(app)
    app.config['JWT_BLACKLIST_ENABLED'] = False
    # app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']
    # # 创建我们的函数以检查令牌是否已被列入黑名单。在这简单
    # # 情况下，我们将只存储在Redis的令牌JTI（唯一标识符）
    # # 每当我们创建一个新令牌时（撤销状态为'false'）。这个
    # # function将返回令牌的撤销状态。如果令牌没有
    # # 存在于这个商店，我们不知道它来自哪里（因为我们正在新添加
    # # 创建令牌到我们的商店，撤销状态为'false'）。在这种情况下
    # # 出于安全考虑，我们会考虑撤销令牌。
    # @jwt.token_in_blacklist_loader
    # def check_if_token_in_blacklist(decrypted_token):
    #     jti = decrypted_token['jti']
    #     entry = revoked_store.get(jti)
    #     if entry is None:
    #         return False
    #     return entry == 'true'

    @jwt.user_claims_loader
    def add_claims_to_access_token(user):
        return {'role': user.role,'id':user.id}


    @jwt.user_identity_loader
    def user_identity_lookup(user):
        return user.username

    @jwt.expired_token_loader
    def my_expired_token_callback(expired_token):
        token_type = expired_token['type']
        return jsonify({"errno": "4101","errmsg": '验证登录状态失败,请重新登录',"data":"The {} token has expired".format(token_type)}),200

    app.url_map.converters["re"] = ReConverter

    # 注册蓝图
    from attendance import api
    app.register_blueprint(api.api,url_prefix="/api/v1.0",)

    # 注册提供静态文件的蓝图
    from attendance import web_html
    app.register_blueprint(web_html.html)

    return app

#记录日志信息方法
def log_file(level):
    # 设置日志的记录等级,常见等级有: DEBUG<INFO<WARING<ERROR
    logging.basicConfig(level=level)  # 调试debug级
    # 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)
    # 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
    formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局的日志工具对象（flask app使用的）添加日志记录器
    logging.getLogger().addHandler(file_log_handler)