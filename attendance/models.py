__author__ = 'zhangenmin'
__date__ = '2019/2/28 10:50'

import datetime
from datetime import datetime
from attendance import constants
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import SQLAlchemyError


class Users(db.Model):
    __tablename_ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # id
    username = db.Column(db.String(30), unique=True, nullable=False)  # 账号
    password_hash = db.Column(db.String(255), nullable=False)  # 加秘密码
    role = db.Column(db.Integer, nullable=False)  # 角色类型

    # 加上property装饰器后，会把函数变为属性，属性名即为函数名
    @property
    def password(self):
        """读取属性的函数行为"""
        # print(user.password)  # 读取属性时被调用
        # 函数的返回值会作为属性值
        # return "xxxx"
        raise AttributeError("这个属性只能设置，不能读取")

    # 使用这个装饰器, 对应设置属性操作
    @password.setter
    def password(self, value):
        """
        设置属性  user.passord = "xxxxx"
        :param value: 设置属性时的数据 value就是"xxxxx", 原始的明文密码
        :return:
        """
        self.password_hash = generate_password_hash(value)

    # def generate_password_hash(self, origin_password):
    #     """对密码进行加密"""
    #     self.password_hash = generate_password_hash(origin_password)

    def check_password(self, passwd):
        """
        检验密码的正确性
        :param passwd:  用户登录时填写的原始密码
        :return: 如果正确，返回True， 否则返回False
        """
        return check_password_hash(self.password_hash, passwd)

    @classmethod
    def is_users_blacklisted(cls, username):
        query = cls.query.filter_by(username=username).first()
        return bool(query)

    def to_dict(self):
        """将对象转换为字典数据"""
        user_dict = {
            "user_id": self.id,
            "username": self.username,
            "role": self.role,
        }
        return user_dict


class Teacher(db.Model):
    __tablename__ = 'teacher'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 自增ID
    sno = db.Column(db.String(30), db.ForeignKey('users.username', ondelete='CASCADE'), unique=True)  # 教师职工号
    name = db.Column(db.String(10), nullable=True)  # 姓名
    sex = db.Column(db.String(2))  # 性别
    idcard_num = db.Column(db.String(18), nullable=True)  # 身份证号
    phone_num = db.Column(db.String(11), nullable=True)  # 手机号码
    qq = db.Column(db.String(20), nullable=True)  # 姓名
    email = db.Column(db.String(50), nullable=True)  # 邮箱
    head_picture = db.Column(db.String(64), nullable=True)  # 头像
    office = db.Column(db.String(30), nullable=True)  # 办公室地址

    def to_basic_dict(self):
        teacher_dict = {
            "teacher_id": self.id,
            "sno": self.sno,
            "name": self.name,
            "sex": self.sex,
            "idcard_num": self.idcard_num,
            "phone_num": self.phone_num,
        }
        return teacher_dict

    def to_full_dict(self):
        teacher_dict = {
            "teacher_id": self.id,
            "sno": self.sno,
            "name": self.name,
            "sex": self.sex,
            "idcard_num": self.idcard_num,
            "phone_num": self.phone_num,
            "qq": self.qq,
            "email": self.email,
            "head_picture": constants.IMAGE_URL + self.head_picture if self.head_picture else "",
            "office": self.office
        }
        return teacher_dict

    def to_teacher_basic_dict(self):
        '''教师端使用'''
        teacher_dict = {
            "id": self.id,
            "sno": self.sno,
            "name": self.name,
            "sex": self.sex,
            "idcard_num": self.idcard_num,
            "phone_num": self.phone_num,
            "qq": self.qq,
            "email": self.email,
            "head_picture": constants.IMAGE_URL + self.head_picture if self.head_picture else "",
            "office": self.office
        }
        return teacher_dict

