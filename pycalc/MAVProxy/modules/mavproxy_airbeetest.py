from MAVProxy.modules.lib import mp_module
import time
from datetime import datetime
import threading,Queue
import os
import subprocess
import xlrd, xlwt
from xlutils.copy import copy
import platform
import sys
import re

class AirbeetestModule(mp_module.MPModule):
    def __init__(self,mpstate):
        super(AirbeetestModule, self).__init__(mpstate, "AirbeeTest1")
        self.add_command('hardware',self.hardware,'test hardware,test imu')
        self.add_command('bsp',self.bsp,'burn bsp')
        self.add_command('bspall',self.bspall,'burn bsp all')
        self.add_command('device',self.find_device,'find device')
        self.add_command('wifi',self.wifi,'find wifi')
        self.add_command('check_log',self.check_log,'check_log')
        self.add_command('ssid',self.ssid,'set ssid')
        self.add_command('versions',self.version,'find version')
        self.add_command('app_version',self.app_version,'app version')
        self.add_command('airbee',self.airbee,'burn airbee app')
        self.add_command('airbeeall',self.airbeeall,'burn all airbee app')
        self.add_command('adb_exist',self.adb_exist,'adb_exist')
        self.add_command('set_build_dir',self.set_build_dir,'set build dir')
        self.add_command('pressure',self.pressure,'test restart pressure and restart time')
        self.add_command('boot_test',self.boot_time_test,'test restart time of music on')
        self.add_command('imu_test',self.imu_test,'test imu and distance')
        self.distance = None
        self.current_distance = None
        self.HIGHRES_IMU = None
        self.test_result = 0
        self.start_time = 0
        self.result_list = []
        self.imu = 0
        self.begin = 0
        self.ssid = "Daybreaker2_1d229258"
        self.excel_name = "test.xls"
	self.sudo_passwd = "Avl1108"
        #self.sheet_all = self.exl_obj.add_sheet("result_all", cell_overwrite_ok=True)
        if platform.system() == "Linux":
            #self.bsp_dir = "/home/jenkins/release/bsp/20170720-Release"
            self.bsp_script = "echo %s | sudo -S ./fastboot-all.sh" % self.sudo_passwd
            self.bsp_all_script = "sudo ./fastboot-4.sh"
            #self.airbee_dir = "/home/jenkins/release/AirBee"
            self.airbee_script = "./push_1.sh"
            self.airbee_all_script = "./push_4.sh"
        elif platform.system() == "Windows":
            self.bsp_dir = r"F:\tools\20170712-Release"
            self.bsp_script = "fastboot-all.bat"
            self.airbee_dir = r"F:\tools\build_tool"
            self.airbee_script = r"push_1.bat"
        else:
            print "unknown os",platform.system()
            sys.exit()
        self.bsp_dir = mpstate.bsp_dir
        self.airbee_dir = mpstate.app_dir
        self.mpstate = mpstate
        #self.wifi = "netsh wlan connect name=Daybreaker2_1d229231"
        #self.restart = "adb shell reboot -f"
        self.zlogqueue = Queue.Queue()
        self.zlog_tag = 0
    def set_build_dir(self, args):
        self.bsp_dir = self.mpstate.bsp_dir
        self.airbee_dir = self.mpstate.app_dir
    def adb_exist(self, args):
        #import ipdb
        import re

        adb_result = os.popen("adb devices")
        devices_name = adb_result.read()
        #print devices_name
        devices_name = re.search("device\n",devices_name)
        #print devices_name
        #ipdb.set_trace()
        if devices_name:

            return 1
        else:
            self.mpstate.uiqueue.put("device not found,exist\n")
            return 0
    def check_log(self,args):
        if not self.adb_exist(1):
            print "device not found,exist"
            return 0
        _line = os.popen("adb shell ls /root/log")
        _line = _line.read()
        if _line:
            self.mpstate.uiqueue.put(_line)
        else:
            self.mpstate.uiqueue.put("log is empty\n")
    def qprint(self, _line):
        self.mpstate.uiqueue.put(_line)
    def airbee(self, args):
        "burn airbee app by adb push"
        
        if not self.adb_exist(1):
            print "device not found,exist"
            return 0
        print self.airbee_dir
        os.chdir(self.airbee_dir)
        p = subprocess.Popen(self.airbee_script,stdin = subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell="True")
        self.mpstate.uiqueue.put("burning airbee app,waiting...")
        while 1:
        #while p.poll() is None:
            _line = p.stdout.readline()
            _err = p.stderr.readline()
            if _line:
                print _line
                self.mpstate.uiqueue.put(_line)
            else:
                break
            if _err:
                print _err
                self.mpstate.uiqueue.put(_err)
        p.wait()
    def find_device(self,args):
        
        _popen = os.popen("adb devices")
        _devices = _popen.read()
        print _devices
        
        self.device_list = re.findall(r"(\w+)\tdevice\n", _devices)
        print self.device_list
    
    def bspall(self, args):
        "burn all devices bsp by fastboot-4.sh,don't restart before complete"
        if not self.adb_exist(1):
            print "device not found,exit burn bsp"
            return 0
        self.find_device(1)
        os.chdir(self.bsp_dir)
        os.system("pwd")
        for i in self.device_list:
            subprocess.Popen("%s %s"%(self.bsp_all_script,i),shell="True")
        '''
        for i in range(100):
            _line = p.readline()
            print _line
            if "rebooting" in _line:
            #if "jenkins" in _line:
                print "reboot board!!"
                break
        '''
    def airbeeall(self,args):
        "burn all devices airbee app by push_all.sh"
        if not self.adb_exist(1):
            return 0
        self.find_device(1)
        os.chdir(self.airbee_dir)
        os.system("pwd")
        for i in self.device_list:
            print "====================" 
            print "      %s" % i
            print "====================" 
            subprocess.Popen("%s %s"%(self.airbee_all_script,i),shell="True")
    def ssid(self,args):
        "set the ssid for test"
        if not args:
            print "current ssid is: %s" % self.ssid
        else:
            self.ssid = args[0]
            print "set ssid to %s" % self.ssid
    def wifi(self, args):
        "find all devices's wifi ssid"
        if not self.adb_exist(1):
            return 0
        self.find_device(1)
        for i in self.device_list:
            print "====================" 
            print "      %s" % i
            print "====================" 
            p_mac = os.popen("adb shell ifconfig | grep HWaddr")
            p_mac_read = p_mac.read()
            print p_mac_read
            mac_search = re.search("HWaddr (\S*)", p_mac_read)
            self.mac = "".join(mac_search.group(1).split(':')[-4:])
            self.mpstate.mac = self.mac
            print "mac:%s" % self.mac
            #print "adb -s %s shell cat /etc/system.prop" % i
            p = os.popen("adb -s %s shell sed -n '56,60p' /etc/hostapd.conf" % i)
            _line = p.read()
            self.mpstate.uiqueue.put(_line)
            while 1:
                p_wifi = os.popen("adb shell cat /etc/hostapd.conf | grep 'ssid='")
                p_wifi_r = p_wifi.read()
                if "device not found" in p_wifi_r:
                    print  "can not find device"
                else:
                    ssid_search = re.search("ssid=(\w*)", p_wifi_r)
                    self.ssid = ssid_search.group(1)
                    self.mpstate.ssid = self.ssid
                    print "ssid: %s" % self.ssid
                    break
    def version(self, args):
        "find all devices's bsp version"
        if not self.adb_exist(1):
            return 0
        self.find_device(1)
        for i in self.device_list:
            print "====================" 
            print "      %s" % i
            print "====================" 
            print "adb -s %s shell cat /etc/system.prop" % i
            #os.popen("chcp 65001")
            #os.popen('adb -s %s shell alias ls="ls --color=never"')
            p = os.popen("adb -s %s shell cat /etc/system.prop" % i)
            _line = p.read()
            _line = _line.decode("utf8")
            print _line
            self.mpstate.uiqueue.put("===============================================================\n")
            self.mpstate.uiqueue.put(_line+"\n")
            self.mpstate.uiqueue.put("===============================================================\n")

    def app_version(self, args):
        "find all devices's bsp version"
        if not self.adb_exist(1):
            return 0
        self.find_device(1)
        for i in self.device_list:
            print "====================" 
            print "      %s" % i
            print "====================" 
            print "adb -s %s shell cat /etc/system.prop" % i
            #os.popen("chcp 65001")
            #os.popen('adb -s %s shell alias ls="ls --color=never"')
            p = os.popen("adb -s %s shell cat /etc/version.txt" % i)
            _line = p.read()
            _line = _line.decode("utf8")
            print _line
            self.mpstate.uiqueue.put("===============================================================\n")
            self.mpstate.uiqueue.put(_line+"\n")
            self.mpstate.uiqueue.put("===============================================================\n")
    def bsp(self,args):
        "burn TS bsp by fastboot,don't restart before complete"
        if not self.adb_exist(1):
            print "device not found,exit burn bsp"
            return 0
        print self.bsp_dir
        os.chdir(self.bsp_dir)
        os.system("pwd")
        p = subprocess.Popen(self.bsp_script,stdin = subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell="True")
        self.mpstate.uiqueue.put("burning bsp,waiting...")
        while 1:
            _line = p.stdout.readline()
            _err = p.stderr.readline()
            if _line:
                print _line
                self.mpstate.uiqueue.put(_line)
            else:
                break
            if _err:
                print _err
                self.mpstate.uiqueue.put(_err)
            print "----"
        p.wait()


    def restart(self):
        print "reboot board"
        #os.system("adb shell reboot -f")
        #p = subprocess.Popen("adb shell reboot -f",stdin = subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell="True")
        p = os.popen("adb shell reboot -f")
        _line = p.read()
        print "rebooting ...\n%s\n=========" % _line
        if "device not found" in _line:
            return 0
        else:
            return 1
        #p.wait()
        #stdout,stderr = p.communicate()
        #print "stdout:", stdout
        #print "stderr:", stderr
        #if "device not found" in stderr:  
        #    return 0
        #else:
        #    return 1
    def connect_wifi(self, ssid):
        print "reconnect wifi"

        times = 0
        #os.system("netsh wlan show interfaces")
        while 1:
            if platform.system() == "Windows":
                p = subprocess.Popen("netsh wlan show networks",stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell="True")
            if platform.system() == "Linux":
                p = subprocess.Popen("nmcli dev wifi",stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell="True")
            stdout,stderr = p.communicate()
            #print "stdout:", stdout
            #print "stderr:", stderr
            if ssid in stdout:
                times = 0
                break
            if times > 70:
                print "can not search wifi"
                return 0
            time.sleep(1)
            times = times + 1

        #os.system("netsh wlan connect name=%s" %ssid)       
        while 1:
            if platform.system() == "Windows":
                os.system("netsh wlan connect name=%s" %ssid)
            if platform.system() == "Linux":
                os.system("nmcli dev wifi connect '%s' password '12345678'" %ssid)

            time.sleep(3)
            if platform.system() == "Windows":
                p = subprocess.Popen("netsh wlan show interfaces",stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell="True")
            if platform.system() == "Linux":
                p = subprocess.Popen("nmcli dev status",stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell="True")
            
            stdout,stderr = p.communicate()
            print "stdout:", stdout
            print "stderr:", stderr
            
            if ssid in stdout:
                print "wifi conenct successful"
                return 1
            if times > 20:
                print "can not connect wifi"
                return 0
                
            time.sleep(1)
            times = times + 1
        #print os.system("netsh wlan show interfaces"),"~~~~~~~~~~"
    
    def hardware(self, args):
        "do hardware test,test the imu and distance"
        print "hardware"
        if not args:
            print "usage:hardware board_id"
            return 0
        thread_obj = threading.Thread(target=self._hardware_test, args=(args[0],))
        thread_obj.setDaemon(True)
        thread_obj.start()        
    
    def _hardware_test(self, args):
        
        self.creat_excel("hardware_test.xls")
        #import ipdb
        #_sheet_name = time.strftime("%Y_%m_%d_%H_%M", time.localtime())
        #ipdb.set_trace()
        self.creat_sheet(args)
        #print "!!!!!",args[0]
        
        column_0 = ["name","abs_pressure","current_distance","mag","acc","gyro","start time","test_result",self.ssid]    
        self.creat_sheet_header(column_0)
        
        self.connect_wifi(self.ssid)
        self.get_info(0)
        self.save_excel()
    def pressure(self, args):
        "do presure test,reboot the board then test the start time and the imu info"
        print "hardware"
        if not args:
            print "usage:pressure test_time"
            return 0
        #self.presure_test(int(args[0]))
        thread_obj = threading.Thread(target=self.presure_test, args=(int(args[0]),))
        thread_obj.setDaemon(True)
        thread_obj.start()
    def time_count(self):
        #end_time = time.clock()
        end_time = time.time()
        return int(end_time - self.begin)
    def test_start_time(self):
        '''test the start time between start poower and find wifi ssid'''
        end_time = time.time()
        print "end time:%s\n" % end_time
        self.start_time = (end_time - self.power_on_time)
        print "boot time:",self.start_time
        self.qprint("boot time:%s\n" % self.start_time)
    def zlog_write(self):
        while 1:
            one_log = self.zlogqueue.get()
            self.zlog.write(one_log)

    def imu_test(self,args):
        _time =  datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.zlog_tag = 1
        with open("%s_%s_LOG.txt" % (self.ssid, _time),"w") as self.zlog:
            #zlog_thread = threading.Thread(target = self.zlog_write)
            #zlog_thread.start()
            for i in range(5):
                time.sleep(1)
                print i
        self.zlog_tag = 0
    def stop_imu_test(self):
        self.zlog_tag = 0
    def boot_time_test(self, args):
        test_time = int(args[0])
        self.creat_excel("boot_test.xls")
        _sheet_name = time.strftime("%Y_%m_%d_%H_%M", time.localtime())
        self.creat_sheet("%s_%s" % (self.ssid.split("_")[1], _sheet_name))
        column_0 = ["time","boot time","boot_result","total success","total faild"]    
        self.creat_sheet_header(column_0)
        success_time = 0
        failed_time = 0
        for i in range(test_time):
            print "start No.%s test: " % i
            self.qprint("start No.%s test:\n" % i)
            self.result = 0
            if not self.restart():
                print "can not find adb device!!! exit test"
                return 0
            else:
                #self.power_on_time = time.clock()
                self.power_on_time = time.time()
                print "power on time:",self.power_on_time
                #self.qprint("power on time:%s\n" % self.power_on_time)
            time.sleep(12)
            while 1:
                print "start success:%s\n" % success_time
                print "start failed:%s\n" % failed_time
                p_wifi = os.popen("adb shell cat /home/linaro/afc_log.txt | grep -A 1 STARTUP")
                p_wifi_r = p_wifi.read()

                self.sheet_1.write(i+1,1,i)
                if "failed" in p_wifi_r:
                    failed_time = failed_time + 1
                    print "start failed !!!!!!!!!!!!",faild_time,"\n"
                    self.sheet_1.write(i+1,3,"failed")
                    break
                elif "success" in p_wifi_r:
                    print "start success !!!!!!!!!!!!\n"
                    boot_search = re.search("CLOCK_MONOTONIC: (\d*),", p_wifi_r)
                    if boot_search:
                        self.boot_time = boot_search.group(1)
                        print "======boot time: %s======\n" % self.boot_time
                        self.qprint("boot time: %s\n" % self.boot_time)
                        success_time = success_time + 1
                        self.sheet_1.write(i+1,2,self.boot_time)
                    else:
                        print "boot success but can not find time!!!!"
                        success_time = success_time + 1
                    self.sheet_1.write(i+1,3,"success")
                    time.sleep(10)
                    break
                else:
                    time.sleep(1)
                    print "wait 1 s"
        self.sheet_1.write(i+1,4,success_time)
        self.sheet_1.write(i+1,5,failed_time)
        #print self.result_list
        self.save_excel()
        
    def presure_test(self, test_time):
        self.creat_excel("pressure_test.xls")
        _sheet_name = time.strftime("%Y_%m_%d_%H_%M", time.localtime())
        self.creat_sheet("%s_%s" % (self.ssid.split("_")[1], _sheet_name))
        column_0 = ["time","abs_pressure","current_distance","mag","acc","gyro","start time","test_result",self.ssid]    
        self.creat_sheet_header(column_0)
        for i in range(test_time):
            print "start No.%s test: " % i
            self.qprint("start No.%s test:\n" % i)
            self.result = 0
            if not self.restart():
                print "can not find adb device!!! exit test"
                return 0
            else:
                #self.power_on_time = time.clock()
                self.power_on_time = time.time()
                print "power on time:",self.power_on_time
                #self.qprint("power on time:%s\n" % self.power_on_time)
            time.sleep(12)
            while 1:
                p_wifi = os.popen("adb shell cat /etc/hostapd.conf | grep 'ssid='")
                p_wifi_r = p_wifi.read()
                if "device not found" in p_wifi_r:
                    time.sleep(2)
                else:
                    ssid_search = re.search("ssid=(\w*)", p_wifi_r)
                    print len(self.ssid)
                    self.ssid = ssid_search.group(1)
                    print "ssid: %s" % self.ssid
                    self.qprint("ssid: %s\n" % self.ssid)
                    break
            #time.sleep(12)
            if self.connect_wifi(self.ssid):
                self.test_start_time()
                time.sleep(5)
                self.get_info(i)
            else:
                print "wifi connect fail,exit test"
                self.qprint("wifi connect fail,exit test")
                return 0
        print self.result_list
        self.save_excel()
        #os.system(self.restart)
        #time.sleep(17)
        #os.system(self.wifi)
        #time.sleep(5)
    def get_info(self, test_time):
        #self.begin = time.clock()
        self.begin = time.time()
        self.distance = None
        self.HIGHRES_IMU = None
        while 1:
            print self.time_count()
            if self.time_count() > 10:
                self.result = 0
                break
            #if self.HIGHRES_IMU:
            if self.HIGHRES_IMU and self.distance:
                print self.HIGHRES_IMU
                self.qprint("imu:%s\n" % str(self.HIGHRES_IMU))
                print self.distance
                self.qprint("distance:%s\n" % str(self.distance))
                self.result = 1
                break
            else:
                print self.HIGHRES_IMU
                print self.distance
                self.result = 0
            #print "distance:",self.distance    
            time.sleep(1)
        self.result_list.append(self.result)
        test_value = [test_time+1,self.abs_pressure,self.current_distance,self.mag,self.acc,self.gyro,self.start_time,["fail","pass"][self.result]]
        
        self.append_excel(test_time, test_value)
        
    def creat_excel(self,excel_name):
        self.excel_name = excel_name
        if not os.path.exists(self.excel_name):
            self.exl_obj = xlwt.Workbook()
            #new
            self.sheet_all_num = 1
            self.sheet_all = self.exl_obj.add_sheet("result_all", cell_overwrite_ok=True)
        else:
            self.exl_obj_read = xlrd.open_workbook(excel_name,formatting_info=True)
            self.get_sheet = self.exl_obj_read.sheet_names()
            print self.get_sheet
            #new
            #sheet_all = self.exl_obj_read.sheet_by_name(u'result_all')
            #print "sheet_all:%d\n" % sheet_all
            if "result_all" in self.get_sheet:
                sheet_all = self.exl_obj_read.sheet_by_name(u'result_all')
                self.sheet_all_num = sheet_all.nrows
                self.exl_obj = copy(self.exl_obj_read)
                self.sheet_all = self.exl_obj.get_sheet("result_all")
                print "!!!!!!!!!!!!!!!!!!!!!!!111"
            else:
                print "!!!!!!!!!!!!!!!!!!!!!!!222"
                self.sheet_all_num = 1

                self.exl_obj = copy(self.exl_obj_read)
                self.sheet_all = self.exl_obj.add_sheet("result_all", cell_overwrite_ok=True)
        

    def creat_sheet(self, sheet_name):    
        #import ipdb
        
        self.sheet_1 = self.exl_obj.add_sheet(sheet_name, cell_overwrite_ok=True)
        #self.sheet_all = self.exl_obj.add_sheet("result_all", cell_overwrite_ok=True)
        #raw_0 = ["item","test_value"]
        
    def creat_sheet_header(self, _header_list):
        for i in range(1,len(_header_list)+1):
            self.sheet_1.write(0,i,_header_list[i-1])
            #self.sheet_all.write(0,i-1,_header_list[i-1])
    def creat_sheet_all_header(self, _header_list):
        for i in range(1,len(_header_list)+1):
            self.sheet_all.write(0,i-1,_header_list[i-1])
    #new
    def append_excel_all_result(self, _list):
        #test_value = [line_num+1,self.abs_pressure,self.current_distance,self.mag,self.acc,self.gyro,self.start_time,["fail","pass"][self.result]]
        pattern = xlwt.Pattern() # Create the Pattern
	pattern.pattern = xlwt.Pattern.SOLID_PATTERN # May be: NO_PATTERN, SOLID_PATTERN, or 0x00 through 0x12
	pattern.pattern_fore_colour = 2 # May be: 8 through 63. 0 = Black, 1 = White, 2 = Red, 3 = Green, 4 = Blue, 5 = Yellow, 6 = Magenta, 7 = Cyan, 16 = Maroon, 17 = Dark Green, 18 = Dark Blue, 19 = Dark Yellow , almost brown), 20 = Dark Magenta, 21 = Teal, 22 = Light Gray, 23 = Dark Gray, the list goes on...
	style = xlwt.XFStyle() # Create the Pattern
	style.pattern = pattern # Add Pattern to Style

        test_value = _list
        for i in range(1,len(test_value)+1):
            if isinstance(test_value[i-1],dict):
                self.sheet_all.write(self.sheet_all_num,i,test_value[i-1]['fail'],style)
            else:
                self.sheet_all.write(self.sheet_all_num,i,test_value[i-1])        
    def append_excel(self,line_num, _list):
        #test_value = [line_num+1,self.abs_pressure,self.current_distance,self.mag,self.acc,self.gyro,self.start_time,["fail","pass"][self.result]]
        pattern = xlwt.Pattern() # Create the Pattern
	pattern.pattern = xlwt.Pattern.SOLID_PATTERN # May be: NO_PATTERN, SOLID_PATTERN, or 0x00 through 0x12
	pattern.pattern_fore_colour = 2 # May be: 8 through 63. 0 = Black, 1 = White, 2 = Red, 3 = Green, 4 = Blue, 5 = Yellow, 6 = Magenta, 7 = Cyan, 16 = Maroon, 17 = Dark Green, 18 = Dark Blue, 19 = Dark Yellow , almost brown), 20 = Dark Magenta, 21 = Teal, 22 = Light Gray, 23 = Dark Gray, the list goes on...
	style = xlwt.XFStyle() # Create the Pattern
	style.pattern = pattern # Add Pattern to Style

        test_value = _list
        for i in range(1,len(test_value)+1):
            if isinstance(test_value[i-1],dict):
                self.sheet_1.write(line_num+1,i,test_value[i-1]['fail'],style)
            else:
                self.sheet_1.write(line_num+1,i,test_value[i-1])        
    def save_excel(self):
        self.exl_obj.save(self.excel_name)       

    def mavlink_packet(self, msg):
        type = msg.get_type()
        if type == 'DISTANCE_SENSOR':
            self.distance = msg
            self.current_distance = msg.current_distance
            self.dis_log_raw = {"message":"DISTANCE_SENSOR", "value":str(self.current_distance)}
            self.mpstate.uiqueue.put(self.dis_log_raw)
            #print self.distance
        if type == 'ATTITUDE':
            self.mpstate.uiqueue.put({"message":"ATTITUDE", "roll":str(msg.roll), "pitch":str(msg.pitch), "yaw":str(msg.yaw)})
        if type == 'HIGHRES_IMU':
            self.HIGHRES_IMU = msg
            #print self.HIGHRES_IMU
            #self.abs_pressure = msg.abs_pressure
            #self.mag = "%s %s %s" % (msg.xmag,msg.ymag,msg.zmag)
            #self.acc = "%s %s %s" % (msg.xacc,msg.yacc,msg.zacc)
            #self.acc_x, self.acc_y, self.acc_z  = msg.xacc, msg.yacc, msg.zacc
            #self.gyro = "%s %s %s" % (msg.xgyro,msg.ygyro,msg.zgyro)
            #self.gyro_x, self.gyro_y, self.gyro_z  = msg.xgyro, msg.ygyro, msg.zgyro
            self.imu_log_raw = {"message":"HIGHRES_IMU", "xacc":str(msg.xacc), "yacc":str(msg.yacc), "zacc":str(msg.zacc),
                            "xgyro":str(msg.xgyro), "ygyro":str(msg.ygyro), "zgyro":str(msg.zgyro),
                            "xmag":str(msg.xmag), "ymag":str(msg.ymag), "zmag":str(msg.zmag), "abs_pressure":str(msg.abs_pressure)}
            self.mpstate.uiqueue.put(self.imu_log_raw)
            if self.zlog_tag:
                #self.zlog_raw = "xacc:%s,yacc:%s,zacc:%s,xgyro:%s,ygyro:%s,zgyro:%s,xmag:%s,ymag:%s,zmag:%s,distance:%s\r\n" % (
                #    str(msg.xacc),str(msg.yacc),str(msg.zacc),str(msg.xgyro),str(msg.ygyro),
                #    str(msg.zgyro),str(msg.xmag),str(msg.ymag),str(msg.zag),str(self.current_distance))
                #self.zlog.write(self.zlog_raw)
                self.zlog.write("%s %s\n" % (str(self.imu_log_raw),str(self.dis_log_raw)))
        if type == 'SVO_POSITION_RAW':
            self.mpstate.uiqueue.put({"message":"SVO_POSITION_RAW", "value_x":str(msg.position_x), "value_y":str(msg.position_y)})
            if self.svo_x_max < msg.position_x:
                self.svo_x_max = msg.position_x
            if self.svo_x_min > msg.position_x:
                self.svo_x_min = msg.position_x
            if self.svo_y_max < msg.position_y:
                self.svo_y_max = msg.position_y
            if self.svo_y_min > msg.position_y:
                self.svo_y_min = msg.position_y   
            self.x_diff = self.svo_x_max - self.svo_x_min
            self.y_diff = self.svo_y_max - self.svo_y_min
            #print self.dis_max
            #print self.dis_min
        if type == "SYS_STATUS":
            self.mpstate.uiqueue.put({"message":"SYS_STATUS", "value":str(msg.errors_count1)})
        elif type == 'LOCAL_POSITION_NED':
            self.console.set_status('position_ned_x','position_x %s' % msg.x)
            self.svo_x = msg.x
            #print type(self.svo_x)
            #self.console.set_status('position_ned_y','position_y %s' % msg.y)
            self.svo_y = msg.y
            #print (svo_y)
            #self.console.set_status('position_ned_z','position_ned %s' % msg.z)
            self.svo_z = msg.z

def init(mpstate):
    '''initialise module'''
    return AirbeetestModule(mpstate)
