__author__ = 'zhangenmin'
__date__ = '2019/3/1 12:06'

from attendance import db
from sqlalchemy import or_
from attendance import UserObject
from flask import jsonify, request, current_app, Session, make_response, send_file
from attendance.utils.commons import login_required, auth_token, limit_role
from attendance.utils.response_code import RET
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import jwt_required
from . import api
from datetime import datetime, date, timedelta
from io import BytesIO
from attendance import constants
from attendance.models import Users, Student, Teacher, Instructor, Department_admin, Grade, Major, Department, \
    course_class_relation, Course, Classes, grade_major_relation, School_roll_type, DormitoryAttendance, Leave,\
    Classroom_attendance , Stu_classroom_atten_res
from flask_jwt_extended import get_jwt_identity,create_access_token

import json
import xlwt
import pandas as pd
import os
import sys
import pymysql
from pypinyin import lazy_pinyin


@api.route("/admin/gmc", methods=["GET"])
def get_gmc_list():
    classes_li = Classes.query.all()
    grade_li = Grade.query.all()
    major_li = Major.query.all()
    school_roll_status_li = School_roll_type.query.all()
    classes, grades, majors, school_roll_statuses = [], [], [], []
    for cls in classes_li:
        classes.append(cls.to_basic_dict())
    for grade in grade_li:
        grades.append(grade.to_basic_dict())
    for major in major_li:
        majors.append(major.to_basic_dict())
    for school_roll_status in school_roll_status_li:
        school_roll_statuses.append(school_roll_status.to_dict())
    resp_dict = dict(errno=RET.OK, errmsg="OK", data={"classes": classes, "grades": grades, "majors": majors,
                                                      "school_roll_status": school_roll_statuses})
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}


@api.route("/admin/students/index", methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def get_student_list():
    """获取学生的列表信息（搜索页面）"""
    sno = request.args.get("sno", "")
    phone = request.args.get("phone",)
    name = request.args.get("name", "")
    grade = request.args.get("grade", "")
    major = request.args.get("major", "")
    classes = request.args.get("class", "")
    # 1.获取参数(页数)
    page = request.args.get('page')
    # 1.获取参数(每页条数)
    page_count = request.args.get('limit')
    # 2.参数据类型转换
    try:
        page_count = int(page_count)
    except Exception as e:
        current_app.logger.error(e)
        page_count = constants.STUDENT_LIST_PAGE_CAPACITY
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    # 过滤条件的参数列表容器
    filter_params = [Student.sno.like("%" + sno + "%"),
                     Student.name.like("%" + name + "%"), grade_major_relation.c.grade_id.contains(grade),
                     grade_major_relation.c.major_id.contains(major), Classes.id.contains(classes)]
    if phone:
        # 过滤条件的参数列表容器
        filter_params = [Student.sno.like("%" + sno + "%"), Student.phone.contains(phone),
                         Student.name.like("%" + name + "%"), grade_major_relation.c.grade_id.contains(grade),
                         grade_major_relation.c.major_id.contains(major), Classes.id.contains(classes)]
    # 时间条件
    conflict_orders = None

    student_query = Student.query.join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                                     Classes.grade_major_id == grade_major_relation.c.id).filter(
        *filter_params).order_by(Student.sno.desc())
    # 3.分页查询
    count = student_query.count()
    try:
        paginate = student_query.paginate(page=page, per_page=page_count, error_out=False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="学生信息获取失败")
    # 获取页面数据
    student_li = paginate.items
    data = []
    for stu in student_li:
        data.append(stu.to_full_dict())
    # 4.获取分页对象属性,总页数,当前页,对象列表
    total_page = paginate.pages
    resp_dict = dict(errno=RET.OK, errmsg="OK", total_page=total_page, data=data, current_page=page, count=count)
    resp_json = json.dumps(resp_dict)

    return resp_json, 200, {"Content-Type": "application/json"}


@api.route("/admin/students", methods=["POST", "DELETE"])
@jwt_required
@limit_role(roles=[1])
def add_delete_student():
    if request.method == 'POST':
        # "添加学生信息"
        data = request.get_json()
        sno = data.get('sno')
        name = data.get("name")
        class_id = data.get("class")
        school_roll_status = data.get("school_roll_status")
        if not all([sno, name, class_id, school_roll_status]):
            return jsonify(errno=RET.PARAMERR, errmsg="参数不完整")
        user = Users(username=sno, role=4)
        user.password = sno
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
            # 表示帐号出现了重复值，即账号已注册过
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询数据库异常")
        student = Student(sno=sno, class_id=int(class_id), name=name, school_roll_status_id=int(school_roll_status))
        db.session.add(student)
        db.session.commit()
        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="添加学生成功")), 200, {"Content-Type": "application/json"}
    if request.method == 'DELETE':
        data = request.get_json()
        user = []
        for i in data:
            stu = Student.query.get(i)
            user.append(stu.sno)
        print(user)
        try:
            db.session.query(Users).filter(Users.username.in_(user)).delete(synchronize_session=False)
            db.session.query(Student).filter(Student.id.in_(data)).delete(synchronize_session=False)
            db.session.commit()
        except Exception as e:
            current_app.logger(e)
            return jsonify(errno=RET.DBERR, errmsg="部分数据删除失败")
        return jsonify(errno=RET.OK, errmsg="批量删除成功")


@api.route("/admin/students/<int:student_id>/image", methods=["POST"])
@jwt_required
@limit_role(roles=[1])
def update_student_image(student_id):
    head_picture = request.files.get('file')
    print(head_picture)
    if not all([head_picture]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不完整")
    filename = head_picture.filename
    try:
        student = Student.query.get(student_id)
        grade_major_classes = student.get_classes()
        class_name = grade_major_classes['class_name']
        # grade_relation为models中的db.relationship的名称
        grade_name = grade_major_classes['grade_name']
        major_name = grade_major_classes['major_name']
        file_url = 'attendance/static/upload/{}/'.format(grade_name) + '{}/'.format(major_name) + '{}/'.format(
            class_name)
        path = ''.join(lazy_pinyin(file_url))
        img_dir = path + '{}.jpg'.format(student.sno)
        if not os.path.exists(path):
            os.makedirs(path)
        try:
            if head_picture:
                head_picture = head_picture.save(img_dir)
                student.face_img = img_dir
            db.session.add(student)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="上传头像失败")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="无此学生信息")
    return json.dumps(dict(errno=RET.OK, errmsg="修改头像成功", data=student.face_img)), 200, {
        "Content-Type": "application/json"}


@api.route("/admin/students/<int:student_id>", methods=["GET", "PUT", "DELETE"])
@jwt_required
@limit_role(roles=[1])
def update_delete_student(student_id):
    if request.method == "GET":
        if request.method == "GET":
            try:
                student = Student.query.get(student_id)
                student = student.to_full_dict()
                resp_dict = dict(errno=RET.OK, errmsg="OK", data={"student": student, })
                resp_json = json.dumps(resp_dict)
                return resp_json, 200, {"Content-Type": "application/json"}
            except Exception as e:
                current_app.logger.error(e)
                return jsonify(errno=RET.DBERR, errmsg="获取学生信息失败")
    if request.method == 'PUT':
        data = request.get_json()
        sno = data.get("sno")
        name = data.get("name")
        sex = data.get("sex")
        idcard_num = data.get("idcard_num")
        dormitory_num = data.get("dormitory_num")
        phone = data.get("phone")
        qq = data.get("qq")
        email = data.get("email")
        leave_status = data.get("leave_status")
        classes = data.get("class")
        try:
            student = Student.query.filter(Student.id == student_id).first()
            if sno != student.sno:
                user = Users.query.filter(Users.username == student.sno).first()
                user.username = sno
                try:
                    db.session.add(user)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    # 表示帐号出现了重复值，即账号已注册过
                    current_app.logger.error(e)
                    return jsonify(errno=RET.DBERR, errmsg="修改的学号重复", data="修改数据失败")
            try:
                student.name = name
                student.idcard_num = idcard_num
                student.dormitory_num = dormitory_num
                student.phone = phone
                student.sex = sex
                student.qq = qq
                student.email = email
                student.leave_status = leave_status
                student.class_id = classes
                db.session.add(student)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(e)
                return jsonify(errno=RET.DBERR, errmsg="修改数据失败", data="修改数据失败")
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="未查到数据", data="未查到数据")
        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="修改学生成功")), 200, {"Content-Type": "application/json"}
    if request.method == 'DELETE':
        try:
            student = Student.query.filter(Student.id == student_id).first()
            sno = student.sno
            user = Users.query.filter(Users.username == sno).first()
            db.session.delete(student)
            db.session.delete(user)
            db.session.commit()
            db.session.delete(user)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="未查到数据")

        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="删除学生成功")), 200, {"Content-Type": "application/json"}


@api.route("/admin/students/exceldemo/", methods=["GET"])
def student_excel_demo():
    filename = '导入模板' + '.xls'
    # 创建一个sheet对象
    wb = xlwt.Workbook(encoding='utf-8')
    sheet = wb.add_sheet('order-sheet')
    # 写入文件标题
    sheet.write(0, 0, '学号')
    sheet.write(0, 1, '姓名')
    sheet.write(0, 2, '年级')
    sheet.write(0, 3, '专业')
    sheet.write(0, 4, '班级')
    # 写出到IO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['content_type='] = ' application/vnd.ms-excel'
    # 创建一个文件对象
    response.headers['Content-Disposition'] = 'attachment;filename={}'.format(filename.encode().decode('latin-1'))
    return response


@api.route("/admin/students/excel/", methods=["GET"])
def student_get_excel():
    now = datetime.now()
    time = datetime.strftime(now, '%Y%m%d%H%M%S')
    filename = time + '.xls'
    # 创建一个sheet对象
    wb = xlwt.Workbook(encoding='utf-8')
    sheet = wb.add_sheet('order-sheet')
    # 写入文件标题
    sheet.write(0, 0, '学号')
    sheet.write(0, 1, '姓名')
    sheet.write(0, 2, '性别')
    sheet.write(0, 3, '身份证号')
    sheet.write(0, 4, '在读状态')
    sheet.write(0, 5, '班级')
    sheet.write(0, 6, '年级')
    sheet.write(0, 7, '专业')
    data_row = 1
    for stu in Student.query.all():
        sheet.write(data_row, 0, stu.to_basic_dict()['sno'])
        sheet.write(data_row, 1, stu.to_basic_dict()['name'])
        sheet.write(data_row, 2, stu.to_basic_dict()['sex'])
        sheet.write(data_row, 3, stu.to_basic_dict()['idcard_num'])
        sheet.write(data_row, 4, stu.to_basic_dict()['school_roll_status']['name'])
        sheet.write(data_row, 5, stu.to_basic_dict()['major']['name'])
        sheet.write(data_row, 6, stu.to_basic_dict()['grade']['name'])
        sheet.write(data_row, 7, stu.to_basic_dict()['class_id']['class_name'])
        data_row = data_row + 1
    # 写出到IO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['content_type='] = ' application/vnd.ms-excel'
    # 创建一个文件对象
    response.headers['Content-Disposition'] = 'attachment;filename={}'.format(filename.encode().decode('latin-1'))
    return response


@api.route("/admin/students/excel/", methods=["POST"])
@jwt_required
@limit_role(roles=[1])
def student_excel():
    # 错误数据
    error_data = []
    excel_raw_data = pd.read_excel(request.files.get('file', ''), header=None)
    # 删除第一行的标题
    excel_raw_data.drop([0, 0], inplace=True)
    sno_col = excel_raw_data.iloc[:, [0]]
    name_col = excel_raw_data.iloc[:, [1]]
    class_col = excel_raw_data.iloc[:, [4]]
    grade_col = excel_raw_data.iloc[:, [2]]
    major_col = excel_raw_data.iloc[:, [3]]
    sno_list = sno_col.values.tolist()
    name_list = name_col.values.tolist()
    class_list = class_col.values.tolist()
    grade_list = grade_col.values.tolist()
    major_list = major_col.values.tolist()
    for i in range(len(name_list)):
        name_list_index = name_list[i]
        sno_list_index = sno_list[i]
        grade_list_index = grade_list[i]
        major_list_index = major_list[i]
        class_list_index = class_list[i]
        user = Users(username=sno_list_index[0], role=4)
        user.password = str(sno_list_index[0])
        print(major_list_index[0], grade_list_index[0])
        try:
            major_id = Major.query.filter(Major.name == major_list_index[0]).first()
            grade_id = Grade.query.filter(Grade.name == grade_list_index[0]).first()
            print(grade_id, major_id.name)
            try:
                class_id = Classes.query.join(grade_major_relation,
                                              Classes.grade_major_id == grade_major_relation.c.id). \
                    filter(grade_major_relation.c.grade_id == grade_id.id,
                           grade_major_relation.c.major_id == major_id.id,
                           Classes.class_name == class_list_index[0]).first()
                try:
                    db.session.add(user)
                    db.session.commit()
                    try:
                        student = Student(sno=sno_list_index[0], class_id=class_id.id, name=name_list_index[0],
                                          school_roll_status_id=1)
                        db.session.add(student)
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        error_data.append(str(sno_list_index[0]) + '添加失败')
                except Exception as e:
                    # 数据库操作错误后的回滚
                    db.session.rollback()
                    # 表示账号出现了重复值，即账号已注册过
                    current_app.logger.error(e)
                    error_data.append(str(sno_list_index[0]) + '的账号已经存在')
            except Exception as e:
                current_app.logger.error(e)
                error_data.append(str(sno_list_index[0]) + '的班级专业信息错误')
        except Exception as e:
            current_app.logger.error(e)
            error_data.append(str(sno_list_index[0]) + '的年级专业信息错误')
    if error_data:
        return json.dumps(dict(errno=RET.PARAMERR, errmsg="OK", data=error_data)), 200, {
            "Content-Type": "application/json"}
    else:
        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="全部信息导入成功")), 200, {"Content-Type": "application/json"}


