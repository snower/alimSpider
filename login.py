# -*- coding: utf-8 -*-
# 14/10/15
# create by: snower

import os
import time
import json
import hashlib
from cStringIO import StringIO
import argparse
import threading
import requests
from PIL import Image
from selenium import webdriver
from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler

def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

parser = argparse.ArgumentParser(description='audo login alimama')
parser.add_argument('-u', dest='username', help='alimama username')
parser.add_argument('-p', dest='password', help='alimama password')
parser.add_argument('-i', dest='index_url', default="http://pub.alimama.com/myunion.htm", help='login index url')
parser.add_argument('-H', dest='bind_host', default='0.0.0.0', help='api bing host (default: 0.0.0.0)')
parser.add_argument('-P', dest='bind_port', default=0, type=int, help='api bing port (default: 0) if port is 0, it will not bind')
parser.add_argument('-s', dest='session_filename', default="cookies.json", help='session cookies save fileame (default: cookies.json)')
parser.add_argument('-o', dest='cookies_fileanme', default='', help='login cookies output fileame (default: stdout)')
parser.add_argument('-D', dest='demon_mod', default=False, type=str2bool, nargs='?', const=True, help='demon')
parser.add_argument('-t', dest='refresh_time', default=900, type=int, help='refresh time (default: 900s)')

args = parser.parse_args()

username = args.username
password = args.password
success_url = args.index_url
bind_host = args.bind_host
bind_port = args.bind_port
session_filename = os.path.abspath(args.session_filename)
cookies_fileanme = args.cookies_fileanme or ''
demon_mod = args.demon_mod
refresh_time = args.refresh_time

if cookies_fileanme:
    cookies_fileanme = os.path.abspath(cookies_fileanme)

class QRcode:
    def __init__(self, image, width=33, height=33):
        self.image = image
        self.width = width
        self.height = height
        self.white_block = '\033[0;37;47m   '
        self.black_block = '\033[0;37;40m   '
        self.new_line = '\033[0m\n'

    def show(self):
        img = Image.open(self.image)
        img = img.resize((self.width, self.height), Image.NEAREST)
        img = img.convert('L')
        text = self.white_block * (self.width + 4) + self.new_line
        text += self.white_block * (self.width + 4) + self.new_line
        for w in range(self.width):
            text += self.white_block * 2
            for h in range(self.height):
                res = img.getpixel((h, w))
                text += self.white_block if res >= 128 else self.black_block
            text += self.white_block * 2 + self.new_line
        text += self.white_block * (self.width + 4) + self.new_line
        text += self.white_block * (self.width + 4) + self.new_line
        return text

