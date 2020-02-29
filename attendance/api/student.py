# -*- coding:utf-8 -*-
import datetime

from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token

from attendance import db, UserObject
from attendance.api import api
from attendance.check_times.check_time import check_time
from attendance.constants import IMAGE_URL
from attendance.face_token.faces import face_login, face_upload
from attendance.models import Student, Users, Department, Leave, Stu_classroom_atten_res, \
    Equipment_info, Instructor, Classes, DormitoryAttendance, Grade, Course
from attendance.utils.class_att_check import class_att_time_check, class_att
from attendance.utils.commons import login_required
from attendance.utils.response_code import RET

__author__ = 'zdt'
__date__ = '2019/3/4 15:20'


@api.route('/student/info', methods=['GET'])
@jwt_required

def personal_information():
    """
    显示个人信息
    :return:
    """
    if request.method == 'GET':
        username = get_jwt_identity()
        # 获得当前登陆用户的对象
        result = Student.query.filter_by(sno=username).first()
        if result:
            data = result.get_stu_data()
            return jsonify(errno=RET.OK, errmsg="用户信息获得成功", data=data)
        else:
            return jsonify(errno=RET.DBERR, errmsg="获取用户信息失败")

    else:
        return jsonify(errno=RET.REQERR, errmsg="非法请求或请求次数受限")


@api.route('/student/repassword', methods=['POST'])
@jwt_required

def change_pwd():
    """
    更新密码
    :return:
    """
    # 通过登陆后的token获得username和role
    username = get_jwt_identity()
    if request.method == 'POST':
        data_json = request.get_json()
        user = Users.query.filter_by(username=username, role=4).first()

        try:
            user = Users.query.get(user.id)
            user.password = data_json['password']
            db.session.add(user)
            db.session.commit()
            return jsonify(errno=RET.OK, errmsg="密码更改成功")
        except Exception as e:
            print(e)
            current_app.logger.error(e)
            db.session.rollback()
            return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")

    else:
        return jsonify(errno=RET.REQERR, errmsg="非法请求或请求次数受限")


@api.route('/student/repassword/face', methods=['POST'])
@jwt_required

def repassword_face():
    """
    修改密码，人脸验证
    :return:
    """
    if request.method == 'POST':
        try:
            import datetime
            starttime = datetime.datetime.now()
            username = get_jwt_identity()
            img = request.files.get('file').read()
            code, student_id = face_login(img, username)

            if code == 0:
                endtime = datetime.datetime.now()
                print((endtime - starttime).seconds)
                return jsonify(errno=RET.OK, errmsg="用户验证成功")
            else:
                return jsonify(errno=RET.ERRFACE, errmsg="验证未通过")

        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="数据错误")
    else:
        return jsonify(errno=RET.REQERR, errmsg="非法请求或请求次数受限")


@api.route('/forget_password', methods=['POST'])
def check_user():
    """
    忘记密码时校验账号是否存在
    :return:
    """
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            img = request.files.get('file').read()
            user = Users.query.filter_by(username=username, role=4).first()
            if not user:
                return jsonify(errno=RET.USERERR, errmsg="用户不存在")
            # 检验人脸是否正确
            code, student_id = face_login(img, username)
            if code == 0:
                data = UserObject(id=user.id, username=username, role=user.role)
                expires = datetime.timedelta(days=0.5)
                access_token = create_access_token(identity=data, expires_delta=expires)

                return jsonify(errno=RET.OK, errmsg="用户验证成功", access_token=access_token)

            else:
                return jsonify(errno=RET.ERRFACE, errmsg="人脸验证未通过")

        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="数据错误")
    else:
        return jsonify(errno=RET.REQERR, errmsg="非法请求或请求次数受限")


@api.route('/student/check/dormitory', methods=['GET'])
@jwt_required

