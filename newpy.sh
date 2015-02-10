#! /bin/sh

# python 模板  用于创建一个新的python文件

filename=$1

sed -e "s/testname/$filename/g" /opt/caldata/mycode/pytemple.py > $filename.py
