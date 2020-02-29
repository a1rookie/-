import random
import re

from sqlalchemy import or_

from attendance import constants
from . import api
from flask import jsonify, request, current_app, session, render_template
from attendance.utils.email import send_mail
from attendance import db, redis_store
from attendance.models import Users, Teacher, Course, Classes, Student, School_roll_type, course_class_relation, Leave
from attendance.models import grade_major_relation, Major, Grade, Equipment_info, Classroom_attendance, Stu_classroom_atten_res
from attendance.utils.response_code import RET
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt_claims
import datetime
import pymysql


# 查看图片
@api.route('/teacher/face/image', methods=['GET'])
@jwt_required
def image():
    username = get_jwt_identity()
    image = Teacher.query.filter_by(sno=username).first()
    name = image.name
    img_path = constants.IMAGE_URL + str(image.head_picture)
    print(img_path)

    return jsonify(errno=RET.OK, image=img_path, name=name)


# 修改图片
@api.route('/teacher/info/change/picture', methods=['POST'])
@jwt_required
def change_picture():
    username = get_jwt_identity()
    head_picture = request.files.get("file")
    try:
        # 获取老师信息
        data = Teacher.query.filter_by(sno=username).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="获取信息失败")

    # 上传图片
    try:
        head_picture.save(r'attendance/static/upload/teacher/{}.jpg'.format(data.sno))
        head_picture = (r'/static/upload/teacher/{}.jpg'.format(data.sno))
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="照片传输异常")
    # 6.判断图片是否上传成功
    if not head_picture:
        return jsonify(errno=RET.DATAERR, errmsg="图片上传失败")

    data.head_picture = head_picture
    # 6.保存到数据库
    try:
        db.session.add(data)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="编辑信息失败")
    # 8.返回响应
    return jsonify(errno=RET.OK, errmsg="编辑成功")


# 修改老师信息
@api.route('/teacher/info/change', methods=['POST'])
@jwt_required
def change_teacher():
    username = get_jwt_identity()
    # 获取参数
    phone_num = request.json.get("phone")
    qq = request.json.get("qq")
    email = request.json.get("email")
    office = request.json.get("office")

    try:
        # 获取老师信息
        data = Teacher.query.filter_by(sno=username).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="获取信息失败")

    # 7.设置编辑信息，到对象列表
    data.phone_num = phone_num
    data.qq = qq
    data.email = email
    data.office = office

    # 6.保存到数据库
    try:
        db.session.add(data)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="编辑信息失败")
    # 8.返回响应
    return jsonify(errno=RET.OK, errmsg="编辑成功")


# 查看老师信息
@api.route('/teacher/info', methods=['GET'])
@jwt_required
def teacher_see_teacher():
    try:
        username = get_jwt_identity()
        # 获取老师信息
        data = Teacher.query.filter_by(sno=username).first()
        # 信息转化为字典
        data = Teacher.to_teacher_basic_dict(data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="信息获取失败")

    return jsonify(errno=RET.OK, errmsg="信息获取成功", data=data)


# 补全老师信息
@api.route('/teacher/info/modify', methods=['GET', 'POST'])
@jwt_required
def teacher_update_teacher():
    if request.method == 'GET':
        username = get_jwt_identity()
        try:
            # 获取老师信息
            data = Teacher.query.filter_by(sno=username).first()
            data = Teacher.to_basic_dict(data)
            print(data)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="获取信息失败")
        return jsonify(errno=RET.OK, errmsg="信息获取成功", data=data)
    username = get_jwt_identity()
    # 获取参数
    phone_num = request.form.get("phone")
    qq = request.form.get("qq")
    email = request.form.get("email")
    head_picture = request.files.get("file")
    office = request.form.get("office")
    sex = request.form.get("sex")
    idcard_num = request.form.get("idcard_num")

    try:
        # 获取老师信息
        data = Teacher.query.filter_by(sno=username).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="获取信息失败")

    # 上传图片
    try:
        head_picture.save(r'attendance/static/upload/teacher/{}.jpg'.format(data.sno))
        head_picture = (r'/static/upload/teacher/{}.jpg'.format(data.sno))
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="照片传输异常")
    # 6.判断图片是否上传成功
    if not head_picture:
        return jsonify(errno=RET.DATAERR, errmsg="图片上传失败")

    # 7.设置编辑信息，到对象列表
    data.phone_num = phone_num
    data.qq = qq
    data.email = email
    data.head_picture = head_picture
    data.office = office
    data.sex =sex
    data.idcard_num = idcard_num

    # 6.保存到数据库
    try:
        db.session.add(data)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="编辑信息失败")
    # 8.返回响应
    return jsonify(errno=RET.OK, errmsg="编辑成功")


