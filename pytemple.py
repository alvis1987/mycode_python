#! /usr/bin/python
# -*- coding:utf-8 -*-

import logging
logging.basicConfig(level=logging.DEBUG,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                datefmt='%a, %d %b %Y %H:%M:%S',
                filename='log_testname.log',
                filemode='a')

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('[行数:%(lineno)d] 函数:%(funcName)s - -信息:%(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

import sys
sys.path.append("/opt/caldata/mycode")
from alvis import *


def main():
    pass


if __name__ == "__main__":
    main()