@api.route("/admin/teachers/index", methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def get_teacher_list():
    """获取老师的列表信息（搜索页面）"""
    sno = request.args.get("sno", "")
    phone = request.args.get("phone")
    name = request.args.get("name", "")
    # 1.获取参数(页数)
    page = request.args.get('page')
    # 1.获取参数(每页条数)
    page_count = request.args.get('limit')
    # 2.参数据类型转换
    try:
        page_count = int(page_count)
    except Exception as e:
        current_app.logger.error(e)
        page_count = constants.TEACHER_LIST_PAGE_CAPACITY
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    # 过滤条件的参数列表容器
    filter_params = [Teacher.sno.like("%" + sno + "%"),Teacher.name.like("%" + name + "%")]

    if phone:
        filter_params = [Teacher.sno.like("%" + sno + "%"), Teacher.phone_num.contains(phone),
                         Teacher.name.like("%" + name + "%")]
    # 时间条件
    conflict_orders = None
    teacher_query = Teacher.query.filter(*filter_params).order_by(Teacher.sno.desc())
    count = teacher_query.count()
    try:
        paginate = teacher_query.paginate(page=page, per_page=page_count, error_out=False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="老师信息获取失败")
    # 获取页面数据
    teacher_li = paginate.items
    teachers = []
    for tea in teacher_li:
        teachers.append(tea.to_full_dict())
    # 4.获取分页对象属性,总页数,当前页,对象列表
    total_page = paginate.pages
    resp_dict = dict(errno=RET.OK, errmsg="OK", total_page=total_page, data=teachers, current_page=page, count=count)
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}


@api.route("/admin/teachers", methods=["POST", "DELETE"])
@jwt_required
@limit_role(roles=[1])
def add_delete_teacher():
    if request.method == "POST":
        # "添加老师信息"
        data = request.get_json()
        sno = data.get('sno')
        name = data.get("name")
        sex = data.get("sex")
        if not all([sno, name,sex]):
            return jsonify(errno=RET.PARAMERR, errmsg="参数不完整")
        user = Users(username=sno, role=2)
        user.password = sno
        try:
            db.session.add(user)
            db.session.commit()
            try:
                teacher = Teacher(sno=sno, name=name, sex=sex)
                db.session.add(teacher)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                # 表示帐号出现了重复值，即账号已注册过
                current_app.logger.error(e)
                return jsonify(errno=RET.DBERR, errmsg="添加失败")
        except Exception as e:
            # 数据库操作错误后的回滚
            db.session.rollback()
            # 表示账号出现了重复值，即账号已注册过
            current_app.logger.error(e)
            return jsonify(errno=RET.DATAEXIST, errmsg="账号已存在")
        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="添加老师成功")), 200, {"Content-Type": "application/json"}
    if request.method == 'DELETE':
        data = request.get_json()
        print(data)
        user = []
        for i in data:
            tea = Teacher.query.get(i)
            user.append(tea.sno)
        print(user)
        try:
            db.session.query(Users).filter(Users.username.in_(user)).delete(synchronize_session=False)
            db.session.query(Teacher).filter(Teacher.id.in_(data)).delete(synchronize_session=False)
            db.session.commit()
        except Exception as e:
            current_app.logger(e)
            return jsonify(errno=RET.DBERR, errmsg="部分数据删除失败")
        return jsonify(errno=RET.OK, errmsg="批量删除成功")


@api.route("/admin/teachers/<int:teacher_id>/image", methods=["POST"])
@jwt_required
@limit_role(roles=[1])
def update_teacher_image(teacher_id):
    head_picture = request.files.get('file')
    filename = head_picture.filename
    try:
        teacher = Teacher.query.get(teacher_id)
        file_url = 'attendance/static/upload/teacher/'
        path = ''.join(lazy_pinyin(file_url))
        img_dir = path + '{}.jpg'.format(teacher.sno)
        if not os.path.exists(path):
            os.makedirs(path)
        try:
            if head_picture:
                head_picture = head_picture.save(img_dir)
                teacher.head_picture = img_dir[10:]
            db.session.add(teacher)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="上传头像失败")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="无此老师信息")
    return json.dumps(dict(errno=RET.OK, errmsg="OK", data="修改头像成功")), 200, {"Content-Type": "application/json"}


@api.route("/admin/teachers/<int:teacher_id>", methods=["GET", "PUT", "DELETE"])
@jwt_required
@limit_role(roles=[1])
def admin_update_teacher(teacher_id):
    if request.method == "GET":
        try:
            teacher = Teacher.query.get(teacher_id)
            teacher = teacher.to_full_dict()
            resp_dict = dict(errno=RET.OK, errmsg="OK", data={"teacher": teacher, })
            resp_json = json.dumps(resp_dict)
            return resp_json, 200, {"Content-Type": "application/json"}
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="获取老师信息失败")
    if request.method == "PUT":
        data = request.get_json()
        sno = data.get("sno")
        name = data.get("name")
        sex = data.get("sex")
        idcard_num = data.get("idcard_num")
        phone_num = data.get("phone")
        qq = data.get("qq")
        email = data.get("email")
        office = data.get("office")
        try:
            teacher = Teacher.query.filter(Teacher.id == teacher_id).first()
            if sno != teacher.sno:
                user = Users.query.filter(Users.username == teacher.sno).first()
                user.username = sno
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
                    # 表示帐号出现了重复值，即账号已注册过
                    current_app.logger.error(e)
                    return jsonify(errno=RET.DBERR, errmsg="修改数据失败")
            try:
                teacher.name = name
                teacher.idcard_num = idcard_num
                teacher.phone_num = phone_num
                teacher.sex = sex
                teacher.qq = qq
                teacher.email = email
                teacher.office = office
                db.session.add(teacher)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                # 表示帐号出现了重复值，即账号已注册过
                current_app.logger.error(e)
                return jsonify(errno=RET.DBERR, errmsg="修改数据失败")
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="未查到数据")
        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="修改老师成功")), 200, {"Content-Type": "application/json"}
    if request.method == "DELETE":
        try:
            teacher = Teacher.query.filter(Teacher.id == teacher_id).first()
            sno = teacher.sno
            user = Users.query.filter(Users.username == sno).first()
            db.session.delete(teacher)
            db.session.delete(user)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="未查到数据")
        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="删除老师成功")), 200, {"Content-Type": "application/json"}


@api.route("/admin/teachers/exceldemo/", methods=["GET"])
def teacher_excel_demo():
    filename = '导入模板' + '.xls'
    # 创建一个sheet对象
    wb = xlwt.Workbook(encoding='utf-8')
    sheet = wb.add_sheet('order-sheet')
    # 写入文件标题
    sheet.write(0, 0, '职工号')
    sheet.write(0, 1, '姓名')
    # 写出到IO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['content_type='] = ' application/vnd.ms-excel'
    # 创建一个文件对象
    response.headers['Content-Disposition'] = 'attachment;filename={}'.format(filename.encode().decode('latin-1'))
    return response


@api.route("/admin/teachers/excel/", methods=["GET"])
def teacher_get_excel():
    now = datetime.now()
    time = datetime.strftime(now, '%Y%m%d%H%M%S')
    filename = time + '.xls'
    # 创建一个sheet对象
    wb = xlwt.Workbook(encoding='utf-8')
    sheet = wb.add_sheet('order-sheet')
    # 写入文件标题
    sheet.write(0, 0, '职工号')
    sheet.write(0, 1, '姓名')
    sheet.write(0, 2, '性别')
    sheet.write(0, 3, '身份证号')
    sheet.write(0, 4, '手机')
    sheet.write(0, 5, '办公室')
    sheet.write(0, 6, '邮箱')
    sheet.write(0, 7, 'QQ')
    data_row = 1
    for teacher in Teacher.query.all():
        sheet.write(data_row, 0, teacher.to_full_dict()['sno'])
        sheet.write(data_row, 1, teacher.to_full_dict()['name'])
        sheet.write(data_row, 2, teacher.to_full_dict()['sex'])
        sheet.write(data_row, 3, teacher.to_full_dict()['idcard_num'])
        sheet.write(data_row, 4, teacher.to_full_dict()['phone_num'])
        sheet.write(data_row, 5, teacher.to_full_dict()['office'])
        sheet.write(data_row, 6, teacher.to_full_dict()['email'])
        sheet.write(data_row, 7, teacher.to_full_dict()['qq'])
        data_row = data_row + 1
    # 写出到IO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['content_type='] = ' application/vnd.ms-excel'
    # 创建一个文件对象
    response.headers['Content-Disposition'] = 'attachment;filename={}'.format(filename.encode().decode('latin-1'))
    return response


@api.route("/admin/teachers/excel/", methods=["POST"])
@jwt_required
@limit_role(roles=[1])
def teacher_excel():
    # 错误数据
    error_data = []
    excel_raw_data = pd.read_excel(request.files.get('file', ''), header=None)
    # 删除第一行的标题
    excel_raw_data.drop([0, 0], inplace=True)
    sno_col = excel_raw_data.iloc[:, [0]]
    name_col = excel_raw_data.iloc[:, [1]]
    sno_list = sno_col.values.tolist()
    name_list = name_col.values.tolist()
    for i in range(len(name_list)):
        name_list_index = name_list[i]
        sno_list_index = sno_list[i]
        user = Users(username=sno_list_index[0], role=4)
        user.password = str(sno_list_index[0])
        try:
            db.session.add(user)
            db.session.commit()
            try:
                teacher = Teacher(sno=sno_list_index[0], name=name_list_index[0])
                db.session.add(teacher)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                error_data.append(str(sno_list_index[0]) + '添加失败')
        except Exception as e:
            # 数据库操作错误后的回滚
            db.session.rollback()
            # 表示账号出现了重复值，即账号已注册过
            current_app.logger.error(e)
            error_data.append(str(sno_list_index[0]) + '的账号已经存在')
    if error_data:
        return json.dumps(dict(errno=RET.DATAEXIST, errmsg="部分信息导入失败",data=error_data)), 200, {"Content-Type": "application/json"}
    else:
        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="全部信息导入成功")), 200, {
            "Content-Type": "application/json"}


@api.route("/admin/instructors/index", methods=["GET"])
@jwt_required
@limit_role([1])
def get_instructor_list():
    """获取辅导员的列表信息（搜索页面）"""
    sno = request.args.get("sno", "")
    phone = request.args.get("phone",)
    name = request.args.get("name", "")
    # 1.获取参数(页数)
    page = request.args.get('page')
    # 1.获取参数(每页条数)
    page_count = request.args.get('limit')
    # 2.参数据类型转换
    try:
        page_count = int(page_count)
    except Exception as e:
        current_app.logger.error(e)
        page_count = constants.TEACHER_LIST_PAGE_CAPACITY
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    # 过滤条件的参数列表容器
    filter_params = [Instructor.sno.like("%" + sno + "%"),
                     Instructor.name.like("%" + name + "%")]
    if phone:
        filter_params = [Instructor.sno.like("%" + sno + "%"),Instructor.phone_num.contains(phone),
                         Instructor.name.like("%" + name + "%")]
    # 时间条件
    conflict_orders = None
    instructor_query = Instructor.query.filter(*filter_params).order_by(Instructor.sno.desc())
    try:
        paginate = instructor_query.paginate(page=page, per_page=page_count, error_out=False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="辅导信息获取失败")
    count = instructor_query.count()
    # 获取页面数据
    instructor_li = paginate.items
    instructors = []
    for ins in instructor_li:
        instructors.append(ins.to_full_dict())
    # 4.获取分页对象属性,总页数,当前页,对象列表
    total_page = paginate.pages
    resp_dict = dict(errno=RET.OK, errmsg="OK", total_page=total_page, data=instructors, current_page=page, count=count)
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}


@api.route("/admin/instructors", methods=["POST", "DELETE"])
@jwt_required
@limit_role(roles=[1])
def add_delete_instructor():
    if request.method == "POST":
        # "添加辅导员信息"
        data = request.get_json()
        sno = data.get("sno")
        name = data.get("name")
        sex = data.get("sex")
        if not all([sno, name, sex]):
            return jsonify(errno=RET.PARAMERR, errmsg="参数不完整")
        user = Users(username=sno, role=3)
        user.password = sno
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
            # 表示帐号出现了重复值，即账号已注册过
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询数据库异常")
        instructor = Instructor(sno=sno, name=name, sex=sex)
        db.session.add(instructor)
        db.session.commit()
        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="添加辅导员成功")), 200, {"Content-Type": "application/json"}
    if request.method == 'DELETE':
        data = request.get_json()
        user = []
        for i in data:
            ins = Instructor.query.get(i)
            user.append(ins.sno)
        try:
            db.session.query(Users).filter(Users.username.in_(user)).delete(synchronize_session=False)
            db.session.query(Instructor).filter(Instructor.id.in_(data)).delete(synchronize_session=False)
            db.session.commit()
        except Exception as e:
            current_app.logger(e)
            return jsonify(errno=RET.DBERR, errmsg="部分数据删除失败")
        return jsonify(errno=RET.OK, errmsg="批量删除成功")


@api.route("/admin/instructors/<int:instructor_id>/image", methods=["POST"])
@jwt_required
@limit_role(roles=[1])
def update_instructor_image(instructor_id):
    head_picture = request.files.get('file')
    filename = head_picture.filename
    try:
        instructor = Instructor.query.get(instructor_id)
        file_url = 'attendance/static/upload/instructor/'+ '{}.jpg'.format(instructor.sno)
        path = ''.join(lazy_pinyin(file_url))
        img_dir = path + '{}.jpg'.format(instructor.sno)
        if not os.path.exists(path):
            os.makedirs(path)
        try:
            if head_picture:
                head_picture = head_picture.save(img_dir)
                instructor.head_picture = img_dir[10:]
            db.session.add(instructor)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="上传头像失败")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="无此老师信息")
    return json.dumps(dict(errno=RET.OK, errmsg="OK", data="修改头像成功")), 200, {"Content-Type": "application/json"}


