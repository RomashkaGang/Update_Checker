#!/usr/bin/env python3
# encoding: utf-8

import json
import random
import time
from collections import OrderedDict
from urllib.parse import unquote, urlencode

import requests
from bs4 import BeautifulSoup
from requests.packages import urllib3

from config import _PROXIES_DIC, TIMEOUT
from database import DBSession, Saved

# 禁用安全请求警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

UAS = [
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36"),
    ("Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 "
     "(KHTML, like Gecko) Version/5.1 Safari/534.50"),
    "Opera/9.80 (Windows NT 6.1; U; en) Presto/2.8.131 Version/11.11",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:2.0.1) Gecko/20100101 Firefox/4.0.1"
]

_KEY_TO_PRINT = {
    "BUILD_TYPE": "Build type",
    "BUILD_VERSION": "Build version",
    "BUILD_DATE": "Build date",
    "BUILD_CHANGELOG": "Changelog",
    "FILE_MD5": "MD5",
    "FILE_SHA1": "SHA1",
    "FILE_SHA256": "SHA256",
    "DOWNLOAD_LINK": "Download",
    "FILE_SIZE": "Size",
}

def select_bs4_parser():
    try:
        import lxml
        del lxml
        return "lxml"
    except ModuleNotFoundError:
        try:
            import html5lib
            del html5lib
            return "html5lib"
        except ModuleNotFoundError:
            raise Exception(
                "No bs4 parser available. "
                "Please install at least one parser in 'lxml' and 'html5lib'!"
            )

BS4_PARSER = select_bs4_parser()

class ErrorCode(requests.exceptions.RequestException):
    """ 自定义异常, 当requests请求结果返回错误代码时抛出 """