def true_or_false_time_period():
    """
    检查宿舍是否能考勤
    :return:
    """
    if request.method == 'GET':
        try:
            username = get_jwt_identity()
            stu = Student.query.filter_by(sno=username).first()
            classes = Classes.query.get(stu.class_id)
            if classes.whether_attendance == 1:
                s_e_time = Department.query.first()

                start_time = s_e_time.dormitory_start_time
                end_time = s_e_time.dormitory_end_time

                code = check_time(start_time, end_time)

                if code == 1:
                    n_time = datetime.datetime.now().strftime("%Y-%m-%d")
                    dor = DormitoryAttendance.query.filter_by(student_id=stu.id, attendance_date=n_time).first()
                    if dor:
                        if dor.status == 0:
                            return jsonify(errno=RET.OK, errmsg="宿舍可以考勤", dormitory=stu.dormitory_num)
                        elif dor.status == 2:
                            return jsonify(errno=RET.LEAVE, errmsg="请假")
                        else:
                            return jsonify(errno=RET.DATAEXIST, errmsg="已考勤")
                    else:
                        return jsonify(errno=RET.NODATA, errmsg="无考勤数据")
                else:
                    return jsonify(errno=RET.NODATA, errmsg="不再考勤时间段")
            else:
                return jsonify(errno=RET.NOATT, errmsg="该生所在班级不用考勤")
        except Exception as e:
            current_app.logger.error(e)
            db.session.rollback()
            return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
    else:
        return jsonify(errno=RET.REQERR, errmsg="非法请求或请求次数受限")


@api.route('/student/submit/face', methods=['POST'])
@jwt_required

def change_pwd_face():
    """
    宿舍考勤，人脸验证并提交，相当于更改当天录入的原始信息
    :return:
    """
    if request.method == 'POST':
        username = get_jwt_identity()
        img = request.files.get('file').read()
        code, student_id = face_login(img, username)
        print(code)

        if code == 0:
            try:
                stu = Student.query.filter_by(sno=username).first()
                n_time = datetime.datetime.now()
                # 通过学生id以及当天时间查询数据库的信息
                dormitory = DormitoryAttendance.query.filter_by(student_id=stu.id, attendance_date=n_time.strftime("%Y-%m-%d")).first()
                dormitory.time = n_time
                dormitory.status = 1
                db.session.commit()
            except Exception as e:
                current_app.logger.error(e)
                db.session.rollback()
                return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")

            return jsonify(errno=RET.OK)
        else:
            return jsonify(errno=RET.DBERR, errmsg="验证未通过")
    else:
        return jsonify(errno=RET.REQERR, errmsg="非法请求或请求次数受限")


@api.route('/student/dormitory/attendance/record', methods=['GET'])
@jwt_required

def dor_att_record():
    """
    获得宿舍考勤记录
    :return:
    """
    if request.method == 'GET':
        username = get_jwt_identity()
        stu = Student.query.filter_by(sno=username).first()
        dormitory = DormitoryAttendance.query.filter_by(student_id=stu.id).all()

        attendance_success = []
        attendance_failed = []
        attendance_leave = []
        for dor in dormitory:
            d = dor.get_stu_record()
            if dor.status == 1 or dor.status == 3:
                attendance_success.append(d)
            elif dor.status == 0:
                attendance_failed.append(d)
            elif dor.status == 2:
                attendance_leave.append(d)

        total_attendance = len(dormitory)
        # 考勤次数
        yes_attendance = len(attendance_success)
        # 缺勤次数
        no_attendance = len(attendance_failed)
        # 请假次数
        leave_attendance = len(attendance_leave)
        # 考勤率
        try:
            attendance_rate = "%.2f%%" % (yes_attendance / total_attendance * 100)
        except Exception as e:
            attendance_rate = "%.2f%%" % 0

        attendance_data = {
            "yes_attendance": yes_attendance,
            "no_attendance": no_attendance,
            "leave_attendance": leave_attendance,
            "attendance_rate": attendance_rate,
            "attendance_success": attendance_success,
            "attendance_failed": attendance_failed,
            "attendance_leave": attendance_leave
        }
        return jsonify(errno=RET.OK, data=attendance_data)

    else:
        return jsonify(errno=RET.REQERR, errmsg="非法请求或请求次数受限")


@api.route('/student/check/classroom', methods=['GET'])
@jwt_required

