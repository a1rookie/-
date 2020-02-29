__author__ = 'zhangenmin'
__date__ = '2019/2/26 9:42'

import redis
import logging


class Config(object):
    # 设置启动模式,秘钥
    SECRET_KEY = "school attendance"
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']

    SQLALCHEMY_DATABASE_URI = "mysql://muji:mujiwuliankeji@192.168.1.142:3306/muji"
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True  # 当数据库操作完成,自动提交

    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379
    REDIS_pwd = 123456

    SESSION_TYPE = "redis"
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_pwd)
    SESSION_USE_SIGNER = True
    PERMANENT_SESSION_LIFETIME = 84600

    # 设置默认日志级别
    LEVEL = logging.DEBUG

    # QQ邮箱配置
    MAIL_DEBUG = True  # 开启debug，便于调试看信息
    MAIL_SUPPRESS_SEND = False  # 发送邮件，为True则不发送
    MAIL_SERVER = 'smtp.qq.com'  # 邮箱服务器
    MAIL_PORT = 465  # 端口
    MAIL_USE_SSL = True  # 重要，qq邮箱需要使用SSL
    MAIL_USE_TLS = False  # 不需要使用TLS
    MAIL_USERNAME = '1367983386@qq.com'  # 填邮箱
    MAIL_PASSWORD = 'bbvfdxwdiexkjffd'  # 填授权码
    FLASK_MAIL_SENDER = '皮皮虾！我们走！<1367983386@qq.com>'  # 邮件发送方
    FLASK_MAIL_SUBJECT_PREFIX = '[皮皮虾！我们走]'  # 邮件标题
    # MAIL_DEFAULT_SENDER = 'xxx@qq.com'  # 填邮箱，默认发送者


    # 人脸识别TOKEN
    # ACCESS_TOKEN_LIST = ['24.4a66ed0825206a9ce86f4645ed3c25bb.2592000.1553783388.282335-10877765']
    FACE_URL = "https://aip.baidubce.com/rest/2.0/face/v3/"

    IP = "192.168.1.107"
    PORT = "5000"


class DevelopmentConfig(Config):
    DEBUG = True
    JSON_AS_ASCII = False
    LEVEL = logging.ERROR


class ProductionConfig(Config):
    # 生产环境配置信息(线上)
    DEBUG = False
    LEVEL = logging.ERROR


# 测试环境配置信息
class TestingConfig(Config):
    TESTING = True


config_map = {
    "develop": DevelopmentConfig,
    "product": ProductionConfig,
    "testing": TestingConfig,
}
