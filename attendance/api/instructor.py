from sqlalchemy import or_, and_

from attendance.face_token.faces import face_upload

__author__ = 'zhangenmin'
__date__ = '2019/3/1 12:06'

from attendance import db
from flask import jsonify, request, current_app, Session, make_response, send_file
from attendance.utils.commons import login_required, auth_token, limit_role
from attendance.utils.response_code import RET
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt_claims
from . import api
from datetime import datetime, date, timedelta
from io import BytesIO
from attendance import constants
from attendance.models import Users, Student, Teacher, Instructor, Department_admin, Grade, Major, course_class_relation, Course \
    , Classes, grade_major_relation, School_roll_type, Leave, DormitoryAttendance, Stu_classroom_atten_res, Classroom_attendance, \
    Equipment_info, Department
import json


@api.route("/instructor/banner", methods=["GET"])
def banner_image():
    pass


# 获取当前辅导员所带的班级
@api.route("/instructor/classes", methods=["GET"])
@jwt_required
@limit_role(roles=[1, 3])
def instructor_class():
    """
    获取当前登录的辅导员所带的班级返回班级和班级id
    ：：在用
    :return:
    """
    try:
        username = get_jwt_identity()
        ins_class = Instructor.query.filter(Instructor.sno == username).first().get_ins_class()

        return jsonify(errno=RET.OK, errmsg="OK", ins_class=ins_class)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据错误")


# 获取当前辅导员所带的学生的所有信息
@api.route("/instructor/students", methods=["GET"])
@jwt_required
@limit_role(roles=[1, 3])
def instructor_student_list():
    """
    获取当前登录的辅导员所带的学生的所有信息
    ：：在用
    :return:
    """
    if request.method == "GET":
        keywords = request.args.get("keywords", "")
        class_id = request.args.get("class_id", "")
        page = request.args.get("page")

        try:
            page = int(page)
        except Exception as e:
            current_app.logger.error(e)
            page = 1

        try:
            username = get_jwt_identity()
            instructor_id = Instructor.query.filter(Instructor.sno == username).first().id

            # 过滤条件的参数列表容器
            # if keywords:
            #     stu = Student.query.filter(or_(Student.sno.like("%" + keywords + "%"), Student.name.like("%" + keywords + "%"))).all()
            # else:
            #     stu = Student.query.all()
            # sid = [s.id for s in stu]
            if class_id:
                filter_params = [and_(Student.class_id == class_id, Classes.instructor_id == instructor_id,
                                      or_(Student.sno.like("%" + keywords + "%"),
                                          Student.name.like("%" + keywords + "%")))]
            else:
                filter_params = [and_(Classes.instructor_id == instructor_id,
                                      or_(Student.sno.like("%" + keywords + "%"),
                                          Student.name.like("%" + keywords + "%")))]

            stu_data = Student.query.order_by(Student.sno.desc()).join(
                Classes, Student.class_id == Classes.id).filter(*filter_params)
            # 分页操作
            count = int(stu_data.count() / 10) + 1
            stu_data = stu_data.paginate(page=page, per_page=10, error_out=False).items
            stu_data = [s.get_ins_detail_stu() for s in stu_data]

            if stu_data:
                return jsonify(errno=RET.OK, errmsg="查询成功", data=stu_data, count=count)
            else:
                return jsonify(errno=RET.NODATA, errmsg="无数据")
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="数据错误")
    else:
        return jsonify(errno=RET.REQERR, errmsg="非法请求")


# 得到辅导员管理的某个学生的详细信息和修改此学生的信息
@api.route("/instructor/students/detail/<int:student_id>", methods=["GET", "POST"])
@jwt_required
@limit_role(roles=[1, 3])
def get_student_detail(student_id):
    """
    得到辅导员管理的某个学生的详细信息和修改此学生的信息
    ：：在用
    :param student_id:
    :return:
    """
    if request.method == "GET":
        try:
            student = Student.query.get(student_id).get_ins_stu()
            return jsonify(errno=RET.OK, errmsg="OK", data=student)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="数据异常")
    if request.method == "POST":
        data = request.get_json()
        name = data.get("name")
        sex = data.get("sex")
        # idcard_num = data.get("idcard_num", "")
        dormitory_num = data.get("dorRoom", "")
        phone = data.get("phone", "")
        qq = data.get("qq", "")
        email = data.get("email", "")
        roll_status = data.get("status", "")
        # classes = data.get("class", "")
        try:
            student = Student.query.filter(Student.id == student_id).first()
            try:
                student.name = name
                # student.idcard_num = idcard_num
                student.dormitory_num = dormitory_num
                student.phone = phone
                student.sex = sex
                student.qq = qq
                student.email = email
                student.school_roll_status_id = roll_status
                # db.session.add(student)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                # 表示帐号出现了重复值，即账号已注册过
                current_app.logger.error(e)
                return jsonify(errno=RET.DBERR, errmsg="修改数据失败")
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.NODATA, errmsg="未查到数据")
        return jsonify(errno=RET.OK, errmsg="OK", data="修改学生成功")
    else:
        return jsonify(errno=RET.REQERR, errmsg="非法请求")


# 辅导员修改学生信息时所要的宿舍号、学籍状态
@api.route("/instructor/stu/dor/cls", methods=["GET"])
@jwt_required
@limit_role(roles=[1, 3])
def get_dor_cls():
    """
    辅导员修改学生信息时所要的宿舍号、学籍状态
    ：：在用
    :return:
    """
    try:
        dor = Equipment_info.query.all()
        cls = Classes.query.all()
        school_roll_status = School_roll_type.query.all()

        dor_name = [d.to_stu_base_dict() for d in dor if d.dormitory]
        cls_name = [c.ins_get_data() for c in cls]
        roll_status = [s.to_dict() for s in school_roll_status]

        data = {
            "dor_name": dor_name,
            "roll_status": roll_status
        }

        return jsonify(errno=0, data=data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据异常")


# 删除学生信息
@api.route("/instructor/del/stu", methods=["POST"])
@jwt_required
@limit_role(roles=[1, 3])
def del_stu():
    """
    删除学生信息
    ：：在用
    :return:
    """
    if request.method == 'POST':
        sid = request.json.get("id", "")
        if sid:
            try:
                stu = Student.query.get(sid)
                db.session.delete(stu)
                db.session.commit()

                return jsonify(errno=RET.OK, errmsg="删除信息成功")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(e)
                return jsonify(errno=RET.DBERR, errmsg="删除数据失败")
        else:
            return jsonify(errno=RET.NODATA, errmsg="没有收到信息")
    else:
        return jsonify(errno=RET.REQERR, errmsg="非法请求")


# 辅导员更改学生图片
@api.route("/instructor/students/face/<int:student_id>", methods=["POST"])
@jwt_required
@limit_role(roles=[1, 3])
def get_student_face(student_id):
    """
    辅导员更改学生图片
    ：：在用
    :param student_id:
    :return:
    """
    if request.method == 'POST':
        try:
            img = request.files.get('file')
            stu = Student.query.get(student_id)
            code = face_upload(img, stu.sno)
            if code == 0:
                return jsonify(errno=RET.OK, errmsg="更改成功")
            else:
                return jsonify(errno=RET.ERRFACE, errmsg="人脸验证未通过")
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="数据异常")
    else:
        return jsonify(errno=RET.REQERR, errmsg="非法请求")


