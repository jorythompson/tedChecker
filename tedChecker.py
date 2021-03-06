from emailSender import EmailConnection
from emailSender import EmailSender
import ConfigParser
import ast
import argparse
import urllib2
import locale
import xml.etree.ElementTree as ET
import dominate.tags as tags
import platform
import traceback
import sys
import logging
import logging.handlers

########################################################################################################################
# put a script into /etc/cron.daily (or under /etc/cron.X) and run the following to verify:
# run-parts --test /etc/cron.daily
########################################################################################################################


class TedConfigFile:
    TED = "ted"
    HOST = "host"
    LOCALE = "locale"
    DEBIAN_LOCALE = "debian"
    WINDOWS_LOCALE = "windows"
    EMAIL_RECIPIENTS = "Email Recipients"
    TO_USER = "to"
    SUBJECT = "subject"
    MTU_NAMES = ["Total", "MTU1", "MTU2", "MTU3", "MTU4"]

    def __init__(self, config_file):
        config = ConfigParser.ConfigParser()
        config.read(config_file)
        self.host = config.get(TedConfigFile.TED, TedConfigFile.HOST)
        self.email_connection = EmailConnection(config)
        self.email_users = ast.literal_eval("[" + config.get(TedConfigFile.EMAIL_RECIPIENTS, TedConfigFile.TO_USER) + "]")
        self.email_subject = config.get(TedConfigFile.EMAIL_RECIPIENTS, TedConfigFile.SUBJECT)
        locale.setlocale(locale.LC_ALL, config.get(TedConfigFile.LOCALE, platform.system()))
        self.mtu_names = {}
        for mtu_name in TedConfigFile.MTU_NAMES:
            self.mtu_names[mtu_name] = config.get(TedConfigFile.TED, mtu_name)


class MTU:
    def __init__(self, mtu, name):
        self.name = name
        self.power_now = {"val": float(mtu.find("PowerNow").text),
                          "help": "The most recent Power reading from the MTU"}
        self.power_tdy = {"val": float(mtu.find("PowerTDY").text),
                          "help": "Cumulative Power since midnight"}
        self.power_mtd = {"val": float(mtu.find("PowerMTD").text),
                          "help": "Cumulative Power since the beginning of the billing cycle"}
        self.power_avg = {"val": float(mtu.find("PowerAvg").text),
                          "help": "The average daily power used this billing cycle"}

    @staticmethod
    def _to_html(val, tags):
        pwr = val["val"]
        pwr_val = ""
        if pwr > 0:
            neg = False
        else:
            pwr = - pwr
            neg = True
        if pwr > 1000000:
            pwr /= 1000000
            pwr_val = " M"
        elif pwr > 1000:
            pwr /= 1000
            pwr_val = " K"

        if neg:
            pwr = - pwr
        tags.td(val["help"])
        tags.td(locale.format("%.2f",pwr, grouping=True) + pwr_val, style="text-align:right")

    def to_html(self, tags):
        border_style = "border-bottom:1px solid black"
        tags.h1(self.name)
        with tags.table(rules="cols", frame="box"):
            with tags.thead():
                tags.th("Power Type", style=border_style)
                tags.th("Amount (Watts)", style=border_style)
                tags.tr()
                self._to_html(self.power_now, tags)
                tags.tr()
                self._to_html(self.power_tdy, tags)
                tags.tr()
                self._to_html(self.power_mtd, tags)
                tags.tr()
                self._to_html(self.power_avg, tags)


class TedChecker:
    def __init__(self, config_file):
        self.config = config_file
        self.mtus = []

    def get_data(self):
        live_data = "/api/LiveData.xml"
        try:
            url = urllib2.urlopen("http://" + self.config.host + live_data)
            page = url.read()
            tree = ET.fromstring(page)
            for power in tree.iter("Power"):
                for valid_mtu in TedConfigFile.MTU_NAMES:
                    for child in power.getchildren():
                        if child.tag == valid_mtu:
                            name = self.config.mtu_names[valid_mtu]
                            if name != "":
                                self.mtus.append(MTU(child, name))
                            break
            return True
        except:
            return False


def get_args():
    parser = argparse.ArgumentParser(description='Read Information from The Energy Detective 5000')
    parser.add_argument('--config', required=True,
                        help='Configuration file containing your username, password, and mint cookie')
    return parser.parse_args()


if __name__ == "__main__":
    logger = logging.getLogger("tedChecker")
    level = logging.WARN
    logger.setLevel(level)
    file_handler = logging.handlers.RotatingFileHandler("tedChecker.log", mode='a', maxBytes=10000, backupCount=5)
    file_handler.setLevel(level)
    formatter = logging.Formatter('%(asctime)s:%(levelname)s: %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.debug("Starting session")
    args = get_args()
    config = TedConfigFile(args.config)
    try:
        ted = TedChecker(config)
        if ted.get_data():
            html = tags.html()
            with html.add(tags.body()).add(tags.div(id='content')):
                for mtu in ted.mtus:
                    mtu.to_html(tags)
            with open("ted.html", 'w') as f:
                f.write(str(html))
            message = str(html)
        else:
            message = "<html>Could not connect to " + config.host + ", please try rebooting the device.</html>"
    except Exception as (e):
        message = "<html>"
        type_, value_, traceback_ = sys.exc_info()
        tb = traceback.format_exception(type_, value_, traceback_)
        for line in tb:
            logger.critical(line)
            message += line + "<br>"
        message += "</html>"
    email_sender = EmailSender(config.email_connection)
    for user in config.email_users:
        email_sender.send(user, config.email_subject, message)