@api.route("/admin/instructors/<int:instructor_id>", methods=["GET", "PUT", "DELETE"])
@jwt_required
@limit_role(roles=[1])
def update_delete_instructor(instructor_id):
    if request.method == "GET":
        try:
            instructor = Instructor.query.get(instructor_id)
            instructor = instructor.to_full_dict()
            resp_dict = dict(errno=RET.OK, errmsg="OK", data={"instructor": instructor})
            resp_json = json.dumps(resp_dict)
            return resp_json, 200, {"Content-Type": "application/json"}
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="获取辅导员信息失败")
    if request.method == "PUT":
        data = request.get_json()
        sno = data.get("sno")
        name = data.get("name")
        sex = data.get("sex")
        idcard_num = data.get("idcard_num")
        phone_num = data.get("phone")
        qq = data.get("qq")
        email = data.get("email")
        office = data.get("office")
        try:
            instructor = Instructor.query.filter(Instructor.id == instructor_id).first()
            if sno != instructor.sno:
                user = Users.query.filter(Users.username == instructor.sno).first()
                user.username = sno
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
                    # 表示帐号出现了重复值，即账号已注册过
                    current_app.logger.error(e)
                    return jsonify(errno=RET.DBERR, errmsg="修改数据失败")
            try:
                instructor.name = name
                instructor.name = name
                instructor.idcard_num = idcard_num
                instructor.phone_num = phone_num
                instructor.sex = sex
                instructor.qq = qq
                instructor.email = email
                instructor.office = office
                db.session.add(instructor)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                # 表示帐号出现了重复值，即账号已注册过
                current_app.logger.error(e)
                return jsonify(errno=RET.DBERR, errmsg="修改数据失败")
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="未查到数据")
        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="修改辅导员成功")), 200, {"Content-Type": "application/json"}
    if request.method == "DELETE":
        try:
            instructor = Instructor.query.get(instructor_id)
            sno = instructor.sno
            user = Users.query.filter(Users.username == sno).first()
            db.session.delete(instructor)
            db.session.delete(user)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="未查到数据")
        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="删除辅导员成功")), 200, {"Content-Type": "application/json"}


@api.route("/admin/instructors/exceldemo", methods=["GET"])
def instructor_excel_demo():
    filename = '导入模板' + '.xls'
    # 创建一个sheet对象
    wb = xlwt.Workbook(encoding='utf-8')
    sheet = wb.add_sheet('order-sheet')
    # 写入文件标题
    sheet.write(0, 0, '职工号')
    sheet.write(0, 1, '姓名')
    # 写出到IO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['content_type='] = ' application/vnd.ms-excel'
    # 创建一个文件对象
    response.headers['Content-Disposition'] = 'attachment;filename={}'.format(filename.encode().decode('latin-1'))
    return response


@api.route("/admin/instructors/excel", methods=["GET"])
def instructor_get_excel():
    now = datetime.now()
    time = datetime.strftime(now, '%Y%m%d%H%M%S')
    filename = time + '.xls'
    # 创建一个sheet对象
    wb = xlwt.Workbook(encoding='utf-8')
    sheet = wb.add_sheet('order-sheet')
    # 写入文件标题
    sheet.write(0, 0, '职工号')
    sheet.write(0, 1, '姓名')
    sheet.write(0, 2, '性别')
    sheet.write(0, 3, '身份证号')
    sheet.write(0, 4, '手机')
    sheet.write(0, 5, '办公室')
    sheet.write(0, 6, '邮箱')
    sheet.write(0, 7, 'QQ')
    data_row = 1
    for instructor in Instructor.query.all():
        sheet.write(data_row, 0, instructor.to_full_dict()['sno'])
        sheet.write(data_row, 1, instructor.to_full_dict()['name'])
        sheet.write(data_row, 2, instructor.to_full_dict()['sex'])
        sheet.write(data_row, 3, instructor.to_full_dict()['idcard_num'])
        sheet.write(data_row, 4, instructor.to_full_dict()['phone_num'])
        sheet.write(data_row, 5, instructor.to_full_dict()['office'])
        sheet.write(data_row, 6, instructor.to_full_dict()['email'])
        sheet.write(data_row, 7, instructor.to_full_dict()['qq'])
        data_row = data_row + 1
    # 写出到IO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['content_type='] = ' application/vnd.ms-excel'
    # 创建一个文件对象
    response.headers['Content-Disposition'] = 'attachment;filename={}'.format(filename.encode().decode('latin-1'))
    return response


@api.route("/admin/instructors/excel", methods=["POST"])
@jwt_required
@limit_role(roles=[1])
def instructor_excel():
    error_data = []
    excel_raw_data = pd.read_excel(request.files.get('file', ''), header=None)
    # 删除第一行的标题
    excel_raw_data.drop([0, 0], inplace=True)
    sno_col = excel_raw_data.iloc[:, [0]]
    name_col = excel_raw_data.iloc[:, [1]]
    sno_list = sno_col.values.tolist()
    name_list = name_col.values.tolist()
    for i in range(len(name_list)):
        name_list_index = name_list[i]
        sno_list_index = sno_list[i]
        user = Users(username=sno_list_index[0], role=3)
        user.password = str(sno_list_index[0])
        try:
            db.session.add(user)
            db.session.commit()
            try:
                instructor = Instructor(sno=sno_list_index[0], name=name_list_index[0])
                db.session.add(instructor)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                error_data.append(str(sno_list_index[0]) + '添加失败')
        except Exception as e:
            # 数据库操作错误后的回滚
            db.session.rollback()
            # 表示账号出现了重复值，即账号已注册过
            current_app.logger.error(e)
            error_data.append(str(sno_list_index[0]) + '的账号已经存在')
    if error_data:
        return json.dumps(dict(errno=RET.PARAMERR, errmsg="部分信息导入失败", data=error_data)), 200, {
            "Content-Type": "application/json"}
    else:
        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="全部信息导入成功")), 200, {
            "Content-Type": "application/json"}


@api.route('/admin/students/repassword', methods=["POST"])
def student_repassword():
    data = request.get_json()
    id = data.get('id')
    try:
        student = Student.query.get(id)
        user = Users.query.filter(Users.username == student.sno).first()
        user.password = student.sno
    except Exception as e:
        current_app.logger(e)
        return jsonify(errno=RET.DBERR, errmsg="重置密码错误")
    return jsonify(errno=RET.OK, errmsg="重置密码成功")


@api.route('/admin/teachers/repassword', methods=["POST"])
def teacher_repassword():
    data = request.get_json()
    id = data.get('id')
    try:
        teacher = Teacher.query.get(id)
        user = Users.query.filter(Users.username == teacher.sno).first()
        user.password = teacher.sno
    except Exception as e:
        current_app.logger(e)
        return jsonify(errno=RET.DBERR, errmsg="重置密码错误")
    return jsonify(errno=RET.OK, errmsg="重置密码成功")


@api.route('/admin/instructors/repassword', methods=["POST"])
def instructor_repassword():
    data = request.get_json()
    id = data.get('id')
    try:
        instructor = Instructor.query.get(id)
        user = Users.query.filter(Users.username == instructor.sno).first()
        user.password = instructor.sno
    except Exception as e:
        current_app.logger(e)
        return jsonify(errno=RET.DBERR, errmsg="重置密码错误")
    return jsonify(errno=RET.OK, errmsg="重置密码成功")


@api.route("/admin/grades/index", methods=["GET"])
@jwt_required
def get_grade_list():
    grade_li = Grade.query.all()
    grades = []
    for grade in grade_li:
        grades.append(grade.to_basic_dict())
    resp_dict = dict(errno=RET.OK, errmsg="OK", data=grades)
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}


@api.route("/admin/grades", methods=["POST", "DELETE"])
@jwt_required
@limit_role(roles=[1])
def add_delete_grader():
    if request.method == "POST":
        data = request.get_json()
        name = data.get('name')
        try:
            grade = Grade(name=name)
            db.session.add(grade)
            db.session.commit()
        except Exception as e:
            current_app.logger(e)
            return jsonify(errno=RET.DATAEXIST, errmsg="数据已存在")
        return jsonify(errno=RET.OK, errmsg="添加年级成功")
    if request.method == "DELETE":
        data = request.get_json()
        try:
            db.session.query(Grade).filter(Grade.id.in_(data)).delete(synchronize_session=False)
            db.session.commit()
        except Exception as e:
            current_app.logger(e)
            return jsonify(errno=RET.DBERR, errmsg="部分数据删除失败")
        return jsonify(errno=RET.OK, errmsg="批量删除成功")


@api.route("/admin/grades/<int:grade_id>", methods=["GET", "PUT", "DELETE"])
@jwt_required
@limit_role(roles=[1])
def update_delete_grade(grade_id):
    if request.method == "GET":
        try:
            grade = Grade.query.get(grade_id)
            grade = grade.to_full_dict()
            resp_dict = dict(errno=RET.OK, errmsg="OK", data={"grade": grade})
            resp_json = json.dumps(resp_dict)
            return resp_json, 200, {"Content-Type": "application/json"}
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="获取年级信息失败")
    if request.method == "PUT":
        data = request.get_json()
        name = data.get("name")
        try:
            grade = Grade.query.filter(Grade.id == grade_id).first()
            try:
                grade.name = name
                db.session.add(grade)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                # 表示年级出现了重复值，即账号已注册过
                current_app.logger.error(e)
                return jsonify(errno=RET.DATAEXIST, errmsg="修改数据失败")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="修改年级成功")), 200, {"Content-Type": "application/json"}
    if request.method == "DELETE":
        try:
            grade = Grade.query.filter(Grade.id == grade_id).first()
            db.session.delete(grade)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="未查到数据")
        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="删除年级成功")), 200, {"Content-Type": "application/json"}


@api.route("/admin/majors/index", methods=["GET"])
@jwt_required
def get_major_list():
    grade = request.args.get("grade", "")
    # 1.获取参数(页数)
    page = request.args.get('page')
    # 1.获取参数(每页条数)
    page_count = request.args.get('limit')
    # 2.参数据类型转换
    try:
        page_count = int(page_count)
    except Exception as e:
        current_app.logger.error(e)
        page_count = constants.STUDENT_LIST_PAGE_CAPACITY
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    # 过滤条件的参数列表容器
    filter_params = [grade_major_relation.c.grade_id.contains(grade)]

    if grade:
        majors_query = Major.query.join(grade_major_relation,Major.id == grade_major_relation.c.major_id).filter(
            *filter_params)
        count = majors_query.count()
    else:
        majors_query = Major.query
        count = Major.query.count()
    try:
        paginate = majors_query.paginate(page=page, per_page=page_count, error_out=False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="专业信息获取失败")
    # 获取页面数据
    major_li = paginate.items
    data = []
    for major in major_li:
        data.append(major.to_basic_dict())
    # 4.获取分页对象属性,总页数,当前页,对象列表
    total_page = paginate.pages
    resp_dict = dict(errno=RET.OK, errmsg="OK", total_page=total_page, data=data, current_page=page, count=count)
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}


@api.route("/admin/majors", methods=["POST", "DELETE"])
@jwt_required
@limit_role(roles=[1])
def add_delete_major():
    if request.method == "POST":
        data = request.get_json()
        name = data.get('name')
        try:
            major = Major(name=name)
            db.session.add(major)
            db.session.commit()
        except Exception as e:
            current_app.logger(e)
            return jsonify(errno=RET.DATAEXIST, errmsg="数据已存在")
        return jsonify(errno=RET.OK, errmsg="添加专业成功")
    if request.method == "DELETE":
        data = request.get_json()
        try:
            db.session.query(Major).filter(Major.id.in_(data)).delete(synchronize_session=False)
            db.session.commit()
        except Exception as e:
            current_app.logger(e)
            return jsonify(errno=RET.DBERR, errmsg="部分数据删除失败")
        return jsonify(errno=RET.OK, errmsg="批量删除成功")


@api.route("/admin/majors/<int:major_id>", methods=["GET", "PUT", "DELETE"])
@jwt_required
@limit_role(roles=[1])
def update_delete_major(major_id):
    if request.method == "GET":
        try:
            major = Major.query.get(major_id)
            major = major.to_full_dict()
            resp_dict = dict(errno=RET.OK, errmsg="OK", data={"major": major})
            resp_json = json.dumps(resp_dict)
            return resp_json, 200, {"Content-Type": "application/json"}
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="获取年级信息失败")
    if request.method == "PUT":
        data = request.get_json()
        name = data.get("name")
        try:
            major = Major.query.filter(Major.id == major_id).first()
            try:
                major.name = name
                db.session.add(major)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                # 表示年级出现了重复值，即账号已注册过
                current_app.logger.error(e)
                return jsonify(errno=RET.DATAEXIST, errmsg="修改数据失败")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="修改专业成功")), 200, {"Content-Type": "application/json"}
    if request.method == "DELETE":
        try:
            #major = Major.query.filter(Major.id == major_id).first()
            db.session.query(Major).filter(Major.id==major_id).delete(synchronize_session=False)
            #db.session.delete(major)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="未查到数据")
        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="删除专业成功")), 200, {"Content-Type": "application/json"}


@api.route("/admin/classes/index", methods=["GET"])
@jwt_required
def get_class_list():
    grade = request.args.get("grade", "")
    major = request.args.get("major", "")
    classes = request.args.get("class","")
    # 1.获取参数(页数)
    page = request.args.get('page')
    # 1.获取参数(每页条数)
    page_count = request.args.get('limit')
    # 2.参数据类型转换
    try:
        page_count = int(page_count)
    except Exception as e:
        current_app.logger.error(e)
        page_count = constants.STUDENT_LIST_PAGE_CAPACITY
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    # 过滤条件的参数列表容器
    filter_params = [grade_major_relation.c.grade_id.contains(grade), grade_major_relation.c.major_id.contains(major),Classes.class_name.like(("%" + classes + "%"))]
    classes_query = Classes.query.join(grade_major_relation,
                                       Classes.grade_major_id == grade_major_relation.c.id).filter(
        *filter_params)
    count = classes_query.count()
    try:
        paginate = classes_query.paginate(page=page, per_page=page_count, error_out=False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="班级信息获取失败")
    # 获取页面数据
    classes_li = paginate.items
    data = []
    for cls in classes_li:
        data.append(cls.to_full_dict())
    # 4.获取分页对象属性,总页数,当前页,对象列表
    total_page = paginate.pages
    resp_dict = dict(errno=RET.OK, errmsg="OK", total_page=total_page, data=data, current_page=page, count=count)
    resp_json = json.dumps(resp_dict)

    return resp_json, 200, {"Content-Type": "application/json"}


