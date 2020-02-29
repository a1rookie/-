# -*- coding:utf-8 -*-
import datetime

from attendance import db
from attendance.models import Student, Dormitory_atten, Classes, Department

__author__ = 'zdt'
__date__ = '2019/3/8 13:58'


def time_task():
    """
    定时任务，每天宿舍考勤前十分钟，将所有学生信息写入宿舍考勤记录表
    :return:
    """
    # 获得在读学生的信息
    stu = Student.query.filter_by(school_roll_status_id=1).all()
    pause_time = Department.query.get(1)
    n_time = datetime.datetime.now()
    start_time = pause_time.pause_start_time
    end_time = pause_time.pause_time

    if start_time < n_time < end_time:
        # 在暂停考勤时间内
        return 0
    else:
        # 不在暂停考勤时间内
        yes_leave_stu = []
        no_leave_stu = []

        # 分离请假和未请假的学生
        for i in stu:
            status = i.yes_no_leave()
            # 判断是否需要考勤
            class_status = Classes.query.get(i.class_id).whether_attendance
            # 若等于0，则直接跳过不用写入宿舍考勤表
            if class_status == 0:
                continue
            if status == 1:
                yes_leave_stu.append(i)
            else:
                no_leave_stu.append(i)

        dormitory_yes_list = []
        today = datetime.date.today()

        for stu in yes_leave_stu:
            # 获得当前学生的年纪专业班级id以及辅导员id
            grade_major_classes = stu.grade_major_classes()
            # 生成dormitory对象即宿舍考勤对象
            dormitory = Dormitory_atten()
            dormitory.student_id = stu.id
            dormitory.instructor_id = grade_major_classes['instructor_id']
            dormitory.grade_id = grade_major_classes['grade_id']
            dormitory.major_id = grade_major_classes['major_id']
            dormitory.class_id = grade_major_classes['class_id']
            dormitory.status = 2
            dormitory.attendance_data = today
            dormitory_yes_list.append(dormitory)

        db.session.add_all(dormitory_yes_list)
        db.session.commit()

        dormitory_no_list = []

        for stu in no_leave_stu:
            # 获得当前学生的年纪专业班级id以及辅导员id
            grade_major_classes = stu.grade_major_classes()
            # 生成dormitory对象即宿舍考勤对象
            dormitory = Dormitory_atten()
            dormitory.student_id = stu.id
            dormitory.instructor_id = grade_major_classes['instructor_id']
            dormitory.grade_id = grade_major_classes['grade_id']
            dormitory.major_id = grade_major_classes['major_id']
            dormitory.class_id = grade_major_classes['class_id']
            dormitory.attendance_data = today
            dormitory_no_list.append(dormitory)

        db.session.add_all(dormitory_no_list)
        db.session.commit()

        return 0
