#! C:\Python36\python.exe
# coding:utf-8
import json
import re
from _md5 import md5
from json import JSONDecodeError
from multiprocessing.pool import Pool
from urllib.parse import urlencode

import os
import pymongo
from bs4 import BeautifulSoup
from requests.exceptions import RequestException
import requests
from project.config import *

client = pymongo.MongoClient(MONGO_URL, connect=False)  # 创建mongodb对象,connect为了防止警告
db = client[MONGO_DB]  # 创建数据库


# 获取页面内容,offset为偏移量,keyword为关键字
def getPageIndex(offset, keyword):
    # get请求所附带的信息
    data = {
        'offset': 0,
        'format': 'json',
        'keyword': '街拍',
        'autoload': 'true',
        'count': '20',
        'cur_tab': 3,  # 图集面板
        'from': 'gallery'
    }
    url = 'https://www.toutiao.com/search_content/?' + urlencode(data)  # 将字典转换为字符串
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求索引页出错')
        return None


def parsePageIndex(html):
    try:
        data = json.loads(html)  # 将json转换为字典
        if data and 'data' in data.keys():  # 判断data是否为空和'data'键是否存在
            for item in data.get('data'):
                yield item.get('article_url')  # 返回url的生成器
    except JSONDecodeError:
        pass


# 获得每一个url的内容
def getPageDetail(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求详情页出错', url)
        return None


# 解析页面内容
def parsePageDetail(html, url):
    soup = BeautifulSoup(html, 'lxml')  # 新建一个BeautifulSoup对象
    title = soup.select('title')[0].get_text()  # 找到标题
    print(title)
    # 正则匹配正文的json信息
    imgPattern = re.compile('gallery: JSON.parse\((.*?)\),', re.S)
    result = re.search(imgPattern, html)
    if result:
        # print(result.group(1))
        print("---------------------------------")
        data = json.loads(result.group(1))  # 转换为json字符串
        data = json.loads(data)  # 转换为字典
        # print(data)
        # print(type(data))
        if data and 'sub_images' in data.keys():
            sub_images = data.get('sub_images')
            images = [item.get('url') for item in sub_images]
            for image in images:
                downloadImage(image)
            return {
                'title': title,
                'url': url,
                'images': images
            }


# 向MongoDB中插入数据
def saveToMongo(result):
    if db[MONGO_TABLE].insert(result):
        print('存储到MongoDB成功', result)
        return True
    return False


# 下载图片
def downloadImage(url):
    print('正在下载', url)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            saveImage(response.content)  # 保存图片
            return response.text
        return None
    except RequestException:
        print('请求图片出错', url)
        return None


# 保存图片
def saveImage(content):
    path = r'C:\Users\Leon\Desktop\jiepai'
    # 文件包括三个部分,分别是路径、文件名、后缀,这里用md5码作为文件名是为了避免重复
    filePath = '{0}/{1}.{2}'.format(path, md5(content).hexdigest(), 'jpg')
    if not os.path.exists(filePath):
        with open(filePath, 'wb') as f:
            f.write(content)
            f.close()


def main(offset):
    html = getPageIndex(offset, KEYWORD)  # 网页源码
    # print(html)
    for url in parsePageIndex(html):
        # print(url)
        html = getPageDetail(url)
        if html:
            result = parsePageDetail(html, url)
            # print(result)
            if result:
                saveToMongo(result)


if __name__ == '__main__':
    # main()
    # 构建偏移量列表
    groups = [x * 20 for x in range(GROUP_START, GROUP_END + 1)]
    pool = Pool()  # 创建进程池
    pool.map(main, groups)