class CheckUpdate:

    fullname = None

    def __init__(self):
        self._raise_if_missing_property("fullname")
        self.__info_dic = OrderedDict([
            ("LATEST_VERSION", None),
            ("BUILD_TYPE", None),
            ("BUILD_VERSION", None),
            ("BUILD_DATE", None),
            ("BUILD_CHANGELOG", None),
            ("FILE_MD5", None),
            ("FILE_SHA1", None),
            ("FILE_SHA256", None),
            ("DOWNLOAD_LINK", None),
            ("FILE_SIZE", None),
        ])
        self._private_dic = {}

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def info_dic(self):
        return self.__info_dic

    def _raise_if_missing_property(self, *props):
        if None in (getattr(self, key, None) for key in props):
            raise Exception(
                "Subclasses inherited from the %s class must specify the '%s' property when defining!"
                % (self.name, "' & '".join(props))
            )

    def update_info(self, key, value):
        """ 更新info_dic字典, 在更新之前会对key和value进行检查和转换 """
        if key not in self.__info_dic.keys():
            raise KeyError("Invalid key: %s" % key)
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        self.__info_dic[key] = str(value) if value is not None else None

    @staticmethod
    def request_url(url, encoding="utf-8", **kwargs):
        """
        对requests.get方法进行了简单的包装
        timeout, headers, proxies这三个参数有默认值, 也可以根据需要自定义这些参数
        :param url: 要请求的url
        :param encoding: 文本编码, 默认为utf-8
        :param kwargs: 需要传递给requests.get方法的参数
        :return: url页面的源码
        """
        timeout = kwargs.pop("timeout", TIMEOUT)
        headers = kwargs.pop("headers", {"user-agent": random.choice(UAS)})
        proxies = kwargs.pop("proxies", _PROXIES_DIC)
        req = requests.get(
            url, timeout=timeout, headers=headers, proxies=proxies, **kwargs
        )
        if not req.ok:
            raise ErrorCode(req.status_code)
        req.encoding = encoding
        return req.text

    @classmethod
    def get_hash_from_file(cls, url, **kwargs):
        """
        请求哈希校验文件的url, 返回文件中的哈希值
        请求过程中发生任何异常都允许忽略
        :param url: 哈希校验文件的url
        :param kwargs: 需要传递给self.request_url方法的参数
        :return: 哈希值字符串或None
        """
        try:
            return cls.request_url(url, **kwargs).strip().split()[0]
        except:
            return None

    @staticmethod
    def get_bs(url_text):
        """
        对BeautifulSoup函数进行了简单的包装
        :param url_text: url源码
        :return: BeautifulSoup对象
        """
        return BeautifulSoup(url_text, BS4_PARSER)

    def do_check(self):
        """
        开始进行更新检查, 包括页面请求 数据清洗 info_dic更新, 都应该在此方法中完成
        :return: None
        """
        # 注意: 请不要直接修改self.__info_dic字典, 应该使用self.update_info方法
        # 为保持一致性, 此方法不允许传入任何参数, 并且不允许返回任何值
        # 如确实需要引用参数, 可以在继承时添加新的类属性
        raise NotImplementedError

    def after_check(self):
        """
        此方法将在确定检查对象有更新之后才会执行
        比如: 将下载哈希文件并获取哈希值的代码放在这里, 可以节省一些时间(没有更新时做这些是没有意义的)
        :return: None
        """
        # 为保持一致性, 此方法不允许传入任何参数, 并且不允许返回任何值
        # 如确实需要使用self.do_check方法中的部分变量, 可以借助self._private_dic进行传递
        pass

    def write_to_database(self):
        """ 将CheckUpdate实例的info_dic数据写入数据库 """
        session = DBSession()
        try:
            if self.name in {x.ID for x in session.query(Saved).all()}:
                saved_data = session.query(Saved).filter(Saved.ID == self.name).one()
                saved_data.FULL_NAME = self.fullname
                for key, value in self.__info_dic.items():
                    setattr(saved_data, key, value)
            else:
                new_data = Saved(
                    ID=self.name,
                    FULL_NAME=self.fullname,
                    **self.__info_dic
                )
                session.add(new_data)
            session.commit()
        finally:
            session.close()

    def is_updated(self):
        """ 与数据库中已存储的数据进行比对, 如果有更新, 则返回True, 否则返回False """
        if self.__info_dic["LATEST_VERSION"] is None:
            return False
        saved_info = Saved.get_saved_info(self.name)
        if saved_info is None:
            return True
        if self.__info_dic["LATEST_VERSION"] == saved_info.LATEST_VERSION:
            return False
        return True

    def get_print_text(self):
        """ 返回更新消息文本 """
        print_str_list = [
            "*%s Update*" % self.fullname,
            time.strftime("%Y-%m-%d", time.localtime(time.time())),
        ]
        for key, value in self.info_dic.items():
            if key != "LATEST_VERSION" and value is not None:
                if key in {"FILE_MD5", "FILE_SHA1", "FILE_SHA256", "BUILD_DATE"}:
                    value = "`%s`" % value
                if key == "BUILD_CHANGELOG" and not value.startswith("http"):
                    value = "`%s`" % value
                if key == "DOWNLOAD_LINK":
                    assert value[0] != "{"
                    if value[0] == "[":
                        value = "\n".join(["# %s\n%s" % (k, v) for k, v in json.loads(value)])
                    else:
                        value = "[%s](%s)" % (self.info_dic.get("LATEST_VERSION", ""), value)
                print_str_list.append("\n%s:\n%s" % (_KEY_TO_PRINT[key], value))
        return "\n".join(print_str_list)

    def __repr__(self):
        return "%s(fullname='%s', info_dic={%s})" % (
            self.name,
            self.fullname,
            ", ".join([
                "%s='%s'" % (key, value.replace("\n", "\\n"))
                for key, value in self.__info_dic.items() if value is not None
            ])
        )