@api.route("/admin/classes", methods=["POST", "DELETE"])
@jwt_required
def add_delete_class():
    if request.method == "POST":
        data = request.get_json()
        class_name = data.get('name')
        class_num = data.get('class_num')
        whether_attendance = data.get('whether_attendance')
        grade = data.get('grade')
        major = data.get('major')
        instructor = data.get('instructor')
        grade = Grade.query.filter(Grade.id == grade).first()
        major = Major.query.filter(Major.id == major).first()
        grade.major_relation.append(major)
        db.session.add(major)
        db.session.commit()


        db1 = pymysql.connect("192.168.1.142", "muji", "mujiwuliankeji", "muji")
        cursor = db1.cursor()
        sql = "select id from grade_major_relation where  grade_id = %s and major_id= %s" % (grade.id, major.id)
        # 查询到班级课程关系的id
        cursor.execute(sql)
        data = cursor.fetchone()
        grade_major_id = data[0]
        classes = Classes(class_name=class_name, class_num=class_num, whether_attendance=whether_attendance,
                          instructor_id=instructor, grade_major_id=grade_major_id)
        db.session.add(classes)
        db.session.commit()
        return jsonify(errno=RET.OK, errmsg="添加专业成功")
    if request.method == "DELETE":
        data = request.get_json()
        try:
            db.session.query(Classes).filter(Classes.id.in_(data)).delete(synchronize_session=False)
            db.session.commit()
        except Exception as e:
            current_app.logger(e)
            return jsonify(errno=RET.DBERR, errmsg="部分数据删除失败")
    return jsonify(errno=RET.OK, errmsg="批量删除成功")

#批量添加班级
@api.route("/admin/classes/more", methods=["POST"])
@jwt_required
def add_class_more():
    data = request.get_json()
    classes = data.get("class")
    grade = data.get('grade')
    major = data.get('major')

    grade = Grade.query.filter(Grade.id == grade).first()
    major = Major.query.filter(Major.id == major).first()
    grade.major_relation.append(major)
    db.session.add(major)
    db.session.commit()
    db1 = pymysql.connect("192.168.1.142", "muji", "mujiwuliankeji", "muji")
    cursor = db1.cursor()
    sql = "select id from grade_major_relation where  grade_id = %s and major_id= %s" % (grade.id, major.id)
    # 查询到班级课程关系的id
    cursor.execute(sql)
    data = cursor.fetchone()
    grade_major_id = data[0]
    for c in classes:
        class_name = data.get('name')
        class_num = data.get('class_num')
        whether_attendance = data.get('whether_attendance')
        instructor = data.get('instructor')
        classes = Classes(class_name=class_name, class_num=class_num, whether_attendance=whether_attendance,
                      instructor_id=instructor, grade_major_id=grade_major_id)
        db.session.add(classes)
        db.session.commit()
    return jsonify(errno=RET.OK, errmsg="添加班级成功")


@api.route("/admin/classes/<int:class_id>", methods=["GET", "PUT", "DELETE"])
@jwt_required
def update_delete_class(class_id):
    if request.method == "GET":
        try:
            classes = Major.query.get(class_id)
            classes = classes.to_full_dict()
            resp_dict = dict(errno=RET.OK, errmsg="OK", data={"classes": classes})
            resp_json = json.dumps(resp_dict)
            return resp_json, 200, {"Content-Type": "application/json"}
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="获取班级信息失败")
    if request.method == "PUT":
        data = request.get_json()
        class_name = data.get('name')
        class_num = data.get('class_num')
        #whether_attendance = data.get('whether_attendance')
        instructor = data.get("instructor")
        grade = data.get('grade')
        major = data.get('major')
        classes = Classes.query.filter(Classes.id == class_id).first()
        db1 = pymysql.connect("192.168.1.142", "muji", "mujiwuliankeji", "muji")
        cursor = db1.cursor()
        sql = "select id from grade_major_relation where  grade_id = %s and major_id= %s" % (grade, major)
        # 查询到班级课程关系的id
        cursor.execute(sql)
        data = cursor.fetchone()
        try:
            grade_major_id = data[0]
        except Exception as e:
            grade = Grade.query.filter(Grade.id == grade).first()
            major = Major.query.filter(Major.id == major).first()
            grade.major_relation.append(major)
            db.session.add(major)
            db.session.commit()
            db1 = pymysql.connect("192.168.1.142", "muji", "mujiwuliankeji", "muji")
            cursor = db1.cursor()
            sql = "select id from grade_major_relation where  grade_id = %s and major_id= %s" % (grade, major)
            # 查询到班级课程关系的id
            cursor.execute(sql)
            data = cursor.fetchone()
            grade_major_id = data[0]
        if grade_major_id:
            classes.class_num = class_num
            classes.class_name = class_name
            #classes.whether_attendance = whether_attendance
            classes.instructor_id = instructor
            classes.grade_major_id = grade_major_id
            db.session.add(classes)
            db.session.commit()
        return json.dumps(dict(errno=RET.OK, errmsg="修改班级成功", data="修改班级成功")), 200, {"Content-Type": "application/json"}
    if request.method == "DELETE":
        try:
            db.session.query(Classes).filter(Classes.id==class_id).delete(synchronize_session=False)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="未查到数据")
        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="删除专业成功")), 200, {"Content-Type": "application/json"}


@api.route('/admin/leaves/history/index', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def stu_leave_history():
    sno = request.args.get("sno", "")
    phone = request.args.get("phone",)
    name = request.args.get("name", "")
    grade = request.args.get("grade", "")
    major = request.args.get("major", "")
    classes = request.args.get("class", "")
    # 1.获取参数(页数)
    page = request.args.get('page')
    # 1.获取参数(每页条数)
    page_count = request.args.get('count')
    # 2.参数据类型转换
    try:
        page_count = int(page_count)
    except Exception as e:
        current_app.logger.error(e)
        page_count = constants.STUDENT_LIST_PAGE_CAPACITY
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    # 过滤条件的参数列表容器

    filter_params = [Student.sno.like("%" + sno + "%"),
                     Student.name.like("%" + name + "%"), grade_major_relation.c.grade_id.contains(grade),
                     grade_major_relation.c.major_id.contains(major), Classes.id.contains(classes)]
    if phone:
        filter_params = [Student.sno.like("%" + sno + "%"), Student.phone.contains(phone),
                         Student.name.like("%" + name + "%"), grade_major_relation.c.grade_id.contains(grade),
                         grade_major_relation.c.major_id.contains(major), Classes.id.contains(classes)]
    # 时间条件
    conflict_orders = None
    leave_query = Leave.query.join(Student, Leave.student_id == Student.id).join(Classes,Student.class_id == Classes.id)\
        .join(grade_major_relation, Classes.grade_major_id == grade_major_relation.c.id).filter(Leave.status.in_([0,1]))\
        .filter(*filter_params).order_by(Student.sno.desc())
    print(leave_query)
    # 3.分页查询
    try:
        paginate = leave_query.paginate(page=page, per_page=page_count, error_out=False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="请假信息获取失败")
    count = leave_query.count()
    # 获取页面数据
    leave_li = paginate.items
    leaves = []
    for lea in leave_li:
        leaves.append(lea.get_leave_stu())
    # 4.获取分页对象属性,总页数,当前页,对象列表
    total_page = paginate.pages
    resp_dict = dict(errno=RET.OK, errmsg="OK",total_page=total_page, data=leaves,current_page=page,count=count)
    resp_json = json.dumps(resp_dict)

    return resp_json, 200, {"Content-Type": "application/json"}

@api.route('/admin/leaves/permit',methods=["GET"])
@jwt_required
@limit_role(roles=[1,3])
def admin_permit_attendance():
    sno = request.args.get("sno", "")
    phone = request.args.get("phone",)
    name = request.args.get("name", "")
    grade = request.args.get("grade", "")
    major = request.args.get("major", "")
    classes = request.args.get("class", "")
    # 1.获取参数(页数)
    page = request.args.get('page')
    # 1.获取参数(每页条数)
    page_count = request.args.get('count')
    # 2.参数据类型转换
    try:
        page_count = int(page_count)
    except Exception as e:
        current_app.logger.error(e)
        page_count = constants.STUDENT_LIST_PAGE_CAPACITY
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    # 过滤条件的参数列表容器
    filter_params = [Student.sno.like("%" + sno + "%"),
                     Student.name.like("%" + name + "%"), grade_major_relation.c.grade_id.contains(grade),
                     grade_major_relation.c.major_id.contains(major), Classes.id.contains(classes)]
    if phone:
        filter_params = [Student.sno.like("%" + sno + "%"),Student.phone.contains(phone),
                         Student.name.like("%" + name + "%"), grade_major_relation.c.grade_id.contains(grade),
                         grade_major_relation.c.major_id.contains(major), Classes.id.contains(classes)]
    # 时间条件
    conflict_orders = None

    student_query = Student.query.join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                                     Classes.grade_major_id == grade_major_relation.c.id).filter(
        *filter_params).order_by(Student.sno.desc())
    count = student_query.count()
    # 3.分页查询
    try:
        paginate = student_query.paginate(page=page, per_page=page_count, error_out=False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="请假信息获取失败")
    # 获取页面数据
    stu_li = paginate.items
    student = []
    for stu in stu_li:
        student.append(stu.to_leave_status_dict())
    # 4.获取分页对象属性,总页数,当前页,对象列表
    total_page = paginate.pages
    resp_dict = dict(errno=RET.OK, errmsg="OK", total_page=total_page, data=student, current_page=page, count=count)
    resp_json = json.dumps(resp_dict)

    return resp_json, 200, {"Content-Type": "application/json"}

@api.route('/admin/yes/permit/<int:student_id>',methods=["POST"])
@jwt_required
def admin_yes_permit(student_id):
    username = get_jwt_identity()
    name = Department_admin.query.filter(Department_admin.username==username).first().name
    now = datetime.now()
    data = request.get_json()
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    reason = data.get("reason")
    leave = Leave(start_time=start_time,end_time=end_time,permit_person=name,reason=reason,student_id=student_id,status=1,submit_time=now)
    db.session.add(leave)
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="提交请假成功")



#图表昨日个专业考勤率
@api.route('/admin/analyze/chart/yesterday/attendance')
@jwt_required
def yesterday_attendance():
    grade = request.args.get('grade')
    if grade:
        grade_id= grade
    else:
        grade_id = Grade.query.first().id
    cls_now = datetime.now()
    dor_now = date.today()
    majors = Major.query.join(grade_major_relation,Major.id == grade_major_relation.c.major_id)\
        .join(Grade,grade_major_relation.c.grade_id==Grade.id).filter(Grade.id==grade_id)
    data,classroom,dormitory = [],[],[]
    for mj in majors:
        cls_attendance = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
        .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,grade_major_relation.c.id == Classes.grade_major_id) \
        .join(Major, grade_major_relation.c.major_id == Major.id).join(Classroom_attendance,Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
        .filter(Stu_classroom_atten_res.status == 1, Major.id == mj.id).join(Grade,grade_major_relation.c.grade_id==Grade.id).filter(Grade.id==grade_id,Classroom_attendance.end_time.__ge__(cls_now-timedelta(days=1)), Classroom_attendance.end_time.__le__(cls_now)).count()
        dor_attendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,grade_major_relation.c.id == Classes.grade_major_id) \
            .join(Major, grade_major_relation.c.major_id == Major.id).join(Grade,grade_major_relation.c.grade_id==Grade.id).filter(DormitoryAttendance.status == 1,Major.id == mj.id,Grade.id==grade_id, DormitoryAttendance.attendance_date.__ge__(dor_now-timedelta(days=1)),DormitoryAttendance.attendance_date.__le__(dor_now)).count()
        cls_dict = {"major_id": mj.id, "major_name": mj.name, "major_cls_attendance_count": cls_attendance}
        dor_dict = {"major_id": mj.id, "major_name": mj.name, "major_dor_attendance_count": dor_attendance}
        classroom.append(cls_dict)
        dormitory.append(dor_dict)
    resp_dict = dict(errno=RET.OK, errmsg="OK", data=[{"cls_attendance_rate": classroom},{"dor_attendance_rate":dormitory}])
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}


#图表7天专业考勤率
@api.route('/admin/analyze/chart/sevenday/major')
@jwt_required
def sevenday_attendance():
    grade = request.args.get('grade')
    if grade:
        grade_id = grade
    else:
        grade_id = Grade.query.first().id
    cls_now = datetime.now()
    dor_now = date.today()
    majors = Major.query.join(grade_major_relation, Major.id == grade_major_relation.c.major_id)\
        .join(Grade,grade_major_relation.c.grade_id==Grade.id).filter(Grade.id == grade_id)
    classroom, dormitory = [], []
    for mj in majors:
        cls_attendance = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
        .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,grade_major_relation.c.id == Classes.grade_major_id) \
        .join(Major, grade_major_relation.c.major_id == Major.id).join(Classroom_attendance,Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
        .filter(Stu_classroom_atten_res.status == 1, Major.id == mj.id).filter(Classroom_attendance.end_time.__ge__(cls_now-timedelta(weeks=1)), Classroom_attendance.end_time.__le__(cls_now)).count()
        dor_attendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,grade_major_relation.c.id == Classes.grade_major_id) \
            .join(Major, grade_major_relation.c.major_id == Major.id).filter(DormitoryAttendance.status == 1,Major.id == mj.id, DormitoryAttendance.attendance_date.__ge__(dor_now-timedelta(weeks=1)),DormitoryAttendance.attendance_date.__le__(dor_now)).count()
        cls_dict = {"major_id": mj.id, "major_name": mj.name, "major_cls_attendance_count": cls_attendance}
        dor_dict = {"major_id": mj.id, "major_name": mj.name, "major_dor_attendance_count": dor_attendance}
        classroom.append(cls_dict)
        dormitory.append(dor_dict)
    resp_dict = dict(errno=RET.OK, errmsg="OK", data=[{"cls_attendance_rate": classroom},{"dor_attendance_rate":dormitory}])
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}