# 查看学生信息
@api.route('/teacher/info/student', methods=['POST'])
@jwt_required
def teacher_search_student():
    try:
        keywords = request.json.get("keyword")
        if keywords is not None:
            # filter_params = [Student.sno.like("%" + keywords + "%"), Student.name.like("%" + keywords + "%")]
            students = Student.query.filter(or_(Student.sno.like("%" + keywords + "%"), Student.name.like("%" + keywords + "%"))).all()
            student_list = [student.to_teacher_basic_dict() for student in students]
            return jsonify(errno=RET.OK, errmsg="信息获取成功", data=student_list)

        student_id = request.json.get("student_id")
        # 获取学生信息
        data = Student.query.filter_by(sno=student_id).first()
        # 信息转化为字典
        data = Student.to_teacher_basic_dict(data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="信息获取失败")

    return jsonify(errno=RET.OK, errmsg="信息获取成功", data=data)


# 获取所有的班级 查看学生信息
@api.route('/teacher/search/student', methods=['GET', 'POST'])
@jwt_required
def search_student():
    if request.method == "GET":
        try:
            username = get_jwt_identity()
            # 获取老师信息
            teacher = Teacher.query.filter_by(sno=username).first()
            # 由老师id联合查询所有的班级
            classes = Classes.query.join(course_class_relation, Classes.id == course_class_relation.c.class_id).\
                join(Course, course_class_relation.c.course_id == Course.id).filter(Course.teacher_id == teacher.id)
            # 获取所有的班级
            data = [class_name.to_teacher_basic_dict() for class_name in classes]

        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="信息获取失败")

        return jsonify(errno=RET.OK, errmsg="信息获取成功", data=data)

    # 得到班级的id
    classes = request.json.get("classes")
    try:
        # 查询班级
        student_nums = Student.query.filter(Student.class_id == classes)
        # 返回学生信息
        data = [student_num.tea_get_stu() for student_num in student_nums]
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="信息获取失败")
    return jsonify(errno=RET.OK, errmsg="信息获取成功", data=data)


# 课程设置 查看课程名
@api.route('/teacher/course/see', methods=['GET'])
@jwt_required
def see_course():
    if request.method == "GET":
        username = get_jwt_identity()
        # id = get_jwt_claims["id"]
        if not id:
            return jsonify(errno=RET.PARAMERR, errmsg="参数不全")
        try:
            # 获取当前的老师信息
            teacher = Teacher.query.filter_by(sno=username).first()
            # 获取这个老师教的所有课程
            courses = Course.query.filter(Course.teacher_id == teacher.id).all()
            # 遍历所有的课程
            data = [course_name.to_teacher_base_dict() for course_name in courses]
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="信息获取失败")
        return jsonify(errno=RET.OK, errmsg="信息获取成功", data=data)