class SfCheck(CheckUpdate):

    project_name = None
    sub_path = ""

    __MONTH_TO_NUMBER = {
        "Jan": "01",
        "Feb": "02",
        "Mar": "03",
        "Apr": "04",
        "May": "05",
        "Jun": "06",
        "Jul": "07",
        "Aug": "08",
        "Sep": "09",
        "Oct": "10",
        "Nov": "11",
        "Dec": "12",
    }

    def __init__(self):
        self._raise_if_missing_property("project_name")
        super().__init__()

    def do_check(self):
        url = "https://sourceforge.net/projects/%s/rss" % self.project_name
        bs_obj = self.get_bs(self.request_url(url, params={"path": "/"+self.sub_path}))
        builds = list(bs_obj.find_all("item"))
        if not builds:
            return
        builds.sort(key=lambda x: -int(x.find("files:sf-file-id").get_text()))
        for build in builds:
            file_size_mb = int(build.find("media:content")["filesize"]) / 1000 / 1000
            # 过滤小于500MB的文件
            if file_size_mb < 500:
                continue
            file_version = build.guid.string.split("/")[-2]
            if self.filter_rule(file_version):
                self.update_info("LATEST_VERSION", file_version)
                self.update_info("DOWNLOAD_LINK", build.guid.string)
                self.update_info("BUILD_DATE", build.pubdate.string)
                self.update_info("FILE_MD5", build.find("media:hash", {"algo": "md5"}).string)
                self.update_info("FILE_SIZE", "%0.1f MB" % file_size_mb)
                break

    def filter_rule(self, string):
        """ 文件名过滤规则 """
        return string.endswith(".zip")

    @classmethod
    def date_transform(cls, date_str):
        """
        将sf站rss中的日期字符串转为time.struct_time类型, 以便于比较
        例： "Wed, 12 Feb 2020 12:34:56 UT"
        返回: time.struct_time(
            tm_year=2020, tm_mon=2, tm_mday=12, tm_hour=12, tm_min=34, tm_sec=56,
            tm_wday=0, tm_yday=48, tm_isdst=-1
        )
        """
        date_str_ = date_str[5:-3]
        date_str_month = date_str[8:8+3]
        date_str_ = date_str_.replace(date_str_month, cls.__MONTH_TO_NUMBER[date_str_month])
        return time.strptime(date_str_, "%d %m %Y %H:%M:%S")

    def is_updated(self):
        result = super().is_updated()
        if not result:
            return False
        saved_info = Saved.get_saved_info(self.name)
        if saved_info is None:
            return True
        latest_data = self.date_transform(self.info_dic["BUILD_DATE"])
        saved_data = self.date_transform(saved_info.BUILD_DATE)
        return latest_data > saved_data

class SfProjectCheck(SfCheck):

    # file name keyword: full name
    __KNOWN_ROM = OrderedDict([
        ("aicp", "AICP"),
        ("AOSiP", "AOSiP"),
        ("Arrow", "Arrow OS"),
        ("atom", "Atom OS"),
        ("Bliss", "Bliss Rom"),
        ("Bootleggers", "Bootleggers Rom"),
        ("Blaze", "Blaze-AOSP Rom"),
        ("CleanDroid", "CleanDroid OS"),
        ("crDroid", "CrDroid"),
        ("DerpFest", "AOSiP DerpFest"),
        ("ExtendedUI", "ExtendedUI"),
        ("EvolutionX", "EvolutionX"),
        ("Havoc", "Havoc OS"),
        ("Legion", "Legion OS"),
        ("lineage", "Lineage OS"),
        ("Rebellion", "Rebellion OS"),
        ("Titanium", "Titanium OS"),
        ("ion", "ION"),
        ("MK", "Mokee Rom"),
        ("Stag", "Stag OS"),
    ])
    developer = None

    def __init__(self):
        self._raise_if_missing_property("developer")
        self.fullname = "New rom release by %s" % self.developer
        super().__init__()

    def do_check(self):
        super().do_check()
        for key, value in self.__KNOWN_ROM.items():
            if key.upper() in self.info_dic["LATEST_VERSION"].upper():
                self.fullname = "%s (By %s)" % (value, self.developer)
                break

    def get_print_text(self):
        print_str = super().get_print_text()
        if self.fullname.startswith("New rom release by"):
            print_str = print_str.replace(" Update", "")
        return print_str

class H5aiCheck(CheckUpdate):

    base_url = None
    sub_url = None

    def __init__(self):
        self._raise_if_missing_property("base_url", "sub_url")
        super().__init__()

    def do_check(self):
        url = self.base_url + self.sub_url
        bs_obj = self.get_bs(self.request_url(url, verify=False))
        trs = bs_obj.find("div", {"id": "fallback"}).find("table").find_all("tr")[1:]
        trs.sort(key=lambda x: x.find_all("td")[2].get_text(), reverse=True)
        build = list(filter(lambda x: x.find("a").get_text().endswith(".zip"), trs))[0]
        self.update_info("LATEST_VERSION", build.find("a").get_text())
        self.update_info("BUILD_DATE", build.find_all("td")[2].get_text())
        self.update_info("DOWNLOAD_LINK", self.base_url + build.find_all("td")[1].find("a")["href"])
        self.update_info("FILE_SIZE", build.find_all("td")[3].get_text())

