#! /usr/bin/python
# -*- coding:utf-8 -*-

import re
import smtplib
import time ,datetime
from email.mime.text import MIMEText
import os


# *********************************************************************************************************
"""
                        alvis 使用简介
 包含两个类： nginxParser nginxDownload

 nginxParser 类

 输入参数：
 @1 记录 line
 @2 接口名列表 action_strict  默认是空列表:输出所有接口信息,如列表非空，输出指定接口信息。
 @3 字段输出列表 out_attr_strict 默认是空列表:输出包含所有字段的字典，如列表非空，输出字段列表。

 使用注意：

  -1- 接口名 和 字段名 列表均可以缺省。
  -2- 初始化后，首先应该判断isvalid (解析成功 True  解析失败 False)
  -3- 字段名（out_attr_strict） 为空时输出是字典 ，非空时输出是列表
  _4- attrdict函数调用后返回结果，第一步是判断是否为空（可能是{} 或者[]）

 类可调用参数：

 属性：
 isvalid :         解析是否成功
 ip:               日志首个ip
 responseTime      请求反应时间
 actionName        接口名称


 方法：
 dt()              获取timestamp 信息
 attrdict()        获取字段信息（输出参数限制：列表 ，无限制：字典）

*******************************************************************************************************

 nginxDownload 类

 目的：快捷下载晓宁备份的数据

 输入参数：
 @1 date ,             下载日期
 @2 store_dir ,        文件存储路径 , 外层目录，不需要到服务器文件夹
 @3 application ,      下载的日志所属应用名称
 @4 server_set ,       日志服务器编号列表
 @5 logging            为了监测下载状态，输入logging对象


 参数列表：

- 无明显需求

 方法：

 execute()          开始执行下载
 ******************************************************************************************************

alvisMail 类

目的：当工作流出现重大问题时，及时想管理者发送邮件提醒


输入参数：
 @1 sub ,             邮件主题内容
 @2 content ,         邮件正文主要内容
 @3 logging ,         监测发送邮件是否成功


方法：
sendmail()
                                                                                                         """
#**********************************************************************************************************

                ########################### 类定义 #######################################

class nginxParser:
    """
    处理公司的nginx日志
    """
    def __init__(self , line , action_strict=[] , out_attr_strict=[]):
        linelist = line.split(" ")

        self.isvalid , session_type , self.operationTime  = True , linelist[5][1:] , linelist[3][1:]
        self.ip , self.responseTime = linelist[0] , linelist[12]

        if session_type == "GET":
            try:
                self.actionName , self.attrString = linelist[6].split("?")
            except:
                self.isvalid = False
        elif session_type == "POST":
            self.actionName , self.attrString = linelist[6] , linelist[8][1:-1]
        else:
            self.isvalid =  False

        if self.isvalid:
            self.out_attr_strict = out_attr_strict
            if action_strict and self.actionName not in action_strict:
                self.isvalid = False


    def dt(self):
        try:
            date = time.strptime(self.operationTime,'%d/%b/%Y:%H:%M:%S')
            timestamp = time.mktime(date)
        except:
             return 0
        return timestamp

    def hour(self):
        try:
            hour = self.operationTime[12:14]
        except:
             return 0
        return hour



    def attrDict(self):
        attr = {}
        for fieldString in self.attrString.split("&"):
            try:
                name , value = fieldString.split("=")
                name = "errorcode" if name == "errCode" else name
                attr[name] = value
            except:
                attr = {}

        if attr:
            if not self.out_attr_strict:
                outputdic = attr
            else:
                outputdic = [attr.get(k , "") for k in self.out_attr_strict]
            return outputdic
        else:
            return {}


