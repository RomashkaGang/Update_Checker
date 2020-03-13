#!/usr/bin/env python3
# encoding: utf-8

import json

from check_init import UAS, CheckUpdate, SfCheck, SfProjectCheck, H5aiCheck, \
                       AexCheck, PeCheck, PlingCheck, PeCheckPageCache

PE_PAGE_BS_CACHE = PeCheckPageCache()

class Linux44Y(CheckUpdate):

    fullname = "Linux Kernel stable v4.4.y"

    def do_check(self):
        url = "https://www.kernel.org"
        bs_obj = self.get_bs(self.request_url(url))
        for tr_obj in bs_obj.find("table", {"id": "releases"}).find_all("tr"):
            kernel_version = tr_obj.find_all("td")[1].get_text()
            if kernel_version.startswith("4.4."):
                self.update_info("LATEST_VERSION", kernel_version)
                self.update_info(
                    "DOWNLOAD_LINK",
                    "https://git.kernel.org/stable/h/v%s" % kernel_version
                )
                self.update_info(
                    "BUILD_CHANGELOG",
                    "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/log/?h=v%s" % kernel_version
                )
                break
        else:
            raise Exception("Parsing failed!")

    def get_print_text(self):
        return "*Linux Kernel stable* %s *update*\n\n%s" % (
            "[v%s](%s)" % (self.info_dic["LATEST_VERSION"], self.info_dic["DOWNLOAD_LINK"]),
            "[Commits](%s)" % self.info_dic["BUILD_CHANGELOG"]
        )

class Linux414Y(CheckUpdate):

    fullname = "Linux Kernel stable v4.14.y"

    def do_check(self):
        url = "https://www.kernel.org"
        bs_obj = self.get_bs(self.request_url(url))
        for tr_obj in bs_obj.find("table", {"id": "releases"}).find_all("tr"):
            kernel_version = tr_obj.find_all("td")[1].get_text()
            if kernel_version.startswith("4.14."):
                self.update_info("LATEST_VERSION", kernel_version)
                self.update_info(
                    "DOWNLOAD_LINK",
                    "https://git.kernel.org/stable/h/v%s" % kernel_version
                )
                self.update_info(
                    "BUILD_CHANGELOG",
                    "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/log/?h=v%s" % kernel_version
                )
                break
        else:
            raise Exception("Parsing failed!")

class Linux55Y(CheckUpdate):

    fullname = "Linux Kernel stable v5.5.y"

    def do_check(self):
        url = "https://www.kernel.org"
        bs_obj = self.get_bs(self.request_url(url))
        for tr_obj in bs_obj.find("table", {"id": "releases"}).find_all("tr"):
            kernel_version = tr_obj.find_all("td")[1].get_text()
            if kernel_version.startswith("5.5."):
                self.update_info("LATEST_VERSION", kernel_version)
                self.update_info(
                    "DOWNLOAD_LINK",
                    "https://git.kernel.org/stable/h/v%s" % kernel_version
                )
                self.update_info(
                    "BUILD_CHANGELOG",
                    "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/log/?h=v%s" % kernel_version
                )
                break
        else:
            raise Exception("Parsing failed!")


class Linux56Y(CheckUpdate):

    fullname = "Linux Kernel rc v5.6-rc"

    def do_check(self):
        url = "https://www.kernel.org"
        bs_obj = self.get_bs(self.request_url(url))
        for tr_obj in bs_obj.find("table", {"id": "releases"}).find_all("tr"):
            kernel_version = tr_obj.find_all("td")[1].get_text()
            if kernel_version.startswith("5.6-"):
                self.update_info("LATEST_VERSION", kernel_version)
                self.update_info(
                    "DOWNLOAD_LINK",
                    "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/?h=v%s" % kernel_version
                )
                self.update_info(
                    "BUILD_CHANGELOG",
                    "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable-rc.git/log/?h=v%s" % kernel_version
                )
                break
        else:
            raise Exception("Parsing failed!")




    def get_print_text(self):
        return "*Linux Kernel stable* %s *update*\n\n%s" % (
            "[v%s](%s)" % (self.info_dic["LATEST_VERSION"], self.info_dic["DOWNLOAD_LINK"]),
            "[Commits](%s)" % self.info_dic["BUILD_CHANGELOG"]
        )


class GoogleClangPrebuilt(CheckUpdate):

    fullname = "Google Clang Prebuilt"

    def do_check(self):
        base_url = "https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86"
        bs_obj = self.get_bs(self.request_url(base_url + "/+log"))
        commits = bs_obj.find("ol", {"class": "CommitLog"}).find_all("li")
        for commit in commits:
            a_tag = commit.find_all("a")[1]
            commit_title = a_tag.get_text()
            if commit_title.startswith("Update prebuilt Clang to"):
                commit_url = "https://android.googlesource.com" + a_tag["href"]
                commit_id = a_tag["href"].split("/")[-1]
                r_tag = commit_title.split()[4]
                assert r_tag.startswith("r")
                if r_tag[-1] == ".":
                    r_tag = r_tag[:-1]
                self.update_info("LATEST_VERSION", commit_id)
                self.update_info("BUILD_CHANGELOG", commit_url)
                self.update_info(
                    "DOWNLOAD_LINK",
                    "%s/+archive/%s/clang-%s.tar.gz" % (base_url, commit_id, r_tag)
                )
                break
        else:
            raise Exception("Parsing failed!")

    def after_check(self):
        bs_obj_2 = self.get_bs(self.request_url(self.info_dic["BUILD_CHANGELOG"]))
        commit_text = bs_obj_2.find("pre").get_text().splitlines()[2]
        if commit_text[-1] == ".":
            commit_text = commit_text[:-1]
        self.update_info("BUILD_VERSION", commit_text)

    def get_print_text(self):
        return "*%s Update*\n\n%s\n\nDownload tar.gz:\n%s" % (
            self.fullname,
            "[Commit](%s)" % self.info_dic["BUILD_CHANGELOG"],
            "[%s](%s)" % (
                self.info_dic.get("BUILD_VERSION", self.info_dic["DOWNLOAD_LINK"].split("/")[-1]),
                self.info_dic["DOWNLOAD_LINK"]
            )
        )

CHECK_LIST = (
    Linux44Y,
    Linux56Y,
    Linux55Y,
    Linux414Y,
)