class Instructor(db.Model):
    __tablename__ = 'instructor'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 自增ID
    sno = db.Column(db.String(30), db.ForeignKey('users.username', ondelete='CASCADE'), unique=True)  # 辅导员职工号
    name = db.Column(db.String(10), nullable=True)  # 姓名
    sex = db.Column(db.String(2))  # 性别
    idcard_num = db.Column(db.String(18), nullable=True)  # 身份证号
    phone_num = db.Column(db.String(11), nullable=True)  # 手机号码
    qq = db.Column(db.String(20), nullable=True)  # 姓名
    email = db.Column(db.String(50), nullable=True)  # 邮箱
    head_picture = db.Column(db.String(64), nullable=True)  # 头像
    office = db.Column(db.String(30), nullable=True)  # 办公室地址

    def to_basic_dict(self):
        instructor_dict = {
            "instructor_id": self.id,
            "name": self.name,
            "sex": self.sex
        }
        return instructor_dict

    def to_full_dict(self):
        class_li = Classes.query.filter(Classes.instructor_id == self.id)
        classes = []
        for cls in class_li:
            grade_li = Grade.query.join(grade_major_relation, Grade.id == grade_major_relation.c.grade_id).filter(
                grade_major_relation.c.id == cls.grade_major_id).first()
            classes.append(grade_li.to_basic_dict()["name"] + cls.to_basic_dict()["class_name"])
        instructor_dict = {
            "instructor_id": self.id,
            "sno": self.sno,
            "name": self.name,
            "sex": self.sex,
            "idcard_num": self.idcard_num,
            "phone_num": self.phone_num,
            "qq": self.qq,
            "email": self.email,
            "head_picture": constants.IMAGE_URL + self.head_picture if self.head_picture else "",
            "office": self.office,
            "class": dict(classes=classes)

        }
        return instructor_dict

    def class_dict(self):
        class_li = Classes.query.filter(Classes.instructor_id == self.id)
        classes = []
        for cls in class_li:
            grade_li = Grade.query.join(grade_major_relation, Grade.id == grade_major_relation.c.grade_id).filter(
                grade_major_relation.c.id == cls.grade_major_id).first()
            classes.append(grade_li.to_basic_dict()["name"] + cls.to_basic_dict()["class_name"])
            classes.append({"id": cls.id})
        instructor_dict = {
            "class": dict(classes=classes)
        }
        return instructor_dict

    def get_ins_class(self):
        """
        辅导员获取管理的所有班级
        :return:
        """
        classes = Classes.query.filter_by(instructor_id=self.id).all()
        ins_dict = [cls.ins_get_data() for cls in classes]

        return ins_dict

    def stu_get_ins(self):
        """
        学生端获取他所在班级的辅导员信息
        :return:
        """
        instructor_dict = {
            "name": self.name if self.name else "无",
            "sex": self.sex if self.sex else "无",
            "phone":  self.phone_num if self.phone_num else "无",
            "qq": self.qq if self.qq else "无",
            "email": self.email if self.email else "无",
            "office": self.office if self.office else "无"
        }
        return instructor_dict


course_class_relation = db.Table(
    "course_class_relation",
    db.Column("id", db.Integer, primary_key=True, autoincrement=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id', ondelete="CASCADE")),
    db.Column('class_id', db.Integer, db.ForeignKey('classes.id', ondelete="CASCADE"))
)


class Course(db.Model):
    __tablename__ = 'course'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(40), nullable=True)  # 课程名字
    teacher_id = db.Column(db.Integer, db.ForeignKey("teacher.id"))  # 授课教师ID
    course_room = db.Column(db.String(200), nullable=True)  # 上课教室

    # classes_relation = db.relationship('classes',
    #                                    secondary=course_class_relation,
    #                                    backref=db.backref('course', lazy='dynamic'),
    #                                    lazy='dynamic')

    classes_relation = db.relationship('Classes',
                                       secondary=course_class_relation,
                                       backref=db.backref('course', lazy='dynamic'),
                                       lazy='dynamic')

    def to_basic_dict(self):
        course_dict = {
            "name": self.name,
            "teacher_id": Teacher.query.filter(Teacher.id == self.teacher_id).first().to_basic_dict()['name'],
            "course_room": self.course_room
        }
        return course_dict

    def to_full_dict(self):
        course_dict = {
            "course_id": self.id,
            "name": self.name,
            "teacher": Teacher.query.filter(Teacher.id == self.teacher_id).first().to_basic_dict(),
            "course_room": self.course_room
        }
        return course_dict

    def to_teacher_full_dict(self, class_list):
        '''教师端使用'''
        course_dict = {
            "course_id": self.id,
            "name": self.name,
            "classes": class_list,
            "course_room": [Equipment_info.query.filter_by(classroom=course_name).first().to_teacher_base_dict() for
                            course_name in
                            self.course_room.split(',')],
        }
        return course_dict

    def to_base_dict(self):
        """
        学生端使用
        :return:
        """
        course_dict = {
            "course_id": self.id,
            "name": self.name,
            "teacher_id": self.teacher_id.name,
            "course_room": self.course_room
        }
        return course_dict

    def to_teacher_base_dict(self):
        '''教师端使用'''
        course_dict = {
            "course_id": self.id,
            "name": self.name,
            "grade": Grade.query.join(grade_major_relation, grade_major_relation.c.grade_id == Grade.id).filter
            (grade_major_relation.c.id == (
                Classes.query.join(course_class_relation, Classes.id == course_class_relation.c.class_id).filter(
                    course_class_relation.c.course_id == self.id).first()).grade_major_id).first().to_teacher_basic_dict(),
        }
        return course_dict

    def to_teacher_dict(self):
        '''教师端使用'''
        course_dict = {
            "name": self.name,
            "id":self.id
        }
        return course_dict