def true_or_false_time_class():
    """
    判断教室考勤是否在时间段内
    :return:
    """
    if request.method == 'GET':
        username = get_jwt_identity()
        attendance = class_att_time_check(username)
        sid = Student.query.filter_by(sno=username).first().id
        if len(attendance):
            ok_attendance = []
            stu_class_attendance = [atd.stu_get_data() for atd in attendance]
            for s in stu_class_attendance:
                sc_atten_res = Stu_classroom_atten_res.query.filter_by(
                    student_id=sid, classroom_attendance_id=s.get('id')).order_by(-Stu_classroom_atten_res.time).first().status
                if sc_atten_res == 0:
                    ok_attendance.append(s)
            if len(ok_attendance) == 0:
                return jsonify(errno=RET.NODATA, errmsg="当前开启的考勤已考勤")
            else:
                return jsonify(errno=RET.OK, errmsg="当前时间有多门开启的考勤课程", class_num=len(ok_attendance), data=ok_attendance)
        else:
            return jsonify(errno=RET.NOATT, errmsg="没有开启的考勤")
    else:
        return jsonify(errno=RET.REQERR, errmsg="非法请求或请求次数受限")


@api.route('/student/classes/attendance', methods=['POST'])
@jwt_required

def class_attendance():
    """
    当有多门课程时
    :return:
    """
    if request.method == 'POST':
        img = request.files.get('file').read()
        username = get_jwt_identity()
        # class_att_id是教室考勤开始表中的id
        class_att_id = request.form.get('id')
        code, student_id = face_login(img, username)
        now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if code == 0:
            try:
                s_c_a_r = Stu_classroom_atten_res.query.filter_by(student_id=student_id, classroom_attendance_id=class_att_id).first()
                if s_c_a_r:
                    # 判断考勤记录表中是否存在当前用户本次的记录，若存在则更改为1，即考勤成功
                    s_c_a_r.status = 1
                    s_c_a_r.time = now_time
                    db.session.commit()
                    return jsonify(errno=RET.OK, errmsg="考勤成功")
                else:
                    return jsonify(errno=RET.NODATA, errmsg="无数据")
            except Exception as e:
                current_app.logger.error(e)
                db.session.rollback()
                return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
        else:
            return jsonify(errno=RET.ERRFACE, errmsg="人脸识别失败")
    else:
        return jsonify(errno=RET.REQERR, errmsg="非法请求或请求次数受限")


@api.route('/student/classroom/attendance/record', methods=['GET', 'POST'])
@jwt_required
def class_att_data():
    """
    查询当前用户的各门课程的考勤结果
    :return:
    """
    # course_data为课程信息列表
    course_data = []

    username = get_jwt_identity()
    sid = Student.query.filter_by(sno=username).first()
    attendance_record = Stu_classroom_atten_res.query.filter_by(student_id=sid.id).all()
    if len(attendance_record):
        for a_record in attendance_record:
            course_data.append(a_record.stu_get_course())

        course_dict = []
        for course in course_data:
            # # 判断当前课程是否在列表中已存在
            if course not in course_dict:
                course_dict.append(course)

        if request.method == 'GET':
            # 给前端返回课程信息和课程id
            # 获得列表第一项课程的详细考勤信息
            course_r = course_dict[0]
            attendance_data = class_att(sid, course_r.get('course_id'))
            # run_function = lambda x, y: x if y in x else x + [y]          reduce(run_function, [[], ] + course_dict)
            return jsonify(data=course_dict, errno=RET.OK, attendance_data=attendance_data, course=course_r.get('course_name'))

        elif request.method == 'POST':
            try:
                # get_json()获得课程id
                course_id = request.get_json()['id']
                # 获得当前学生以及该课程下的考勤记录
                # stu_course_record = Stu_classroom_atten_res.query.filter_by(student_id=sid.id, cource_id=course_id).all()
                # # 分离考勤成功、未考勤以及请假记录
                # attendance_success = []
                # attendance_failed = []
                # attendance_leave = []
                # for stu in stu_course_record:
                #     s = stu.stu_get_record()
                #     if stu.status == 1 or stu.status == 3:
                #         attendance_success.append(s)
                #     elif stu.status == 0:
                #         attendance_failed.append(s)
                #     elif stu.status == 2:
                #         attendance_leave.append(s)
                #
                # # attendance_success = [stu.stu_get_record() for stu in stu_course_record if stu.status == 1 or stu.status == 3]
                # # attendance_failed = [stu.stu_get_record() for stu in stu_course_record if stu.status == 0]
                # # attendance_leave = [stu.stu_get_record() for stu in stu_course_record if stu.status == 2]
                #
                # # 获得考勤次数，缺勤次数，请假次数，以及考勤率
                # # 总次数
                # total_attendance = len(stu_course_record)
                # # 考勤次数
                # yes_attendance = len(attendance_success)
                # # 缺勤次数
                # no_attendance = len(attendance_failed)
                # # 请假次数
                # leave_attendance = len(attendance_leave)
                # # 考勤率
                # attendance_rate = "%.2f%%" % (yes_attendance / total_attendance * 100)
                #
                # attendance_data = {
                #     "yes_attendance": yes_attendance,
                #     "no_attendance": no_attendance,
                #     "leave_attendance": leave_attendance,
                #     "attendance_rate": attendance_rate,
                #     "attendance_success": attendance_success,
                #     "attendance_failed": attendance_failed,
                #     "attendance_leave": attendance_leave
                # }
                course_name = Course.query.get(course_id).name
                attendance_data = class_att(sid, course_id)
                return jsonify(attendance_data=attendance_data, errno=RET.OK, data=course_dict, course=course_name)
            except Exception as e:
                current_app.logger.error(e)
                db.session.rollback()
                return jsonify(errno=RET.SERVERERR, errmsg="内部错误")

        else:
            return jsonify(errno=RET.REQERR, errmsg="非法请求或请求次数受限")
    else:
        return jsonify(data='无考勤信息')


