import base64
import os

from attendance import db
from attendance.face_token import face
from attendance.face_token.face_check import face_m
from attendance.models import Student
from pypinyin import lazy_pinyin

__author__ = 'zdt'
__date__ = '2019/2/28 10:40'


# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.getcwd()


def face_upload(img, sno):
    """
    上传照片以及保存
    :param img:
    :param sno:
    :return:
    """
    access_token = face_m()

    # img = request.files.get('file')
    # sno = request.form.get("sno")
    # 多对多查询 年级、专业、班级
    student_data = Student.query.filter_by(sno=sno).first()
    grade_major_classes = student_data.get_classes()

    class_name = grade_major_classes['class_name']
    # grade_relation为models中的db.relationship的名称
    grade_name = grade_major_classes['grade_name']
    major_name = grade_major_classes['major_name']

    # 拼接路由，path为相对路径 static/....
    path = 'attendance/static/upload/{}/'.format(grade_name) + '{}/'.format(major_name) + '{}/'.format(class_name)
    path = ''.join(lazy_pinyin(path))

    if not os.path.exists(path):
        os.makedirs(path)

    # 绝对路径
    img_dir = os.path.join(os.path.join(BASE_DIR, '{}'.format(path)), '{}.jpg'.format(sno))
    # 判断是否有旧的照片，如果有，则用a_buf保存其二进制流
    if os.path.exists(img_dir):
        with open('{}'.format(img_dir), 'rb') as f:
            a_buf = f.read()
    else:
        a_buf = b''
    # 保存照片，地址为img_dir
    img.save(img_dir)
    with open('{}'.format(img_dir), 'rb') as f:
        img_buf = f.read()

    code = face.check_pic_quality(img_buf, access_token)

    # 将照片路径上传个人信息, 保存进数据库，照片原图保存本地
    if code == 0:
        img_path = path + '{}.jpg'.format(sno)

        student_data.face_img = img_path
        db.session.commit()

        return code
    else:
        os.remove(img_dir)
        with open('{}'.format(img_dir), 'wb') as f:
            f.write(a_buf)
        return 404


def face_login(img, username):
    """
    人脸识别
    :param img: 前端传输照片
    :param img_root: 底片照片
    :return:
    """

    # 获得底片路径
    result = Student.query.filter_by(sno=username).first()
    img_root = result.face_img
    student_id = result.id

    access_token = face_m()

    # 将二进制流照片转换为base64
    img_64 = base64.b64encode(img)
    # 调用识别函数
    code = face.check_face(img_64, img_root, access_token)
    return code, student_id