class Department(db.Model):
    __tablename__ = 'department'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=True)  # 系院名称
    instructor_permit_leave_time = db.Column(db.Integer, nullable=True)  # 辅导员最大批假时间（天）
    instructor_manage_time = db.Column(db.Integer, nullable=True)  # 辅导员需在多长时间内处理当天宿舍考勤结果
    dormitory_start_time = db.Column(db.Time, nullable=True)  # 宿舍考勤开始时间
    dormitory_end_time = db.Column(db.Time, nullable=True)  # 宿舍考勤结束时间
    pause_start_time = db.Column(db.DateTime, nullable=True)
    pause_time = db.Column(db.DateTime, nullable=True)
    modify_stu_status = db.Column(db.Integer, nullable=True)

    def to_basic_dict(self):
        department_dict = {
            "id": self.id,
            "name": self.name,
            "instructor_permit_leave_time": self.instructor_permit_leave_time,
            "instructor_manage_time": self.instructor_manage_time,
            "dormitory_start_time": self.dormitory_start_time.strftime("%H:%M:%S"),
            "dormitory_end_time": self.dormitory_end_time.strftime("%H:%M:%S"),
            "pause_time": self.pause_time.strftime("%Y-%m-%d %H:%M:%S"),
            "pause_start_time": self.pause_start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "modify_stu_status": self.modify_stu_status
        }
        return department_dict

    def to_full_dict(self):
        department_dict = {
            "id": self.id,
            "name": self.name,
            "instructor_permit_leave_time": self.instructor_permit_leave_time,
            "instructor_manage_time": self.instructor_manage_time,
            "dormitory_start_time": self.dormitory_start_time,
            "dormitory_end_time": self.dormitory_end_time
        }
        return department_dict


class Department_admin(db.Model):
    __tablename__ = 'department_admin'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(10), nullable=True)  # 系院管理员姓名
    department_id = db.Column(db.Integer, db.ForeignKey('department.id', ondelete="CASCADE"))  # 系院ID
    username = db.Column(db.String(30),db.ForeignKey('users.id',ondelete="CASCADE"))

    def to_base_dict(self):
        department_admin_dict = {
            "id": self.id,
            "name": self.name,
            "department_id": self.department_id.name
        }
        return department_admin_dict

    def to_full_dict(self):
        department_admin_dict = {
            "id": self.id,
            "name": self.name,
            "department_id": self.department_id.name,
        }
        return department_admin_dict


grade_major_relation = db.Table(
    "grade_major_relation",
    db.Column("id", db.Integer, primary_key=True, autoincrement=True),
    db.Column('grade_id', db.Integer, db.ForeignKey('grade.id', ondelete="CASCADE")),
    db.Column('major_id', db.Integer, db.ForeignKey('major.id', ondelete="CASCADE"))
)


class Major(db.Model):
    __tablename__ = 'major'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=True, )  # 专业名字
    department_id = db.Column(db.Integer, db.ForeignKey('department.id', ondelete="CASCADE"))  # 系院ID
    # relation = db.relationship('classes',
    #                            secondary=grade_major_relation,
    #                             backref=db.backref('major', lazy='dynamic'),
    #                             lazy='dynamic')

    relation = db.relationship('Classes',
                               secondary=grade_major_relation,
                               backref=db.backref('major', lazy='dynamic'),
                               lazy='dynamic')

    def to_basic_dict(self):
        major_dict = {
            "id": self.id,
            "name": self.name,

        }
        return major_dict

    def to_full_dict(self):
        major_dict = {
            "id": self.id,
            "name": self.name,
            "department_id": Instructor.query.filter(Instructor.id==self.department_id).first().to_basic_dict()
        }
        return major_dict

    def to_teacher_basic_dict(self):
        '''教师端使用'''
        major_dict = {
            "major_id": self.id,
            "name": self.name,
        }
        return major_dict

class Grade(db.Model):
    __tablename__ = 'grade'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=True, )  # 年级名称
    department_id = db.Column(db.Integer, db.ForeignKey('department.id', ondelete="CASCADE"))  # 系院ID
    whether_attendance = db.Column(db.Integer,default=1)
    classes_relation = db.relationship('Classes',
                                       secondary=grade_major_relation,
                                       backref=db.backref('grade', lazy='dynamic'),
                                       lazy='dynamic')
    major_relation = db.relationship('Major',
                                     secondary=grade_major_relation,
                                     backref=db.backref('grade', lazy='dynamic'),
                                     lazy='dynamic')

    def to_teacher_basic_dict(self):
        '''教师端使用'''
        grade_dict = {
            "id": self.id,
            "name": self.name,
        }
        return grade_dict

    def to_basic_dict(self):
        grade_dict = {
            "id": self.id,
            "name": self.name,
            "whether_attendace": self.whether_attendance,
        }
        return grade_dict

    def to_full_dict(self):
        grade_dict = {
            "id": self.id,
            "name": self.name,
            "whether_attendace": self.whether_attendance,
            "department_id": Instructor.query.get(self.department_id).to_basic_dict()
        }
        return grade_dict