# 课程设置 查看课程名(详细信息)
@api.route('/teacher/course/detail', methods=['POST'])
@jwt_required
def detail_course():
    course_id = request.json.get("id")
    if not course_id:
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")
    try:
        # 根据课程ID查找所有的班级
        classes = Classes.query.join(course_class_relation, course_class_relation.c.class_id == Classes.id).filter(
            course_class_relation.c.course_id == course_id).all()
        # 遍历所有的班级
        class_list = [Classes.query.filter(Classes.id == class_name.id).first().to_teacher_dict() for class_name in
                      classes]
        # 获取当前的课程
        courses = Course.query.filter(Course.id == course_id).first()
        # 把课程填到列表里
        data = Course.to_teacher_full_dict(courses, class_list)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="信息获取失败")
    return jsonify(errno=RET.OK, errmsg="信息获取成功", data=data)


# 课程设置 年级 专业
@api.route('/teacher/course/grademajor', methods=['GET'])
@jwt_required
def grade_major():
    if request.method == "GET":
        try:
            # 获取所有的年级
            grades = Grade.query.all()
            # 遍历所有的年级
            grade_list = [grade.to_teacher_basic_dict() for grade in grades]
            # 获取所有的专业
            majors = Major.query.all()
            # 遍历所有的专业
            major_list = [major.to_teacher_basic_dict() for major in majors]
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="信息获取失败")
        return jsonify(errno=RET.OK, errmsg="信息获取成功", grade_list=grade_list, major_list=major_list)


# 课程设置 班级
@api.route('/teacher/course/classes', methods=['POST'])
@jwt_required
def classes():
    grade_id = request.json.get("grade_id")  # 年级名称.id
    major_id = request.json.get("major_id")  # 专业名称.id

    if not grade_id:
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")
    if not major_id:
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")
    try:
        # 联合查询 年级ID和专业ID
        classes = Classes.query.join(grade_major_relation, grade_major_relation.c.id == Classes.grade_major_id). \
            filter(grade_major_relation.c.major_id == major_id, grade_major_relation.c.grade_id == grade_id).all()
        # 遍历班级
        data = [Classes.query.filter(Classes.id == class_name.id).first().to_teacher_basic_dict() for class_name in classes]
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="信息获取失败")
    return jsonify(errno=RET.OK, errmsg="信息获取成功", data=data)


# 课程设置 设备教室
@api.route('/teacher/course/classroom', methods=['GET'])
@jwt_required
def classroom():
    if request.method == "GET":
        try:
            # 获取所有的教室
            room_list = Equipment_info.query.all()
            # 获取所有的教室
            data = [Equipment_info.query.filter(Equipment_info.id == room.id).first().to_teacher_base_dict() for room in
                    room_list if room.classroom is not None]
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="信息获取失败")
        return jsonify(errno=RET.OK, errmsg="信息获取成功", data=data)


# 课程设置 修改课程
@api.route('/teacher/course/update', methods=['POST'])
@jwt_required
def course_update():
    username = get_jwt_identity()
    # id = get_jwt_claims["id"]
    course_id = request.json.get("course_id")  # 课程id
    course_name = request.json.get("course_name")  # 课程名称
    course_room = request.json.get("course_room")  # 课程教室
    class_name = request.json.get("class_name")  # 班级
    try:
        teacher = Teacher.query.filter_by(sno=username).first()
        course = Course.query.filter(Course.id == course_id).first()
        room_list = [Equipment_info.query.get(course_id["id"]).classroom for course_id in course_room]
        room_list = ','.join(room_list)
        # 7.设置编辑信息，到对象列表
        course.name = course_name
        course.teacher_id = teacher.id
        course.course_room = room_list

        class_list = Classes.query.join(course_class_relation, Classes.id == course_class_relation.c.class_id)\
            .filter(course_class_relation.c.course_id == course.id).all()
        for classes in class_list:
            classes = Classes.query.get(classes.id)
            course.classes_relation.remove(classes)
            db.session.commit()

        db.session.add(course)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="信息添加失败")

    for class_id in class_name:
        try:
            cls = Classes.query.get(class_id["id"])
            course.classes_relation.append(cls)
            db.session.add(cls)
            db.session.commit()

        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="信息添加失败")
        # 6.保存到数据库
    return jsonify(errno=RET.OK, errmsg="信息添加成功")


