__author__ = 'zhangenmin'
__date__ = '2019/2/27 11:11'

from . import api
from flask import jsonify,request,current_app,session
from attendance.models import Users,Student,Leave,Teacher,Banner
from attendance.utils.response_code import RET
from attendance.utils.commons import login_required,limit_role
from attendance import db,redis_store,revoked_store,UserObject
from sqlalchemy.exc import IntegrityError
from attendance import constants
import datetime
import json
from flask_jwt_extended import (create_access_token,get_jwt_claims,jwt_required, get_jwt_identity, get_raw_jwt)
from flask_jwt_extended.tokens import encode_access_token
from flask_jwt_extended.utils import _get_jwt_manager
from flask_jwt_extended.config import config
from  attendance.models import Department_admin
from flask_cors import cross_origin


@api.route('/',methods=['GET'])
def hello():
    return jsonify(status=200,message="智能考勤系统")


@api.route('/user/banner/image',methods=['GET'])
@jwt_required
def banner_images():
    role = get_jwt_claims()['role']
    images = Banner.query.filter(Banner.role == role).all()
    data = []
    for img in images:
        data.append(img.to_basic_dict())
    print(data)
    return jsonify(errno=RET.OK, data=data, errmsg="读取轮播图成功")


@api.route('/media/upload/<string:filename>',methods=['GET'])
@jwt_required
def hello_world(filename):
    username = get_jwt_identity()
    print(username)
    return jsonify(status=200,message="智能考勤系统")


@api.route("/register",methods=["POST"])
def register():
    """
    用户注册
    :return json:
    """
    req_dict = request.get_json()
    username = req_dict.get('username')
    password = req_dict.get('password')
    role = req_dict.get("role")

    # 校验参数
    if not all([username,password,role]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不完整")

    user = Users(username=username, role=role)
    user.password = password
    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError as e:
        # 数据库操作错误后的回滚
        db.session.rollback()
        # 表示账号出现了重复值，即账号已注册过
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAEXIST, errmsg="账号已存在")
    except Exception as e:
        db.session.rollback()
        # 表示手机号出现了重复值，即账号已注册过
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据库异常")

        # 保存登录状态到session中
    session["username"] = username
    session["role"] = role
    session["user_id"] = user.id

    # jwt
    if user.role == 2 or 3 :
        expires = datetime.timedelta(days=365)
        access_token = create_access_token(identity={'username':username,'role':user.role},expires_delta=expires)

    else:
        expires = datetime.timedelta(minutes=30)
        access_token = create_access_token(identity={'username':username,'role':user.role}, expires_delta=expires)
    # 返回结果
    return jsonify(errno=RET.OK, errmsg="添加成功",access_token=access_token)


@api.route("/login",methods=["POST"])
def login():
    req_dict = request.get_json()
    username = req_dict.get('username')
    password = req_dict.get('password')
    role = req_dict.get("role")
    if not all([username,password,role]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不完整")
    user_ip = request.remote_addr
    try:
        access_nums = redis_store.get("access_num_%s" % user_ip)
    except Exception as e:
        current_app.logger.error(e)
    else:
        if access_nums is not None and int(access_nums) >= constants.LOGIN_ERROR_MAX_TIMES:
            return jsonify(errno=RET.REQERR, errmsg="登录错误次数过多，请稍后重试")

    try:
        user = Users.query.filter_by(username=username,role=role).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="获取用户信息失败")

        # 用数据库的密码与用户填写的密码进行对比验证
    if user is None or not user.check_password(password):
        # 如果验证失败，记录错误次数，返回信息
        try:
            # redis的incr可以对字符串类型的数字数据进行加一操作，如果数据一开始不存在，则会初始化为1
            redis_store.incr("access_num_%s" % user_ip)
            redis_store.expire("access_num_%s" % user_ip, constants.LOGIN_ERROR_FORBID_TIME)
        except Exception as e:
            current_app.logger.error(e)

        return jsonify(errno=RET.DATAERR, errmsg="用户名或密码错误")

    # # 如果验证相同成功，保存登录状态， 在session中
    # session["username"] = username
    # session["role"] = user.role
    # session["user_id"] = user.id

    data = UserObject(id=user.id,username=username,role=user.role)
    if user.role == 4 or 2 or 3:
        expires = datetime.timedelta(days=2)
        access_token = create_access_token(identity=data, expires_delta=expires)

    else:
        expires = datetime.timedelta(hours=0.5)
        access_token = create_access_token(identity=data, expires_delta=expires)

    # access_jti = get_jti(encoded_token=access_token)
    # revoked_store.set(access_jti, 'false')
    resp_dict = dict(errno=RET.OK, errmsg="登录成功",data={"access_token":access_token})
    resp_json = json.dumps(resp_dict)
    if user.role == 2:
        data = Teacher.query.filter_by(sno=username).first()
        if data.email is None:
            return jsonify(errno=RET.OK, status=RET.STATUS, errmsg="用户信息未填写", access_token=access_token)
    if user.role == 4:
        # 针对学生端
        data = Student.query.filter_by(sno=username).first()
        if data.face_img is None or data.face_img == '':
            return jsonify(errno=RET.OK, status=RET.STATUS, errmsg="用户信息未填写", access_token=access_token)
        stu_lea = Leave.query.filter_by(student_id=data.id).order_by(-Leave.end_time).first()
        lea_code = 0
        if stu_lea:
            if stu_lea.start_time < datetime.datetime.now() < stu_lea.end_time and stu_lea.status == 1:
                lea_code = 1
            elif stu_lea.status == 2:
                if stu_lea.start_time < datetime.datetime.now() < stu_lea.end_time or stu_lea.start_time > datetime.datetime.now():
                    lea_code = 2

        return jsonify(errno=RET.OK, status=RET.OK, errmsg="登录成功", access_token=access_token, lea_code=lea_code)
    if user.role == 1:
        return resp_json,200, {"Content-Type": "application/json"}
    else:
        return jsonify(errno=RET.OK, status=RET.OK, errmsg="登录成功", access_token=access_token)


@api.route("/session", methods=["GET"])
@jwt_required
def check_login():
    # """检查登陆状态"""
    # # 尝试从session中获取用户的名字
    # username = session.get("username")
    # # 如果session中数据username名字存在，则表示用户已登录，否则未登录
    username = get_jwt_identity()
    data = get_jwt_claims()
    name = Department_admin.query.filter(Department_admin.username==username).first().name
    if username is not None:
        return jsonify(errno=RET.OK, errmsg="获取登录信息成功", data={"username": username,"name":name})
    else:
        return jsonify(errno=RET.SESSIONERR, data={"username":""},errmsg="获取登录信息失败")


@api.route('/session',methods=['DELETE'])
#@login_required
@jwt_required
def logout():
    # csrf_token = session.get('csrf_token')
    # session.clear()
    # session['csrf_token'] = csrf_token
    jti = get_raw_jwt()['jti']
    username = get_jwt_identity()
    jwt_manager = _get_jwt_manager()
    access_token = encode_access_token(identity=jwt_manager._user_identity_callback(username),
            secret='revoked-secret',
            algorithm=config.algorithm,
            expires_delta=None,
            fresh=False,
            user_claims=jwt_manager._user_claims_callback(username),
            csrf=config.csrf_protect,
            identity_claim_key=config.identity_claim_key,
            user_claims_key=config.user_claims_key,
            json_encoder=config.json_encoder)
    # revoked_store.set(jti, 'true')
    return jsonify(errno=RET.OK, access_token=access_token,errmsg="退出登录成功")