class Classes(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    grade_major_id = db.Column(db.Integer,
                               db.ForeignKey('grade_major_relation.id', ondelete="SET NULL", onupdate="SET NULL"))
    instructor_id = db.Column(db.Integer, db.ForeignKey('instructor.id', onupdate="SET NULL", ondelete="SET NULL"))
    class_name = db.Column(db.String(50), nullable=True)
    class_num = db.Column(db.String(30), nullable=True)
    whether_attendance = db.Column(db.Integer, nullable=True)
    # classes_relation = db.relationship('course',
    #                                    secondary=course_class_relation,
    #                                    backref=db.backref('classes', lazy='dynamic'),
    #
    #                                    lazy='dynamic')

    grade_relation = db.relationship('Grade',
                                     secondary="grade_major_relation",
                                     backref=db.backref('cls', lazy='dynamic'),
                                     lazy='dynamic')

    major_relation = db.relationship('Major',
                                     secondary=grade_major_relation,
                                     backref=db.backref('cls', lazy='dynamic'),
                                     lazy='dynamic')

    def to_basic_dict(self):
        classes_dict = {
            "id": self.id,
            "class_name": self.class_name,
            "class_num": self.class_num
        }
        return classes_dict

    def to_dict(self):
        """
        学生端使用
        :return:
        """
        classes_dict = {
            "id": self.id,
            "grade_major_id": self.grade_major_id,
            "instructor_id": Instructor.query.get(self.instructor_id).to_basic_dict(),
            "class_name": self.class_name,
            "class_num": self.class_num
        }
        return classes_dict

    def to_full_dict(self):
        try:
         a  =   Instructor.query.get(self.instructor_id).to_basic_dict()
        except Exception as e:
            a = {"name":""}
        classes_dict = {
            "id": self.id,
            "class_name": self.class_name,
            "class_num": self.class_num,
            "grade": Grade.query.join(grade_major_relation, grade_major_relation.c.grade_id == Grade.id).
                join(Classes, Classes.grade_major_id == grade_major_relation.c.id).filter(Classes.id == self.id).
                first().to_basic_dict(),
            "major": Major.query.join(grade_major_relation, grade_major_relation.c.major_id == Major.id).
                join(Classes, Classes.grade_major_id == grade_major_relation.c.id).filter(Classes.id == self.id).
                first().to_basic_dict(),
            "instructor_id": a


        }
        return classes_dict

    def ins_get_data(self):
        """
        辅导员端考勤信息使用
        :return:
        """
        classes_dict = {
            "id": self.id,
            "class_name": self.class_name,
            "grade": Grade.query.join(grade_major_relation, grade_major_relation.c.grade_id == Grade.id).join(
                Classes, Classes.grade_major_id == grade_major_relation.c.id).filter(
                Classes.id == self.id).first().name,
            "major": Major.query.join(grade_major_relation, grade_major_relation.c.major_id == Major.id).join(
                Classes, Classes.grade_major_id == grade_major_relation.c.id).filter(Classes.id == self.id).first().name
        }
        return classes_dict

    def to_teacher_basic_dict(self):
        '''教师端使用'''
        classes_dict = {
            "id": self.id,
            "class_name": self.class_name,
            "grade_id": Grade.query.get(
                ((Grade.query.join(grade_major_relation, grade_major_relation.c.grade_id == Grade.id).filter(
                    grade_major_relation.c.id == self.grade_major_id)).first()).id).to_teacher_basic_dict(),
        }
        return classes_dict

    def to_teacher_dict(self):
        '''教师端使用'''
        classes_dict = {
            "id": self.id,
            "grade_id": Grade.query.get(((Grade.query.join(grade_major_relation, grade_major_relation.c.grade_id == Grade.id).filter(
                grade_major_relation.c.id == self.grade_major_id)).first()).id).to_basic_dict(),
            "major_id": Major.query.get(((Major.query.join(grade_major_relation, grade_major_relation.c.major_id == Major.id).filter(
                grade_major_relation.c.id == self.grade_major_id)).first()).id).to_basic_dict(),
            "class_name": self.class_name,
            "class_num": self.class_num
        }
        return classes_dict


class School_roll_type(db.Model):
    __tabelname__ = 'school_rool_type'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(20), nullable=True)

    def to_dict(self):
        school_roll_type_dict = {
            "id": self.id,
            "name": self.name
        }
        return school_roll_type_dict

    def get_stu_status(self):
        """
        学生端使用
        :return:
        """
        school_roll_type_dict = {
            "name": self.name
        }
        return school_roll_type_dict