# 请假信息
@api.route("/instructor/students/leave/<int:student_id>", methods=["GET", "POST"])
@jwt_required
@limit_role(roles=[1, 3])
def instructor_student_leave(student_id):
    """
    请假信息
    ：：在用
    :param student_id:
    :return:
    """
    if request.method == "GET":
        try:
            leave = Leave.query.filter(Leave.student_id == student_id).order_by(-Leave.id).first()
            leave_info = leave.to_full_dict()
            return jsonify(errno=RET.OK, errmsg="OK", data=leave_info)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DATAERR, errmsg="数据错误")

    if request.method == "POST":
        try:
            data = request.get_json()
            start_time = data.get("start_time")
            end_time = data.get("end_time")
            reason = data.get("reason")
            stu_id = data.get("stu_id")
            if not all([start_time, end_time, reason, stu_id]):
                return jsonify(errno=RET.PARAMERR, errmsg="参数不完整")
            leave = Leave.query.filter(Leave.student_id == student_id).order_by(Leave.start_time).first()
            leave.start_time = start_time
            leave.end_time = start_time
            leave.reason = reason
            leave.student_id = stu_id
            db.session.add(leave)
            db.session.commit()
            return json.dumps(dict(errno=RET.OK, errmsg="OK", data="修改请假记录成功")), 200, {"Content-Type": "application/json"}
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(e)
            return jsonify(errno=RET.DATAERR, errmsg="数据错误")


# 辅导员给学生请假
@api.route("/instructor/students/leave", methods=["POST", "GET"])
@jwt_required
@limit_role(roles=[1, 3])
def instructor_add_leave():
    """
    辅导员给学生请假
    ：：在用
    :return:
    """
    if request.method == "POST":
        try:
            data = request.get_json()
            start_time = data.get("start_time")
            end_time = data.get("end_time")
            reason = data.get("reason")
            stu_id = data.get("stu_id")
            username = get_jwt_identity()
            name = Instructor.query.filter_by(sno=username).first().name
            if not all([start_time, end_time, reason, stu_id]):
                return jsonify(errno=RET.PARAMERR, errmsg="参数不完整")
            leave = Leave(start_time=start_time, end_time=end_time, reason=reason, student_id=stu_id, permit_person=name, status=1,
                          submit_time=datetime.now())
            db.session.add(leave)
            db.session.commit()
            return jsonify(errno=RET.OK, errmsg="ok")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(e)
            return jsonify(errno=RET.DATAERR, errmsg="数据错误")
    else:
        try:
            sid = request.args.get("sid")
            stu_data = Student.query.get(sid)
            grade_id = stu_data.grade_major_classes()['grade_id']
            day = Department.query.get(Grade.query.get(grade_id).department_id).instructor_permit_leave_time

            return jsonify(errno=RET.OK, errmsg="ok", day=day)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DATAERR, errmsg="数据错误")


# 待处理的请假记录
@api.route("/instructor/students/wait_record", methods=['GET'])
@jwt_required
@limit_role(roles=[1, 3])
def wart_leave_record():
    """
    待处理的请假记录
    ：：在用
    :return:
    """
    try:
        username = get_jwt_identity()
        instructor_id = Instructor.query.filter(Instructor.sno == username).first().id

        stu = Leave.query.join(Student, Student.id == Leave.student_id).join(
            Classes, Student.class_id == Classes.id).join(
            Instructor, Instructor.id == instructor_id).filter(Leave.status == 2).all()

        # stu_leave = [s.get_leave_ins() for s in stu]
        now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stu_leave = []
        for s in stu:
            end_time = s.end_time.strftime("%Y-%m-%d %H:%M:%S")
            lid = s.id
            if end_time < now_time:
                try:
                    lea = Leave.query.get(lid)
                    lea.status = 0
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(e)
                    return jsonify(errno=RET.DATAERR, errmsg="数据错误")
            else:
                stu_leave.append(s.get_leave_ins())

        return jsonify(errno=RET.OK, errmsg="获得数据", date=stu_leave)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据错误")


# 修改请假状态
@api.route("/instructor/students/wait_record/<int:leave_id>", methods=['POST'])
@jwt_required
@limit_role(roles=[1, 3])
def wait_leave_mange(leave_id):
    """
    修改请假状态
    ：：在用
    :param leave_id:
    :return:
    """
    if request.method == "POST":
        try:
            data = request.get_json()
            status = data.get("status", 2)
            leave = Leave.query.get(leave_id)
            leave.status = status
            db.session.add(leave)
            db.session.commit()
            return jsonify(errno=RET.OK, errmsg="OK", data="修改请假状态成功")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(e)
            return jsonify(errno=RET.DATAERR, errmsg="数据错误")
    else:
        return jsonify(errno=RET.REQERR, errmsg="非法请求")


# 已批准的请假记录
@api.route("/instructor/students/yes_reacord", methods=['GET'])
@jwt_required
@limit_role(roles=[1, 3])
def yes_leave_record():
    """
    已批准的请假记录
    ：：在用
    :return:
    """
    try:
        page = request.args.get("page")

        try:
            page = int(page)
        except Exception as e:
            current_app.logger.error(e)
            page = 1

        username = get_jwt_identity()
        instructor_id = Instructor.query.filter(Instructor.sno == username).first().id

        stu = Leave.query.order_by(-Leave.end_time).join(Student, Student.id == Leave.student_id).join(Classes, Student.class_id == Classes.id) \
            .join(Instructor, Instructor.id == instructor_id).filter(Leave.status == 1)
        # 分页操作
        count = int(stu.count() / 10) + 1
        stu = stu.paginate(page=page, per_page=10, error_out=False).items

        stu_leave = [s.get_leave_ins() for s in stu]

        return jsonify(errno=RET.OK, errmsg="获得数据", date=stu_leave, count=count)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据异常")


# 未批准的请假记录
@api.route("/instructor/students/no_reacord", methods=['GET'])
@jwt_required
@limit_role(roles=[1, 3])
def no_leave_record():
    """
    未批准的请假记录
    ：：在用
    :return:
    """
    try:
        page = request.args.get("page")

        try:
            page = int(page)
        except Exception as e:
            current_app.logger.error(e)
            page = 1

        username = get_jwt_identity()
        instructor_id = Instructor.query.filter(Instructor.sno == username).first().id

        stu = Leave.query.order_by(-Leave.submit_time).join(Student, Student.id == Leave.student_id).join(
            Classes, Student.class_id == Classes.id).join(
            Instructor, Instructor.id == instructor_id).filter(Leave.status == 0)
        # 分页操作
        count = int(stu.count() / 10) + 1
        stu = stu.paginate(page=page, per_page=10, error_out=False).items

        stu_leave = [s.get_leave_ins() for s in stu]

        return jsonify(errno=RET.OK, errmsg="获得数据", date=stu_leave, count=count)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据异常")