#图表7日考勤率
@api.route('/admin/analyze/chart/seven/attendance')
def seven_chart():
    grade = request.args.get('grade')
    if grade:
        grade_id = grade
    else:
        grade_id = Grade.query.first().id
    sevendate = []
    days = []
    day=[]
    now1 = date.today()
    rate1 = []
    rate2 = []
    for i in range(1,8):
        #day = now1-timedelta(days=i)
        sevendate.append((now1-timedelta(days=8-i)).strftime("%Y-%m-%d"))
        days.append((now1 - timedelta(days=8-i)).strftime("%m-%d"))
        day.append(now1-timedelta(days=8-i))
    for x in sevendate:
        cls_count = Stu_classroom_atten_res.query.join(Student,Stu_classroom_atten_res.student_id==Student.id)\
            .join(Classes,Student.class_id==Classes.id).join(grade_major_relation,Classes.grade_major_id==grade_major_relation.c.id)\
            .join(Grade,grade_major_relation.c.grade_id==Grade.id).filter(Grade.id==grade_id,Stu_classroom_atten_res.time.__ge__(datetime.strptime((x+" 00:00:00"),"%Y-%m-%d %H:%M:%S")),Stu_classroom_atten_res.time.__le__(datetime.strptime((x+" 23:59:59"),"%Y-%m-%d %H:%M:%S"))).count()
        cls_attendance = Stu_classroom_atten_res.query.join(Student,Stu_classroom_atten_res.student_id==Student.id)\
            .join(Classes,Student.class_id==Classes.id).join(grade_major_relation,Classes.grade_major_id==grade_major_relation.c.id)\
            .join(Grade,grade_major_relation.c.grade_id==Grade.id).filter(Grade.id==grade_id,Stu_classroom_atten_res.status == 1,Stu_classroom_atten_res.time.__ge__(datetime.strptime(x + (" 00:00:00"),"%Y-%m-%d %H:%M:%S")),Stu_classroom_atten_res.time.__le__(datetime.strptime(x + (" 23:59:59"),"%Y-%m-%d %H:%M:%S"))).count()
        try:
            rate = "%0.2f" % ((cls_attendance/cls_count)*100)
        except:
            rate = "%0.2f" % 0
        rate1.append(rate)
    for x in day:
        dor_count = DormitoryAttendance.query.filter(
            DormitoryAttendance.attendance_date == x,DormitoryAttendance.grade_id==grade_id ).count()
        dor_attendance = DormitoryAttendance.query.filter(DormitoryAttendance.grade_id==grade_id,DormitoryAttendance.attendance_date == x, DormitoryAttendance.status == 1).count()
        try:
            rate = "%0.2f" % ((dor_attendance/dor_count)*100)
        except Exception as e:
            rate = "%0.2f" %  0
        rate2.append(rate)
    resp_dict = dict(errno=RET.OK, errmsg="OK", data=[{"cls_rate":rate1,"dor_rate":rate2,"days":days}])
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}