class nginxDownload:
    """
    用于下载晓宁备份的nginx日志
    """
    def __init__(self , date , application , store_dir , server_set , logging):
        self.date , self.store_dir , self.application , self.server_set = date , store_dir , application , server_set
        self.shaped_date = alter_format(self.date, "%Y-%m-%d" ,"%Y%m%d")
        self.logging = logging

    def execute(self):
        if not os.path.exists(self.store_dir):
            os.makedirs(self.store_dir)

        for server in self.server_set:
            for hour in range(24):
                hour_view = "0%d"%hour if hour < 10 else "%d"%hour
                filename = "%s_access.log_%s-%s.log"%(self.application ,self.date , hour_view)

                operator="wget -nv 'http://10.6.6.180:60500/gz_front0%d/%s/%s/%s' &> /dev/null"%(server , self.application , \
                self.shaped_date , filename)

                store_server_dir = "/".join([self.store_dir , "0%d"%server])
                if os.path.exists(store_server_dir):
                    os.chdir(store_server_dir)
                else:
                    os.mkdir(store_server_dir)
                    os.chdir(store_server_dir)

                if not os.path.exists(filename):
                    result = os.system(operator)
                    if not result:
                        self.logging.info("download successful in server:%d , hour:%d"%(server , hour))
                    else:
                        self.logging.error("download operator failed!")
                else:
                    self.logging.info("file in server: %d , hour: %s exists"%(server , hour_view))

    def delete(self):
        for server in self.server_set:
            for hour in range(24):
                hour_view = "0%d"%hour if hour < 10 else "%d"%hour
                filename = "%s_access.log_%s-%s.log"%(self.application ,self.date , hour_view)
                operator="rm -rf %s"%filename
                store_server_dir = "/".join([self.store_dir , "0%d"%server])
                if os.path.exists(store_server_dir):
                    os.chdir(store_server_dir)
                else:
                    os.mkdir(store_server_dir)
                    os.chdir(store_server_dir)
                if os.path.exists(filename):
                    os.system(operator)


class alvisMail:
    """
    自定义邮件发送模块，用于发送关键错误信息
    """
    def __init__(self , sub , content , logging):
        self.mailto_list=["xiaokepi@126.com"]
        self.mail_host="smtp.qq.com:25"  #设置服务器
        self.mail_user="453609216"    #用户名
        self.mail_pass="tk4479"   #口令
        self.mail_postfix="qq.com"  #发件箱的后缀
        self.sub = sub
        self.content = content
        self.logging = logging

    def sendmail(self):  #to_list：收件人；sub：主题；content：邮件内容
        """
        模块导入放这里不知道是否合理。。。。
        """


        me="alvis_alert"+"<"+self.mail_user+"@"+self.mail_postfix+">"   #这里的hello可以任意设置，收到信后，将按照设置显示

        real_content = """
        <html>
        <body>
        <h3>主题信息：%s</h3>
        <p>流程出错：</p>
        <p>%s</p>
        </body>
        </html>
        """%(self.sub , self.content)

        msg = MIMEText(real_content , _subtype='html' , _charset='utf-8')    #创建一个实例，这里设置为html格式邮件
        msg['Subject'] = self.sub    #设置主题
        msg['From'] = me
        msg['To'] = ";".join(self.mailto_list)
        try:
            s = smtplib.SMTP()
            s.connect(self.mail_host)  #连接smtp服务器
            s.login(self.mail_user,self.mail_pass)  #登陆服务器
            s.sendmail(me, self.mailto_list, msg.as_string())  #发送邮件
            s.close()
            status = True
        except Exception, e:
            status = False
        if status:
            self.logging.error("已向您的126邮箱成功发送信息")
        else:
            self.logging.error("向您的邮箱发送邮件时发生错误了")


                ############################# 方法定义 ############################################

def toDate(dateString , format="" , is_date=True):
    if not format:
        dt = datetime.datetime.strptime(dateString , "%Y-%m-%d")
    else:
        dt = datetime.datetime.strptime(dateString , format)
    if is_date:
        return dt.date()
    return dt


def previous_n(dateString , n , format=""):
    if not format:
        dt = datetime.datetime.strptime(dateString , "%Y-%m-%d").date()
    else:
        dt = datetime.datetime.strptime(dateString , format).date()
    delta = datetime.timedelta(days=n)
    return str(dt-delta)


def toTimestamp(dateString , format=""):
    #ngnix format '%d/%b/%Y:%H:%M:%S'
    if not format:
        date = time.strptime(dateString ,'%Y-%m-%d %H:%M:%S')
    else:
        date = time.strptime(dateString , format)

    return time.mktime(date)

def alter_format(dateString , previouse_format , current_format):
    dt = datetime.datetime.strptime(dateString , previouse_format).date()
    return datetime.datetime.strftime(dt , current_format)


                ########################### 数据结构重定义 ##########################################


class multi_dict(dict):
    """
    重新定义了dict ，使得多层字典使用时，不再需要初始化
    """
    def __missing__(self , key):
        self[key] = multi_dict()
        return self[key]


if __name__ == "__main__":
    pass