class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sno = db.Column(db.String(30), db.ForeignKey('users.username', ondelete='CASCADE'), unique=True)
    school_roll_status_id = db.Column(db.Integer,
                                      db.ForeignKey('school_roll_type.id', ondelete='SET NULL', onupdate='CASCADE'))
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id', ondelete='SET NULL', onupdate='SET NULL'))
    name = db.Column(db.String(10), nullable=True)  # 姓名
    sex = db.Column(db.String(2))  # 性别
    idcard_num = db.Column(db.String(18), nullable=True)  # 身份证号
    phone = db.Column(db.String(11), nullable=True)
    dormitory_num = db.Column(db.String(20), nullable=True)
    face_img = db.Column(db.String(255), nullable=True)
    qq = db.Column(db.String(20), nullable=True)  # qq
    email = db.Column(db.String(50), nullable=True)  # 邮箱
    monitor = db.Column(db.Integer, nullable=True)

    def to_basic_dict(self):
        student_dict = {
            "id": self.id,
            "sno": self.sno,
            "school_roll_status": School_roll_type.query.get(self.school_roll_status_id).to_dict(),
            "class_id": Classes.query.get(self.class_id).to_basic_dict(),
            "name": self.name,
            "sex": self.sex,
            "idcard_num": self.idcard_num,
            "phone": self.phone,
            "dormitory_num": self.dormitory_num,
            "grade": Grade.query.join(grade_major_relation, grade_major_relation.c.grade_id == Grade.id).
                join(Classes, Classes.grade_major_id == grade_major_relation.c.id).filter(Classes.id == self.class_id).
                first().to_basic_dict(),
            "major": Major.query.join(grade_major_relation, grade_major_relation.c.major_id == Major.id).
                join(Classes, Classes.grade_major_id == grade_major_relation.c.id).filter(Classes.id == self.class_id).
                first().to_basic_dict(),
            "monitor": self.monitor

        }
        return student_dict

    def to_full_dict(self):
        try:
            leave_status = Leave.query.filter(Leave.student_id == self.id, Leave.status == 1).order_by(
                Leave.start_time).first().to_basic_dict()
        except Exception as e:
            leave_status = "0"
        student_dict = {
            "id": self.id,
            "sno": self.sno,
            "school_roll_status": School_roll_type.query.get(self.school_roll_status_id).to_dict(),
            "class_id": Classes.query.get(self.class_id).to_basic_dict(),
            "name": self.name,
            "sex": self.sex,
            "idcard_num": self.idcard_num,
            "phone": self.phone,
            "dormitory_num": self.dormitory_num,
            "qq": self.qq,
            "email": self.email,
            "monitor": self.monitor,
            "face_img": constants.IMAGE_URL + self.face_img[10:] if self.face_img else "",
            "grade": Grade.query.join(grade_major_relation, grade_major_relation.c.grade_id == Grade.id).
                join(Classes, Classes.grade_major_id == grade_major_relation.c.id).filter(Classes.id == self.class_id).
                first().to_basic_dict(),
            "major": Major.query.join(grade_major_relation, grade_major_relation.c.major_id == Major.id).
                join(Classes, Classes.grade_major_id == grade_major_relation.c.id).filter(Classes.id == self.class_id).
                first().to_basic_dict(),
            "leave": Leave.query.filter(Leave.student_id == self.id).first().to_basic_dict() if Leave.query.filter(
                Leave.student_id == self.id).first() else "未请假"


        }
        return student_dict

    def get_ins_detail_stu(self):
        """
        辅导员请求多学生数据
        :return:
        """
        student_dict = {
            "id": self.id,
            "sno": self.sno,
            "name": self.name,
            "sex": self.sex,
            "phone": self.phone,
            "dormitory_num": self.dormitory_num,
            "class_name": Classes.query.get(self.class_id).class_name,
        }
        return student_dict

    def get_ins_stu(self):
        """
        辅导员端获得学生信息
        :return:
        """
        n_time = datetime.now()
        try:
            leave = Leave.query.order_by(-Leave.end_time).filter(Leave.student_id == self.id, Leave.status == 1).first()
            if leave.start_time < n_time < leave.end_time:
                leave_status = 1
            else:
                leave_status = 0
        except Exception as e:
            leave_status = 0
        student_dict = {
            "id": self.id,
            "sno": self.sno,
            "school_roll_status": School_roll_type.query.get(self.school_roll_status_id).name,
            "class_id": self.class_id,
            "name": self.name,
            "sex": self.sex,
            "phone": self.phone,
            "dormitory_num": self.dormitory_num,
            "qq": self.qq,
            "email": self.email,
            "monitor": self.monitor,
            "face_img": constants.IMAGE_URL + self.face_img[10:] if self.face_img else "",
            "leave": leave_status,
            "g_m_cls_name": self.get_classes(),
            "cls_num": Classes.query.get(self.class_id).class_num

        }
        return student_dict

    def to_leave_dict(self, status):
        leave_li = Leave.query.filter(Leave.student_id == self.id, Leave.status == status)
        leaves = []
        for leave in leave_li:
            leaves.append(leave.to_full_dict())
        student_dict = {
            "leave": leaves,
            "class": Grade.query.join(grade_major_relation, grade_major_relation.c.grade_id == Grade.id).
                         join(Classes, Classes.grade_major_id == grade_major_relation.c.id).filter(Classes.id == self.class_id).
                         first().to_basic_dict()["name"] +
                     Major.query.join(grade_major_relation, grade_major_relation.c.major_id == Major.id).
                         join(Classes, Classes.grade_major_id == grade_major_relation.c.id).filter(Classes.id == self.class_id).
                         first().to_basic_dict()["name"] + Classes.query.get(self.class_id).to_basic_dict()["class_name"]
        }
        return student_dict

    def to_leave_status_dict(self):
        now = datetime.now()
        try:
            leave_status = Leave.query.filter(Leave.student_id == self.id,Leave.start_time.__le__(now),Leave.end_time.__ge__(now),Leave.status==1).first().to_basic_dict()
        except:
            leave_status = {"status":"未请假"}
        student_dict = {
            "id":self.id,
            "sno": self.sno,
            "name": self.name,
            "sex": self.sex,
            "qq": self.qq,
            "phone": self.phone,
            "class_id": Classes.query.get(self.class_id).to_basic_dict()['class_name'],
            "grade": Grade.query.join(grade_major_relation, grade_major_relation.c.grade_id == Grade.id).
                join(Classes, Classes.grade_major_id == grade_major_relation.c.id).filter(Classes.id == self.class_id).
                first().to_basic_dict()['name'],
            "major": Major.query.join(grade_major_relation, grade_major_relation.c.major_id == Major.id).
                join(Classes, Classes.grade_major_id == grade_major_relation.c.id).filter(Classes.id == self.class_id).
                first().to_basic_dict()['name'],
            "leave": leave_status
        }
        return student_dict

    def to_dict(self):
        student_dict = {
            "name": self.name,
            "sno": self.sno,
            "sex": self.sex,
            "phone": self.phone,
            "class_id": Grade.query.join(grade_major_relation, grade_major_relation.c.grade_id == Grade.id).
                            join(Classes, Classes.grade_major_id == grade_major_relation.c.id).filter(Classes.id == self.class_id).
                            first().to_basic_dict()["name"] + Classes.query.get(self.class_id).to_basic_dict()["class_name"],
        }
        return student_dict

    def get_stu_data(self):
        """
        学生端显示学生信息
        :return:
        """
        student_dict = {
            "sno": self.sno,
            "school_roll_status_id": School_roll_type.query.get(self.school_roll_status_id).name,
            "grade_major_class": self.get_classes(),
            "name": self.name,
            "sex": self.sex,
            "idcard_num": self.idcard_num,
            "phone": self.phone,
            "dormitory_num": self.dormitory_num,
            "leave_status": self.yes_no_leave(),
            "qq": self.qq,
            "email": self.email
        }
        return student_dict

    def yes_no_leave(self):
        """
        判断是否还在请假时间内
        :return:
        """
        import datetime
        n_time = datetime.datetime.now()
        times = Leave.query.filter_by(student_id=self.id).order_by(Leave.end_time.desc()).first()
        if times:
            end_time = times.end_time
            start_time = times.start_time
            if start_time < n_time < end_time and times.status == 1:
                return 1
            else:
                return 0
        else:
            return 0

    def first_get_data(self):
        """
        首次登陆补全信息时显示
        :return:
        """
        student_dict = {
            "sno": self.sno,
            "school_roll_status": School_roll_type.query.get(self.school_roll_status_id).name,
            "grade_major_class": self.get_classes(),
            "name": self.name,
            "class_num": Classes.query.get(self.class_id).class_num,
            "sex": self.sex
        }
        return student_dict

    def get_classes(self):
        # 返回当前学生的年级、专业、班级
        # 多对多查询 年级、专业、班级
        class_data = Classes.query.get(self.class_id)
        class_name = class_data.class_name
        # grade_relation为models中的db.relationship的名称
        grade_name = class_data.grade_relation.first().name
        major_name = class_data.major_relation.first().name

        grade_major_classes = {
            "grade_name": grade_name,
            "major_name": major_name,
            "class_name": class_name

        }

        return grade_major_classes

    def grade_major_classes(self):
        """
        宿舍考勤获取当前学生的年纪专业班级id以及辅导员id
        :return:
        """
        class_data = Classes.query.get(self.class_id)
        # grade_relation为models中的db.relationship的名称
        grade_id = class_data.grade_relation.first().id
        major_id = class_data.major_relation.first().id
        instructor_id = class_data.instructor_id

        grade_major_classes = {
            "grade_id": grade_id,
            "major_id": major_id,
            "class_id": self.class_id,
            "instructor_id": instructor_id

        }

        return grade_major_classes

    def to_teacher_basic_dict(self):
        '''教师端使用'''
        student_dict = {
            "id": self.id,
            "sno": self.sno,
            "school_roll_status": School_roll_type.query.get(self.school_roll_status_id).to_dict(),
            "class_id": Classes.query.get(self.class_id).to_teacher_dict(),
            "name": self.name,
            "sex": self.sex,
            "idcard_num": self.idcard_num,
            "phone": self.phone,
            "dormitory_num": self.dormitory_num,
            "face_img": constants.IMAGE_URL + self.face_img[10:] if self.face_img else "",
            "qq": self.qq,
            "email": self.email,
            "monitor": self.monitor,
        }
        return student_dict

    def to_teacher_full_dict(self):
        '''教师端使用'''
        student_dict = {
            "id": self.id,
            "sno": self.sno,
            "sex": self.sex,
            "class_id": Classes.query.get(self.class_id).to_teacher_basic_dict(),
            "name": self.name,
            "phone": self.phone,
            "dormitory_num": self.dormitory_num,
            "face_img": constants.IMAGE_URL + self.face_img[10:] if self.face_img else "",
        }
        return student_dict

    def tea_get_stu(self):
        """
        教师获得首页学生信息
        :return:
        """
        student_dict = {
            "id": self.id,
            "sno": self.sno,
            "sex": self.sex,
            "class_name": Classes.query.get(self.class_id).class_name,
            "name": self.name,
            "phone": self.phone,
            "dormitory_num": self.dormitory_num,
            # "face_img": constants.IMAGE_URL + self.face_img[10:] if self.face_img else "",
        }
        return student_dict