class Spider(object):
    def __init__(self):
        self.web_options = webdriver.ChromeOptions()
        self.web_options.add_argument('--headless')
        self.web_options.add_argument('--disable-gpu')
        self.web = webdriver.Chrome(chrome_options=self.web_options)
        self.web.set_window_size(1920, 980)
        self.cookies = ''
        self.login_succed = False

    def get_user_id(self):
        return hashlib.md5(username.encode("utf-8")).hexdigest()

    def load_cookies(self):
        try:
            with open(session_filename) as fp:
                session = json.load(fp)
                user_id = self.get_user_id()
                if user_id in session:
                    cookies = session[user_id]
                    for cookie in cookies:
                        self.web.add_cookie(cookie)
                    print 'load cookies'
        except Exception as e:
            print 'load cookies error', e

    def save_cookies(self):
        user_id = self.get_user_id()

        session = {}
        try:
            with open(session_filename) as fp:
                session = json.load(fp)
                if not dict(session):
                    session = {}
        except Exception as e:
            pass

        cookies = self.web.get_cookies()
        session[user_id] = cookies
        with open(session_filename, "w") as fp:
            json.dump(session, fp)

        fcookies = []
        for cookie in cookies:
            fcookies.append("%s=%s" % (cookie["name"], cookie["value"]))
        self.cookies = ";".join(fcookies)

        if not cookies_fileanme:
            print
            print '*' * 8 + "COOKIES" + "*" * 8
            print self.cookies
            print '*' * 8 + "COOKIES" + "*" * 8
            print
        else:
            try:
                with open(cookies_fileanme, "w"):
                    fp.write(self.cookies.encode("utf-8"))
            except Exception as e:
                print "output error", e
        print 'save cookies'

    def show_qrcode(self):
        J_QRCodeImg = self.web.find_element_by_id('J_QRCodeImg')
        while not J_QRCodeImg.is_displayed():
            time.sleep(0.05)
        J_QRCodeImg_url = ''
        while not J_QRCodeImg_url:
            J_QRCodeImg = J_QRCodeImg.find_element_by_tag_name("img")
            while not J_QRCodeImg.is_displayed():
                time.sleep(0.05)
            J_QRCodeImg_url = J_QRCodeImg.get_attribute("src")
            if not J_QRCodeImg_url:
                time.sleep(0.05)
        print 'scan qrcode', J_QRCodeImg_url

        self.save_cookies()
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 5.0; SM-G900P Build/LRX21T) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Mobile Safari/537.36",
            "Cookie": self.cookies
        }
        res = requests.get(J_QRCodeImg_url, headers = headers)
        if res.ok:
            img = StringIO(res.content)
            qrcode = QRcode(img, 46, 46)
            print qrcode.show()

    def login(self):
        self.web.get("http://pub.alimama.com/")
        self.load_cookies()
        url = 'http://pub.alimama.com/myunion.htm'
        print "load", url
        self.web.get(url)
        if self.web.current_url == success_url:
            print 'login success'
            self.login_succed = True
            self.save_cookies()
        elif self.web.current_url != url:
            print "redirect login", self.web.current_url
            taobaoLoginIfr = self.web.find_elements_by_name("taobaoLoginIfr")
            if taobaoLoginIfr:
                url = taobaoLoginIfr[0].get_attribute("src")
                print 'load', url
                self.web.get(url)
                self.web.find_element_by_class_name('login-switch').click()
                self.web.find_element_by_id('TPL_username_1').send_keys(username)
                self.web.find_element_by_id('TPL_password_1').send_keys(password)
                print "login", self.web.find_element_by_id('TPL_username_1').get_attribute("value"), self.web.find_element_by_id('TPL_password_1').get_attribute("value")
                self.web.find_element_by_id('J_SubmitStatic').click()
                if self.web.current_url.startswith('https://login.taobao.com/member/login.jhtml'):
                    print "start qrcode login", self.web.current_url
                    J_Static2Quick = self.web.find_element_by_id('J_Static2Quick')
                    if J_Static2Quick.is_displayed():
                        J_Static2Quick.click()

                    self.show_qrcode()
                    while True:
                        if self.web.current_url == success_url:
                            print 'login success'
                            self.login_succed = True
                            self.save_cookies()
                            break
                        J_QRCodeRefresh = self.web.find_element_by_class_name('J_QRCodeRefresh')
                        if J_QRCodeRefresh.is_displayed():
                            J_QRCodeRefresh.click()
                            self.show_qrcode()
                        time.sleep(1)

    def quit(self):
        self.web.quit()

class CookiesRequestHandler(RequestHandler):
    def get(self):
        self.write(spider.cookies.encode("utf-8"))

def start_server():
    app = Application([
        (r"/.*", CookiesRequestHandler),
    ])
    app.listen(bind_port, bind_host)
    IOLoop.current().start()

if __name__ == '__main__':
    if bind_port:
        server_thread = threading.Thread(target=start_server)
        server_thread.setDaemon(True)
        server_thread.start()

    spider = Spider()
    spider.login()
    if demon_mod:
        while True:
            time.sleep(refresh_time)
            print "start refresh"
            spider.login()
            print "end refresh"
    else:
        spider.quit()