@api.route('/student/leave', methods=['POST', 'GET'])
@jwt_required
def stu_leave():
    """
    提交请假
    :return:
    """
    # 先判断GET请求，返回当前登陆人的姓名
    # name 为辅导员名称
    username = get_jwt_identity()
    try:
        stu_data = Student.query.filter_by(sno=username).first()
        if stu_data:
            sid = stu_data.id
            cid = stu_data.class_id
            ins_name = Instructor.query.get(Classes.query.get(cid).instructor_id).name

            if request.method == 'GET':
                # GET请求所需要的数据
                grade_id = stu_data.grade_major_classes()['grade_id']
                day = Department.query.get(Grade.query.get(grade_id).department_id).instructor_permit_leave_time
                n_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                stu_lea = Leave.query.filter_by(student_id=sid, status=2).order_by(-Leave.end_time).first()
                if stu_lea:
                    with db.auto_commit():
                        stu_lea.status = 0
                data = {
                    "name": ins_name,
                    "day": day,
                    "n_time": n_time
                }
                return jsonify(errno=RET.OK, errmsg="身份验证成功", data=data)

            # POST请求，提交请假信息
            if request.method == 'POST':
                try:
                    data = request.get_json()
                    reason = data['reason']
                    start_time = data['start_time']
                    end_time = data['end_time']
                    n_time = datetime.datetime.now()
                    # 生成请假表对象，将前端发送的信息储存
                    with db.auto_commit():
                        lea = Leave()
                        lea.start_time = start_time
                        lea.end_time = end_time
                        lea.reason = reason
                        lea.student_id = sid
                        lea.submit_time = n_time
                        lea.permit_person = ins_name
                        db.session.add(lea)
                except Exception as e:
                    current_app.logger.error(e)
                    return jsonify(errno=RET.DBERR, errmsg="请假信息上传失败")

                return jsonify(errno=RET.OK, errmsg="请假信息上传成功")

        else:
            return jsonify(errno=RET.USERERR, errmsg="获取用户信息失败")

    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="内部错误")


@api.route('/student/leave/record', methods=['GET'])
@jwt_required