class AexCheck(CheckUpdate):

    sub_path = None

    def __init__(self):
        self._raise_if_missing_property("sub_path")
        super().__init__()

    def do_check(self):
        url = "https://api.aospextended.com/builds/" + self.sub_path
        json_text = self.request_url(
            url,
            headers={
                "origin": "https://downloads.aospextended.com",
                "referer": "https://downloads.aospextended.com/" + self.sub_path.split("/")[0],
                "user-agent": UAS[0]
            }
        )
        json_dic = json.loads(json_text)[0]
        self.update_info("LATEST_VERSION", json_dic["file_name"])
        self.update_info("FILE_SIZE", "%0.2f MB" % (int(json_dic["file_size"]) / 1048576,))
        self.update_info("DOWNLOAD_LINK", json_dic["download_link"])
        self.update_info("FILE_MD5", json_dic["md5"])
        self.update_info("BUILD_DATE", json_dic["timestamp"])
        self.update_info("BUILD_CHANGELOG", json_dic.get("changelog"))

class PeCheckPageCache:

    def __init__(self):
        self.cache = None

    clear = __init__

class PeCheck(CheckUpdate):

    index = None
    page_cache = None

    def __init__(self):
        self._raise_if_missing_property("index")
        if not (self.page_cache is None or isinstance(self.page_cache, PeCheckPageCache)):
            raise Exception(
                "'page_cache' property must be NoneType or PeCheckPageCache object!"
            )
        super().__init__()

    def do_check(self):
        url = "https://download.pixelexperience.org"
        if self.page_cache is None:
            bs_obj = self.get_bs(self.request_url(url + "/whyred"))
        elif self.page_cache.cache is None:
            bs_obj = self.get_bs(self.request_url(url + "/whyred"))
            self.page_cache.cache = bs_obj
        else:
            bs_obj = self.page_cache.cache
        build = bs_obj.find_all("div", {"class": "panel panel-collapse"})[self.index]
        build_info = build.find("tbody").find("tr").find_all("td")
        self.update_info("BUILD_DATE", build_info[0].get_text())
        self.update_info("LATEST_VERSION", build_info[1].get_text().strip())
        build_id = build_info[1].find("a")["data-modal-id"]
        build_info_sp_div = bs_obj.find("div", {"id": build_id})
        self.update_info("BUILD_CHANGELOG", build_info_sp_div.find("pre").get_text())
        for line in build_info_sp_div.get_text().splitlines():
            if "MD5 hash: " in line:
                self.update_info("FILE_MD5", line.strip().split(": ")[1])
            if "File size: " in line:
                self.update_info("FILE_SIZE", line.strip().split(": ")[1])
        self._private_dic = {
            "fake_download_link": "".join([
                url, "/download/", build_info_sp_div.find("a")["data-file-uid"]
            ]),
            "request_headers_referer": url + build_info_sp_div.find("a")["href"],
        }

    def after_check(self):
        real_download_link = self.request_url(
            self._private_dic["fake_download_link"],
            headers={
                "referer": self._private_dic["request_headers_referer"],
                "user-agent": UAS[0],
            }
        )
        self.update_info("DOWNLOAD_LINK", real_download_link)

class PlingCheck(CheckUpdate):

    p_id = None
    collection_id = None

    def __init__(self):
        self._raise_if_missing_property("p_id", "collection_id")
        super().__init__()

    def do_check(self):
        url = "https://www.pling.com/p/%s/getfilesajax" % self.p_id
        params = {
            "format": "json",
            "ignore_status_code": 1,
            "status": "all",
            "collection_id": self.collection_id,
            "perpage": 1000,
            "page": 1,
        }
        json_dic = json.loads(self.request_url(url, params=params))
        if json_dic["files"]:
            latest_build = json_dic["files"][-1]
            self.update_info("LATEST_VERSION", latest_build["name"])
            self.update_info("BUILD_DATE", latest_build["updated_timestamp"])
            self.update_info("FILE_MD5", latest_build["md5sum"])
            if latest_build["tags"] is None:
                self.update_info(
                    "DOWNLOAD_LINK",
                    "https://www.pling.com/p/%s/startdownload?%s" % (
                        self.p_id,
                        urlencode({
                            "file_id": latest_build["id"],
                            "file_name": latest_build["name"],
                            "file_type": latest_build["type"],
                            "file_size": latest_build["size"],
                        })
                    )
                )
                self.update_info("FILE_SIZE", "%0.2f MB" % (int(latest_build["size"]) / 1048576,))
            else:
                self.update_info("DOWNLOAD_LINK", unquote(latest_build["tags"]).replace("link##", ""))