#图表专业教室考勤率
@api.route('/admin/analyze/chart/major/classroom', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def mj_alz_clsroom():
    day = request.args.get("day", "")
    now = datetime.now()
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    else:
        filter_params = [(now - timedelta(weeks=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    major = Major.query.all()
    data= []
    for mj in major:
        major_unattendance = Stu_classroom_atten_res.query.join(Student,
                                                                Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                grade_major_relation.c.id == Classes.grade_major_id) \
            .join(Major, grade_major_relation.c.major_id == Major.id).join(Classroom_attendance,
                                                                           Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Stu_classroom_atten_res.status == 0, Major.id == mj.id, *filter_params).count()
        major_attendance = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                grade_major_relation.c.id == Classes.grade_major_id) \
            .join(Major, grade_major_relation.c.major_id == Major.id).join(Classroom_attendance,
                                                                           Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Stu_classroom_atten_res.status == 1, Major.id == mj.id, *filter_params).count()
        major_leave = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                grade_major_relation.c.id == Classes.grade_major_id) \
            .join(Major, grade_major_relation.c.major_id == Major.id).join(Classroom_attendance,
                                                                           Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Stu_classroom_atten_res.status.in_([2, 3]), Major.id == mj.id, *filter_params).count()
        try:
            major_attendance_rate = "%.2f%%" % (major_attendance / (major_leave + major_attendance + major_unattendance) * 100)
        except Exception as e:
            current_app.logger.error(e)
            major_attendance_rate = 0
        data_dict = {"major_id": mj.id, "major_name": mj.name, "major_attendance_rate": major_attendance_rate}
        data.append(data_dict)
    resp_dict = dict(errno=RET.OK, errmsg="OK", data={"statistics_rate": data})
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}

#图表年级教室考勤率
@api.route('/admin/analyze/chart/grade/classroom', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def cs_alz_clsroom():
    day = request.args.get("day", "")
    now = datetime.now()
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    else:
        filter_params = [(now - timedelta(weeks=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    grade = Grade.query.all()
    data = []
    for gd in grade:
        grade_unattendance = Stu_classroom_atten_res.query.join(Student,
                                                                Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                grade_major_relation.c.id == Classes.grade_major_id) \
            .join(Grade, grade_major_relation.c.grade_id == Grade.id).join(Classroom_attendance,
                                                                           Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Stu_classroom_atten_res.status == 0, Grade.id == gd.id, *filter_params).count()
        grade_attendance = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                grade_major_relation.c.id == Classes.grade_major_id) \
            .join(Grade, grade_major_relation.c.grade_id == Grade.id).join(Classroom_attendance,
                                                                           Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Stu_classroom_atten_res.status == 1, Grade.id == gd.id, *filter_params).count()
        grade_leave = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                grade_major_relation.c.id == Classes.grade_major_id) \
            .join(Grade, grade_major_relation.c.grade_id == Grade.id).join(Classroom_attendance,
                                                                           Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Stu_classroom_atten_res.status.in_([2, 3]), Grade.id == gd.id, *filter_params).count()
        try:
            grade_attendance_rate = "%.4f" % (grade_attendance / (grade_leave + grade_attendance + grade_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            grade_attendance_rate = 0
        data_dict = {"major_id": gd.id, "major_name": gd.name, "major_attendance_rate": grade_attendance_rate}
        data.append(data_dict)
    resp_dict = dict(errno=RET.OK, errmsg="OK", data={"statistics_rate": data})
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}

#图表某年级某专业的班级考勤率
@api.route('/admin/analyze/chart/grade/<int:grade_id>/major/<int:major_id>/classroom', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def cls_alz_clsroom(grade_id,major_id):
    day = request.args.get("day", "")
    now = datetime.now()
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    elif day == 7:
        filter_params = [(now - timedelta(weeks=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    elif day == 30:
        filter_params = [(now - timedelta(days=30)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    else:
        filter_params = [(now - timedelta(days=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    classes = Classes.query.join(grade_major_relation, Classes.grade_major_id == grade_major_relation.c.id) \
        .join(Major,grade_major_relation.c.major_id==Major.id).join(Grade,grade_major_relation.c.grade_id==Grade.id)\
        .filter(Major.id == major_id,Grade.id == grade_id)
    data = []
    for cls in classes:
        class_unattendance = Stu_classroom_atten_res.query.join(Student,
                                                                Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classes, Student.class_id == cls.id).join(Classroom_attendance,
                                                            Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Stu_classroom_atten_res.status == 0, *filter_params).count()
        class_attendance = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classes, Student.class_id == cls.id).join(Classroom_attendance,
                                                            Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Stu_classroom_atten_res.status == 1).count()
        class_leave = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classes, Student.class_id == cls.id).join(Classroom_attendance,
                                                            Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Stu_classroom_atten_res.status.in_([2, 3])).count()
        try:
            class_attendance_rate = "%.4f" % (class_attendance / (class_leave + class_attendance + class_unattendance) *100)
        except Exception as e:
            current_app.logger.error(e)
            class_attendance_rate = 0
        data_dict = {"class_id": cls.id, "class_name": cls.class_name, "class_attendance_rate": class_attendance_rate}
        data.append(data_dict)
    resp_dict = dict(errno=RET.OK, errmsg="OK", data= data)
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}

#图表某年级的专业考勤率
@api.route('/admin/analyze/chart/major/<int:grade_id>/classroom',methods=['GET'])
@jwt_required
@limit_role(roles=[1])

def gd_mj_cls(grade_id):
    day = request.args.get("day", "")
    now = datetime.now()
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    elif day == 7:
        filter_params = [(now - timedelta(weeks=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    elif day == 30:
        filter_params = [(now - timedelta(days=30)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    else:
        filter_params = [(now - timedelta(days=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    majors_query = Major.query.join(grade_major_relation, Major.id == grade_major_relation.c.major_id).join(Grade,grade_major_relation.c.grade_id==Grade.id)\
    .filter(Grade.id==grade_id)
    data = []
    # 获取页面数据
    for mj in majors_query:
        classes = Classes.query.join(grade_major_relation,Classes.grade_major_id==grade_major_relation.c.id)\
            .join(Major,grade_major_relation.c.major_id==Major.id).join(Grade,grade_major_relation.c.grade_id==Grade.id)\
            .filter(Major.id==mj.id,Grade.id==grade_id)
        unattendance_count = 0
        attendance_count = 0
        leave_count = 0
        for cls in classes:
            class_unattendance = Stu_classroom_atten_res.query.join(Student,
                                                                    Stu_classroom_atten_res.student_id == Student.id) \
                .join(Classes, Student.class_id == cls.id).join(Classroom_attendance,
                                                                Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
                .filter(Stu_classroom_atten_res.status == 0, *filter_params).count()
            class_attendance = Stu_classroom_atten_res.query.join(Student,
                                                                  Stu_classroom_atten_res.student_id == Student.id) \
                .join(Classes, Student.class_id == cls.id).join(Classroom_attendance,
                                                                Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
                .filter(Stu_classroom_atten_res.status == 1).count()
            class_leave = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
                .join(Classes, Student.class_id == cls.id).join(Classroom_attendance,
                                                                Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
                .filter(Stu_classroom_atten_res.status.in_([2, 3])).count()
            unattendance_count += class_unattendance
            attendance_count += class_attendance
            leave_count += class_leave
        try:
            major_attendance_rate = "%.4f" % (
                        attendance_count / (leave_count + attendance_count + unattendance_count)*100 )
        except Exception as e:
            current_app.logger.error(e)
            major_attendance_rate = 0
        data_dict = {"major_id": mj.id, "major_name": mj.name, "major_attendance_rate": major_attendance_rate}
        data.append(data_dict)
    resp_dict = dict(errno=RET.OK, errmsg="OK", data=data)
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}
    pass


#图表专业考勤率
@api.route('/admin/analyze/chart/major/dormitory', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def mj_alz_dmy():
    day = request.args.get("day", "")
    now = date.today()
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    else:
        filter_params = [(now - timedelta(weeks=1)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    major = Major.query.all()
    data = []
    for mj in major:
        print(mj.id)
        major_unattendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                grade_major_relation.c.id == Classes.grade_major_id) \
            .join(Major, grade_major_relation.c.major_id == Major.id).filter(DormitoryAttendance.status == 0,
                                                                             Major.id == mj.id, *filter_params).count()
        major_attendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                grade_major_relation.c.id == Classes.grade_major_id) \
            .join(Major, grade_major_relation.c.major_id == Major.id).filter(DormitoryAttendance.status == 1,
                                                                             Major.id == mj.id, *filter_params).count()
        major_leave = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                grade_major_relation.c.id == Classes.grade_major_id) \
            .join(Major, grade_major_relation.c.major_id == Major.id).filter(DormitoryAttendance.status.in_([2, 3]),
                                                                             Major.id == mj.id, *filter_params).count()
        print(major_leave, major_unattendance, major_attendance)
        try:
            major_attendance_rate = "%.2f%%" % (major_attendance / (major_leave + major_attendance + major_unattendance) * 100)
        except Exception as e:
            current_app.logger.error(e)
            major_attendance_rate = 0
        data_dict = {"major_id": mj.id, "major_name": mj.name, "major_attendance_rate": major_attendance_rate}
        data.append(data_dict)
    resp_dict = dict(errno=RET.OK, errmsg="OK", data={"statistics_rate": data})
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}

#图表年级宿舍考勤率
@api.route('/admin/analyze/chart/grade/dormitory', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def cs_alz_dmy():
    day = request.args.get("day", "")
    now = date.today()
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    else:
        filter_params = [(now - timedelta(weeks=1)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    grade = Grade.query.all()
    data = []
    for gd in grade:
        grade_unattendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                grade_major_relation.c.id == Classes.grade_major_id) \
            .join(Grade, grade_major_relation.c.major_id == Grade.id).filter(DormitoryAttendance.status == 0,
                                                                             Grade.id == gd.id, *filter_params).count()
        grade_attendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                grade_major_relation.c.id == Classes.grade_major_id) \
            .join(Grade, grade_major_relation.c.major_id == Grade.id).filter(DormitoryAttendance.status == 1,
                                                                             Grade.id == gd.id, *filter_params).count()
        grade_leave = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                grade_major_relation.c.id == Classes.grade_major_id) \
            .join(Grade, grade_major_relation.c.major_id == Grade.id).filter(DormitoryAttendance.status.in_([2, 3]),
                                                                             Grade.id == gd.id, *filter_params).count()
        try:
            grade_attendance_rate = "%.2f%%" % (grade_attendance / (grade_leave + grade_attendance + grade_unattendance) * 100)
        except Exception as e:
            current_app.logger.error(e)
            grade_attendance_rate = 0
        data_dict = {"grade_id": gd.id, "grade_name": gd.name, "grade_attendance_rate": grade_attendance_rate}
        data.append(data_dict)
    resp_dict = dict(errno=RET.OK, errmsg="OK", data={"statistics_rate": data})
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}

#图标某年纪宿舍考勤率
@api.route('/admin/analyze/chart/grade/<int:grade_id>/dormitory', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def cls_alz_dmy(grade_id):
    day = request.args.get("day", "")
    now = date.today()
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    else:
        filter_params = [(now - timedelta(weeks=1)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    classes = Classes.query.join(grade_major_relation, Classes.grade_major_id == grade_major_relation.c.id) \
        .filter(grade_major_relation.c.grade_id == grade_id)
    data = []
    for cls in classes:
        class_unattendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).filter(DormitoryAttendance.status == 0, Classes.id == cls.id,
                                                                  *filter_params).count()
        class_attendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).filter(DormitoryAttendance.status == 1, Classes.id == cls.id,
                                                                  *filter_params).count()
        class_leave = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).filter(DormitoryAttendance.status.in_([2, 3]),
                                                                  Classes.id == cls.id, *filter_params).count()
        try:
            class_attendance_rate = "%.2f%%" % (class_attendance / (class_leave + class_attendance + class_unattendance) *100)
        except Exception as e:
            current_app.logger.error(e)
            class_attendance_rate = 0
        data_dict = {"class_id": cls.id, "class_name": cls.class_name, "class_attendance_rate": class_attendance_rate}
        data.append(data_dict)
    resp_dict = dict(errno=RET.OK, errmsg="OK", data={"statistics_rate": data})
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}

#表格学生教室考勤率
@api.route('/admin/analyze/form/student/classroom', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def stu_form_clsrom():
    day = request.args.get("day", "")
    sno = request.args.get("sno","")
    now = datetime.now()
    # 1.获取参数(页数)
    page = request.args.get('page')
    # 1.获取参数(每页条数)
    page_count = request.args.get('limit')
    # 2.参数据类型转换
    try:
        page_count = int(page_count)
    except Exception as e:
        current_app.logger.error(e)
        page_count = constants.STUDENT_LIST_PAGE_CAPACITY
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    elif day==7:
        filter_params = [(now - timedelta(weeks=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    elif day==30:
        filter_params = [(now - timedelta(days=30)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    else:
        filter_params = [(now - timedelta(days=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    data = []
    students = Student.query.filter(Student.sno.like("%"+sno+"%"))
    count = students.count()
    try:
        paginate = students.paginate(page=page, per_page=page_count, error_out=False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="学生信息获取失败")
    # 获取页面数据
    student_li = paginate.items
    for stu in student_li:
        stu_unattendance = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classroom_attendance, Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Student.id == stu.id, Stu_classroom_atten_res.status == 0, *filter_params).count()
        stu_attendance = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classroom_attendance, Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Student.id == stu.id, Stu_classroom_atten_res.status == 1, *filter_params).count()
        stu_leave = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classroom_attendance, Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Student.id == stu.id, Stu_classroom_atten_res.status.in_([2, 3]), *filter_params).count()
        classes = Classes.query.get(stu.class_id).to_full_dict()
        try:
            attendance_rate = "%.2f%%" % (stu_attendance / (stu_unattendance + stu_attendance + stu_leave) *100)
        except Exception as e:
            current_app.logger.error(e)
            attendance_rate = 0
        try:
            leave_rate = "%.2f%%" % (stu_leave / (stu_unattendance + stu_attendance + stu_leave) *100)
        except Exception as e:
            current_app.logger.error(e)
            leave_rate = 0
        try:
            unattendance_rate = "%.2f%%" % (stu_unattendance / (stu_unattendance + stu_attendance + stu_leave) *100)
        except Exception as e:
            current_app.logger.error(e)
            unattendance_rate = 0

        data_dict = {"stu_id": stu.id, "name": stu.name, "sno":stu.sno, "phone": stu.phone, "classes": classes,
                     "attendance_count": stu_unattendance + stu_attendance + stu_leave,
                     "unattendance_rate": unattendance_rate, "attendance_rate": attendance_rate,
                     "leave_rate": leave_rate,}
        data.append(data_dict)
    total_page = paginate.pages
    resp_dict = dict(errno=RET.OK, errmsg="OK", data=data,total_page=total_page, current_page=page, count=count)
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}

#表格班级教室考勤率
@api.route('/admin/analyze/form/classes/classroom', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def cls_form_clsrom():
    day = request.args.get("day", "")
    name = request.args.get('name',"")
    # 1.获取参数(页数)
    page = request.args.get('page')
    # 1.获取参数(每页条数)
    page_count = request.args.get('limit')
    # 2.参数据类型转换
    try:
        page_count = int(page_count)
    except Exception as e:
        current_app.logger.error(e)
        page_count = constants.STUDENT_LIST_PAGE_CAPACITY
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    now = datetime.now()
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    elif day == 7:
        filter_params = [(now - timedelta(weeks=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    elif day == 30:
        filter_params = [(now - timedelta(days=30)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    else:
        filter_params = [(now - timedelta(days=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    data = []
    classes = Classes.query.filter(Classes.class_name.like("%" + name + "%"))
    try:
        paginate = classes.paginate(page=page, per_page=page_count, error_out=False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="班级信息获取失败")
    # 获取页面数据
    count = classes.count()
    classes_li = paginate.items
    for cls in classes_li:
        class_unattendance = Stu_classroom_atten_res.query.join(Student,
                                                                Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classes, Student.class_id == cls.id).join(Classroom_attendance,
                                                            Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Stu_classroom_atten_res.status == 0, *filter_params).count()
        class_attendance = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classes, Student.class_id == cls.id).join(Classroom_attendance,
                                                            Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Stu_classroom_atten_res.status == 1).count()
        class_leave = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classes, Student.class_id == cls.id).join(Classroom_attendance,
                                                            Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Stu_classroom_atten_res.status.in_([2, 3])).count()
        count = Classroom_attendance.query.join(course_class_relation,Classroom_attendance.course_class_id==course_class_relation.c.id)\
            .join(Classes,course_class_relation.c.class_id==Classes.id).filter(Classes.id==cls.id).count()
        try:
            class_attendance_rate = "%.2f%%" % (class_attendance / (class_leave + class_attendance + class_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            class_attendance_rate = 0
        try:
            class_unattendance_rate = "%.2f%%" % (
                    class_unattendance / (class_leave + class_attendance + class_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            class_unattendance_rate = 0
        try:
            class_leave_rate = "%.2f%%" % (class_leave / (class_leave + class_attendance + class_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            class_leave_rate = 0
        data_dict = {"class": cls.to_full_dict(), "class_attendance": count,
                     "class_attendance_rate": class_attendance_rate
            , "class_unattendance_rate": class_unattendance_rate, "class_leave_rate": class_leave_rate}
        data.append(data_dict)
    total_page = paginate.pages
    resp_dict = dict(errno=RET.OK, errmsg="OK", data=data,total_page=total_page,current_page=page,count=classes.count())
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}

#表格某学生的教室考勤率
@api.route('/admin/analyze/form/student/<int:student_id>/classroom', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def stu_form_clsroom_info(student_id):
    attendance = Stu_classroom_atten_res.query.filter(Stu_classroom_atten_res.student_id == student_id)
    data = []
    for ad in attendance:
        data.append(ad.to_dict())
    resp_dict = dict(errno=RET.OK, errmsg="OK", data={"statistics_rate": data})
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}

#表格某班级的教室考勤率
@api.route('/admin/analyze/form/classes/<int:classes_id>/classroom', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def cls_form_clsroom_info(classes_id):
    cls_attandence = Classroom_attendance.query.join(course_class_relation,
                                                     Classroom_attendance.course_class_id == course_class_relation.c.id) \
        .join(Classes, course_class_relation.c.class_id == Classes.id).filter(Classes.id == classes_id)
    data = []
    for cad in cls_attandence:
        cad_unattendance = Stu_classroom_atten_res.query.join(Classroom_attendance,
                                                              Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Classroom_attendance.id == cad.id, Stu_classroom_atten_res.status == 0).count()
        cad_attendance = Stu_classroom_atten_res.query.join(Classroom_attendance,
                                                            Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Classroom_attendance.id == cad.id, Stu_classroom_atten_res.status == 1).count()
        cad_leave = Stu_classroom_atten_res.query.join(Classroom_attendance,
                                                       Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Classroom_attendance.id == cad.id, Stu_classroom_atten_res.status.in_([2, 3])).count()
        try:
            cad_attendance_rate = "%.2f%%" % (cad_attendance / (cad_leave + cad_attendance + cad_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            cad_attendance_rate = 0
        try:
            cad_unattendance_rate = "%.2f%%" % (cad_unattendance / (cad_leave + cad_attendance + cad_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            cad_unattendance_rate = 0
        try:
            cad_leave_rate = "%.2f%%" % (cad_leave / (cad_leave + cad_attendance + cad_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            cad_leave_rate = 0
        course = Course.query.join(course_class_relation, Course.id == course_class_relation.c.course_id) \
            .join(Classroom_attendance, Classroom_attendance.course_class_id == course_class_relation.c.id).filter(
            Classroom_attendance.id == cad.id).first()
        data_dict = {"course": course.to_basic_dict(), "cad_attendance_rate": cad_attendance_rate,
                     "cad_unattendance_rate": cad_unattendance_rate, "cad_leave_rate": cad_leave_rate}
        data.append(data_dict)
    resp_dict = dict(errno=RET.OK, errmsg="OK", data={"statistics_rate": data})
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}

#表格学生宿舍考勤率
@api.route('/admin/analyze/form/student/dormitory', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def stu_form_dmy():
    day = request.args.get("day", "")
    sno = request.args.get("sno","")
    now = date.today()
    # 1.获取参数(页数)
    page = request.args.get('page')
    # 1.获取参数(每页条数)
    page_count = request.args.get('limit')
    # 2.参数据类型转换
    try:
        page_count = int(page_count)
    except Exception as e:
        current_app.logger.error(e)
        page_count = constants.STUDENT_LIST_PAGE_CAPACITY
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now ]
    if day == 30:
        filter_params = [(now - timedelta(days=30)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    if day == 7:
        filter_params = [(now - timedelta(weeks=1)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    else:
        filter_params = [(now - timedelta(days=1)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    data = []
    students = Student.query.filter(Student.sno.like("%" + sno + "%"))
    count = students.count()
    try:
        paginate = students.paginate(page=page, per_page=page_count, error_out=False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="学生信息获取失败")
    student_li = paginate.items
    for stu in student_li:
        stu_unattendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id). \
            filter(DormitoryAttendance.status == 0, Student.id == stu.id).filter(*filter_params).count()
        stu_attendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id). \
            filter(DormitoryAttendance.status == 1, Student.id == stu.id).filter(*filter_params).count()
        stu_leave = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id). \
            filter(DormitoryAttendance.status.in_([2, 3]), Student.id == stu.id).filter(*filter_params).count()
        classes = Classes.query.get(stu.class_id).to_full_dict()
        try:
            attendance_rate = "%.2f%%" % (stu_attendance / (stu_unattendance + stu_attendance + stu_leave)*100)
        except Exception as e:
            current_app.logger.error(e)
            attendance_rate = 0
        try:
            leave_rate = "%.2f%%" % (stu_leave / (stu_unattendance + stu_attendance + stu_leave)*100)
        except Exception as e:
            current_app.logger.error(e)
            leave_rate = 0
        try:
            unattendance_rate = "%.2f%%" % (stu_unattendance / (stu_unattendance + stu_attendance + stu_leave)*100)
        except Exception as e:
            current_app.logger.error(e)
            unattendance_rate = 0
        data_dict = {"stu_id": stu.id, "name": stu.name,"sno":stu.sno, "phone": stu.phone, "classes": classes,
                     "attendance_count": stu_attendance + stu_unattendance + stu_leave,
                     "unattendance_rate": unattendance_rate, "attendance_rate": attendance_rate,
                     "leave_rate": leave_rate}
        data.append(data_dict)
    total_page = paginate.pages
    resp_dict = dict(errno=RET.OK, errmsg="OK", data=data,total_page=total_page, current_page=page, count=count)
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}

#表格班级宿舍考勤率
@api.route('/admin/analyze/form/classes/dormitory', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def cls_form_dmy():
    day = request.args.get("day", "")
    name = request.args.get("name","")
    now = date.today()
    # 1.获取参数(页数)
    page = request.args.get('page')
    # 1.获取参数(每页条数)
    page_count = request.args.get('limit')
    # 2.参数据类型转换
    try:
        page_count = int(page_count)
    except Exception as e:
        current_app.logger.error(e)
        page_count = constants.STUDENT_LIST_PAGE_CAPACITY
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    if day == 30:
        filter_params = [(now - timedelta(days=30)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    if day == 7:
        filter_params = [(now - timedelta(weeks=1)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    else:
        filter_params = [(now - timedelta(days=1)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    data = []
    classes = Classes.query.filter(Classes.class_name.like("%" + name + "%"))
    try:
        paginate = classes.paginate(page=page, per_page=page_count, error_out=False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="班级信息获取失败")
        # 获取页面数据
    count = classes.count()
    classes_li = paginate.items
    for cls in classes_li:
        class_unattendance = DormitoryAttendance.query.join(Student,DormitoryAttendance.student_id == Student.id) \
            .filter(*filter_params).join(Classes, Student.class_id == Classes.id).filter(DormitoryAttendance.status == 0,
                                                                                         Classes.id == cls.id,*filter_params).count()
        class_attendance =  DormitoryAttendance.query.join(Student,DormitoryAttendance.student_id == Student.id) \
            .filter(*filter_params).join(Classes, Student.class_id == Classes.id).filter(DormitoryAttendance.status == 1,
                                                                                         *filter_params,Classes.id == cls.id).count()
        class_leave = DormitoryAttendance.query.join(Student,DormitoryAttendance.student_id == Student.id) \
            .filter(*filter_params).join(Classes, Student.class_id == Classes.id).filter(DormitoryAttendance.status.in_([2,3]),
                                                                                         *filter_params,Classes.id == cls.id).count()
        count = DormitoryAttendance.query.filter(DormitoryAttendance.class_id==cls.id).count()
        try:
            class_attendance_rate = "%.2f%%" % (class_attendance / (class_leave + class_attendance + class_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            class_attendance_rate = 0
        try:
            class_unattendance_rate = "%.2f%%" % (
                    class_unattendance / (class_leave + class_attendance + class_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            class_unattendance_rate = 0
        try:
            class_leave_rate = "%.2f%%" % (class_leave / (class_leave + class_attendance + class_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            class_leave_rate = 0
        data_dict = {"class": cls.to_full_dict(), "class_attendance": count,
                     "class_attendance_rate": class_attendance_rate
            , "class_unattendance_rate": class_unattendance_rate, "class_leave_rate": class_leave_rate}
        data.append(data_dict)
    total_page = paginate.pages
    resp_dict = dict(errno=RET.OK, errmsg="OK", data=data,total_page=total_page,current_page=page,count=classes.count())
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}

#表格专业教室考勤率
@api.route('/admin/analyze/form/majors/classroom', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def mj_form_clsrom():
    day = request.args.get("day", "")
    name = request.args.get("name", "")
    now = datetime.now()
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    elif day==7:
        filter_params = [(now - timedelta(weeks=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    elif day==30:
        filter_params = [(now - timedelta(days=30)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    else:
        filter_params = [(now - timedelta(days=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    data = []
    major = Major.query.filter(Major.name.like("%" + name + "%"))
    for mj in major:
        major_unattendance = Stu_classroom_atten_res.query.join(Student,Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,Classes.grade_major_id==grade_major_relation.c.id)\
        .join(Major,grade_major_relation.c.major_id==mj.id).join(Classroom_attendance,Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Stu_classroom_atten_res.status == 0, *filter_params).count()
        major_attendance =  Stu_classroom_atten_res.query.join(Student,Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,Classes.grade_major_id==grade_major_relation.c.id)\
        .join(Major,grade_major_relation.c.major_id==mj.id).join(Classroom_attendance,Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Stu_classroom_atten_res.status == 1, *filter_params).count()
        major_leave =  Stu_classroom_atten_res.query.join(Student,Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,Classes.grade_major_id==grade_major_relation.c.id)\
        .join(Major,grade_major_relation.c.major_id==mj.id).join(Classroom_attendance,Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Stu_classroom_atten_res.status.in_([2,3]), *filter_params).count()
        count = Classroom_attendance.query.join(course_class_relation,Classroom_attendance.course_class_id==course_class_relation.c.id)\
            .join(Classes,course_class_relation.c.class_id==Classes.id).join(grade_major_relation,Classes.grade_major_id==grade_major_relation.c.id)\
            .join(Major,grade_major_relation.c.major_id==Major.id).filter(Major.id==mj.id).count()
        try:
            major_attendance_rate = "%.2f%%" % (major_attendance / (major_leave + major_attendance + major_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            major_attendance_rate = 0
        try:
            major_unattendance_rate = "%.2f%%" % (
                    major_unattendance / (major_leave + major_attendance + major_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            major_unattendance_rate = 0
        try:
            major_leave_rate = "%.2f%%" % (major_leave / (major_leave + major_attendance + major_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            major_leave_rate = 0
        data_dict = {"major": mj.to_basic_dict(), "major_attendance": count,
                     "major_attendance_rate": major_attendance_rate
            , "major_unattendance_rate": major_unattendance_rate, "major_leave_rate": major_leave_rate}
        data.append(data_dict)
    resp_dict = dict(errno=RET.OK, errmsg="OK", data=data)
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}

#表格专业宿舍考勤率
@api.route('/admin/analyze/form/majors/dormitory', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def mj_form_dmy():
    day = request.args.get("day", "")
    name = request.args.get("name","")
    now = date.today()
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    if day == 30:
        filter_params = [(now - timedelta(days=30)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    if day == 7:
        filter_params = [(now - timedelta(weeks=1)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    else:
        filter_params = [(now - timedelta(days=1)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    data = []
    major = Major.query.filter(Major.name.like("%" + name + "%"))
    for mj in major:
        major_unattendance = DormitoryAttendance.query.join(Student,DormitoryAttendance.student_id == Student.id) \
            .filter(*filter_params).join(Classes, Student.class_id == Classes.id).join(grade_major_relation,Classes.id==grade_major_relation.c.id)\
            .join(Major,grade_major_relation.c.major_id==Major.id).filter(DormitoryAttendance.status == 0,Major.id == mj.id,*filter_params).count()
        major_attendance =  DormitoryAttendance.query.join(Student,DormitoryAttendance.student_id == Student.id) \
            .filter(*filter_params).join(Classes, Student.class_id == Classes.id).join(grade_major_relation,Classes.id==grade_major_relation.c.id)\
            .join(Major,grade_major_relation.c.major_id==Major.id).filter(DormitoryAttendance.status == 1,*filter_params,Major.id == mj.id).count()
        major_leave = DormitoryAttendance.query.join(Student,DormitoryAttendance.student_id == Student.id) \
            .filter(*filter_params).join(Classes, Student.class_id == Classes.id).join(grade_major_relation,Classes.id==grade_major_relation.c.id)\
            .join(Major,grade_major_relation.c.major_id==Major.id).filter(DormitoryAttendance.status.in_([2,3]),*filter_params,Major.id == mj.id).count()
        count = DormitoryAttendance.query.filter(DormitoryAttendance.major_id==mj.id).count()
        try:
            major_attendance_rate = "%.2f%%" % (major_attendance / (major_leave + major_attendance + major_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            major_attendance_rate = 0
        try:
            major_unattendance_rate = "%.2f%%" % (
                    major_unattendance / (major_leave + major_attendance + major_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            major_unattendance_rate = 0
        try:
            major_leave_rate = "%.2f%%" % (major_leave / (major_leave + major_attendance + major_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            major_leave_rate = 0
        data_dict = {"major": mj.to_basic_dict(), "major_attendance": count,
                     "major_attendance_rate": major_attendance_rate
            , "major_unattendance_rate": major_unattendance_rate, "major_leave_rate": major_leave_rate}
        data.append(data_dict)
    resp_dict = dict(errno=RET.OK, errmsg="OK", data=data)
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}


#比哦啊个年级教师考勤率
@api.route('/admin/analyze/form/grades/classroom', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def grade_form_clsrom():
    day = request.args.get("day", "")
    name = request.args.get("name","")
    now = datetime.now()
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    elif day==7:
        filter_params = [(now - timedelta(weeks=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    elif day==30:
        filter_params = [(now - timedelta(days=30)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    else:
        filter_params = [(now - timedelta(days=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    data = []
    grade = Grade.query.filter(Grade.name.like("%" + name + "%"))
    for gd in grade:
        grade_unattendance = Stu_classroom_atten_res.query.join(Student,
                                                                Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                Classes.grade_major_id == grade_major_relation.c.id) \
            .join(Grade, grade_major_relation.c.grade_id == Grade.id).join(Classroom_attendance,
                                                                        Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Stu_classroom_atten_res.status == 0,Grade.id==gd.id, *filter_params).count()
        grade_attendance = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                Classes.grade_major_id == grade_major_relation.c.id) \
            .join(Grade, grade_major_relation.c.grade_id == Grade.id).join(Classroom_attendance,
                                                                        Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Stu_classroom_atten_res.status == 1,Grade.id==gd.id, *filter_params).count()
        grade_leave = Stu_classroom_atten_res.query.join(Student, Stu_classroom_atten_res.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                Classes.grade_major_id == grade_major_relation.c.id) \
            .join(Grade, grade_major_relation.c.grade_id == Grade.id).join(Classroom_attendance,
                                                                        Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .filter(Stu_classroom_atten_res.status.in_([2,3]), Grade.id==gd.id,*filter_params).count()
        count = Classroom_attendance.query.join(course_class_relation,
                                                Classroom_attendance.course_class_id == course_class_relation.c.id) \
            .join(Classes, course_class_relation.c.class_id == Classes.id).join(grade_major_relation,
                                                                                Classes.grade_major_id == grade_major_relation.c.id) \
            .join(Grade, grade_major_relation.c.grade_id == Grade.id).filter(Grade.id == gd.id).count()
        try:
            grade_attendance_rate = "%.2f%%" % (
                        grade_attendance / (grade_leave + grade_attendance + grade_unattendance) * 100)
        except Exception as e:
            current_app.logger.error(e)
            grade_attendance_rate = 0
        try:
            grade_unattendance_rate = "%.2f%%" % (
                    grade_unattendance / (grade_leave + grade_attendance + grade_unattendance) * 100)
        except Exception as e:
            current_app.logger.error(e)
            grade_unattendance_rate = 0
        try:
            grade_leave_rate = "%.2f%%" % (grade_leave / (grade_leave + grade_attendance + grade_unattendance) * 100)
        except Exception as e:
            current_app.logger.error(e)
            grade_leave_rate = 0
        data_dict = {"grade": gd.to_basic_dict(), "grade_attendance": count,
                     "grade_attendance_rate": grade_attendance_rate
            , "grade_unattendance_rate": grade_unattendance_rate, "grade_leave_rate": grade_leave_rate}
        data.append(data_dict)
    resp_dict = dict(errno=RET.OK, errmsg="OK", data=data)
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}


#表格年级宿舍考勤率
@api.route('/admin/analyze/form/grades/dormitory',methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def grade_form_dmy():
    day = request.args.get("day", "")
    name = request.args.get("name","")
    now = date.today()
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    if day == 30:
        filter_params = [(now - timedelta(days=30)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    if day == 7:
        filter_params = [(now - timedelta(weeks=1)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    else:
        filter_params = [(now - timedelta(days=1)) <= DormitoryAttendance.attendance_date,
                         DormitoryAttendance.attendance_date <= now]
    data = []
    grade = Grade.query.filter(Grade.name.like("%" + name + "%"))
    for gd in grade:
        grade_unattendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                                       Classes.id == grade_major_relation.c.id) \
            .join(Grade, grade_major_relation.c.grade_id == Grade.id).filter(DormitoryAttendance.status == 0,
                                                                             Grade.id == gd.id, *filter_params).count()
        grade_attendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                                       Classes.id == grade_major_relation.c.id) \
            .join(Grade, grade_major_relation.c.grade_id == Grade.id).filter(DormitoryAttendance.status == 1,
                                                                             *filter_params, Grade.id == gd.id).count()
        grade_leave = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(grade_major_relation,
                                                                                       Classes.id == grade_major_relation.c.id) \
            .join(Grade, grade_major_relation.c.grade_id == Grade.id).filter(DormitoryAttendance.status.in_([2, 3]),
                                                                             *filter_params, Grade.id == gd.id).count()
        count = DormitoryAttendance.query.filter(DormitoryAttendance.grade_id == gd.id).count()
        try:
            grade_attendance_rate = "%.2f%%" % (
                        grade_attendance / (grade_leave + grade_attendance + grade_unattendance) * 100)
        except Exception as e:
            current_app.logger.error(e)
            grade_attendance_rate = 0
        try:
            grade_unattendance_rate = "%.2f%%" % (
                    grade_unattendance / (grade_leave + grade_attendance + grade_unattendance) * 100)
        except Exception as e:
            current_app.logger.error(e)
            grade_unattendance_rate = 0
        try:
            grade_leave_rate = "%.2f%%" % (grade_leave / (grade_leave + grade_attendance + grade_unattendance) * 100)
        except Exception as e:
            current_app.logger.error(e)
            grade_leave_rate = 0
        data_dict = {"grade": gd.to_basic_dict(), "grade_attendance": count,
                     "grade_attendance_rate": grade_attendance_rate
            , "grade_unattendance_rate": grade_unattendance_rate, "grade_leave_rate": grade_leave_rate}
        data.append(data_dict)
    resp_dict = dict(errno=RET.OK, errmsg="OK", data=data)
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}

#表格教师教师考勤率
@api.route('/admin/analyze/form/teacher/classroom', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def tea_form_clsroom():
    day = request.args.get("day", "")
    sno = request.args.get("sno","")
    now = datetime.now()
    # 1.获取参数(页数)
    page = request.args.get('page')
    # 1.获取参数(每页条数)
    page_count = request.args.get('limit')
    # 2.参数据类型转换
    try:
        page_count = int(page_count)
    except Exception as e:
        current_app.logger.error(e)
        page_count = constants.STUDENT_LIST_PAGE_CAPACITY
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= Classroom_attendance.end_time,
                             Classroom_attendance.end_time <= now]
    elif day == 7:
        filter_params = [(now - timedelta(weeks=1)) <= Classroom_attendance.end_time,
                             Classroom_attendance.end_time <= now]
    elif day == 30:
        filter_params = [(now - timedelta(days=30)) <= Classroom_attendance.end_time,
                             Classroom_attendance.end_time <= now]
    else:
        filter_params = [(now - timedelta(days=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    teacher = Teacher.query.filter(Teacher.sno.like("%" + sno + "%"))
    data = []
    try:
        paginate = teacher.paginate(page=page, per_page=page_count, error_out=False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="班级信息获取失败")
        # 获取页面数据
    count = teacher.count()
    teacher_li = paginate.items
    for tea in teacher_li:
        tea_unattendance = Stu_classroom_atten_res.query.join(Classroom_attendance,
                                                              Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .join(course_class_relation, Classroom_attendance.course_class_id == course_class_relation.c.id) \
            .join(Course, course_class_relation.c.course_id == Course.id).join(Teacher, Course.teacher_id == Teacher.id) \
            .filter(Stu_classroom_atten_res.status == 0, Teacher.id == tea.id,*filter_params).count()
        tea_attendance = Stu_classroom_atten_res.query.join(Classroom_attendance,
                                                            Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .join(course_class_relation, Classroom_attendance.course_class_id == course_class_relation.c.id) \
            .join(Course, course_class_relation.c.course_id == Course.id).join(Teacher, Course.teacher_id == Teacher.id) \
            .filter(Stu_classroom_atten_res.status == 1, Teacher.id == tea.id,*filter_params).count()
        tea_leave = Stu_classroom_atten_res.query.join(Classroom_attendance,
                                                       Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .join(course_class_relation, Classroom_attendance.course_class_id == course_class_relation.c.id) \
            .join(Course, course_class_relation.c.course_id == Course.id).join(Teacher, Course.teacher_id == Teacher.id) \
            .filter(Stu_classroom_atten_res.status.in_([2, 3]), Teacher.id == tea.id,*filter_params).count()
        attendance_count = Classroom_attendance.query.join(course_class_relation,
                                                           Classroom_attendance.course_class_id == course_class_relation.c.id) \
            .join(Course, course_class_relation.c.course_id == Course.id).join(Teacher, Course.teacher_id == Teacher.id) \
            .filter(Teacher.id == tea.id).count()
        try:
            tea_attendance_rate = "%.2f%%" % (tea_attendance / (tea_leave + tea_attendance + tea_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            tea_attendance_rate = 0
        try:
            tea_unattendance_rate = "%.2f%%" % (tea_unattendance / (tea_leave + tea_attendance + tea_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            tea_unattendance_rate = 0
        try:
            tea_leave_rate = "%.2f%%" % (tea_leave / (tea_leave + tea_attendance + tea_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            tea_leave_rate = 0
        data_dict = {"teacher": tea.to_basic_dict(), "tea_attendance": attendance_count,
                     "tea_attendance_rate": tea_attendance_rate, "tea_unattendance_rate": tea_unattendance_rate,
                     "tea_leave_rate": tea_leave_rate}
        data.append(data_dict)
    total_page = paginate.pages
    resp_dict = dict(errno=RET.OK, errmsg="OK", data=data,total_page=total_page,current_page = page,count=count)
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}


#表格课程考勤率
@api.route('/admin/analyze/form/course/classroom', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def cs_form_clsroom():
    day = request.args.get("day", "")
    name = request.args.get("name","")
    now = datetime.now()
    # 1.获取参数(页数)
    page = request.args.get('page')
    # 1.获取参数(每页条数)
    page_count = request.args.get('limit')
    # 2.参数据类型转换
    try:
        page_count = int(page_count)
    except Exception as e:
        current_app.logger.error(e)
        page_count = constants.STUDENT_LIST_PAGE_CAPACITY
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    elif day==7:
        filter_params = [(now - timedelta(weeks=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    elif day==30:
        filter_params = [(now - timedelta(days=30)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    else:
        filter_params = [(now - timedelta(days=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    course = Course.query.filter(Course.name.like("%" + name + "%"))
    data = []
    try:
        paginate = course.paginate(page=page, per_page=page_count, error_out=False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="班级信息获取失败")
        # 获取页面数据
    count = course.count()
    course_li = paginate.items
    for cs in course_li:
        cs_unattendance = Stu_classroom_atten_res.query.join(Classroom_attendance,
                                                              Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .join(course_class_relation, Classroom_attendance.course_class_id == course_class_relation.c.id) \
            .join(Course, course_class_relation.c.course_id == Course.id).filter(Stu_classroom_atten_res.status == 0, Course.id == cs.id,*filter_params).count()
        cs_attendance = Stu_classroom_atten_res.query.join(Classroom_attendance,
                                                            Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .join(course_class_relation, Classroom_attendance.course_class_id == course_class_relation.c.id) \
            .join(Course, course_class_relation.c.course_id == Course.id).filter(Stu_classroom_atten_res.status == 1, Course.id == cs.id,*filter_params).count()
        cs_leave = Stu_classroom_atten_res.query.join(Classroom_attendance,
                                                       Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .join(course_class_relation, Classroom_attendance.course_class_id == course_class_relation.c.id) \
            .join(Course, course_class_relation.c.course_id == Course.id).filter(Stu_classroom_atten_res.status.in_([2, 3]), Course.id == cs.id,*filter_params).count()
        attendance_count = Classroom_attendance.query.join(course_class_relation,
                                                           Classroom_attendance.course_class_id == course_class_relation.c.id) \
            .join(Course, course_class_relation.c.course_id == Course.id).filter(Course.id == cs.id).count()
        try:
            cs_attendance_rate = "%.2f%%" % (cs_attendance / (cs_leave + cs_attendance + cs_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            cs_attendance_rate = 0
        try:
            cs_unattendance_rate = "%.2f%%" % (cs_unattendance / (cs_leave + cs_attendance + cs_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            cs_unattendance_rate = 0
        try:
            cs_leave_rate = "%.2f%%" % (cs_leave / (cs_leave + cs_attendance + cs_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            cs_leave_rate = 0
        data_dict = {"course": cs.to_full_dict(), "cs_attendance": attendance_count,
                     "cs_attendance_rate": cs_attendance_rate, "cs_unattendance_rate": cs_unattendance_rate,
                     "cs_leave_rate": cs_leave_rate}
        data.append(data_dict)
    total_page = paginate.pages
    resp_dict = dict(errno=RET.OK, errmsg="OK", data=data,total_page=total_page,current_page=page,count=count)
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}


#图标最低考勤率缺勤率
@api.route('/admin/analyze/charts/teacher/classroom', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def tea_es_clsroom():
    day = request.args.get("day", "")
    now = datetime.now()
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= Classroom_attendance.end_time,
                             Classroom_attendance.end_time <= now]
    elif day == 7:
        filter_params = [(now - timedelta(weeks=1)) <= Classroom_attendance.end_time,
                             Classroom_attendance.end_time <= now]
    elif day == 30:
        filter_params = [(now - timedelta(days=30)) <= Classroom_attendance.end_time,
                             Classroom_attendance.end_time <= now]
    else:
        filter_params = [(now - timedelta(days=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    teacher = Teacher.query.all()
    data = []
    for tea in teacher:
        tea_unattendance = Stu_classroom_atten_res.query.join(Classroom_attendance,
                                                              Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .join(course_class_relation, Classroom_attendance.course_class_id == course_class_relation.c.id) \
            .join(Course, course_class_relation.c.course_id == Course.id).join(Teacher, Course.teacher_id == Teacher.id) \
            .filter(Stu_classroom_atten_res.status == 0, Teacher.id == tea.id,*filter_params).count()
        tea_attendance = Stu_classroom_atten_res.query.join(Classroom_attendance,
                                                            Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .join(course_class_relation, Classroom_attendance.course_class_id == course_class_relation.c.id) \
            .join(Course, course_class_relation.c.course_id == Course.id).join(Teacher, Course.teacher_id == Teacher.id) \
            .filter(Stu_classroom_atten_res.status == 1, Teacher.id == tea.id,*filter_params).count()
        tea_leave = Stu_classroom_atten_res.query.join(Classroom_attendance,
                                                       Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .join(course_class_relation, Classroom_attendance.course_class_id == course_class_relation.c.id) \
            .join(Course, course_class_relation.c.course_id == Course.id).join(Teacher, Course.teacher_id == Teacher.id) \
            .filter(Stu_classroom_atten_res.status.in_([2, 3]), Teacher.id == tea.id,*filter_params).count()
        attendance_count = Classroom_attendance.query.join(course_class_relation,
                                                           Classroom_attendance.course_class_id == course_class_relation.c.id) \
            .join(Course, course_class_relation.c.course_id == Course.id).join(Teacher, Course.teacher_id == Teacher.id) \
            .filter(Teacher.id == tea.id).count()
        try:
            tea_attendance_rate = "%.4f" % (tea_attendance / (tea_leave + tea_attendance + tea_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            tea_attendance_rate = 0
        try:
            tea_unattendance_rate = "%.4f" % (tea_unattendance / (tea_leave + tea_attendance + tea_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            tea_unattendance_rate = 0
        try:
            tea_leave_rate = "%.4f" % (tea_leave / (tea_leave + tea_attendance + tea_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            tea_leave_rate = 0
        data_dict = {"name":tea.name,"tea_attendance_rate": tea_attendance_rate, "tea_unattendance_rate": tea_unattendance_rate,
                     "tea_leave_rate":tea_leave_rate}
        data.append(data_dict)
    resp_dict = dict(errno=RET.OK, errmsg="OK", data=data)
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}


#图标课程最低考勤率
@api.route('/admin/analyze/charts/course/classroom', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def cs_es_clsroom():
    day = request.args.get("day", "")
    now = datetime.now()
    if day:
        day = int(day)
    if day == 180:
        filter_params = [(now - timedelta(weeks=20)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    elif day==7:
        filter_params = [(now - timedelta(weeks=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    elif day==30:
        filter_params = [(now - timedelta(days=30)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    else:
        filter_params = [(now - timedelta(days=1)) <= Classroom_attendance.end_time,
                         Classroom_attendance.end_time <= now]
    course = Course.query.all()
    data = []
    for cs in course:
        cs_unattendance = Stu_classroom_atten_res.query.join(Classroom_attendance,
                                                              Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .join(course_class_relation, Classroom_attendance.course_class_id == course_class_relation.c.id) \
            .join(Course, course_class_relation.c.course_id == Course.id).filter(Stu_classroom_atten_res.status == 0, Course.id == cs.id,*filter_params).count()
        cs_attendance = Stu_classroom_atten_res.query.join(Classroom_attendance,
                                                            Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .join(course_class_relation, Classroom_attendance.course_class_id == course_class_relation.c.id) \
            .join(Course, course_class_relation.c.course_id == Course.id).filter(Stu_classroom_atten_res.status == 1, Course.id == cs.id,*filter_params).count()
        cs_leave = Stu_classroom_atten_res.query.join(Classroom_attendance,
                                                       Stu_classroom_atten_res.classroom_attendance_id == Classroom_attendance.id) \
            .join(course_class_relation, Classroom_attendance.course_class_id == course_class_relation.c.id) \
            .join(Course, course_class_relation.c.course_id == Course.id).filter(Stu_classroom_atten_res.status.in_([2, 3]), Course.id == cs.id,*filter_params).count()
        attendance_count = Classroom_attendance.query.join(course_class_relation,
                                                           Classroom_attendance.course_class_id == course_class_relation.c.id) \
            .join(Course, course_class_relation.c.course_id == Course.id).filter(Course.id == cs.id).count()
        try:
            cs_attendance_rate = "%.4f" % (cs_attendance / (cs_leave + cs_attendance + cs_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            cs_attendance_rate = 0
        try:
            cs_unattendance_rate = "%.4f" % (cs_unattendance / (cs_leave + cs_attendance + cs_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            cs_unattendance_rate = 0
        try:
            cs_leave_rate = "%.4f" % (cs_leave / (cs_leave + cs_attendance + cs_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            cs_leave_rate = 0
        data_dict = {"name":cs.name,"cs_attendance_rate": cs_attendance_rate, "cs_unattendance_rate": cs_unattendance_rate,}
        data.append(data_dict)
    resp_dict = dict(errno=RET.OK, errmsg="OK", data=data)
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}

@api.route('/admin/analyze/form/teacher/dormitory', methods=["GET"])
@jwt_required
@limit_role(roles=[1])
def tea_form_dmy():
    teacher = Teacher.query.all()
    data = []
    for tea in teacher:
        tea_unattendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(course_class_relation,
                                                                Classes.id == course_class_relation.c.class_id) \
            .join(Course, course_class_relation.c.course_id == Course.id).join(Teacher, Course.teacher_id == Teacher.id) \
            .filter(DormitoryAttendance.status == 0, Teacher.id == tea.id).count()
        tea_attendance = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(course_class_relation,
                                                                Classes.id == course_class_relation.c.class_id) \
            .join(Course, course_class_relation.c.course_id == Course.id).join(Teacher, Course.teacher_id == Teacher.id) \
            .filter(DormitoryAttendance.status == 1, Teacher.id == tea.id).count()
        tea_leave = DormitoryAttendance.query.join(Student, DormitoryAttendance.student_id == Student.id) \
            .join(Classes, Student.class_id == Classes.id).join(course_class_relation,
                                                                Classes.id == course_class_relation.c.class_id) \
            .join(Course, course_class_relation.c.course_id == Course.id).join(Teacher, Course.teacher_id == Teacher.id) \
            .filter(DormitoryAttendance.status.in_([1, 2]), Teacher.id == tea.id).count()
        try:
            tea_attendance_rate = "%.2f%%" % (tea_attendance / (tea_leave + tea_attendance + tea_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            tea_attendance_rate = 0
        try:
            tea_unattendance_rate = "%.2f%%" % (tea_attendance / (tea_leave + tea_attendance + tea_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            tea_unattendance_rate = 0
        try:
            tea_leave_rate = "%.2f%%" % (tea_attendance / (tea_leave + tea_attendance + tea_unattendance)*100)
        except Exception as e:
            current_app.logger.error(e)
            tea_leave_rate = 0
        data_dict = {"teacher": tea.to_basic_dict(),
                     "tea_attendance_rate": tea_attendance_rate, "tea_unattendance_rate": tea_unattendance_rate,
                     "tea_leave_rate": tea_leave_rate}
        data.append(data_dict)
    resp_dict = dict(errno=RET.OK, errmsg="OK", data={"statistics_rate": data})
    resp_json = json.dumps(resp_dict)
    return resp_json, 200, {"Content-Type": "application/json"}


@api.route('/admin/setting', methods=['GET', 'POST'])
@jwt_required
@limit_role(roles=[1])
def admin_setting():
    if request.method == "GET":
        setting = Department.query.first()
        resp_dict = dict(errno=RET.OK, errmsg="OK", data=setting.to_basic_dict())
        resp_json = json.dumps(resp_dict)
        return resp_json, 200, {"Content-Type": "application/json"}
    if request.method == "POST":
        data = request.get_json()
        print(data)
        id = data.get("id")
        instructor_permit_leave_time = data.get("instructor_permit_leave_time", "")
        instructor_manage_time = data.get("instructor_manage_time", "")
        dormitory_start_time = data.get("dormitory_start_time", "")
        dormitory_end_time = data.get("dormitory_end_time", "")
        pause_start_time = data.get("pause_start_time", "")
        pause_time = data.get("pause_time", "")
        modify_stu_status = data.get("modify_stu_status", "")
        setting = Department.query.filter(Department.id == id).first()
        setting.instructor_permit_leave_time = instructor_permit_leave_time
        setting.instructor_manage_time = instructor_manage_time
        setting.dormitory_start_time = dormitory_start_time
        setting.dormitory_end_time = dormitory_end_time
        setting.pause_start_time = pause_start_time
        setting.pause_time = pause_time
        setting.modify_stu_status = modify_stu_status
        db.session.add(setting)
        db.session.commit()
        nocheck = data.get('uncheck_val',"")
        yescheck = data.get("check_val","")
        for i in nocheck:
            gd = Grade.query.filter(Grade.id==i).first()
            gd.whether_attendance = 0
            db.session.add(gd)
            db.session.commit()
            classes = Classes.query.join(grade_major_relation,Classes.grade_major_id==grade_major_relation.c.id).join(Grade,grade_major_relation.c.grade_id==Grade.id).filter(Grade.id==i)
            for cls in classes:
                cls.whether_attendance =0
                db.session.add(cls)
                db.session.commit()
        for i in yescheck:
            gd = Grade.query.filter(Grade.id==i).first()
            gd.whether_attendance = 1
            db.session.add(gd)
            db.session.commit()
            classes = Classes.query.join(grade_major_relation,
                                         Classes.grade_major_id == grade_major_relation.c.id).join(Grade,
                                                                                                   grade_major_relation.c.grade_id == Grade.id).filter(
                Grade.id == i)
            for cls in classes:
                cls.whether_attendance = 1
                db.session.add(cls)
                db.session.commit()
        # os.system('python F:/attendance/task.py')
        return json.dumps(dict(errno=RET.OK, errmsg="OK", data="修改设置成功")), 200, {"Content-Type": "application/json"}



@api.route("/admin/gmc", methods=["POST"])
def whether_attendance():
    data = request.get_json()
    print("\n++++++++++++++++++++\n")
    print(data)
    print("\n---------------------\n")
    return json.dumps(dict(errno=RET.OK, errmsg="OK", data="设置考勤成功")), 200, {"Content-Type": "application/json"}
# @api.route('/admin/setatthendance', methods=['POST'])
# def set_attendance():
#     data = request.get_json()
#     for id in data:
#         major = Major.query.filter(Major.id==id)
#         major.whether_attendace ==



@api.route("/admin/repassword",methods=["POST"])
@jwt_required
@limit_role(roles=[1])
def admin_repassword():
    data = request.get_json()
    old_password = data.get("old_password")
    new_password = data.get("new_password")
    username = get_jwt_identity()
    if not all([old_password,new_password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不完整")
    user = Users.query.filter(username==username).first()
    data = UserObject(id=user.id, username=username, role=user.role)
    if user.check_password(old_password):
        user.password = new_password
        expires = timedelta(hours=0.5)
        access_token = create_access_token(identity=data, expires_delta=expires)
        return jsonify(errno=RET.OK, status=RET.OK, errmsg="密码修改成功", access_token=access_token)
    else:
        return jsonify(errno=RET.DATAERR, status=RET.OK, errmsg="原密码错误")