def stu_leave_case():
    """
    获得当前学生的请假记录
    :return:
    """
    if request.method == 'GET':
        username = get_jwt_identity()
        try:
            student_id = Student.query.filter_by(sno=username).first().id
            leave_data = Leave.query.filter_by(student_id=student_id)
            wait_leave_data_list = leave_data.filter_by(status=2).all()
            no_leave_data_list = leave_data.filter_by(status=0).all()
            yes_leave_data_list = leave_data.filter_by(status=1).all()

            wait_leave_data = [wait_leave_data.get_leave_stu() for wait_leave_data in wait_leave_data_list]
            no_leave_data = [no_leave_data.get_leave_stu() for no_leave_data in no_leave_data_list]
            yes_leave_data = [yes_leave_data.get_leave_stu() for yes_leave_data in yes_leave_data_list]

            data = {
                "wait_leave_data": wait_leave_data,
                "no_leave_data": no_leave_data,
                "yes_leave_data": yes_leave_data,
            }
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询失败")

        return jsonify(errno=RET.OK, errmsg="请假记录信息获得成功", data=data)
    return jsonify(errno=RET.REQERR, errmsg="非法请求或请求次数受限")


@api.route('/student/completion_stu', methods=['POST', 'GET'])
@jwt_required
def completion_stu():
    """
    更改个人信息
    :return:
    """
    username = get_jwt_identity()
    if request.method == 'POST':
        try:
            stu_data = request.form

            # sex = stu_data.get('sex')
            phone = stu_data.get('phone')
            dormitory_num = stu_data.get('dormitory_num')
            idcard_num = stu_data.get('idcard_num')
            qq = stu_data.get('qq')
            email = stu_data.get('email')
            sex = stu_data.get("sex")

            img = request.files.get('file')

            code = face_upload(img, username)
            if code == 0:
                # 获得当前用户对象，进行信息填充
                stu = Student.query.filter_by(sno=username).first()
                # stu.sex = sex
                stu.phone = phone
                stu.dormitory_num = dormitory_num
                stu.idcard_num = idcard_num
                stu.qq = qq
                stu.email = email
                stu.sex = sex

                db.session.commit()
                return jsonify(errno=RET.OK, errmsg="更改个人信息成功")
            else:
                return jsonify(errno=RET.ERRFACE, errmsg="人脸识别未通过")
        except Exception as e:
            current_app.logger.error(e)
            db.session.rollback()
            return jsonify(errno=RET.DATAERR, errmsg="数据错误")

    elif request.method == 'GET':
        # 进入更改个人信息页面显示基本信息
        student = Student.query.filter_by(sno=username).first().first_get_data()
        # 全部宿舍的列表
        dorm = Equipment_info.query.filter(Equipment_info.classroom == None, Equipment_info.dormitory != None).all()
        dorm = [d.to_stu_base_dict() for d in dorm]
        return jsonify(errno=RET.OK, errmsg="信息获得成功", data=student, dormitory_num=dorm)
    else:
        return jsonify(errno=RET.REQERR, errmsg="非法请求或请求次数受限")


@api.route('/student/instructor/info', methods=['GET'])
@jwt_required
def instructor_info():
    """
    获取当前学生所在班级的辅导员信息
    :return:
    """
    username = get_jwt_identity()
    try:
        stu = Student.query.filter_by(sno=username).first().grade_major_classes()
        instructor = Instructor.query.get(stu['instructor_id']).stu_get_ins()
        return jsonify(errno=RET.OK, data=instructor)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据错误")


@api.route('/user/face/image', methods=['GET'])
@jwt_required
def head_face():
    """
    获得当前用户的头像和用户名
    :return:
    """
    username = get_jwt_identity()
    stu = Student.query.filter_by(sno=username).first()
    image = stu.face_img[10:]
    img_path = IMAGE_URL + image
    print(img_path)

    return jsonify(errno=RET.OK, image=img_path, name=stu.name)


# @api.route('/student/upload/face', methods=['POST'])
# @jwt_required
# 
# def upload_face():
#     """
#     第一次登陆上传头像
#     :return:
#     """
#     if request.method == 'POST':
#         img = request.files.get('file')
#         sno = get_jwt_identity()
#         code = face_upload(img, sno)
#         if code == 0:
#             return jsonify(errno=RET.OK)
#         else:
#             return jsonify(errno=RET.DATAERR, errmsg="人脸识别未通过")
#     else:
#         return jsonify(errno=RET.REQERR, errmsg="非法请求或请求次数受限")


@api.route('/student/about', methods=['GET'])
@jwt_required
def about():
    """
    关于
    :return:
    """
    return jsonify(about="About")