# 课程设置 添加课程
@api.route('/teacher/course/add', methods=['POST'])
@jwt_required
def add_course():
    username = get_jwt_identity()
    course_name = request.json.get("course_name")   # 课程名称
    course_room = request.json.get("course_room")   # 课程教室
    class_name = request.json.get("class_name")     # 班级
    try:
        teacher = Teacher.query.filter_by(sno=username).first()
        course = Course()
        room_list = [Equipment_info.query.get(course_id["id"]).classroom for course_id in course_room]
        room_list = ','.join(room_list)
        # 7.设置编辑信息，到对象列表
        course.name = course_name
        course.teacher_id = teacher.id
        course.course_room = room_list

        db.session.add(course)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="信息添加失败")

    for class_id in class_name:
        try:
            course = Course.query.filter(Course.name == course.name, Course.teacher_id == course.teacher_id).first()
            cls = Classes.query.get(class_id["id"])
            course.classes_relation.append(cls)
            db.session.add(cls)
            db.session.commit()

        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="信息添加失败")
        # 6.保存到数据库
    return jsonify(errno=RET.OK, errmsg="信息添加成功")


# 设备bssid
@api.route('/teacher/wifi/init', methods=['GET'])
@jwt_required
def wifi():
    if request.method == "GET":
        try:
            bssid = str(random.choice(range(0, 8, 2)))
            random_str_two = ''
            random_str = ''
            base_str = '0123456789abcdef'
            length = len(base_str) - 1
            for i in range(1):
                random_str_two += base_str[random.randint(0, length)]
            for i in range(10):
                random_str += base_str[random.randint(0, length)]
            bssid = random_str_two + bssid + random_str
            bssid = ':'.join(re.findall('.{2}', bssid))
            test = Classroom_attendance.query.filter_by(bssid=bssid).first()
            if test is None:
                return jsonify(errno=RET.OK, errmsg="信息获取成功", bssid=bssid)
            else:
                wifi()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="信息获取失败")
        return jsonify(errno=RET.OK, errmsg="信息获取成功", bssid=bssid)