# 当天的考勤人数缺勤人数，请假人数，考勤率
@api.route('/instructor/today/rate/attendance', methods=["GET"])
@jwt_required
@limit_role(roles=[1, 3])
def today_attendance_rate():
    """
    当天的考勤人数缺勤人数，请假人数，考勤率
    ：：在用，待修改！！--------------------
    :return:
    """
    try:
        username = get_jwt_identity()
        instructor_id = Instructor.query.filter(Instructor.sno == username).first().id

        # unattendance_count = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
        #     .filter(DormitoryAttendance.attendance_date == now, DormitoryAttendance.status == 0) \
        #     .join(Classes, Student.class_id == Classes.id).filter(Classes.instructor_id == instructor_id).count()
        # print(unattendance_count)
        now = date.today()
        dor_att = DormitoryAttendance.query.order_by(-DormitoryAttendance.attendance_date).first().attendance_date

        if now.strftime("%Y-%m-%d") > dor_att.strftime("%Y-%m-%d"):
            now = now + timedelta(days=-1)

        unattendance_count = DormitoryAttendance.query.filter_by(instructor_id=instructor_id, status=0, attendance_date=now).count()
        attendance_count = DormitoryAttendance.query.filter_by(instructor_id=instructor_id, status=1, attendance_date=now).count()
        ins_atten_count = DormitoryAttendance.query.filter_by(instructor_id=instructor_id, status=3, attendance_date=now).count()
        leave_count = DormitoryAttendance.query.filter_by(instructor_id=instructor_id, status=2, attendance_date=now).count()
        attendance_all = attendance_count + ins_atten_count
        # attendance_count = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
        #     .filter(DormitoryAttendance.attendance_date == now, DormitoryAttendance.status == 1) \
        #     .join(Classes, Student.class_id == Classes.id).filter(Classes.instructor_id == instructor_id).count()

        # leave_count = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
        #     .filter(DormitoryAttendance.attendance_date == now, DormitoryAttendance.status == 2) \
        #     .join(Classes, Student.class_id == Classes.id).filter(Classes.instructor_id == instructor_id).count()
        try:
            attendance_rate = "%.2f%%" % (attendance_all / (leave_count + attendance_all + unattendance_count) * 100)
        except Exception as e:
            attendance_rate = 0

        data = {
            "attendance_rate": attendance_rate,
            "attendance_count": attendance_all,
            "leave": leave_count,
            "unattendance_count": unattendance_count
        }
        return jsonify(errno=RET.OK, errmsg="OK", data=data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据异常")


@api.route('/instructor/today/no/attendance', methods=["GET"])
@jwt_required
@limit_role(roles=[1, 3])
def instructor_no_attendance():
    keywords = request.args.get("keywords", "")
    classes = request.args.get("classes", "")
    now = date.today()
    username = get_jwt_identity()
    instructor_id = Instructor.query.filter(Instructor.sno == username).first().id
    if classes:
        filter_params = [Student.sno.like("%" + keywords + "%"), Student.name.like("%" + keywords + "%"),
                         Student.class_id == classes]
    else:
        filter_params = [Student.sno.like("%" + keywords + "%"), Student.name.like("%" + keywords + "%")]

    dormitory_attendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
        .filter(DormitoryAttendance.attendance_date == now, DormitoryAttendance.status == 0) \
        .join(Classes, Student.class_id == Classes.id).filter(Classes.instructor_id == instructor_id).filter(*filter_params)

    data_list = []
    for da in dormitory_attendance:
        data_list.append(da.to_dict())

    unattendance_count = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
        .filter(DormitoryAttendance.attendance_date == now, DormitoryAttendance.status == 0) \
        .join(Classes, Student.class_id == Classes.id).filter(Classes.instructor_id == instructor_id).count()

    attendance_count = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
        .filter(DormitoryAttendance.attendance_date == now, DormitoryAttendance.status == 1) \
        .join(Classes, Student.class_id == Classes.id).filter(Classes.instructor_id == instructor_id).count()

    leave_count = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
        .filter(DormitoryAttendance.attendance_date == now, DormitoryAttendance.status == 2) \
        .join(Classes, Student.class_id == Classes.id).filter(Classes.instructor_id == instructor_id).count()

    try:
        attendance_rate = "%.4f" % (attendance_count / (leave_count + attendance_count + unattendance_count))
    except Exception as e:
        attendance_rate = 0

    # instructor_id = Instructor.query.filter(Instructor.sno == username).first().id

    resp_dict = dict(errno=RET.OK, errmsg="OK",
                     data={"attendance_rate": attendance_rate, "attendance_count": attendance_count, "leave": leave_count,
                           "unattendance_count": unattendance_count, "dormitory_attendance": data_list})
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}


@api.route('/instructor/today/yes/attendance', methods=["GET"])
@jwt_required
@limit_role(roles=[1, 3])
def instructor_yes_attendance():
    """
    当天宿舍考勤信息
    附带参数时姓名学号查询班级?kewords=test&classes=1  班级为班级id
    :return:
    """
    keywords = request.args.get("keywords", "")
    classes = request.args.get("classes", "")
    now = date.today()
    # 过滤条件的参数列表容器
    if classes:
        filter_params = [Student.sno.like("%" + keywords + "%"), Student.name.like("%" + keywords + "%"),
                         Student.class_id == classes]
    else:
        filter_params = [Student.sno.like("%" + keywords + "%"), Student.name.like("%" + keywords + "%")]
    username = get_jwt_identity()
    instructor_id = Instructor.query.filter(Instructor.sno == username).first().id
    dormitory_attendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
        .filter(DormitoryAttendance.attendance_date == now, DormitoryAttendance.status == 1) \
        .join(Classes, Student.class_id == Classes.id).filter(Classes.instructor_id == instructor_id).filter(*filter_params)
    data_list = []
    for da in dormitory_attendance:
        data_list.append(da.to_dict())
    resp_dict = dict(errno=RET.OK, errmsg="OK", data={"dormitory_attendance": data_list})
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}


@api.route('/instructor/today/leave/attendance', methods=["GET"])
@jwt_required
@limit_role(roles=[1, 3])
def instructor_leave_attendance():
    """
    当天考勤请假记录
    :return:
    """
    keywords = request.args.get("keywords", "")
    classes = request.args.get("classes", "")
    now = date.today()
    # 过滤条件的参数列表容器
    if classes:
        filter_params = [Student.sno.like("%" + keywords + "%"), Student.name.like("%" + keywords + "%"),
                         Student.class_id == classes]
    else:
        filter_params = [Student.sno.like("%" + keywords + "%"), Student.name.like("%" + keywords + "%")]
    username = get_jwt_identity()
    instructor_id = Instructor.query.filter(Instructor.sno == username).first().id
    dormitory_attendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
        .filter(DormitoryAttendance.attendance_date == now, DormitoryAttendance.status == 2) \
        .join(Classes, Student.class_id == Classes.id).filter(Classes.instructor_id == instructor_id).filter(
        *filter_params)
    data_list = []
    for da in dormitory_attendance:
        data_list.append(da.to_dict())
    resp_dict = dict(errno=RET.OK, errmsg="OK", data={"dormitory_attendance": data_list})
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}