class Leave(db.Model):
    __tablename__ = 'leave'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    permit_person = db.Column(db.String(10), nullable=True)
    reason = db.Column(db.String(255), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id", ondelete="CASCADE"))
    status = db.Column(db.Integer, nullable=True, default=2)
    submit_time = db.Column(db.DateTime, nullable=True)

    def to_basic_dict(self):
        leave_dict = {
            "id": self.id,
            "status": "已请假" if self.status==1 else self.status,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "permit_person": self.permit_person,
            "submit_time": self.submit_time.strftime("%Y-%m-%d %H:%M:%S"),
            "reason": self.reason,
        }
        return leave_dict

    def to_full_dict(self):
        leave_dict = {
            "id": self.id,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "permit_person": self.permit_person,
            "reason": self.reason,
            "student": Student.query.filter(Student.id == self.student_id).first().name,
            "submit_time": self.submit_time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": self.status
        }
        return leave_dict

    def get_leave_stu(self):
        """
        获得学生请假记录
        :return:
        """
        leave_dict = {
            "student": Student.query.get(self.student_id).to_basic_dict(),
            "id": self.id,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "permit_person": self.permit_person,
            "reason": self.reason,
            "status": self.status,
            "submit_time": self.submit_time.strftime("%Y-%m-%d %H:%M:%S")
        }
        return leave_dict

    def get_leave_ins(self):
        """
        辅导员获得学生请假记录
        :return:
        """
        stu = Student.query.get(self.student_id)
        leave_dict = {
            "id": self.id,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "reason": self.reason,
            "status": self.status,
            "submit_time": self.submit_time.strftime("%Y-%m-%d %H:%M:%S"),
            "stu_name": stu.name,
            "cls": stu.get_classes(),
            "sid": self.student_id
        }
        return leave_dict

class Classroom_attendance(db.Model):
    __tablename__ = 'classroom_attendance'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    class_room = db.Column(db.String(11), nullable=True)
    course_class_id = db.Column(db.Integer, db.ForeignKey('course_class_relation.id', ondelete='CASCADE'))
    bssid = db.Column(db.String(20), nullable=True)
    nums = db.Column(db.Integer)

    def to_dict(self):
        classroom_attendance_dict = {
            "id": self.id,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "class_room": self.class_room,
            "course_class_id": Course.query.join(course_class_relation,
                                                 Course.id == course_class_relation.c.course_id).first().to_basic_dict(),
            "bssid": self.bssid
        }
        return classroom_attendance_dict

    def stu_get_data(self):
        """
        学生端获得开始考勤的课程信息
        :return:
        """
        ccr_c_course_id = course_class_relation.c.course_id
        ccr_c_id = course_class_relation.c.id
        course = Course.query.join(course_class_relation, ccr_c_course_id == Course.id).filter(
            ccr_c_id == self.course_class_id).first()

        classroom_attendance_dict = {
            "id": self.id,
            # "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            # "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "class_room": self.class_room,
            "teacher": Teacher.query.join(Course, Teacher.id == Course.teacher_id).join(
                course_class_relation, ccr_c_course_id == Course.id).filter(ccr_c_id == self.course_class_id).first().name,

            "course": course.name,
            "bssid": self.bssid,
        }

        return classroom_attendance_dict

    def to_basic_dict(self):
        classroom_attendance_dict = {
            "id": self.id,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        return classroom_attendance_dict

    def to_teacher_basic_dict(self):
        '''教师端使用'''
        classroom_attendance_dict = {
            "id": self.id,
            "course_class_id": Course.query.join(course_class_relation,
                                                 course_class_relation.c.course_id == Course.id).filter
            (course_class_relation.c.id == self.course_class_id).first().to_teacher_dict(),
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "nums": self.nums,
        }
        return classroom_attendance_dict

    def to_teacher_dict(self):
        '''教师端使用'''
        classroom_attendance_dict = {
            "id": self.id,
            "course_class_id": Course.query.join(course_class_relation,
                                                 course_class_relation.c.course_id == Course.id).filter
            (course_class_relation.c.id == self.course_class_id).first().to_teacher_dict(),
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S")[:13],
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "nums": self.nums,
        }
        return classroom_attendance_dict

    def to_teacher_num_dict(self):
        '''教师端使用'''
        classroom_attendance_dict = {
            "nums": self.nums,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S")[:13],
        }
        return classroom_attendance_dict


class Stu_classroom_atten_res(db.Model):
    __tablename__ = 'stu_classroom_atten_res'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', ondelete='CASCADE'))
    classroom_attendance_id = db.Column(db.Integer, db.ForeignKey('classroom_attendance.id', ondelete='CASCADE'))
    time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.Integer, nullable=True)
    class_id = db.Column(db.Integer, nullable=True)
    major_id = db.Column(db.Integer, nullable=True)
    cource_id = db.Column(db.Integer, nullable=True)
    teacher_id = db.Column(db.Integer, nullable=True)

    def to_dict(self):
        classroom_attendance_dict = {
            "id": self.id,
            "student_id ": Student.query.get(self.student_id).to_basic_dict()['name'],
            "time": self.time.strftime("%Y-%m-%d %H:%M:%S"),
            "classroom_attendance_id": Classroom_attendance.query.filter(
                Classroom_attendance.id == self.classroom_attendance_id).first().to_dict(),
            "status": self.status,
        }
        return classroom_attendance_dict

    def stu_get_record(self):
        """
        返回给学生端的教室考勤记录
        :return:
        """
        course = Course.query.get(self.cource_id)
        teacher = Teacher.query.get(self.teacher_id)
        classroom_attendance_dict = {
            "time": self.time.strftime("%Y-%m-%d"),
            "status": self.status,
            # "course_name": course.name,
            "teacher_name": teacher.name,
            "course_room": Classroom_attendance.query.get(self.classroom_attendance_id).class_room
        }
        return classroom_attendance_dict

    def stu_get_course(self):
        """
        返回课程名和课程id
        :return:
        """
        course_data = {
            "course_id": self.cource_id,
            "course_name": Course.query.get(self.cource_id).name
        }
        return course_data

    def to_teacher_dict(self):
        '''教师端使用'''
        classroom_attendance_dict = {
            "id": self.id,
            "student_id": Student.query.get(self.student_id).to_teacher_full_dict(),
            "time": self.time.strftime("%Y-%m-%d %H:%M:%S"),
            "classroom_attendance_id": self.classroom_attendance_id,
        }
        return classroom_attendance_dict

class DormitoryAttendance(db.Model):
    """
    宿舍考勤数据表
    """
    __tablename__ = 'dormitory_atten'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', ondelete='CASCADE'))
    attendance_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.Integer, nullable=True)
    class_id = db.Column(db.Integer, nullable=True)
    major_id = db.Column(db.Integer, nullable=True)
    grade_id = db.Column(db.Integer, nullable=True)
    instructor_id = db.Column(db.Integer, nullable=True)
    time = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        dormitory_attendance_dict = {
            "id": self.id,
            "student": Student.query.get(self.student_id).to_dict(),
            "attendance_time": self.attendance_date.strftime("%Y-%m-%d"),
            "student_id": self.student_id
        }
        return dormitory_attendance_dict

    def ins_get_record(self):
        """
        辅导员端获得考勤信息
        :return:
        """
        dormitory_attendance_dict = {
            "id": self.id,
            "student": Student.query.get(self.student_id).to_dict(),
            "status": self.status
        }
        return dormitory_attendance_dict

    def get_stu_record(self):
        """
        学生端获得本人的所有考勤记录
        :return:
        """
        l_date = Leave.query.order_by(-Leave.end_time).filter_by(student_id=self.student_id).first()
        dormitory_attendance_dict = {
            "date": self.time.strftime("%Y-%m-%d %H:%M:%S") if self.time else self.attendance_date.strftime("%Y-%m-%d"),
            "status": self.status,
            "leave_date": l_date.end_time.strftime("%Y-%m-%d") if l_date else None,
        }
        return dormitory_attendance_dict


