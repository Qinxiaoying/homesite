# coding:utf8
from flask import flash, render_template


def flash_alert(msg,typename="success"):
    msg_in_type = render_template('__alert.html', msg=msg, typename=typename)
    return flash(msg_in_type)