# 开启考勤
@api.route('/teacher/attendance/open', methods=['POST'])
@jwt_required
def attendance_open():
    username = get_jwt_identity()
    course_name = request.json.get("course_name")  # 课程名称
    course_room = request.json.get("course_room")  # 课程教室
    class_name = request.json.get("class_name")  # 班级
    start_time = datetime.datetime.now()  # 开启时间
    long_time = request.json.get("long_time")  # 考勤时长
    end_time = datetime.datetime.now() + datetime.timedelta(minutes=long_time)
    bssid = request.json.get("bssid")  # bssid值
    list1 = []  # 创建一个新的数组来存储无重复元素的数组
    for class_num in class_name:
        if (class_num not in list1):
            list1.append(class_num)
    try:
        # 获取老师信息
        teacher = Teacher.query.filter_by(sno=username).first()
        # 获取课程信息
        course = Course.query.get(course_name)
        # 获取教室最近的一次考勤记录
        course_ateendance = Classroom_attendance.query.order_by(-Classroom_attendance.end_time).filter_by(class_room=course_room).first()
        if course_ateendance is None or not (course_ateendance.start_time.strftime("%Y-%m-%d %H:%M:%S") < datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") < course_ateendance.end_time.strftime("%Y-%m-%d %H:%M:%S")):
            course_ateendance_nums = Classroom_attendance.query.order_by(-Classroom_attendance.end_time).join(course_class_relation,
                course_class_relation.c.course_id == course_name).filter(Classroom_attendance.course_class_id == course_class_relation.c.id).first()
            print(course_ateendance_nums)
            if course_ateendance_nums is not None:
                nums = course_ateendance_nums.nums + 1
            else:
                nums = 1
            for class_id in list1:
                try:
                    # 获取当前的班级
                    classes = Classes.query.filter(Classes.id == class_id["id"]).first()
                    # 获取当前的班级专业
                    major = Major.query.join(grade_major_relation, Major.id == grade_major_relation.c.major_id). \
                        filter(grade_major_relation.c.id == classes.grade_major_id).first()

                    # 写入老师开启考勤记录
                    classroom_attenance = Classroom_attendance()
                    classroom_attenance.start_time = start_time
                    classroom_attenance.end_time = end_time
                    classroom_attenance.class_room = course_room
                    # 使用pymysql 来使用原生sql
                    test = pymysql.connect("192.168.1.142", "muji", "mujiwuliankeji", "muji")
                    # 使用 cursor() 方法创建一个游标对象 cursor
                    cursor = test.cursor()
                    sql = "select * from course_class_relation where class_id = %s and course_id = %s" % (class_id["id"], course.id)
                    # 查询到班级课程关系的id
                    cursor.execute(sql)
                    data = cursor.fetchone()
                    # print(data[0])
                    classroom_attenance.course_class_id = data[0]
                    classroom_attenance.bssid = bssid
                    classroom_attenance.nums = nums
                    # 写入数据库
                    db.session.add(classroom_attenance)
                    db.session.commit()
                    course_atten = Classroom_attendance.query.order_by(-Classroom_attendance.end_time).filter_by(
                        course_class_id=data[0]).first()
                    # print(course_atten)
                    # 获取当前班级的所有学生
                    students = Student.query.filter(Student.class_id == class_id["id"]).all()
                    # 遍历学生列表
                    for student in students:
                        # 查看学生是否在读
                        if student.school_roll_status_id == 1:
                            # 获取当前学生的请假记录
                            leave = Leave.query.filter_by(student_id=student.id).order_by(
                                -Leave.end_time).first()
                            # 判断学生的请假时间是否在考勤时间段内并判断辅导员是否准假
                            if leave is not None:
                                if leave.start_time < datetime.datetime.now() < leave.end_time and leave.status == 1:
                                    # 写入学生考勤记录，为请假
                                    # print(student.id)
                                    student_classroom = Stu_classroom_atten_res()
                                    student_classroom.student_id = student.id
                                    student_classroom.classroom_attendance_id = course_atten.id
                                    student_classroom.time = datetime.datetime.now()
                                    student_classroom.status = 2
                                    student_classroom.class_id = class_id["id"]
                                    student_classroom.major_id = major.id
                                    student_classroom.cource_id = course.id
                                    student_classroom.teacher_id = teacher.id

                                    db.session.add(student_classroom)
                                    db.session.commit()
                                    continue

                            student_classroom = Stu_classroom_atten_res()
                            student_classroom.student_id = student.id

                            student_classroom.classroom_attendance_id = course_atten.id
                            student_classroom.time = datetime.datetime.now()
                            student_classroom.status = 0
                            student_classroom.class_id = class_id["id"]
                            student_classroom.major_id = major.id
                            student_classroom.cource_id = course.id
                            student_classroom.teacher_id = teacher.id

                            db.session.add(student_classroom)
                            db.session.commit()
                except Exception as e:
                    current_app.logger.error(e)
                    return jsonify(errno=RET.DBERR, errmsg="开启考勤失败")

            # 6.保存到数据库
            return jsonify(errno=RET.OK, errmsg="开启考勤成功")
        # 查看是否在考勤时间段
        return jsonify(errno=RET.DBERR, errmsg="不要重复开启考勤")
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="信息添加失败")