class TokenKey(db.Model):
    """
    获得access_token的key值表
    """
    __tablename__ = 'tokenKey'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    app_id = db.Column(db.Integer, nullable=False)
    api_key = db.Column(db.String(50), nullable=False)
    secret_key = db.Column(db.String(50), nullable=False)
    access_token = db.Column(db.String(200), nullable=False)


class Equipment_info(db.Model):
    __tablename__ = 'equipment_info'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    classroom = db.Column(db.String(255), nullable=False)
    dormitory = db.Column(db.String(255), nullable=False)
    passwd = db.Column(db.String(255), nullable=False)

    def to_teacher_base_dict(self):
        course_dict = {
            "id": self.id,
            "classroom": self.classroom,
        }
        return course_dict

    def to_stu_base_dict(self):
        dormitory_dict = {
            "id": self.id,
            "dormitory": self.dormitory,
        }
        return dormitory_dict

class Banner(db.Model):
    __tablename__ = 'banner'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    image = db.Column(db.String(255), nullable=True)
    role = db.Column(db.Integer, nullable=True)

    def to_basic_dict(self):
        banner_dict = {
        "url": constants.IMAGE_URL+self.image if self.image else "",
        "id": self.id ,
        "role": self.role if self.role else ""
         }
        return  banner_dict