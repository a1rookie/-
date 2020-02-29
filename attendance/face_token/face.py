# -*- coding: utf-8 -*-
import base64
import json
from attendance.face_token.face_check import img_bs, check
from attendance.models import TokenKey


def get_img(img):
    img = base64.b64encode(img)
    param = "{\"image\": \"" + img.decode() + "\", \"image_type\": \"BASE64\", \"face_field\": \"quality\"}"
    param = bytes(param, encoding="utf8")

    return param


def check_pic_quality(filePath, access_token):
    """返回值：0照片正常，可用
       --------1图片无人脸
       --------2其他错误原因
       --------3图片中有多张人脸
       --------4人脸质量不佳
       --------5人脸有遮挡
       --------6人脸过小
       --------7图片文件打开失败"""
    from manage import app
    param = get_img(filePath)
    if param == 1:
        return 7
    url = app.config['FACE_URL'] + "detect?access_token=" + access_token
    content = check(url, param)
    # request = urllib.request.Request(url=url, data=param)
    # request.add_header('Content-Type', 'application/json')
    # response = urllib.request.urlopen(request)
    # content = response.read()

    if content:
        print(content)
        content = eval(str(content, encoding="utf8").replace("null", "None"))
        # 没有人脸
        if content["error_code"] == 222202:
            return 1
        # 其他错误
        if content["error_code"] != 0:
            return 2

        face_list = content["result"]["face_list"][0]
        quality = face_list["quality"]
        angle = face_list["angle"]
        location = face_list["location"]
        occlusion = face_list["quality"]["occlusion"]

        # 多张人脸
        if content["result"]["face_num"] != 1:
            return 3
        # 人脸质量不佳
        if quality["blur"] > 0.7 or quality["illumination"] < 40 or angle["yaw"] > 20 or quality["completeness"] == 0 \
                or angle["roll"] > 20 or angle["pitch"] > 20:
            return 4
        # 人脸有遮挡
        if occlusion["right_eye"] > 0.6 or occlusion["nose"] > 0.7 or occlusion["mouth"] > 0.7 or \
                occlusion["left_cheek"] > 0.8 or occlusion["right_cheek"] > 0.8 or occlusion["chin_contour"] > 0.6:
            return 5
        # 人脸大小过小
        if location["height"] <= 100 or location["width"] <= 100:
            return 6

        return 0
"""
def get_imgs(filepath1, filepath2):
    try:
        file1 = open(filepath1, 'rb')
        file2 = open(filepath2, 'rb')
    except OSError:
        print("打开照片文件失败")
        return 1
    img1 = base64.b64encode(file1.read())
    img2 = base64.b64encode(file2.read())

    params = json.dumps(
        [{"image": img1.decode(), "image_type": "BASE64"},
         {"image": img2.decode(), "image_type": "BASE64"}]
    )
    # params = {"images": img1.decode() + ',' + img2.decode()}
    # params = urllib.parse.urlencode(params).encode(encoding='UTF-8')
    file1.close()
    file2.close()
    params = bytes(params, encoding="utf8")
    return params
"""


def check_face(new_file, old_file, access_token):
    # 阀值为80
    """返回值 0为人脸比对成功
       -------1为照片打开错误
       -------2为QPS超限
       -------3活体检测失败
       -------4人脸比对错误，例如参数错误，无人脸、遮挡，等等
       -------5非同一个人"""
    from manage import app
    url = app.config['FACE_URL'] + "match?access_token=" + access_token

    params = check_b64(new_file, old_file)
    if params == 1:
        return 1
    content = check(url, params)

    if content:
        content = eval(str(content, encoding="utf8").replace("null", "None"))
        # print(content)
        if content["error_code"] == 18:
            return 2
        if content["error_code"] == 223120:
            return 3
        if content["error_code"] != 0:
            return "errno:" + content["error_code"]
        if content["result"]["score"] < 80:
            return 5
        return 0


def check_b64(fileb64, file_path):
    img = img_bs(file_path)
    params = json.dumps([{"image": fileb64.decode(), "image_type": "BASE64", "liveness_control": "NORMAL"},
                         {"image": img.decode(), "image_type": "BASE64"}])
    params = bytes(params, encoding="utf8")

    return params



