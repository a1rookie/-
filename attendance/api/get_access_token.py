# -*- coding: utf-8 -*-
import urllib
import urllib.request
import sys
import ssl

import flask
from flask_jwt_extended import jwt_required

from attendance.api import api
from attendance.models import TokenKey
from attendance.utils.commons import login_required


@api.route('/get_token', methods=['GET'])
@jwt_required
@login_required
def get_token():
    if flask.request.method == 'GET':
        code = 0
        keys = TokenKey.query.all()
        for key in keys:
            host = 'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&' \
                   'client_id=%s&client_secret=%s' % (key.api_key, key.secret_key)
            request = urllib.request.Request(host)
            request.add_header('Conten-Type', 'application/json;charset=UTF-8')
            response = urllib.request.urlopen(request)

            content = response.read()
            if content:
                true_content = eval(content)['access_token']
                TokenKey.query.filter_by(id=key.id).update({'access_token': true_content})
                code = 200
        return flask.jsonify({'code': code})

