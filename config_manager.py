#!/usr/bin/env python3
# Config Manager
#
# Copyright (c) 2020 Ivan , Dicom Iots
#
# For the full copyright and license information, please view the LICENSE
# file that was distributed with this source code.
#
import logging
import subprocess
import json
import os
from datetime import timedelta
import time
LOGGER = logging.getLogger('CONFIG_MANAGER')
class ConfigManager(object):
    """ Network Manager
        mode wifi on off"""

    def system_info(self):
        sys = self.cmd('ubus -S call system info')
        sys_info = json.loads(sys)
        data = {}
        with open('/etc/dhome/.dhome_info') as json_file:
             data = json.load(json_file)
        data.update({"uptime": str(timedelta(seconds = sys_info["uptime"]))})
        data.update({"system_time":time.ctime(sys_info["localtime"])})
        return data

    def cmd(self,arg):
        try:
            process = subprocess.Popen(arg,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               shell=True
                               )
            stdout, stderr = process.communicate()
            return (stdout.decode('utf-8')).rstrip()
        except Exception as e:
               LOGGER.error('Run cmd error %s',stderr)
    def reboot(self):
        self.cmd('reboot')
        return "System reboot now .please waiting 2 min"
    def update_software(self):
        pass
    def wifi_on(self):
        self.cmd('uci set wireless.radio0.disabled=0')
        self.cmd('uci commit')
        self.cmd('wifi down')
        self.cmd('delay 1')
        self.cmd('wifi up')
        return "Wifi turn on. Waiting network connection"
        LOGGER.DEBUG('Turn on wifi')

    def wifi_off(self):
        self.cmd('uci set wireless.radio0.disabled = 1')
        self.cmd('uci commit')
        self.cmd('wifi down')
        self.cmd('delay 1')
        self.cmd('wifi up')
        self.res_success()
        LOGGER.DEBUG('Turn off wifi')

    def lan_dhcp(self,enable):
        if enable == True:
           self.cmd('uci set network.lan.proto="dhcp"')
           self.cmd('uci commit')
           self.cmd('/etc/init.d/network restart')
           return "Dhcp Lan network enable"
        else:
            self.cmd('uci set network.lan.proto="static"')
            self.cmd('uci commit')
            self.cmd('/etc/init.d/network restart')
            return "Dhcp Lan network disable"
        LOGGER.DEBUG('Change lan dhcp ',enable)

    def wifi_dhcp(self,enable):
        if enable == True:
           self.cmd('uci set network.wwan.proto="static"')
           self.cmd('uci commit')
           self.cmd('/etc/init.d/network restart')
           return "Dhcp wifi network enable"
        else:
           self.cmd('uci set network.wwan.proto="static"')
           self.cmd('uci commit')
           self.cmd('/etc/init.d/network restart')
           return "Dhcp wifi network enable"
        LOGGER.DEBUG('Change wifi dhcp ',enable)

    def set_lan_manual(self,ip,subnet,netmask):
        if(not (ip and not ip.isspace())):
            return "Ip not empty or wrong format "
        elif (not (subnet and not subnet.isspace())):
            return "Subnet not empty or wrong format "
        elif (not (netmask and not netmask.isspace())):
            return "Subnet not empty or wrong format "
        else:
            self.cmd('uci set network.lan.proto="static"')
            self.cmd('uci set network.lan.ipddr='+"'"+ip+"'")
            self.cmd('uci set network.lan.subnet='+"'"+subnet+"'")
            self.cmd('uci set network.wwan.netmask='+"'"+netmask+"'")
            self.cmd('uci commit')
            self.cmd('/etc/init.d/network restart')
            return "Set homegate static ip is : "+ip

    def get_wifi_info(self):
        en = self.cmd('uci -q get wireless.radio0.disabled')
        channel = self.cmd('uci -q get wireless.radio0.channel')
        mode = self.cmd('uci -q get wireless.radio0.mode')
        ssid = self.cmd('uci -q get wireless.sta.ssid')
        bssid = self.cmd('uci -q get wireless.sta.bssid')
        encryption = self.cmd('uci -q get wireless.sta.encryption')
        connect = self.cmd('/sbin/ifconfig wlan0 | grep inet\ addr | wc -l')
        data = {"enable":bool(en),"connect":bool(connect),"channel":str(channel),"mode":str(mode),"ssid":str(ssid),"bssid":str(bssid),"encryption":str(encryption)}
        return data

    def add_wifi(self,ssid,key):
        if(not (ssid and not ssid.isspace())):
             return "ssid is empty"
        elif (not (key and not key.isspace())):
             return "Password is empty"
        res = self.scan_wifi()
        wifi_list = None
        if res:
            data = json.loads(res)
            for sub in data['results']:
                if sub['ssid'] == ssid:
                   wifi_list = sub
                   break
            if wifi_list:
               encryption= wifi_list['encryption']
               encry = "psk2"
               if encryption['authentication'][0] == "psk" and encryption['wpa'][0] == 2 :
                  encry = "psk2"
               elif encryption['authentication'][0] == "psk" and encryption['wpa'][0] == 1:
                  encry = "psk"
               elif encryption['enabled'] == False:
                  encry = ""
               else:
                   pass
               add_wifi = " '"+wifi_list['ssid']+"' " +wifi_list['bssid']+" "+encry+" "+key
               self.cmd("/etc/dhome/network/add_wifi"+add_wifi)
               return True
            else:
               return False
        LOGGER.DEBUG('Try connect wifi ',ssid)

    def set_wifi_ap(self):
        self.cmd("cp /etc/config/wireless.ap /etc/cofig/wireless")
        self.cmd('/etc/init.d/network restart')
        LOGGER.DEBUG('Remove',ssid)
        return "success"
    def scan_wifi(self):
        arg = 'ubus -S call iwinfo scan'+" '"+'{"device":"wlan0"}'+"'"
        return self.cmd(arg)
    def config_system(self,token,serial,wwan_mac,wan_mac):
        if token is None or wwan_mac is None or wan_mac is None or serial is None:
           return False
        else:
            self.cmd("uci set network.lan_eth0_dev.macaddr="+"'"+wan_mac+"'")
            self.cmd('uci commit')
            self.cmd("uci set wireless.default.macaddr="+"'"+wwan_mac+"'")
            self.cmd('uci commit')
            self.cmd("uci set wireless_ap.default.ssid="+"'Dhome_"+serial+"'")
            self.cmd("uci set wireless_ap.default.macaddr="+"'"+wwan_mac+"'")
            self.cmd('uci commit')
            self.cmd("echo " ">/etc/mosquitto/passwords")
            self.cmd("mosquitto_passwd -b /etc/mosquitto/passwords dicomiots '"+token+"'")
            return True

    def udpate(self,sw_version):
        self.cmd('/etc/dhome/system/update '+ sw_version +'dicomiot')
    def get_ip_local(self):
        ip = self.cmd('/etc/dhome/network/check_ip_local')
        if ip:
            return ip
        else:
            return False
        # db = DbInterface.add_homegate_info(data)
        # if db == "success":
        #    return "success"
# #
# if __name__ == '__main__':
#      n = ConfigManager()
#      # print(n.scan_wifi())
#      # print(n.system_info())
#
#      print(n.add_wifi("DICOM TECH","te"))