# 查看考勤结果
@api.route('/teacher/attendance/result', methods=['POST'])
@jwt_required
def attendance_result():
    number_id = request.json.get("number_id")       # 考勤次数ID
    course_name = request.json.get("course_name")   # 课程名称
    class_name = request.json.get("class_name")     # 班级名称

    check_list = []
    absence_list = []
    leave_list = []
    num_data = []
    try:
        if number_id is not None:
            stu_classroom = Stu_classroom_atten_res.query.join(Classroom_attendance, Classroom_attendance.id == Stu_classroom_atten_res.classroom_attendance_id).\
                filter(Classroom_attendance.nums == number_id).\
                join(course_class_relation, course_class_relation.c.id == Classroom_attendance.course_class_id).\
                filter(course_class_relation.c.course_id == course_name).all()
            # print(stu_classroom)
            check_list = []
            absence_list = []
            leave_list = []
            num_data = []
            for student_status in stu_classroom:
                if student_status.status == 1 or student_status.status == 3:
                    check_list.append(student_status.to_teacher_dict())
                if student_status.status == 0:
                    absence_list.append(student_status.to_teacher_dict())
                if student_status.status == 2:
                    leave_list.append(student_status.to_teacher_dict())
            num_data.append(len(check_list))
            num_data.append(len(absence_list))
            num_data.append(len(leave_list))
            if (len(check_list) + len(absence_list) + len(leave_list)) == 0:
                rate = 0
            else:
                rate = len(check_list) / (len(check_list) + len(absence_list) + len(leave_list))
                rate = "%.2f" % (rate * 100)
            num_data.append(rate)
            # num_data.append(len(numbers))
            # num_data.append(attendance.nums)
            # num_data.append(attendance.start_time)
            return jsonify(errno=RET.OK, errmsg="信息获取成功", check_list=check_list, absence_list=absence_list,
                           leave_list=leave_list, num_data=num_data)

        list1 = []  # 创建一个新的数组来存储无重复元素的数组
        for class_num in class_name:
            if (class_num not in list1):
                list1.append(class_num)

        for class_name in list1:
            course_room = Classroom_attendance.query.join(course_class_relation,course_class_relation.c.id == Classroom_attendance.course_class_id)\
                .filter(course_class_relation.c.class_id == class_name["id"],course_class_relation.c.course_id == course_name).\
                order_by(-Classroom_attendance.end_time).first()

            student_attendance = Stu_classroom_atten_res.query.filter_by(classroom_attendance_id=course_room.id).all()

            for student_status in student_attendance:
                if student_status.status == 1 or student_status.status == 3:
                    check_list.append(student_status.to_teacher_dict())
                if student_status.status == 0:
                    absence_list.append(student_status.to_teacher_dict())
                if student_status.status == 2:
                    leave_list.append(student_status.to_teacher_dict())
        num_data.append(len(check_list))
        num_data.append(len(absence_list))
        num_data.append(len(leave_list))
        if (len(check_list)+len(absence_list)+len(leave_list)) == 0:
            rate = 0
        else:
            rate = len(check_list)/(len(check_list)+len(absence_list)+len(leave_list))
            rate = "%.2f" % (rate * 100)

        num_data.append(rate)
        # num_data.append(len(numbers))
        num_data.append(course_room.nums)
        num_data.append(course_room.start_time.strftime("%Y-%m-%d %H:%M:%S"))
        print(num_data)
        # absence_list = json.dumps(absence_list, ensure_ascii=False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="信息获取失败")
    return jsonify(errno=RET.OK, errmsg="信息获取成功", check_list=check_list, absence_list=absence_list, leave_list=leave_list, num_data=num_data)


# 提前结束考勤
@api.route('/teacher/attendance/advance/end', methods=['POST'])
@jwt_required
def advance_end():
    course_name = request.json.get("course_name")  # 课程名称
    class_name = request.json.get("class_name")  # 班级名称
    print(course_name)
    print(class_name)
    list1 = []  # 创建一个新的数组来存储无重复元素的数组
    for class_num in class_name:
        if (class_num not in list1):
            list1.append(class_num)
    try:
        for class_name in list1:
            course_room = Classroom_attendance.query.order_by(-Classroom_attendance.end_time).join(course_class_relation, course_class_relation.c.id == Classroom_attendance.course_class_id)\
                .filter(course_class_relation.c.class_id == class_name["id"], course_class_relation.c.course_id == course_name).first()
            print(course_room)
            if course_room.end_time < datetime.datetime.now():
                return jsonify(errno=RET.DBERR, errmsg="不在考勤时间内")

            course_room.end_time = datetime.datetime.now()
            db.session.add(course_room)
            db.session.commit()
        return jsonify(errno=RET.OK, errmsg="提前结束考勤成功")
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="信息获取失败")