# 当天学生考勤结果查看
@api.route('/instructor/today/attendance', methods=["GET"])
@jwt_required
@limit_role(roles=[1, 3])
def instructor_attendance_today():
    """
    当天学生考勤结果查看
    keywords：学号或者姓名搜索
    classes：班级搜索
    ：：在用
    :return:
    """
    if request.method == "GET":
        try:
            keywords = request.args.get("keywords", "")
            classes = request.args.get("classes", "")
            username = get_jwt_identity()

            now = datetime.now()
            dep = Department.query.get(1)
            start_time = dep.dormitory_start_time
            end_time = dep.dormitory_end_time
            manage_time = dep.instructor_manage_time
            dor_att = DormitoryAttendance.query.order_by(-DormitoryAttendance.attendance_date).first().attendance_date
            sd = "{} {}".format(dor_att.strftime("%Y-%m-%d"), start_time.strftime("%H:%M:%S"))
            ed = "{} {}".format(dor_att.strftime("%Y-%m-%d"), end_time.strftime("%H:%M:%S"))
            ed = datetime.strptime(ed, "%Y-%m-%d %H:%M:%S") + timedelta(hours=manage_time)

            if (sd < now.strftime("%Y-%m-%d %H:%M:%S") < ed.strftime("%Y-%m-%d %H:%M:%S")) is False:
                return jsonify(errno=RET.NODATA, errmsg="无数据", data={})
            if now.strftime("%Y-%m-%d") > dor_att.strftime("%Y-%m-%d"):
                now = (now + timedelta(days=-1)).strftime("%Y-%m-%d")
            else:
                now = now.strftime("%Y-%m-%d")
            now = datetime.strptime(now, "%Y-%m-%d")
            instructor_id = Instructor.query.filter(Instructor.sno == username).first().id

            classes_list = Classes.query.filter_by(instructor_id=instructor_id).all()
            class_name = [cls.ins_get_data() for cls in classes_list]

            # 过滤条件的参数列表容器
            stu = Student.query.filter(or_(Student.sno.like("%" + keywords + "%"), Student.name.like("%" + keywords + "%"))).all()
            sid = [s.id for s in stu]
            if classes:
                filter_params = [DormitoryAttendance.student_id.in_(sid), DormitoryAttendance.class_id == classes,
                                 DormitoryAttendance.instructor_id == instructor_id, DormitoryAttendance.attendance_date == now]
            else:
                filter_params = [DormitoryAttendance.student_id.in_(sid), DormitoryAttendance.instructor_id == instructor_id,
                                 DormitoryAttendance.attendance_date == now]
            dormitory_attendance = DormitoryAttendance.query.filter(*filter_params).all()
            no_attendance = []
            yes_attendance = []
            leave_attendance = []
            no_count = 0
            yes_count = 0
            leave_count = 0
            all_count = len(dormitory_attendance)
            for dor in dormitory_attendance:
                status = dor.status
                data = dor.ins_get_record()
                if status == 1 or status == 3:
                    yes_attendance.append(data)
                    yes_count += 1
                elif status == 0:
                    no_attendance.append(data)
                    no_count += 1
                elif status == 2:
                    leave_attendance.append(data)
                    leave_count += 1
                else:
                    continue

            try:
                attendance_rate = "%.2f%%" % (yes_count / all_count * 100)
            except Exception as e:
                attendance_rate = 0

            data = {
                "no_attendance": no_attendance,
                "yes_attendance": yes_attendance,
                "leave_attendance": leave_attendance,
                "class_name": class_name,
                "attendance_rate": attendance_rate,
                "attendance_count": yes_count,
                "leave": leave_count,
                "unattendance_count": no_count
            }

            return jsonify(data=data, errno=RET.OK, errmsg="OK")
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="数据异常")
    else:
        return jsonify(errno=RET.REQERR, errmsg="非法请求")


# 修改当前缺勤状态
@api.route('/instructor/today/modify/attendance', methods=["POST"])
@jwt_required
@limit_role(roles=[1, 3])
def instructor_modify_attendance():
    """
    修改当前缺勤状态
    ：：在用
    :return:
    """
    if request.method == 'POST':
        try:
            data = request.get_json()
            status = data.get('status')
            did = data.get('id')
            dormitory_attendance = DormitoryAttendance.query.get(did)
            dormitory_attendance.status = status
            db.session.add(dormitory_attendance)
            db.session.commit()
            return json.dumps(dict(errno=RET.OK, errmsg="OK", data="修改成功")), 200, {"Content-Type": "application/json"}
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
    else:
        return jsonify(errno=RET.REQERR, errmsg="非法请求")


