# -*- coding:utf-8 -*-
import datetime

from attendance.models import Classroom_attendance, course_class_relation, Classes, Student, Stu_classroom_atten_res

__author__ = 'zdt'
__date__ = '2019/3/6 20:42'


def class_att_time_check(username):
    """
    获得考勤课程对象
    :param cid:
    :return:
    """
    cid = Classes.query.get(Student.query.filter_by(sno=username).first().class_id).id
    n_time = datetime.datetime.now()
    # 判断当前本班所有课程现在开始的考勤，且当前时间在考勤时间段内
    attendance = Classroom_attendance.query.join(
        course_class_relation, course_class_relation.c.id == Classroom_attendance.course_class_id).filter(
        course_class_relation.c.class_id == cid,
        Classroom_attendance.start_time < n_time, Classroom_attendance.end_time > n_time).all()

    return attendance


def class_att(sid, course_id):
    """
    获得某门课的考勤信息
    :param sid:
    :param course_id:
    :return:
    """
    # 获得当前学生以及该课程下的考勤记录
    stu_course_record = Stu_classroom_atten_res.query.filter(
        Stu_classroom_atten_res.student_id == sid.id, Stu_classroom_atten_res.cource_id == course_id).order_by(-Stu_classroom_atten_res.time).all()
    # 分离考勤成功、未考勤以及请假记录
    attendance_success = 0
    attendance_failed = 0
    attendance_leave = 0
    stu_course_record_all = []
    for stu in stu_course_record:
        s = stu.stu_get_record()
        if stu.status == 1 or stu.status == 3:
            attendance_success += 1
        elif stu.status == 0:
            attendance_failed += 1
        elif stu.status == 2:
            attendance_leave += 1
        stu_course_record_all.append(s)

    # 获得考勤次数，缺勤次数，请假次数，以及考勤率
    # 总次数
    total_attendance = len(stu_course_record)
    attendance_rate = "%.2f%%" % (attendance_success / total_attendance * 100)
    attendance_data = {
        "stu_course_record_all": stu_course_record_all,
        "attendance_rate": attendance_rate,
        "attendance_success": attendance_success,
        "attendance_failed": attendance_failed,
        "attendance_leave": attendance_leave
    }

    return attendance_data