# 修改考勤结果
@api.route('/teacher/attendance/change/status', methods=['POST'])
@jwt_required
def change_status():
    student_id = request.json.get("student_id")  # 学生ID
    username = get_jwt_identity()
    teacher = Teacher.query.filter_by(sno=username).first()
    try:
        student = Stu_classroom_atten_res.query.order_by(-Stu_classroom_atten_res.time).filter(Stu_classroom_atten_res.student_id == student_id, Stu_classroom_atten_res.teacher_id == teacher.id).first()
        student.time = datetime.datetime.now()
        student.status = 3
        db.session.add(student)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="信息获取失败")
    return jsonify(errno=RET.OK, errmsg="信息修改成功")


# 根据课程ID获取考勤次数
@api.route('/teacher/attendance/record', methods=['POST'])
@jwt_required
def attendance_record():
    course_id = request.json.get("course_id")  # 课程ID
    try:
        classroom_attendance = Classroom_attendance.query.order_by(-Classroom_attendance.end_time).join(course_class_relation, course_class_relation.c.id==Classroom_attendance.course_class_id)\
            .filter(course_class_relation.c.course_id == course_id).all()
        numbers = []
        for classes in classroom_attendance:
            numbers.append(Classroom_attendance.to_teacher_num_dict(classes))

        list1 = []  # 创建一个新的数组来存储无重复元素的数组
        for class_num in numbers:
            # print(class_num["nums"])
            if (class_num not in list1):
                list1.append(class_num)
        print(list1)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="信息获取失败")
    return jsonify(errno=RET.OK, errmsg="信息获取成功", numbers=list1)


# 获取第一次的考勤
@api.route('/teacher/attendance/record/first', methods=['GET'])
@jwt_required
def attendance_record_first():
    try:
        username = get_jwt_identity()
        teacher = Teacher.query.filter_by(sno=username).first()
        classroom_attendance = Classroom_attendance.query.order_by(Classroom_attendance.end_time.desc()).join(
            course_class_relation, course_class_relation.c.id == Classroom_attendance.course_class_id) \
            .filter(course_class_relation.c.course_id == Course.id).join(Course).filter(
            Course.teacher_id == teacher.id).first()
        classroom_attendance = Classroom_attendance.query.filter_by(bssid=classroom_attendance.bssid).all()
        nums = []
        check_list = []
        absence_list = []
        leave_list = []
        num_data = []
        for classes in classroom_attendance:
            nums.append(Classroom_attendance.to_teacher_dict(classes))
            stu_classroom = Stu_classroom_atten_res.query.filter_by(classroom_attendance_id=classes.id).all()

            for student_status in stu_classroom:
                if student_status.status == 1 or student_status.status == 3:
                    check_list.append(student_status.to_teacher_dict())
                if student_status.status == 0:
                    absence_list.append(student_status.to_teacher_dict())
                if student_status.status == 2:
                    leave_list.append(student_status.to_teacher_dict())
        num_data.append(len(check_list))
        num_data.append(len(absence_list))
        num_data.append(len(leave_list))
        if (len(check_list) + len(absence_list) + len(leave_list)) == 0:
            rate = 0
        else:
            rate = len(check_list) / (len(check_list) + len(absence_list) + len(leave_list))
            rate = "%.2f" % (rate * 100)
        num_data.append(rate)
        return jsonify(errno=RET.OK, errmsg="信息获取成功", check_list=check_list, absence_list=absence_list,
                       leave_list=leave_list, num_data=num_data, numbers_time=nums[-1]["start_time"],
                       numbers=nums[-1]["nums"], course_name=nums[-1]["course_class_id"]["name"],course_id=nums[-1]["course_class_id"]["id"])
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="信息获取失败")