# 当前辅导员所管班级的考勤记录
@api.route('/instructor/dormitory/attendance/classes', methods=["GET"])
@jwt_required
@limit_role(roles=[1, 3])
def instructor_dormitory_classes_attendance():
    """
    当前辅导员所管班级的考勤记录
    ：：在用
    :return:
    """
    day = request.args.get("day", "1")
    class_name = request.args.get("class_name", "")

    try:
        username = get_jwt_identity()
        instructor_id = Instructor.query.filter(Instructor.sno == username).first().id

        now = date.today()
        try:
            dor_att = DormitoryAttendance.query.order_by(-DormitoryAttendance.attendance_date).first().attendance_date
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.NODATA)

        if now.strftime("%Y-%m-%d") > dor_att.strftime("%Y-%m-%d"):
            now = dor_att.strftime("%Y-%m-%d") + " " + now.strftime("%H:%M:%S")
            now = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        day = int(day)
        if day == 7:
            filter_params = [(now - timedelta(days=7)) <= DormitoryAttendance.attendance_date,
                             DormitoryAttendance.attendance_date <= now]
        elif day == 30:
            filter_params = [(now - timedelta(days=30)) <= DormitoryAttendance.attendance_date,
                             DormitoryAttendance.attendance_date <= now]
        elif day == 180:
            filter_params = [DormitoryAttendance.attendance_date <= now]
        else:
            filter_params = [DormitoryAttendance.attendance_date == now]

        if class_name:
            classes = Classes.query.filter(Classes.instructor_id == instructor_id, Classes.class_name.like("%" + class_name + "%")).all()
        else:
            classes = Classes.query.filter(Classes.instructor_id == instructor_id).all()
        if len(classes) == 0:
            return jsonify(errno=RET.NODATA, errmsg="无数据")
        data = []
        yes_count = 0
        no_count = 0
        l_count = 0

        for cls in classes:
            unattendance_count = DormitoryAttendance.query.filter(
                DormitoryAttendance.status == 0,
                DormitoryAttendance.class_id == cls.id,
                DormitoryAttendance.instructor_id == instructor_id).filter(*filter_params).count()

            att_count = DormitoryAttendance.query.filter(
                DormitoryAttendance.status == 1,
                DormitoryAttendance.class_id == cls.id,
                DormitoryAttendance.instructor_id == instructor_id).filter(*filter_params).count()

            attendance_count_ins = DormitoryAttendance.query.filter(
                DormitoryAttendance.status == 3,
                DormitoryAttendance.class_id == cls.id,
                DormitoryAttendance.instructor_id == instructor_id).filter(*filter_params).count()

            leave_count = DormitoryAttendance.query.filter(
                DormitoryAttendance.status == 2,
                DormitoryAttendance.class_id == cls.id,
                DormitoryAttendance.instructor_id == instructor_id).filter(*filter_params).count()
            # unattendance_count = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            #     .filter(DormitoryAttendance.attendance_date == now, DormitoryAttendance.status == 0) \
            #     .join(Classes, Student.class_id == Classes.id).filter(Classes.instructor_id == instructor_id, Classes.id == cls.id).count()
            #
            # attendance_count = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            #     .filter(DormitoryAttendance.attendance_date == now, DormitoryAttendance.status == 1, Classes.id == cls.id) \
            #     .join(Classes, Student.class_id == Classes.id).filter(Classes.instructor_id == instructor_id).count()
            #
            # leave_count = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            #     .filter(DormitoryAttendance.attendance_date == now, DormitoryAttendance.status == 2, Classes.id == cls.id) \
            #     .join(Classes, Student.class_id == Classes.id).filter(Classes.instructor_id == instructor_id).count()
            attendance_count = att_count + attendance_count_ins

            no_count += unattendance_count
            yes_count += attendance_count
            l_count += leave_count

            try:
                attendance_rate = "%.2f%%" % (attendance_count / (leave_count + attendance_count + unattendance_count) * 100)
            except Exception as e:
                current_app.logger.error(e)
                attendance_rate = "0.00%"

            try:
                leave_rate = "%.2f%%" % (leave_count / (leave_count + attendance_count + unattendance_count) * 100)
            except Exception as e:
                current_app.logger.error(e)
                leave_rate = "0.00%"

            try:
                unattendance_rate = "%.2f%%" % (unattendance_count / (leave_count + attendance_count + unattendance_count) * 100)
            except Exception as e:
                current_app.logger.error(e)
                unattendance_rate = "0.00%"

            grade = Grade.query.join(grade_major_relation, Grade.id == grade_major_relation.c.grade_id).join(
                Classes, grade_major_relation.c.id == Classes.grade_major_id).filter(
                Classes.id == cls.id).first().to_basic_dict()['name']

            data_dict = {
                "class_id": cls.id,
                # "class": grade[2:] + cls.class_name,
                "attendance_rate": attendance_rate,
                "class": cls.class_name,
                "leave_rate": leave_rate,
                "unattendance_rate": unattendance_rate
            }

            data.append(data_dict)

        try:
            rate = "%.2f%%" % (yes_count / (l_count + yes_count + no_count) * 100)
        except Exception as e:
            current_app.logger.error(e)
            rate = "0.00%"

        data = {
            "statistics_rate": data,
            # "date": now.strftime("%Y-%m-%d"),
            "yes_count": yes_count,
            "no_count": no_count,
            "leave_count": l_count,
            "rate": rate
        }
        return jsonify(errno=RET.OK, errmsg="OK", data=data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")


# 某个班的学生当前考勤记录
@api.route("/instructor/dormitory/attendance/<int:class_id>/student", methods=["GET"])
@jwt_required
@limit_role(roles=[1, 3])
def instructor_dormitory_cls_attendance_stu(class_id):
    """
    某个班的学生当前考勤记录
    传参day: 历史记录同上接口	搜索7天或一学期20周的记录
    ：：在用
    :param class_id:
    :return:
    """
    day = request.args.get("day", "1")
    keywords = request.args.get("keywords", "")
    now = date.today()
    username = get_jwt_identity()
    instructor_id = Instructor.query.filter(Instructor.sno == username).first().id

    try:
        dor_att = DormitoryAttendance.query.order_by(-DormitoryAttendance.attendance_date).first().attendance_date
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.NODATA)

    try:
        if now.strftime("%Y-%m-%d") > dor_att.strftime("%Y-%m-%d"):
            now = dor_att.strftime("%Y-%m-%d") + " " + now.strftime("%H:%M:%S")
            now = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        day = int(day)
        if day != 1:
            if day == 7:
                filter_params = [(now - timedelta(weeks=1)) <= DormitoryAttendance.attendance_date,
                                 DormitoryAttendance.attendance_date <= now]
            elif day == 30:
                filter_params = [(now - timedelta(days=30)) <= DormitoryAttendance.attendance_date,
                                 DormitoryAttendance.attendance_date <= now]
            elif day == 180:
                filter_params = [DormitoryAttendance.attendance_date <= now]
            else:
                filter_params = [DormitoryAttendance.attendance_date == now]
            # students = Student.query.join(Classes, Student.class_id == Classes.id).filter(Classes.instructor_id == instructor_id)
            if keywords:
                students = Student.query.filter(Student.class_id == class_id, Student.name.like("%" + keywords + "%")).all()
            else:
                students = Student.query.filter(Student.class_id == class_id).all()
            if len(students) == 0:
                return jsonify(errno=RET.NODATA, errmsg="无数据")
            data = []
            yes_count = 0
            no_count = 0
            l_count = 0
            for stu in students:
                unattendance_count = DormitoryAttendance.query.filter(
                    DormitoryAttendance.status == 0, DormitoryAttendance.student_id == stu.id).filter(*filter_params).count()

                attendance_count = DormitoryAttendance.query.filter(
                    DormitoryAttendance.status == 1, DormitoryAttendance.student_id == stu.id).filter(*filter_params).count()

                attendance_count_ins = DormitoryAttendance.query.filter(
                    DormitoryAttendance.status == 3, DormitoryAttendance.student_id == stu.id).filter(*filter_params).count()

                leave_count = DormitoryAttendance.query.filter(
                    DormitoryAttendance.status == 2, DormitoryAttendance.student_id == stu.id).filter(*filter_params).count()

                a_count = attendance_count + attendance_count_ins

                no_count += unattendance_count
                yes_count += a_count
                l_count += leave_count

                try:
                    attendance_rate = "%.2f%%" % (a_count / (leave_count + a_count + unattendance_count) * 100)
                except Exception as e:
                    current_app.logger.error(e)
                    attendance_rate = 0
                try:
                    leave_rate = "%.2f%%" % (leave_count / (leave_count + a_count + unattendance_count) * 100)
                except Exception as e:
                    current_app.logger.error(e)
                    leave_rate = 0
                try:
                    unattendance_rate = "%.2f%%" % (unattendance_count / (leave_count + a_count + unattendance_count) * 100)
                except Exception as e:
                    current_app.logger.error(e)
                    unattendance_rate = 0
                data_dict = {
                    "student_id": stu.id,
                    "student_name": stu.name,
                    "attendance_rate": attendance_rate,
                    "leave_rate": leave_rate,
                    "unattendance_rate": unattendance_rate,
                    # "sno": stu.sno,
                    # "classes": Classes.query.get(stu.class_id).class_name
                }
                data.append(data_dict)
            try:
                rate = "%.2f%%" % (yes_count / (l_count + yes_count + no_count) * 100)
            except Exception as e:
                current_app.logger.error(e)
                rate = "0.00%"
            data = {
                "rate": rate,
                "statistics_rate": data,
                "yes_count": yes_count,
                "no_count": no_count,
                "leave_count": l_count,
            }

            # resp_dict = dict(errno=RET.OK, errmsg="OK", data={})
            # resp_json = json.dumps(resp_dict)
            return jsonify(errno=RET.OK, errmsg="ok", data=data)
        else:
            stu = Student.query.filter(
                or_(Student.sno.like("%" + keywords + "%"), Student.name.like("%" + keywords + "%")), Student.class_id == class_id).all()
            if len(stu) == 0:
                return jsonify(errno=RET.NODATA, errmsg="无数据")
            filter_params = [DormitoryAttendance.attendance_date == now,
                             or_(Student.sno.like("%" + keywords + "%"), Student.name.like("%" + keywords + "%"))]

            unattendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
                .filter(DormitoryAttendance.status == 0).join(Classes, Student.class_id == Classes.id) \
                .filter(Classes.instructor_id == instructor_id).filter(Classes.id == class_id).filter(*filter_params).all()

            attendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
                .filter(DormitoryAttendance.status == 1).join(Classes, Student.class_id == Classes.id) \
                .filter(Classes.instructor_id == instructor_id).filter(Classes.id == class_id).filter(*filter_params).all()

            attendance_add = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
                .filter(DormitoryAttendance.status == 3).join(Classes, Student.class_id == Classes.id) \
                .filter(Classes.instructor_id == instructor_id).filter(Classes.id == class_id).filter(*filter_params).all()

            leave = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
                .filter(DormitoryAttendance.status == 2).join(Classes, Student.class_id == Classes.id) \
                .filter(Classes.instructor_id == instructor_id).filter(Classes.id == class_id).filter(*filter_params).all()

            unattendance_list, attendance_list, leave_list = [], [], []
            for ute in unattendance:
                unattendance_list.append(ute.to_dict())
            for ate in attendance:
                attendance_list.append(ate.to_dict())
            for ate_a in attendance_add:
                attendance_list.append(ate_a.to_dict())
            for lev in leave:
                leave_list.append(lev.to_dict())

            yes_count = len(attendance_list)
            no_count = len(unattendance_list)
            leave_count = len(leave_list)

            try:
                rate = "%.2f%%" % (yes_count / (leave_count + no_count + yes_count) * 100)
            except Exception as e:
                current_app.logger.error(e)
                rate = "0.00%"

            data = {
                "unattendance": unattendance_list,
                "attendance": attendance_list,
                "leave": leave_list,
                "yes_count": yes_count,
                "no_count": no_count,
                "leave_count": leave_count,
                "rate": rate
            }
            # resp_dict = dict(errno=RET.OK, errmsg="OK",
            #                  data={"unattendance": unattendance_list, "attendance": attendance_list, "leave": leave_list})
            # resp_json = json.dumps(resp_dict)
            return jsonify(errno=RET.OK, errmsg="OK", data=data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")


# 单个学生的宿舍考勤记录
@api.route("/instructor/dormitory/attendance/student/<int:student_id>", methods=["GET"])
@jwt_required
@limit_role(roles=[1, 3])
def instructor_dormitory_attendance_stu(student_id):
    """
    单个学生的宿舍考勤记录
    传参day：搜索同上一周或半学期即20week
    ：：在用
    :param student_id:
    :return:
    """
    day = request.args.get("day", "1")
    now = date.today()
    # username = get_jwt_identity()
    # instructor_id = Instructor.query.filter(Instructor.sno == username).first().id

    try:
        dor_att = DormitoryAttendance.query.order_by(-DormitoryAttendance.attendance_date).first().attendance_date
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.NODATA)

    try:
        if now.strftime("%Y-%m-%d") > dor_att.strftime("%Y-%m-%d"):
            now = now + timedelta(days=-1)

        day = int(day)
        if day == 7:
            filter_params = [(now - timedelta(weeks=1)) <= DormitoryAttendance.attendance_date,
                             DormitoryAttendance.attendance_date <= now]
        elif day == 30:
            filter_params = [(now - timedelta(days=30)) <= DormitoryAttendance.attendance_date,
                             DormitoryAttendance.attendance_date <= now]
        elif day == 180:
            filter_params = [DormitoryAttendance.attendance_date <= now]
        else:
            filter_params = [DormitoryAttendance.attendance_date == now]

        unattendance = DormitoryAttendance.query.filter(
            DormitoryAttendance.status == 0, DormitoryAttendance.student_id == student_id).filter(*filter_params).all()

        attendance = DormitoryAttendance.query.filter(
            DormitoryAttendance.status == 1, DormitoryAttendance.student_id == student_id).filter(*filter_params).all()

        ins_atten = DormitoryAttendance.query.filter(
            DormitoryAttendance.status == 3, DormitoryAttendance.student_id == student_id).filter(*filter_params).all()

        leave = DormitoryAttendance.query.filter(
            DormitoryAttendance.status == 2, DormitoryAttendance.student_id == student_id).filter(*filter_params).all()

        unattendance_list, attendance_list, leave_list = [], [], []
        for uat in unattendance:
            unattendance_list.append(uat.to_dict()["attendance_time"])
        for ate in attendance:
            attendance_list.append(ate.to_dict()["attendance_time"])
        for ate in ins_atten:
            attendance_list.append(ate.to_dict()["attendance_time"])
        for lev in leave:
            leave_list.append(lev.to_dict()["attendance_time"])

        yes_count = len(attendance_list)
        no_count = len(unattendance_list)
        leave_count = len(leave_list)

        try:
            rate = "%.2f%%" % (yes_count / (leave_count + no_count + yes_count) * 100)
        except Exception as e:
            current_app.logger.error(e)
            rate = "0.00%"

        data = {
            "unattendance": unattendance_list,
            "attendance": attendance_list,
            "leave": leave_list,
            "stu_name": Student.query.get(student_id).name,
            "rate": rate,
            "yes_count": yes_count,
            "no_count": no_count,
            "leave_count": leave_count,
        }

        return jsonify(errno=RET.OK, errmsg="OK", data=data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")


# 当前辅导员所有班级考勤
@api.route("/instructor/classroom/attendance/classes", methods=["GET"])
@jwt_required
@limit_role(roles=[1, 3])
def instruct_clsroom_attendance_cls():
    """
    当前辅导员所有班级考勤
    传参day：搜索同上时间筛选
    ：：在用
    :return:
    """
    day = request.args.get("day", "7")
    class_name = request.args.get("class_name", "")

    now = datetime.now()
    username = get_jwt_identity()
    try:
        instructor_id = Instructor.query.filter(Instructor.sno == username).first().id

        if class_name:
            classes = Classes.query.filter(Classes.instructor_id == instructor_id, Classes.class_name.like("%" + class_name + "%")).all()
        else:
            classes = Classes.query.filter(Classes.instructor_id == instructor_id).all()
        if len(classes) == 0:
            return jsonify(errno=RET.NODATA, errmsg="无数据")

        try:
            stu_res = Stu_classroom_atten_res.query.order_by(-Stu_classroom_atten_res.time).first().time
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.NODATA)
        if now.strftime("%Y-%m-%d") > stu_res.strftime("%Y-%m-%d"):
            now = now + timedelta(days=-1)

        data = []
        if day:
            day = int(day)

        if day == 30:
            filter_params = [(now - timedelta(days=30)) <= Stu_classroom_atten_res.time, Stu_classroom_atten_res.time <= now]
        elif day == 180:
            filter_params = [Stu_classroom_atten_res.time <= now]
        else:
            filter_params = [(now - timedelta(days=7)) <= Stu_classroom_atten_res.time, Stu_classroom_atten_res.time <= now]

        yes_count = 0
        no_count = 0
        l_count = 0

        for cls in classes:
            unattendance_count = Stu_classroom_atten_res.query.filter(
                Stu_classroom_atten_res.class_id == cls.id, Stu_classroom_atten_res.status == 0).filter(*filter_params).count()

            attendance_count = Stu_classroom_atten_res.query.filter(
                Stu_classroom_atten_res.class_id == cls.id, Stu_classroom_atten_res.status == 1).filter(*filter_params).count()

            attendance_add_count = Stu_classroom_atten_res.query.filter(
                Stu_classroom_atten_res.class_id == cls.id, Stu_classroom_atten_res.status == 3).filter(*filter_params).count()

            leave_count = Stu_classroom_atten_res.query.filter(
                Stu_classroom_atten_res.class_id == cls.id, Stu_classroom_atten_res == 2).filter(*filter_params).count()

            # unattendance_count = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            #     .join(Classroom_attendance, Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id).filter(*filter_params) \
            #     .join(Classes, Student.class_id == Classes.id).filter(Stu_classroom_atten_res.status == 0, Classes.id == cls.id).count()
            #
            # attendance_count = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            #     .join(Classroom_attendance, Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id).filter(*filter_params) \
            #     .join(Classes, Student.class_id == Classes.id).filter(Stu_classroom_atten_res.status == 1, Classes.id == cls.id).count()
            #
            # leave_count = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            #     .join(Classroom_attendance, Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id).filter(*filter_params) \
            #     .join(Classes, Student.class_id == Classes.id).filter(Stu_classroom_atten_res.status == 2, Classes.id == cls.id).count()
            att_count = attendance_count + attendance_add_count
            no_count += unattendance_count
            yes_count += att_count
            l_count += leave_count
            try:
                attendance_rate = "%.2f%%" % (att_count / (leave_count + att_count + unattendance_count) * 100)
            except Exception as e:
                current_app.logger.error(e)
                attendance_rate = "0.00%"
            try:
                leave_rate = "%.2f%%" % (leave_count / (leave_count + att_count + unattendance_count) * 100)
            except Exception as e:
                current_app.logger.error(e)
                leave_rate = "0.00%"
            try:
                unattendance_rate = "%.2f%%" % (unattendance_count / (leave_count + att_count + unattendance_count) * 100)
            except Exception as e:
                current_app.logger.error(e)
                unattendance_rate = "0.00%"

            grade = Grade.query.join(grade_major_relation, Grade.id == grade_major_relation.c.grade_id) \
                .join(Classes, grade_major_relation.c.id == Classes.grade_major_id).filter(Classes.id == cls.id) \
                .first().to_basic_dict()['name']

            data_dict = {
                "class_id": cls.id,
                # "classes": grade[2:] + cls.class_name,
                "classes": cls.class_name,
                "attendance_rate": attendance_rate,
                "leave_rate": leave_rate,
                "unattendance_rate": unattendance_rate
            }

            data.append(data_dict)

        try:
            rate = "%.2f%%" % (yes_count / (l_count + yes_count + no_count) * 100)
        except Exception as e:
            current_app.logger.error(e)
            rate = "0.00%"

        data = {
            "statistics_rate": data,
            # "date": now.strftime("%Y-%m-%d"),
            "yes_count": yes_count,
            "no_count": no_count,
            "leave_count": l_count,
            "rate": rate
        }
        return jsonify(errno=RET.OK, errmsg="OK", data=data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")


# 当前辅导员所有班级的课程考勤信息
@api.route("/instructor/classroom/attendance/course/<int:class_id>", methods=["GET"])
@jwt_required
@limit_role(roles=[1, 3])
def instruct_clsroom_attendance_course(class_id):
    """
    当前辅导员所有班级的课程考勤信息
    传参day：同上
    ：：在用
    :return:
    """
    day = request.args.get("day", "7")
    now = datetime.now()
    keywords = request.args.get("keywords", "")
    # username = get_jwt_identity()
    # instructor_id = Instructor.query.filter(Instructor.sno == username).first().id

    try:
        stu_res = Stu_classroom_atten_res.query.order_by(-Stu_classroom_atten_res.time).first().time
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.NODATA)

    try:
        if now.strftime("%Y-%m-%d") > stu_res.strftime("%Y-%m-%d"):
            now = now + timedelta(days=-1)
        # courses = Course.query.join(Course, course_class_relation.c.course_id == Course.id).join(
        #     course_class_relation, class_id == course_class_relation.c.class_id).all()
        if keywords:
            courses = Course.query.join(course_class_relation, course_class_relation.c.course_id == Course.id).filter(
                course_class_relation.c.class_id == class_id, Course.name.like("%" + keywords + "%")).all()
        else:
            courses = Course.query.join(course_class_relation, course_class_relation.c.course_id == Course.id).filter(
                course_class_relation.c.class_id == class_id).all()
        if len(courses) == 0:
            return jsonify(errno=RET.NODATA)
        data = []
        if day:
            day = int(day)
        if day == 30:
            filter_params = [(now - timedelta(days=30)) <= Stu_classroom_atten_res.time, Stu_classroom_atten_res.time <= now]
        elif day == 180:
            filter_params = [Stu_classroom_atten_res.time <= now]
        else:
            filter_params = [(now - timedelta(days=7)) <= Stu_classroom_atten_res.time, Stu_classroom_atten_res.time <= now]

        yes_count = 0
        no_count = 0
        l_count = 0
        for cou in courses:
            unattendance_count = Stu_classroom_atten_res.query.filter(
                Stu_classroom_atten_res.cource_id == cou.id, Stu_classroom_atten_res.status == 0).filter(*filter_params).count()

            attendance_count = Stu_classroom_atten_res.query.filter(
                Stu_classroom_atten_res.cource_id == cou.id, Stu_classroom_atten_res.status == 1).filter(*filter_params).count()

            attendance_add_count = Stu_classroom_atten_res.query.filter(
                Stu_classroom_atten_res.cource_id == cou.id, Stu_classroom_atten_res.status == 3).filter(*filter_params).count()

            leave_count = Stu_classroom_atten_res.query.filter(
                Stu_classroom_atten_res.cource_id == cou.id, Stu_classroom_atten_res.status == 2).filter(*filter_params).count()

            # unattendance_count = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            #     .join(Classroom_attendance, Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id).filter(*filter_params) \
            #     .join(Classes, Student.class_id == Classes.id).join(course_class_relation, Classes.id == course_class_relation.c.class_id) \
            #     .join(Course, course_class_relation.c.course_id == Course.id).filter(Stu_classroom_atten_res.status == 0,
            #                                                                          Classes.instructor_id == instructor_id,
            #                                                                          Course.id == cou.id).count()
            #
            # attendance_count = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            #     .join(Classroom_attendance, Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id).filter(*filter_params) \
            #     .join(Classes, Student.class_id == Classes.id).join(course_class_relation, Classes.id == course_class_relation.c.class_id) \
            #     .join(Course, course_class_relation.c.course_id == Course.id).filter(Stu_classroom_atten_res.status == 1,
            #                                                                          Classes.instructor_id == instructor_id,
            #                                                                          Course.id == cou.id).count()
            # leave_count = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            #     .join(Classroom_attendance, Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id).filter(*filter_params) \
            #     .join(Classes, Student.class_id == Classes.id).join(course_class_relation, Classes.id == course_class_relation.c.class_id) \
            #     .join(Course, course_class_relation.c.course_id == Course.id).filter(Stu_classroom_atten_res.status == 2,
            #                                                                          Classes.instructor_id == instructor_id,
            #                                                                          Course.id == cou.id).count()
            att_count = attendance_add_count + attendance_count
            yes_count += att_count
            no_count += unattendance_count
            l_count += leave_count

            try:
                attendance_rate = "%.2f%%" % (att_count / (leave_count + att_count + unattendance_count) * 100)
            except Exception as e:
                current_app.logger.error(e)
                attendance_rate = "0.00%"
            try:
                leave_rate = "%.2f%%" % (leave_count / (leave_count + att_count + unattendance_count) * 100)
            except Exception as e:
                current_app.logger.error(e)
                leave_rate = "0.00%"
            try:
                unattendance_rate = "%.2f%%" % (unattendance_count / (leave_count + att_count + unattendance_count) * 100)
            except Exception as e:
                current_app.logger.error(e)
                unattendance_rate = "0.00%"
            data_dict = {
                "cid": cou.id,
                "name": cou.name,
                "attendance_rate": attendance_rate,
                "leave_rate": leave_rate,
                "unattendance_rate": unattendance_rate
            }
            data.append(data_dict)
        try:
            rate = "%.2f%%" % (yes_count / (l_count + yes_count + no_count) * 100)
        except Exception as e:
            current_app.logger.error(e)
            rate = "0.00%"

        data = {
            "statistics_rate": data,
            # "date": now.strftime("%Y-%m-%d"),
            "yes_count": yes_count,
            "no_count": no_count,
            "leave_count": l_count,
            "rate": rate,
            "class_id": class_id
        }
        return jsonify(errno=RET.OK, errmsg="OK", data=data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据错误")


# 当前辅导员所学生的课程考勤信息
@api.route("/instructor/classroom/attendance/student/detail/<int:cid>/<int:class_id>", methods=["GET"])
@jwt_required
@limit_role(roles=[1, 3])
def instruct_clsroom_attendance_stu(cid, class_id):
    """
    当前辅导员所学生的课程考勤信息
    传参day：同上
    ：：在用
    :return:
    """
    day = request.args.get("day", "7")
    keywords = request.args.get("keywords", "")
    now = datetime.now()

    try:
        stu_res = Stu_classroom_atten_res.query.order_by(-Stu_classroom_atten_res.time).first().time
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.NODATA)

    try:
        if now.strftime("%Y-%m-%d") > stu_res.strftime("%Y-%m-%d"):
            now = now + timedelta(days=-1)

        if day:
            day = int(day)
        if day == 30:
            filter_params = [(now - timedelta(days=30)) <= Stu_classroom_atten_res.time, Stu_classroom_atten_res.time <= now,
                             Stu_classroom_atten_res.cource_id == cid]
        elif day == 180:
            filter_params = [Stu_classroom_atten_res.time <= now, Stu_classroom_atten_res.cource_id == cid]
        else:
            filter_params = [(now - timedelta(days=7)) <= Stu_classroom_atten_res.time, Stu_classroom_atten_res.time <= now,
                             Stu_classroom_atten_res.cource_id == cid]

        if keywords:
            students = Student.query.filter(Student.class_id == class_id,
                                            or_(Student.name.like("%" + keywords + "%"), Student.sno.like("%" + keywords + "%"))).all()
        else:
            students = Student.query.filter(Student.class_id == class_id).all()
        if len(students) == 0:
            return jsonify(errno=RET.NODATA)
        data = []
        yes_count = 0
        no_count = 0
        l_count = 0
        for stu in students:
            unattendance_count = Stu_classroom_atten_res.query.filter(
                Stu_classroom_atten_res.status == 0, Stu_classroom_atten_res.student_id == stu.id).filter(*filter_params).count()

            attendance_count = Stu_classroom_atten_res.query.filter(
                Stu_classroom_atten_res.status == 1, Stu_classroom_atten_res.student_id == stu.id).filter(*filter_params).count()

            attendance_add_count = Stu_classroom_atten_res.query.filter(
                Stu_classroom_atten_res.status == 3, Stu_classroom_atten_res.student_id == stu.id).filter(*filter_params).count()

            leave_count = Stu_classroom_atten_res.query.filter(
                Stu_classroom_atten_res.status == 2, Stu_classroom_atten_res.student_id == stu.id).filter(*filter_params).count()

            # unattendance_count = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            #     .join(Classroom_attendance, Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id).filter(
            #     *filter_params).join(Classes, Student.class_id == Classes.id).filter(Stu_classroom_atten_res.status == 0,
            #                                                                          Classes.instructor_id == 1, Student.id == stu.id).count()
            # attendance_count = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            #     .join(Classroom_attendance, Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id).filter(
            #     *filter_params).join(Classes, Student.class_id == Classes.id).filter(Stu_classroom_atten_res.status == 1,
            #                                                                          Classes.instructor_id == 1, Student.id == stu.id).count()
            # leave_count = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            #     .join(Classroom_attendance, Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id).filter(
            #     *filter_params).join(Classes, Student.class_id == Classes.id).filter(Stu_classroom_atten_res.status == 1,
            #                                                                          Classes.instructor_id == 1, Student.id == stu.id).count()
            att_count = attendance_add_count + attendance_count
            yes_count += att_count
            no_count += unattendance_count
            l_count += leave_count

            try:
                attendance_rate = "%.2f%%" % (att_count / (leave_count + att_count + unattendance_count) * 100)
            except Exception as e:
                current_app.logger.error(e)
                attendance_rate = "0.00%"
            try:
                leave_rate = "%.2f%%" % (leave_count / (leave_count + att_count + unattendance_count) * 100)
            except Exception as e:
                current_app.logger.error(e)
                leave_rate = "0.00%"
            try:
                unattendance_rate = "%.2f%%" % (unattendance_count / (leave_count + att_count + unattendance_count) * 100)
            except Exception as e:
                current_app.logger.error(e)
                unattendance_rate = "0.00%"
            data_dict = {"name": stu.name, "attendance_rate": attendance_rate,
                         "leave_rate": leave_rate, "unattendance_rate": unattendance_rate}
            data.append(data_dict)

        try:
            rate = "%.2f%%" % (yes_count / (l_count + yes_count + no_count) * 100)
        except Exception as e:
            current_app.logger.error(e)
            rate = "0.00%"

        data = {
            "statistics_rate": data,
            # "date": now.strftime("%Y-%m-%d"),
            "yes_count": yes_count,
            "no_count": no_count,
            "leave_count": l_count,
            "rate": rate,
            "class_id": class_id
        }
        return jsonify(errno=RET.OK, errmsg="OK", data=data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据异常")


@api.route('/instructor/classroom/today/rate/attendance', methods=["GET"])
@jwt_required
@limit_role(roles=[1, 3])
def today_classroom_attendance_rate():
    """
    过去七天教室考勤率
    :return:
    """
    now = datetime.now()
    username = get_jwt_identity()
    instructor_id = Instructor.query.filter(Instructor.sno == username).first().id
    filter_params = [now - timedelta(weeks=1) <= Classroom_attendance.end_time, Classroom_attendance.end_time <= now]

    unattendance_count = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
        .join(Classroom_attendance, Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
        .join(Classes, Student.class_id == Classes.id).filter(Stu_classroom_atten_res.status == 0, Classes.instructor_id == instructor_id,
                                                              *filter_params).count()

    attendance_count = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
        .join(Classroom_attendance, Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
        .join(Classes, Student.class_id == Classes.id).filter(Stu_classroom_atten_res.status == 1, Classes.instructor_id == instructor_id,
                                                              *filter_params).count()

    leave_count = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
        .join(Classroom_attendance, Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
        .join(Classes, Student.class_id == Classes.id).filter(Stu_classroom_atten_res.status == 2, Classes.instructor_id == instructor_id,
                                                              *filter_params).count()
    attendance_rate = "%.4f" % (attendance_count / (leave_count + attendance_count + unattendance_count))
    resp_dict = dict(errno=RET.OK, errmsg="OK",
                     data={"attendance_rate": attendance_rate, "attendance_count": attendance_count,
                           "leave": leave_count, "unattendance_count": unattendance_count})
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}


# 查看个人信息
@api.route("/instructor/info", methods=["GET"])
@jwt_required
@limit_role(roles=[1, 3])
def get_instructor_info():
    """
    查看个人信息
    ：：在用
    :return:
    """
    try:
        username = get_jwt_identity()
        instructor = Instructor.query.filter(Instructor.sno == username).first()
        resp_dict = dict(errno=RET.OK, errmsg="OK", data={"instructor": instructor.to_full_dict()})
        resp_json = json.dumps(resp_dict)
        return resp_json, 200, {"Content-Type": "application/json"}
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据异常")


# 修改个人信息
@api.route("/instructor/info/modify", methods=["POST"])
@jwt_required
@limit_role(roles=[1, 3])
def instructor_modify():
    """
    修改个人信息
    ：：在用
    :return:
    """
    try:
        data = request.get_json()
        office = data.get('office')
        phone_num = data.get('phone')
        qq = data.get('qq')
        email = data.get('email')
        username = get_jwt_identity()
        instructor = Instructor.query.filter(Instructor.sno == username).first()
        instructor.office = office
        instructor.phone_num = phone_num
        instructor.qq = qq
        instructor.email = email
        db.session.add(instructor)
        db.session.commit()
        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="修改个人信息成功")), 200, {"Content-Type": "application/json"}
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据异常")


# 修改密码
@api.route('/instructor/repassword', methods=["POST"])
@jwt_required
@limit_role(roles=[1, 3])
def info_repassword():
    """
    修改密码
    ：：在用
    :return:
    """
    try:
        data = request.get_json()
        password = data.get('password')
        repassword = data.get('repassword')
        username = get_jwt_identity()
        instructor = Instructor.query.filter(Instructor.sno == username).first()
        user = Users.query.filter(Users.username == instructor.sno).first()
        if user.check_password(password):
            try:
                user.password = repassword
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger(e)
                return jsonify(errno=RET.PARAMERR, errmsg="重置密码错误")
            return jsonify(errno=RET.OK, errmsg="重置密码成功")
        else:
            return jsonify(errno=RET.DATAERR, errmsg="原密码验证错误")
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据异常")