# 修改老师密码
@api.route('/teacher/repassword', methods=['POST'])
@jwt_required
def teacher_passwd():
    id = get_jwt_claims()["id"]
    password = request.json.get("password")         # 教师旧密码
    new_passwd = request.json.get("new_password")     # 新密码
    role = request.json.get("role")                 # 当前角色
    teacher = Users.query.get(id)
    if teacher.check_password(password) is True:
        if password is not None and role is '2':
            teacher.password = new_passwd
            db.session.add(teacher)
            db.session.commit()
            return jsonify(errno=RET.OK, errmsg="修改密码成功")
        return jsonify(errno=RET.STATUS, errmsg="旧密码错误")

    return jsonify(errno=RET.STATUS, errmsg="旧密码错误")


# 邮箱发送验证码
@api.route('/teacher/send/mail', methods=['POST'])
def teacher_send_mail():
    '''发送邮箱验证码'''
    email = request.json.get('email')
    # if not all([email, nickname]):
    if email is None:
        return jsonify(re_code=RET.PARAMERR, msg='请填写完整的注册信息')

    # 邮箱匹配正则
    # ^[a-zA-Z0-9_.-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z0-9]{2,6}$
    # 手机号匹配正则
    # ^0\d{2,3}\d{7,8}$|^1[358]\d{9}$|^147\d{8}$

    if not re.match(r'^[a-zA-Z0-9_.-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z0-9]{2,6}$', email):
        return jsonify(RET.PARAMERR, msg='请填写正确的邮箱')

    # 生成邮箱验证码
    email_code = '%06d' % random.randint(0, 99999)
    current_app.logger.debug('邮箱验证码为: ' + email_code)
    try:
        redis_store.set('EMAILCODE:' + email, email_code, 1800)  # half-hour = 1800有效期
    except Exception as e:
        current_app.logger.debug(e)
        return jsonify(re_code=RET.DBERR, msg='存储邮箱验证码失败')

    # 发送邮件
    send_mail(
        to=email,
        mailcode=email_code
    )

    return jsonify(re_code=RET.OK, msg='验证码发送成功')


# 验证邮箱验证码
@api.route('/teacher/mail/verification', methods=['POST'])
def verification():
    email = request.json.get('email')
    mailcode = request.json.get('mailcode')
    password = request.json.get('password')
    try:
        mailcode_server = redis_store.get('EMAILCODE:'+ email).decode()
    except Exception as e:
        current_app.logger.debug(e)
        return jsonify(re_code=RET.DBERR, msg='查询邮箱验证码失败')
    if mailcode_server != mailcode:
        current_app.logger.debug(mailcode_server)
        return jsonify(re_code=RET.PARAMERR, msg='邮箱验证码错误')

    teacher = Teacher.query.filter_by(email=email).first()
    user = Users.query.filter_by(username=teacher.sno).first()
    user.password_hash = password
    db.session.add(user)
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="修改密码成功")


# 测试
@api.route('/teacher/attendance/test', methods=['POST'])
def teacher_test():
    course_name = request.json.get("course_name")  # 课程名称
    course_room = request.json.get("course_room")  # 课程教室

    course_ateendance_nums = Classroom_attendance.query.order_by(-Classroom_attendance.end_time).join(
        course_class_relation, course_class_relation.c.course_id == course_name).filter(
        Classroom_attendance.course_class_id == course_class_relation.c.id,
        Classroom_attendance.class_room == course_room).first()
    print(course_ateendance_nums)
    return jsonify(errno=RET.OK, errmsg="查看成功")
