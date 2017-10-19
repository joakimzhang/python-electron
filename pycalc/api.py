#!/usr/bin/env python
# -*- coding:utf-8 -*- 
'''
mavproxy - a MAVLink proxy program

Copyright Andrew Tridgell 2011
Released under the GNU GPL version 3 or later

'''

import sys, os, time, socket, signal
reload (sys)

sys.setdefaultencoding('utf-8')
import fnmatch, errno, threading
import serial, Queue, select
import traceback
import select
import shlex
import datetime
import os

from MAVProxy.modules.lib import textconsole
from MAVProxy.modules.lib import rline
from MAVProxy.modules.lib import mp_module
from MAVProxy.modules.lib import dumpstacks

# adding all this allows pyinstaller to build a working windows executable
# note that using --hidden-import does not work for these modules
try:
      from multiprocessing import freeze_support
      from pymavlink import mavwp, mavutil
      import matplotlib, HTMLParser
      try:
            import readline
      except ImportError:
            import pyreadline as readline
except Exception:
      pass

if __name__ == '__main__':
      freeze_support()

class MPStatus(object):
    '''hold status information about the mavproxy'''
    def __init__(self):
        self.gps	 = None
        self.msgs = {}
        self.msg_count = {}
        self.counters = {'MasterIn' : [], 'MasterOut' : 0, 'FGearIn' : 0, 'FGearOut' : 0, 'Slave' : 0}
        self.setup_mode = opts.setup
        self.mav_error = 0
        self.altitude = 0
        self.last_altitude_announce = 0.0
        self.last_distance_announce = 0.0
        self.exit = False
        self.flightmode = 'MAV'
        self.last_mode_announce = 0
        self.logdir = None
        self.last_heartbeat = 0
        self.last_message = 0
        self.heartbeat_error = False
        self.last_apm_msg = None
        self.last_apm_msg_time = 0
        self.highest_msec = 0
        self.have_gps_lock = False
        self.lost_gps_lock = False
        self.last_gps_lock = 0
        self.watch = None
        self.last_streamrate1 = -1
        self.last_streamrate2 = -1
        self.last_seq = 0
        self.armed = False

    def show(self, f, pattern=None):
        '''write status to status.txt'''
        if pattern is None:
            f.write('Counters: ')
            for c in self.counters:
                f.write('%s:%s ' % (c, self.counters[c]))
            f.write('\n')
            f.write('MAV Errors: %u\n' % self.mav_error)
            f.write(str(self.gps)+'\n')
        for m in sorted(self.msgs.keys()):
	    #print m
            if pattern is not None and not fnmatch.fnmatch(str(m).upper(), pattern.upper()):
                continue
            f.write("%u: %s\n" % (self.msg_count[m], str(self.msgs[m])))


    def write(self):
        '''write status to status.txt'''
        f = open('status.txt', mode='w')
        self.show(f)
        f.close()

def say_text(text, priority='important'):
    '''text output - default function for say()'''
    mpstate.console.writeln(text)

def say(text, priority='important'):
    '''text and/or speech output'''
    mpstate.functions.say(text, priority)

def add_input(cmd, immediate=False):
    '''add some command input to be processed'''
    if immediate:
        process_stdin(cmd)
    else:
        mpstate.input_queue.put(cmd)

class MAVFunctions(object):
    '''core functions available in modules'''
    def __init__(self):
        self.process_stdin = add_input
        self.param_set = param_set
        self.get_mav_param = get_mav_param
        self.say = say_text
        # input handler can be overridden by a module
        self.input_handler = None

class MPState(object):
    '''holds state of mavproxy'''
    def __init__(self):
        self.bsp_dir = ""
        self.bsp_name = ""
        self.app_dir = ""
        self.app_name = ""
        self.ssid = ""
        self.mac = ""
        self.console = textconsole.SimpleConsole()
        self.map = None
        self.map_functions = {}
        self.vehicle_type = None
        self.vehicle_name = None
        from MAVProxy.modules.lib.mp_settings import MPSettings, MPSetting
        self.settings = MPSettings(
            [ MPSetting('link', int, 1, 'Primary Link', tab='Link', range=(0,4), increment=1),
              MPSetting('streamrate', int, 4, 'Stream rate link1', range=(-1,20), increment=1),
              MPSetting('streamrate2', int, 4, 'Stream rate link2', range=(-1,20), increment=1),
              MPSetting('heartbeat', int, 1, 'Heartbeat rate', range=(0,5), increment=1),
              MPSetting('mavfwd', bool, True, 'Allow forwarded control'),
              MPSetting('mavfwd_rate', bool, False, 'Allow forwarded rate control'),
              MPSetting('shownoise', bool, True, 'Show non-MAVLink data'),
              MPSetting('baudrate', int, opts.baudrate, 'baudrate for new links', range=(0,10000000), increment=1),
              MPSetting('rtscts', bool, opts.rtscts, 'enable flow control'),
              MPSetting('select_timeout', float, 0.01, 'select timeout'),

              MPSetting('altreadout', int, 10, 'Altitude Readout',
                        range=(0,100), increment=1, tab='Announcements'),
              MPSetting('distreadout', int, 200, 'Distance Readout', range=(0,10000), increment=1),

              MPSetting('moddebug', int, opts.moddebug, 'Module Debug Level', range=(0,3), increment=1, tab='Debug'),
              MPSetting('compdebug', int, 0, 'Computation Debug Mask', range=(0,3), tab='Debug'),
              MPSetting('flushlogs', bool, False, 'Flush logs on every packet'),
              MPSetting('requireexit', bool, False, 'Require exit command'),
              MPSetting('wpupdates', bool, True, 'Announce waypoint updates'),

              MPSetting('basealt', int, 0, 'Base Altitude', range=(0,30000), increment=1, tab='Altitude'),
              MPSetting('wpalt', int, 100, 'Default WP Altitude', range=(0,10000), increment=1),
              MPSetting('rallyalt', int, 90, 'Default Rally Altitude', range=(0,10000), increment=1),
              MPSetting('terrainalt', str, 'Auto', 'Use terrain altitudes', choice=['Auto','True','False']),
              MPSetting('rally_breakalt', int, 40, 'Default Rally Break Altitude', range=(0,10000), increment=1),
              MPSetting('rally_flags', int, 0, 'Default Rally Flags', range=(0,10000), increment=1),

              MPSetting('source_system', int, 255, 'MAVLink Source system', range=(0,255), increment=1, tab='MAVLink'),
              MPSetting('source_component', int, 0, 'MAVLink Source component', range=(0,255), increment=1),
              MPSetting('target_system', int, 0, 'MAVLink target system', range=(0,255), increment=1),
              MPSetting('target_component', int, 0, 'MAVLink target component', range=(0,255), increment=1),
              MPSetting('state_basedir', str, None, 'base directory for logs and aircraft directories'),
              MPSetting('allow_unsigned', bool, True, 'whether unsigned packets will be accepted')
            ])

        self.completions = {
            "script"         : ["(FILENAME)"],
            "set"            : ["(SETTING)"],
            "status"         : ["(VARIABLE)"],
            "module"    : ["list",
                           "load (AVAILMODULES)",
                           "<unload|reload> (LOADEDMODULES)"]
            }

        self.status = MPStatus()

        # master mavlink device
        self.mav_master = None

        # mavlink outputs
        self.mav_outputs = []
        self.sysid_outputs = {}

        # SITL output
        self.sitl_output = None

        self.mav_param = mavparm.MAVParmDict()
        self.modules = []
        self.public_modules = {}
        self.functions = MAVFunctions()
        self.select_extra = {}
        self.continue_mode = False
        self.aliases = {}
        import platform
        self.system = platform.system()

    def module(self, name):
        '''Find a public module (most modules are private)'''
        if name in self.public_modules:
            return self.public_modules[name]
        return None
    
    def master(self):
        '''return the currently chosen mavlink master object'''
        if len(self.mav_master) == 0:
              return None
        if self.settings.link > len(self.mav_master):
            self.settings.link = 1

        # try to use one with no link error
        if not self.mav_master[self.settings.link-1].linkerror:
            return self.mav_master[self.settings.link-1]
        for m in self.mav_master:
            if not m.linkerror:
                return m
        return self.mav_master[self.settings.link-1]


def get_mav_param(param, default=None):
    '''return a EEPROM parameter value'''
    return mpstate.mav_param.get(param, default)

def param_set(name, value, retries=3):
    '''set a parameter'''
    name = name.upper()
    return mpstate.mav_param.mavset(mpstate.master(), name, value, retries=retries)

def cmd_script(args):
    '''run a script'''
    if len(args) < 1:
        print("usage: script <filename>")
        return

    run_script(args[0])

def cmd_set(args):
    '''control mavproxy options'''
    mpstate.settings.command(args)

def cmd_status(args):
    '''show status'''
    if len(args) == 0:
        mpstate.status.show(sys.stdout, pattern=None)
    else:
        for pattern in args:
            mpstate.status.show(sys.stdout, pattern=pattern)

def cmd_setup(args):
    mpstate.status.setup_mode = True
    mpstate.rl.set_prompt("")


def cmd_reset(args):
    print("Resetting master")
    mpstate.master().reset()

def cmd_watch(args):
    '''watch a mavlink packet pattern'''
    if len(args) == 0:
        mpstate.status.watch = None
        return
    mpstate.status.watch = args[0]
    print("Watching %s" % mpstate.status.watch)

def load_module(modname, quiet=False):
    '''load a module'''
    modpaths = ['MAVProxy.modules.mavproxy_%s' % modname, modname]
    for (m,pm) in mpstate.modules:
        if m.name == modname:
            if not quiet:
                print("module %s already loaded" % modname)
            return False
    for modpath in modpaths:
        try:
            m = import_package(modpath)
            reload(m)
            module = m.init(mpstate)
            if isinstance(module, mp_module.MPModule):
                mpstate.modules.append((module, m))
                if not quiet:
                    print("Loaded module %s" % (modname,))
                return True
            else:
                ex = "%s.init did not return a MPModule instance" % modname
                break
        except ImportError as msg:
            ex = msg
            if mpstate.settings.moddebug > 1:
                import traceback
                print(traceback.format_exc())
    print("Failed to load module: %s. Use 'set moddebug 3' in the MAVProxy console to enable traceback" % ex)
    return False

def unload_module(modname):
    '''unload a module'''
    for (m,pm) in mpstate.modules:
        if m.name == modname:
            if hasattr(m, 'unload'):
                m.unload()
            mpstate.modules.remove((m,pm))
            print("Unloaded module %s" % modname)
            return True
    print("Unable to find module %s" % modname)
    return False

def cmd_module(args):
    '''module commands'''
    usage = "usage: module <list|load|reload|unload>"
    if len(args) < 1:
        print(usage)
        return
    if args[0] == "list":
        for (m,pm) in mpstate.modules:
            print("%s: %s" % (m.name, m.description))
    elif args[0] == "load":
        if len(args) < 2:
            print("usage: module load <name>")
            return
        load_module(args[1])
    elif args[0] == "reload":
        if len(args) < 2:
            print("usage: module reload <name>")
            return
        modname = args[1]
        pmodule = None
        for (m,pm) in mpstate.modules:
            if m.name == modname:
                pmodule = pm
        if pmodule is None:
            print("Module %s not loaded" % modname)
            return
        if unload_module(modname):
            import zipimport
            try:
                reload(pmodule)
            except ImportError:
                clear_zipimport_cache()
                reload(pmodule)                
            if load_module(modname, quiet=True):
                print("Reloaded module %s" % modname)
    elif args[0] == "unload":
        if len(args) < 2:
            print("usage: module unload <name>")
            return
        modname = os.path.basename(args[1])
        unload_module(modname)
    else:
        print(usage)


def cmd_alias(args):
    '''alias commands'''
    usage = "usage: alias <add|remove|list>"
    if len(args) < 1 or args[0] == "list":
        if len(args) >= 2:
            wildcard = args[1].upper()
        else:
            wildcard = '*'
        for a in sorted(mpstate.aliases.keys()):
            if fnmatch.fnmatch(a.upper(), wildcard):
                print("%-15s : %s" % (a, mpstate.aliases[a]))
    elif args[0] == "add":
        if len(args) < 3:
            print(usage)
            return
        a = args[1]
        mpstate.aliases[a] = ' '.join(args[2:])
    elif args[0] == "remove":
        if len(args) != 2:
            print(usage)
            return
        a = args[1]
        if a in mpstate.aliases:
            mpstate.aliases.pop(a)
        else:
            print("no alias %s" % a)
    else:
        print(usage)
        return


def clear_zipimport_cache():
    """Clear out cached entries from _zip_directory_cache.
    See http://www.digi.com/wiki/developer/index.php/Error_messages"""
    import sys, zipimport
    syspath_backup = list(sys.path)
    zipimport._zip_directory_cache.clear()
 
    # load back items onto sys.path
    sys.path = syspath_backup
    # add this too: see https://mail.python.org/pipermail/python-list/2005-May/353229.html
    sys.path_importer_cache.clear()

# http://stackoverflow.com/questions/211100/pythons-import-doesnt-work-as-expected
# has info on why this is necessary.

def import_package(name):
    """Given a package name like 'foo.bar.quux', imports the package
    and returns the desired module."""
    print "module:%s\n" % name
    import zipimport
    try:
        mod = __import__(name)
    except ImportError:
        clear_zipimport_cache()
        mod = __import__(name)
        
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


command_map = {
    'script'  : (cmd_script,   'run a script of MAVProxy commands'),
    'setup'   : (cmd_setup,    'go into setup mode'),
    'reset'   : (cmd_reset,    'reopen the connection to the MAVLink master'),
    'status'  : (cmd_status,   'show status'),
    'set'     : (cmd_set,      'mavproxy settings'),
    'watch'   : (cmd_watch,    'watch a MAVLink pattern'),
    'module'  : (cmd_module,   'module commands'),
    'alias'   : (cmd_alias,    'command aliases')
    }

def process_stdin(line):
    '''handle commands from user'''
    if line is None:
        sys.exit(0)

    # allow for modules to override input handling
    if mpstate.functions.input_handler is not None:
          mpstate.functions.input_handler(line)
          return
    
    line = line.strip()

    if mpstate.status.setup_mode:
        # in setup mode we send strings straight to the master
        if line == '.':
            mpstate.status.setup_mode = False
            mpstate.status.flightmode = "MAV"
            mpstate.rl.set_prompt("MAV> ")
            return
        if line != '+++':
            line += '\r'
        for c in line:
            time.sleep(0.01)
            mpstate.master().write(c)
        return

    if not line:
        return

    args = shlex.split(line)
    cmd = args[0]
    while cmd in mpstate.aliases:
        line = mpstate.aliases[cmd]
        args = shlex.split(line) + args[1:]
        cmd = args[0]
        
    if cmd == 'help':
        k = command_map.keys()
        k.sort()
        for cmd in k:
            (fn, help) = command_map[cmd]
            print("%-15s : %s" % (cmd, help))
        return
    if cmd == 'exit' and mpstate.settings.requireexit:
        mpstate.status.exit = True
        return

    if not cmd in command_map:
        for (m,pm) in mpstate.modules:
            if hasattr(m, 'unknown_command'):
                try:
                    if m.unknown_command(args):
                        return
                except Exception as e:
                    print("ERROR in command: %s" % str(e))
        print("Unknown command '%s'" % line)
        return
    (fn, help) = command_map[cmd]
    try:
        fn(args[1:])
    except Exception as e:
        print("ERROR in command %s: %s" % (args[1:], str(e)))
        if mpstate.settings.moddebug > 1:
            traceback.print_exc()


def process_master(m):
    '''process packets from the MAVLink master'''
    try:
        s = m.recv(16*1024)
	
    except Exception:
        time.sleep(0.1)
        return
    # prevent a dead serial port from causing the CPU to spin. The user hitting enter will
    # cause it to try and reconnect
    if len(s) == 0:
        time.sleep(0.1)
        return

    if (mpstate.settings.compdebug & 1) != 0:
        return

    if mpstate.logqueue_raw:
        mpstate.logqueue_raw.put(str(s))

    if mpstate.status.setup_mode:
        if mpstate.system == 'Windows':
           # strip nsh ansi codes
           s = s.replace("\033[K","")
        sys.stdout.write(str(s))
        sys.stdout.flush()
        return

    if m.first_byte and opts.auto_protocol:
        m.auto_mavlink_version(s)
    msgs = m.mav.parse_buffer(s)
    #print msgs
    if msgs:
        for msg in msgs:
            sysid = msg.get_srcSystem()
            if sysid in mpstate.sysid_outputs:
                  # the message has been handled by a specialised handler for this system
                  continue
            if getattr(m, '_timestamp', None) is None:
                m.post_message(msg)
            if msg.get_type() == "BAD_DATA":
                if opts.show_errors:
                    mpstate.console.writeln("MAV error: %s" % msg)
                mpstate.status.mav_error += 1



def process_mavlink(slave):
    '''process packets from MAVLink slaves, forwarding to the master'''
    try:
        buf = slave.recv()
    except socket.error:
        return
    try:
        if slave.first_byte and opts.auto_protocol:
            slave.auto_mavlink_version(buf)
        msgs = slave.mav.parse_buffer(buf)
    except mavutil.mavlink.MAVError as e:
        mpstate.console.error("Bad MAVLink slave message from %s: %s" % (slave.address, e.message))
        return
    if msgs is None:
        return
    if mpstate.settings.mavfwd and not mpstate.status.setup_mode:
        for m in msgs:
            if mpstate.status.watch is not None:
                if fnmatch.fnmatch(m.get_type().upper(), mpstate.status.watch.upper()):
                    mpstate.console.writeln('> '+ str(m))
            mpstate.master().write(m.get_msgbuf())
    mpstate.status.counters['Slave'] += 1


def mkdir_p(dir):
    '''like mkdir -p'''
    if not dir:
        return
    if dir.endswith("/"):
        mkdir_p(dir[:-1])
        return
    if os.path.isdir(dir):
        return
    mkdir_p(os.path.dirname(dir))
    os.mkdir(dir)

def log_writer():
    '''log writing thread'''
    while True:
        mpstate.logfile_raw.write(mpstate.logqueue_raw.get())
        while not mpstate.logqueue_raw.empty():
            mpstate.logfile_raw.write(mpstate.logqueue_raw.get())
        while not mpstate.logqueue.empty():
            mpstate.logfile.write(mpstate.logqueue.get())
        if mpstate.settings.flushlogs:
            mpstate.logfile.flush()
            mpstate.logfile_raw.flush()

# If state_basedir is NOT set then paths for logs and aircraft
# directories are relative to mavproxy's cwd
def log_paths():
    '''Returns tuple (logdir, telemetry_log_filepath, raw_telemetry_log_filepath)'''
    if opts.aircraft is not None:
        if opts.mission is not None:
            print(opts.mission)
            dirname = "%s/logs/%s/Mission%s" % (opts.aircraft, time.strftime("%Y-%m-%d"), opts.mission)
        else:
            dirname = "%s/logs/%s" % (opts.aircraft, time.strftime("%Y-%m-%d"))
        # dirname is currently relative.  Possibly add state_basedir:
        if mpstate.settings.state_basedir is not None:
            dirname = os.path.join(mpstate.settings.state_basedir,dirname)
        mkdir_p(dirname)
        highest = None
        for i in range(1, 10000):
            fdir = os.path.join(dirname, 'flight%u' % i)
            if not os.path.exists(fdir):
                break
            highest = fdir
        if mpstate.continue_mode and highest is not None:
            fdir = highest
        elif os.path.exists(fdir):
            print("Flight logs full")
            sys.exit(1)
        logname = 'flight.tlog'
        logdir = fdir
    else:
        logname = os.path.basename(opts.logfile)
        dir_path = os.path.dirname(opts.logfile)
        if not os.path.isabs(dir_path) and mpstate.settings.state_basedir is not None:
            dir_path = os.path.join(mpstate.settings.state_basedir,dir_path)
        logdir = dir_path

    mkdir_p(logdir)
    return (logdir,
            os.path.join(logdir, logname),
            os.path.join(logdir, logname + '.raw'))


def open_telemetry_logs(logpath_telem, logpath_telem_raw):
    '''open log files'''
    if opts.append_log or opts.continue_mode:
        mode = 'a'
    else:
        mode = 'w'
    mpstate.logfile = open(logpath_telem, mode=mode)
    mpstate.logfile_raw = open(logpath_telem_raw, mode=mode)
    print("Log Directory: %s" % mpstate.status.logdir)
    print("Telemetry log: %s" % logpath_telem)

    # use a separate thread for writing to the logfile to prevent
    # delays during disk writes (important as delays can be long if camera
    # app is running)
    t = threading.Thread(target=log_writer, name='log_writer')
    t.daemon = True
    t.start()

def set_stream_rates():
    '''set mavlink stream rates'''
    if (not msg_period.trigger() and
        mpstate.status.last_streamrate1 == mpstate.settings.streamrate and
        mpstate.status.last_streamrate2 == mpstate.settings.streamrate2):
        return
    mpstate.status.last_streamrate1 = mpstate.settings.streamrate
    mpstate.status.last_streamrate2 = mpstate.settings.streamrate2
    for master in mpstate.mav_master:
        if master.linknum == 0:
            rate = mpstate.settings.streamrate
        else:
            rate = mpstate.settings.streamrate2
        if rate != -1:
            master.mav.request_data_stream_send(mpstate.settings.target_system, mpstate.settings.target_component,
                                                mavutil.mavlink.MAV_DATA_STREAM_ALL,
                                                rate, 1)

def check_link_status():
    '''check status of master links'''
    tnow = time.time()
    if mpstate.status.last_message != 0 and tnow > mpstate.status.last_message + 5:
        say("no link")
        mpstate.status.heartbeat_error = True
    for master in mpstate.mav_master:
        if not master.linkerror and (tnow > master.last_message + 5 or master.portdead):
            say("link %u down" % (master.linknum+1))
            master.linkerror = True

def send_heartbeat(master):
    if master.mavlink10():
        master.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                                  0, 0, 0)
    else:
        MAV_GROUND = 5
        MAV_AUTOPILOT_NONE = 4
        master.mav.heartbeat_send(MAV_GROUND, MAV_AUTOPILOT_NONE)

def periodic_tasks():
    '''run periodic checks'''
    if mpstate.status.setup_mode:
        return

    if (mpstate.settings.compdebug & 2) != 0:
        return

    if mpstate.settings.heartbeat != 0:
        heartbeat_period.frequency = mpstate.settings.heartbeat

    if heartbeat_period.trigger() and mpstate.settings.heartbeat != 0:
        mpstate.status.counters['MasterOut'] += 1
        for master in mpstate.mav_master:
            send_heartbeat(master)

    if heartbeat_check_period.trigger():
        check_link_status()

    set_stream_rates()

    # call optional module idle tasks. These are called at several hundred Hz
    for (m,pm) in mpstate.modules:
        if hasattr(m, 'idle_task'):
            try:
                m.idle_task()
            except Exception as msg:
                if mpstate.settings.moddebug == 1:
                    print(msg)
                    print "1111"
                elif mpstate.settings.moddebug > 1:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    traceback.print_exception(exc_type, exc_value, exc_traceback,
                                              limit=2, file=sys.stdout)

        # also see if the module should be unloaded:
        if m.needs_unloading:
            unload_module(m.name)

def main_loop():
    '''main processing loop'''
    if not mpstate.status.setup_mode and not opts.nowait:
        for master in mpstate.mav_master:
            send_heartbeat(master)
            if master.linknum == 0:
                print("Waiting for heartbeat from %s" % master.address)
                #master.wait_heartbeat()
        set_stream_rates()

    while True:
        if mpstate is None or mpstate.status.exit:
            return
        while not mpstate.input_queue.empty():
            line = mpstate.input_queue.get()
            mpstate.input_count += 1
            cmds = line.split(';')
            if len(cmds) == 1 and cmds[0] == "":
                  mpstate.empty_input_count += 1                 
            for c in cmds:
                process_stdin(c)

        for master in mpstate.mav_master:
	    #print master
            if master.fd is None:
                if master.port.inWaiting() > 0:
                    process_master(master)

        periodic_tasks()

        rin = []
        for master in mpstate.mav_master:
	    #print master
            if master.fd is not None and not master.portdead:
                rin.append(master.fd)
        for m in mpstate.mav_outputs:
            rin.append(m.fd)
	    #print m
        for sysid in mpstate.sysid_outputs:
            m = mpstate.sysid_outputs[sysid]
            rin.append(m.fd)
        if rin == []:
            time.sleep(0.0001)
            continue

        for fd in mpstate.select_extra:
            rin.append(fd)
        try:
            (rin, win, xin) = select.select(rin, [], [], mpstate.settings.select_timeout)
        except select.error:
            continue

        if mpstate is None:
            return

        for fd in rin:
            if mpstate is None:
                  return
            for master in mpstate.mav_master:
                  if fd == master.fd:
                        process_master(master)
                        if mpstate is None:
                              return
                        continue
            for m in mpstate.mav_outputs:
                if fd == m.fd:
                    process_mavlink(m)
                    if mpstate is None:
                          return
                    continue

            for sysid in mpstate.sysid_outputs:
                m = mpstate.sysid_outputs[sysid]
                if fd == m.fd:
                    process_mavlink(m)
                    if mpstate is None:
                          return
                    continue

            # this allow modules to register their own file descriptors
            # for the main select loop
            if fd in mpstate.select_extra:
                try:
                    # call the registered read function
                    (fn, args) = mpstate.select_extra[fd]
                    fn(args)
                except Exception as msg:
                    if mpstate.settings.moddebug == 1:
                        print(msg)
                    # on an exception, remove it from the select list
                    mpstate.select_extra.pop(fd)

def input_loop():
    '''wait for user input'''
    while mpstate.status.exit != True:
        
        
        try:
            if mpstate.status.exit != True:
                line = raw_input(mpstate.rl.prompt)
        except EOFError:
            mpstate.status.exit = True
            sys.exit(1)
        if line == "exit":
            mpstate.status.exit = True       
            continue
        if line == "burn":
            #print "get stick"
            burnshow.show()        
            continue
        if line == "stick":
            print "get stick"
            #myshow.show()
            continue
        if line == "unstick":
            print "delete stick"
            #myshow.close()
            continue
        mpstate.input_queue.put(line)


def run_script(scriptfile):
    '''run a script file'''
    try:
        f = open(scriptfile, mode='r')
    except Exception:
        return
    mpstate.console.writeln("Running script %s" % scriptfile)
    for line in f:
        line = line.strip()
        if line == "" or line.startswith('#'):
            continue
        if line.startswith('@'):
            line = line[1:]
        else:
            mpstate.console.writeln("-> %s" % line)
        process_stdin(line)
    f.close()

if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser("mavproxy.py [options]")

    parser.add_option("--master", dest="master", action='append',
                      metavar="DEVICE[,BAUD]", help="MAVLink master port and optional baud rate",
                      default=[])
    parser.add_option("--out", dest="output", action='append',
                      metavar="DEVICE[,BAUD]", help="MAVLink output port and optional baud rate",
                      default=[])
    parser.add_option("--baudrate", dest="baudrate", type='int',
                      help="default serial baud rate", default=57600)
    parser.add_option("--sitl", dest="sitl",  default=None, help="SITL output port")
    parser.add_option("--streamrate",dest="streamrate", default=4, type='int',
                      help="MAVLink stream rate")
    parser.add_option("--source-system", dest='SOURCE_SYSTEM', type='int',
                      default=255, help='MAVLink source system for this GCS')
    parser.add_option("--source-component", dest='SOURCE_COMPONENT', type='int',
                      default=0, help='MAVLink source component for this GCS')
    parser.add_option("--target-system", dest='TARGET_SYSTEM', type='int',
                      default=0, help='MAVLink target master system')
    parser.add_option("--target-component", dest='TARGET_COMPONENT', type='int',
                      default=0, help='MAVLink target master component')
    parser.add_option("--logfile", dest="logfile", help="MAVLink master logfile",
                      default='mav.tlog')
    parser.add_option("-a", "--append-log", dest="append_log", help="Append to log files",
                      action='store_true', default=False)
    parser.add_option("--quadcopter", dest="quadcopter", help="use quadcopter controls",
                      action='store_true', default=False)
    parser.add_option("--setup", dest="setup", help="start in setup mode",
                      action='store_true', default=False)
    parser.add_option("--nodtr", dest="nodtr", help="disable DTR drop on close",
                      action='store_true', default=False)
    parser.add_option("--show-errors", dest="show_errors", help="show MAVLink error packets",
                      action='store_true', default=False)
    parser.add_option("--speech", dest="speech", help="use text to speach",
                      action='store_true', default=False)
    parser.add_option("--aircraft", dest="aircraft", help="aircraft name", default=None)
    parser.add_option("--cmd", dest="cmd", help="initial commands", default=None, action='append')
    parser.add_option("--console", action='store_true', help="use GUI console")
    parser.add_option("--map", action='store_true', help="load map module")
    parser.add_option("--hardware", action='store_true', help="load hardware module")
    parser.add_option(
        '--load-module',
        action='append',
        default=[],
        help='Load the specified module. Can be used multiple times, or with a comma separated list')
    parser.add_option("--mav09", action='store_true', default=False, help="Use MAVLink protocol 0.9")
    parser.add_option("--mav20", action='store_true', default=False, help="Use MAVLink protocol 2.0")
    parser.add_option("--auto-protocol", action='store_true', default=False, help="Auto detect MAVLink protocol version")
    parser.add_option("--nowait", action='store_true', default=False, help="don't wait for HEARTBEAT on startup")
    parser.add_option("-c", "--continue", dest='continue_mode', action='store_true', default=False, help="continue logs")
    #parser.add_option("--dialect",  default="ardupilotmega", help="MAVLink dialect")
    parser.add_option("--dialect",  default="brisky", help="MAVLink dialect")
    parser.add_option("--rtscts",  action='store_true', help="enable hardware RTS/CTS flow control")
    parser.add_option("--moddebug",  type=int, help="module debug level", default=0)
    parser.add_option("--mission", dest="mission", help="mission name", default=None)
    parser.add_option("--daemon", action='store_true', help="run in daemon mode, do not start interactive shell")
    parser.add_option("--profile", action='store_true', help="run the Yappi python profiler")
    parser.add_option("--state-basedir", default=None, help="base directory for logs and aircraft directories")
    parser.add_option("--version", action='store_true', help="version information")
    #parser.add_option("--default-modules", default="log,signing,wp,rally,fence,param,relay,tuneopt,arm,mode,calibration,rc,auxopt,misc,cmdlong,battery,terrain,output,adsb", help='default module list')
    parser.add_option("--default-modules", default="dataflash_logger,airbeetest,log,signing,rally,fence,param,relay,tuneopt,arm,mode,calibration,rc,auxopt,misc,cmdlong,battery,terrain,output,adsb", help='default module list')

    (opts, args) = parser.parse_args()

    # warn people about ModemManager which interferes badly with APM and Pixhawk
    if os.path.exists("/usr/sbin/ModemManager"):
        print("WARNING: You should uninstall ModemManager as it conflicts with APM and Pixhawk")

    if opts.mav09:
        os.environ['MAVLINK09'] = '1'
    if opts.mav20:
        os.environ['MAVLINK20'] = '1'
    from pymavlink import mavutil, mavparm
    mavutil.set_dialect(opts.dialect)

    #version information
    if opts.version:
        import pkg_resources
        version = pkg_resources.require("mavproxy")[0].version
        print ("MAVProxy is a modular ground station using the mavlink protocol")
        print ("MAVProxy Version: " + version)
        sys.exit(1)
    
    # global mavproxy state
    mpstate = MPState()
    mpstate.status.exit = False
    mpstate.command_map = command_map
    mpstate.continue_mode = opts.continue_mode
    # queues for logging
    mpstate.logqueue = Queue.Queue()
    mpstate.logqueue_raw = Queue.Queue()
    
    mpstate.uiqueue = Queue.Queue()


    if opts.speech:
        # start the speech-dispatcher early, so it doesn't inherit any ports from
        # modules/mavutil
        load_module('speech')

    if not opts.master:
        serial_list = mavutil.auto_detect_serial(preferred_list=['*FTDI*',"*Arduino_Mega_2560*", "*3D_Robotics*", "*USB_to_UART*", '*PX4*', '*FMU*'])
        print('Auto-detected serial ports are:')
        for port in serial_list:
              print("%s" % port)

    # container for status information
    mpstate.settings.target_system = opts.TARGET_SYSTEM
    mpstate.settings.target_component = opts.TARGET_COMPONENT

    mpstate.mav_master = []

    mpstate.rl = rline.rline("MAV> ", mpstate)

    def quit_handler(signum = None, frame = None):
        #print 'Signal handler called with signal', signum
        if mpstate.status.exit:
            print ('Clean shutdown impossible, forcing an exit')
            sys.exit(0)
        else:
            mpstate.status.exit = True

    # Listen for kill signals to cleanly shutdown modules
    fatalsignals = [signal.SIGTERM]
    try:
        fatalsignals.append(signal.SIGHUP)
        fatalsignals.append(signal.SIGQUIT)
    except Exception:
        pass
    if opts.daemon: # SIGINT breaks readline parsing - if we are interactive, just let things die
        fatalsignals.append(signal.SIGINT)

    for sig in fatalsignals:
        signal.signal(sig, quit_handler)

    load_module('link', quiet=True)

    mpstate.settings.source_system = opts.SOURCE_SYSTEM
    mpstate.settings.source_component = opts.SOURCE_COMPONENT

    # open master link
    for mdev in opts.master:
        if not mpstate.module('link').link_add(mdev):
            sys.exit(1)

    if not opts.master and len(serial_list) == 1:
          print("Connecting to %s" % serial_list[0])
          mpstate.module('link').link_add(serial_list[0].device)
    elif not opts.master:
          #wifi_device = '0.0.0.0:14550'
          wifi_device = 'udp:0.0.0.0:14550'
          #wifi_device = 'tcp:192.168.1.1:10000'
          mpstate.module('link').link_add(wifi_device)


    # open any mavlink output ports
    for port in opts.output:
        mpstate.mav_outputs.append(mavutil.mavlink_connection(port, baud=int(opts.baudrate), input=False))

    if opts.sitl:
        mpstate.sitl_output = mavutil.mavudp(opts.sitl, input=False)

    mpstate.settings.streamrate = opts.streamrate
    mpstate.settings.streamrate2 = opts.streamrate

    if opts.state_basedir is not None:
        mpstate.settings.state_basedir = opts.state_basedir

    msg_period = mavutil.periodic_event(1.0/15)
    heartbeat_period = mavutil.periodic_event(1)
    heartbeat_check_period = mavutil.periodic_event(0.33)

    mpstate.input_queue = Queue.Queue()
    mpstate.input_count = 0
    mpstate.empty_input_count = 0
    if opts.setup:
        mpstate.rl.set_prompt("")

    # call this early so that logdir is setup based on --aircraft
    (mpstate.status.logdir, logpath_telem, logpath_telem_raw) = log_paths()

    if not opts.setup:
        # some core functionality is in modules
        standard_modules = opts.default_modules.split(',')
        for m in standard_modules:
            load_module(m, quiet=True)

    if opts.console:
        process_stdin('module load console')

    if opts.map:
        process_stdin('module load map')

    for module in opts.load_module:
        modlist = module.split(',')
        for mod in modlist:
            process_stdin('module load %s' % mod)

    if 'HOME' in os.environ and not opts.setup:
        start_script = os.path.join(os.environ['HOME'], ".mavinit.scr")
        if os.path.exists(start_script):
            run_script(start_script)
    if 'LOCALAPPDATA' in os.environ and not opts.setup:
        start_script = os.path.join(os.environ['LOCALAPPDATA'], "MAVProxy", "mavinit.scr")
        if os.path.exists(start_script):
            run_script(start_script)

    if opts.aircraft is not None:
        start_script = os.path.join(opts.aircraft, "mavinit.scr")
        if os.path.exists(start_script):
            run_script(start_script)
        else:
            print("no script %s" % start_script)

    if opts.cmd is not None:
        for cstr in opts.cmd:
            cmds = cstr.split(';')
            for c in cmds:
                process_stdin(c)

    if opts.profile:
        import yappi    # We do the import here so that we won't barf if run normally and yappi not available
        yappi.start()

    # log all packets from the master, for later replay
    open_telemetry_logs(logpath_telem, logpath_telem_raw)

    # run main loop as a thread
    mpstate.status.thread = threading.Thread(target=main_loop, name='main_loop')
    mpstate.status.thread.daemon = True
    mpstate.status.thread.start()




    #add the ui test code !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1
    #coding:utf-8
    from PyQt4 import QtCore, QtGui  
    from PyQt4.QtGui import QFileDialog,QHBoxLayout,QPalette
    from test2 import Ui_MainWindow  
    from burn import Ui_MainWindow_burn
    from PyQt4.QtCore import QDir
    import platform
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    from matplotlib import animation
    import numpy as np
    from matplotlib import pyplot as plt 
    import random
    	
    class WorkThread(QtCore.QThread):
        """workthread to avoid the wt hang"""
        def __init__(self, _func):
            super(WorkThread, self).__init__()
            self._func = _func
        def run(self):
            process_stdin(self._func) 


    class UIThread(QtCore.QThread):
        """workthread to add the ui"""
        finishSignal = QtCore.pyqtSignal(str)
        imu_Signal = QtCore.pyqtSignal(dict)
        def __init__(self):
            super(UIThread, self).__init__()
            
        def run(self):
            while not mpstate.status.exit:
                #time.sleep(0.1)
                try:
                    if mpstate.status.exit:
                        print "!!!!!!!!!!!!!exit while!!!!!!"
                        break
                    else:
                        #print mpstate.status.exit
                        pass
                    _log = mpstate.uiqueue.get()
                    if isinstance(_log,dict):
                        self.imu_Signal.emit(_log)
                        pass
                    else:
                        self.finishSignal.emit(_log)
                        pass
                except KeyboardInterrupt:
                    break
                #self.textEdit.setPlainText(str(_log))
        #def __del__(self):
        #    self.wait()
    class BurnWindow(QtGui.QMainWindow,Ui_MainWindow_burn):  
        
        def __init__(self):  
            super(BurnWindow,self).__init__()  
            self.setupUi(self)  
            self._dis = [0 for i in range(100)]
            self._dis_max = 5
            self._dis_min = 0
            self.x_acc_list = []
            self.y_acc_list = []
            self.z_acc_list = []
            self.x_gyro_list = []
            self.y_gyro_list = []
            self.z_gyro_list = []
            self.x_mag_list = []
            self.y_mag_list = []
            self.z_mag_list = []
            self.distance_list = [0 for i in range(20)]
            self.abs_pressure_list = [0 for i in range(20)]
            
            self.test_num = 500
            self.test_num_ui = 200
            self.x_acc_log = []
            self.y_acc_log = []
            self.z_acc_log = []
            self.x_gyro_log = []
            self.y_gyro_log = []
            self.z_gyro_log = []
            self.x_mag_log = []
            self.y_mag_log = []
            self.z_mag_log = []
            self.distance_log = []
            self.abs_pressure_log = []
            self.temp_log = []            
            self.temp = 0

            self.imu_test_tag = 0
            
            self._createFigures()
            self._createLayouts()
            self.pe = QPalette()
            self.pe.setColor(QPalette.WindowText,QtCore.Qt.red)
            self.pe_black = QPalette()
            self.pe_black.setColor(QPalette.WindowText,QtCore.Qt.black)
            
            self._uithread = UIThread()
            self._uithread.finishSignal.connect(self.write_console)
            self._uithread.imu_Signal.connect(self.write_imu)    
            try:
                self._uithread.start()
            except KeyboardInterrupt:
                print "exit!!!"
            #self._uithread.setDaemon(True)

        def _createFigures(self):
            #self._fig = Figure(figsize=(80, 60), dpi=100, tight_layout=True) 
            #self._fig = Figure()
            self._fig = plt.figure() 
            #self._fig.set_facecolor("#F5F5F5") # 背景色
            #self._fig.subplots_adjust(left=0.08, top=0.92, right=0.95, bottom=0.1) 
            self._canvas = FigureCanvas(self._fig) # 画布
            self._ax = self._fig.add_subplot(111) # 增加subplot
            
            #self._ax = plt.axes(xlim=(0, 2), ylim=(-2, 2)) 
            
            #self._ax.hold(True)
            self._initializeFigure()
            
             


        def _initializeFigure(self):
            #Font = {'family': 'Tahoma',
            #		'weight': 'bold',
            #		'size': 10}
            # Abscissa
            #self._ax.set_xlim([380, 780])
            #self._ax.set_xticks([380, 460, 540, 620, 700, 780])
            #self._ax.set_xticklabels([380, 460, 540, 620, 700, 780], fontdict=Font)
            self._ax.set_xlabel("time")
			# Ordinate
            #self._ax.set_ylim([0.0, 1.0])
            #self._ax.set_yticks(np.arange(0.0, 1.1, 0.2))
            #self._ax.set_yticklabels(np.arange(0.0, 1.1, 0.2), fontdict=Font)
            self._ax.set_ylabel("value")
            self._ax.grid(True)
            self.line, = self._ax.plot(self._dis)
            

        def _createLayouts(self):
            layout = QHBoxLayout(self.frame)
            #layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self._canvas) # Add Matplotli
        
        def _init(self):    
            self.line.set_data([])      
            return self.line,
        def imu_test(self):
            #process_stdin("imu_test")
            process_stdin("wifi")
            #sys.path.append("/home/user/git/test_tool/MAVProxy-master/MAVProxy/modules")
            #print sys.path
            #import mavproxy_airbeetest 
            #self.airbee_test = mavproxy_airbeetest.AirbeetestModule(mpstate)
            if self.imu_test_tag == 0:
                self.imu_to_excel()
                self.imu_test_tag = 1
            else:
                self.save_imu_to_excel()
                self.imu_test_tag = 0
        def ESC_test(self):
            process_stdin("arm throttle")
            time.sleep(2)
            process_stdin("disarm")
        def boot_time(self):
            process_stdin("pressure 1")
        def connect(self):
            process_stdin("link add udp:0.0.0.0:14550")
        def disconnect(self):
            process_stdin("link remove 0")
        def animate(self, i):  

            x = self.x
            y = i
            self._ax.set_ylim([self._dis_min, self._dis_max])
            self.line.set_ydata(i)
            return self.line,
        def data_gen(self):
            
            while 1:
                #self._dis = self._dis[1:]+self._dis
                #print self._dis
                yield(self._dis)
        def on_radioButton_clicked(self):
            anim1=animation.FuncAnimation(self._fig, self.animate,self.data_gen,interval=100)  
            #init_func=self._init,
            self._canvas.draw()
            #self._ax.clear()
            if self.radioButton_dis.isChecked():
                pass
        def versions(self):
            process_stdin("versions")
        def wifi(self):
            #print ('start bsp burn')
            process_stdin("wifi")
        def check_log(self):
            #print ('start bsp burn')
            process_stdin("check_log")
        def app_version(self):
            #print ('start bsp burn')
            process_stdin("app_version")          
        def bsp(self):
            #print ('start bsp burn')
            self._bsp = WorkThread("bsp")
            self._bsp.start()
            #process_stdin('bsp') 

        def airbee(self):
            #print ('start airbee burn')
            self._airbee = WorkThread("airbee")
            self._airbee.start()
            #self.textEdit.setPlainText("bbbb")
            #process_stdin('airbee') 
        def bsp_click(self):
            if platform.system() == "Linux":
                bsp_file_path = QFileDialog.getOpenFileName(self, 'Open file',   
                                                            '/home/jenkins/release/bsp',"txt files (*.sh)")
            if platform.system() == "Windows":
                bsp_file_path = QFileDialog.getOpenFileName(self, 'Open file',   
                                                            'F:/tools/',"txt files (*.bat)")
            if bsp_file_path:  
                self.bsp_dir_lineEdit.setText(bsp_file_path)
                mpstate.bsp_dir,mpstate.bsp_name = os.path.split(str(bsp_file_path))
                print mpstate.bsp_dir,mpstate.bsp_name
                process_stdin("set_build_dir")
        def app_click(self):
            if platform.system() == "Linux":
                app_file_path = QFileDialog.getOpenFileName(self, 'Open file',   
                                                            '/home/jenkins/release/AirBee',"txt files (*.sh)")
            if platform.system() == "Windows":
                app_file_path = QFileDialog.getOpenFileName(self, 'Open file',   
                                                            'F:/tools/build_tool',"txt files (*.bat)")
            if app_file_path:  
                self.app_dir_lineEdit.setText(app_file_path)
                mpstate.app_dir,mpstate.app_name = os.path.split(str(app_file_path))
                print mpstate.app_dir,mpstate.app_name
                process_stdin("set_build_dir")
        def log_click(self):
            log_dir = self.log_dir_lineEdit.text()
            print log_dir
            _time =  datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            os.system("adb pull /root/log/%s %s" % (log_dir, _time))
        def param_click(self):

            if platform.system() == "Linux":
                param_file_path = QFileDialog.getOpenFileName(self, 'Open file',   
                                                            '/home/user/git/test_tool/MAVProxy-master',"txt files (*.parm)")
            if platform.system() == "Windows":
                param_file_path = QFileDialog.getOpenFileName(self, 'Open file',   
                                                            'F:/tools/build_tool',"txt files (*.parm)")
            if param_file_path:  
                self.param_dir_lineEdit.setText(param_file_path)
                #mpstate.app_dir,mpstate.app_name = os.path.split(str(app_file_path))
                #print mpstate.app_dir,mpstate.app_name
                #process_stdin("set_build_dir")
        def param_load(self):
            import datetime
            param_dir = self.param_dir_lineEdit.text()
            print param_dir
            #_time =  datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            process_stdin("param load %s" % param_dir)
        def write_console(self,_str):
            #_log = mpstate.uiqueue.get()
            #print "call write console"
            cursor = self.textEdit.textCursor()
            cursor.insertText(_str)
            self.textEdit.setTextCursor(cursor)
            self.textEdit.ensureCursorVisible()
            #self.textEdit.setPlainText(_str)
        def judge_imu(self, _list, _label,_imu):
            peak_peak = max(_list)-min(_list)
            std = np.std(_list)
            mean = float(sum(_list)/len(_list))
            #_label.setText("pkpk:%.6f std:%.6f" % (peak_peak,std))    
            _label.setText("pkpk:%.6f std:%.6f mean:%.6f" % (peak_peak,std,mean))    
            if _imu == "acc":
                if std>0.015:
                    _label.setPalette(self.pe)
		else:
                    _label.setPalette(self.pe_black)
            if _imu == "gyro":
                if std>0.0014:
                    _label.setPalette(self.pe)
		else:
                    _label.setPalette(self.pe_black)
        def judge_distance(self, _list, _label):
            peak_peak = max(_list)-min(_list)
            std = np.std(_list)
            mean = float(sum(_list)/len(_list))
            _label.setText("pkpk:%.6f std:%.6f mean:%.6f" % (peak_peak,std,mean))    
            if peak_peak>5:
                _label.setPalette(self.pe)
            else:
                _label.setPalette(self.pe_black)
        def _pk_pk(self, _list, _num):
            #import pdb
            #pdb.set_trace()
            #print _list
            if _list:
            	peak_peak = max(_list)-min(_list)
                print "num:%s  pkpk:%s\n" % (_num,peak_peak)
                if peak_peak == 0:
                    return {"fail":peak_peak}
                if _num in [2,3,4]:
            	    if peak_peak>0.5:
                        return {"fail":peak_peak}
                elif _num in [5,6,7]:
            	    if peak_peak>0.1:
                        return {"fail":peak_peak}
                elif _num in [8,9,10]:
            	    if peak_peak>0.1:
                        return {"fail":peak_peak}
                elif _num == 0:
                    if peak_peak>1000:
                        return {"fail":peak_peak}
                elif _num == 1:
                    if peak_peak>5:
                        return {"fail":peak_peak}
                elif _num == 11:
                    if peak_peak>60:
                        return {"fail":peak_peak}
            	else:
                    print "wrong _num of list"
                return max(_list)-min(_list)
            else:
                return 0
        def _std(self, _list, _num):
            if _list:
                std = np.std(_list)
                print "num:%s  std:%s\n" % (_num, std)
                if std == 0:
                  return {"fail":std}
                if _num in [2,3,4]:
            	    if std>0.015:
                        return {"fail":std}
                elif _num in [5,6,7]:
            	    if std>0.0014:
                        return {"fail":std}
                elif _num in [8,9,10]:
            	    if std>0.01:
                        return {"fail":std}
                elif _num == 0:
                    if std>10000:
                        return {"fail":std}
                elif _num == 1:
                    if std>10000:
                        return {"fail":std}
                elif _num == 11:
                    pass
            	else:
                    print "wrong _num of list"
            	return np.std(_list)
            else:
                return 0
        def _mean(self, _list, _num):
            if _list:
            	return float(sum(_list)/len(_list))
            else:
                return 0
        def imu_to_excel(self):
            self.label_imutest.setText("testing")
            self.pushButton_imutest.setText("stop")
            #current_path = self.getcwd()
            sys.path.append("%s/MAVProxy/modules" % os.getcwd())
            print sys.path
            import mavproxy_airbeetest 
            self.airbee_test = mavproxy_airbeetest.AirbeetestModule(mpstate)
            self.airbee_test.creat_excel("imu_test.xls")
            _time =  datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            #print "=============",mpstate.ssid,"================="
            #sheet_name = "%s_%s" % (_time, mpstate.ssid[-3:])
            print "=============",mpstate.mac,"================="
            #sheet_name = "%s_%s" % (_time, mpstate.mac)
            self.sheet_name = "%s_%s" % ("Daybreaker2", mpstate.mac)
            self.airbee_test.creat_sheet(self.sheet_name)
            column_0 = ["name","abs_pressure","current_distance","xacc","yacc","zacc","xgyro","ygyro","zgyro","xmag","ymag","zmag","temprature","test_result"]
            column_all = ["name","mac","test_item","abs_pressure","current_distance","xacc","yacc","zacc","xgyro","ygyro","zgyro","xmag","ymag","zmag","temprature","test_result"]
            #time.sleep(5)
            #print self.distance_log
            self.airbee_test.creat_sheet_header(column_0)
            self.airbee_test.creat_sheet_all_header(column_all)
        def math_clume_list(self, func, _list):
            math_list = [func(_list[i],i) for i in range(len(_list))]
            return math_list
        def save_imu_to_excel(self):
            #apeend none for distance if less then self.test_num, \
            #so that the distanse data number will equal to imu
            colume_raw = [self.abs_pressure_log, self.distance_log, self.x_acc_log, self.y_acc_log,
                          self.z_acc_log, self.x_gyro_log, self.y_gyro_log, self.z_gyro_log,
                          self.x_mag_log, self.y_mag_log, self.z_mag_log, self.temp_log]
            if len(colume_raw[1])<self.test_num:
                colume_raw[1] = colume_raw[1] + [0 for i in range(self.test_num-len(colume_raw[1]))]
            colume_pkpk = ["PKPK"]+self.math_clume_list(self._pk_pk,colume_raw)   
            colume_std = ["STD"]+self.math_clume_list(self._std,colume_raw)   
            colume_mean = ["Mean"]+self.math_clume_list(self._mean,colume_raw)   
            self.airbee_test.append_excel(1,colume_pkpk)
            self.airbee_test.append_excel(2,colume_std)
            self.airbee_test.append_excel(3,colume_mean)
            #new
            self.airbee_test.append_excel_all_result([self.sheet_name]+colume_std)

            for i in range(self.test_num):
                colume_line = [j[i] for j in colume_raw]
                #print colume_line
                self.airbee_test.append_excel(i+5,[str(i)]+ colume_line)


            self.airbee_test.save_excel()
            self.label_imutest.setText("complete")
            self.label_distest.setText("complete")
            self.pushButton_imutest.setText("imu test")
            #reset the imu log
            self.x_acc_log = []
            self.y_acc_log = []
            self.z_acc_log = []
            self.x_gyro_log = []
            self.y_gyro_log = []
            self.z_gyro_log = []
            self.x_mag_log = []
            self.y_mag_log = []
            self.z_mag_log = []
            self.distance_log = []
            self.abs_pressure_log = []
            self.temp_log = []
            self.temp = 0
            #print self.distance_log
        def _get_log(self, _list, _str, _item):    
            if self.imu_test_tag == 0:
                return 0
            if len(_list)<self.test_num:
                _list.append(float(_str[_item]))
                self.label_distest.setText(str(len(_list)))
            else:
                _list[:] = _list[1:]+[float(_str[_item])] 
                self.label_imutest.setPalette(self.pe)
                self.label_distest.setText("get imu")
        def _get_log_dis(self, _list, _str, _item):    
            if self.imu_test_tag == 0:
                return 0
            if len(_list)<self.test_num:
                _list.append(float(_str[_item]))
                self.label_imutest.setText(str(len(_list)))
            else:
                _list[:] = _list[1:]+[float(_str[_item])] 
                self.label_imutest.setPalette(self.pe)
                self.label_imutest.setText("get dis")
        def _get_log_temp(self, _list, _item):    
            if self.imu_test_tag == 0:
                return 0
            if len(_list)<self.test_num:
                _list.append(float(_item))
            else:
                _list[:] = _list[1:]+[float(_item)] 
                
        def write_imu(self,_str):
            #print _str
            if _str["message"] == "DISTANCE_SENSOR":
                self.label_dis.setText(_str["value"])
                if len(self._dis)<100:
                    self._dis.append(int(_str["value"]))
                else:
                    self._dis = self._dis[1:]+[int(_str["value"])]
                self._get_log_dis(self.distance_log, _str, "value")
                self.judge_distance(self._dis, self.label_distance)
                self._dis_max = max(self._dis)
                self._dis_min = min(self._dis)
               
            if _str["message"] == "SVO_POSITION_RAW":
                self.label_svo_x.setText(_str["value_x"])
                self.label_svo_y.setText(_str["value_y"])
            if _str["message"] == "SYS_STATUS":
                self.label_tmp.setText(_str["value"])
                self.temp = _str["value"]          
            if _str["message"] == "HIGHRES_IMU":
                #"abs_pressure"
                if len(self.abs_pressure_list)<100:
                    self.abs_pressure_list.append(float(_str["abs_pressure"]))
                else:
                    self.abs_pressure_list = self.abs_pressure_list[1:]+[float(_str["abs_pressure"])] 
                self._get_log(self.abs_pressure_log, _str, "abs_pressure")
                self._get_log_temp(self.temp_log, self.temp)
                self.judge_imu(self.abs_pressure_list, self.label_pressure,"abs_pressure")
                #"xacc"
                if len(self.x_acc_list)<self.test_num_ui:
                    self.x_acc_list.append(float(_str["xacc"]))
                else:
                    self.x_acc_list = self.x_acc_list[1:]+[float(_str["xacc"])] 
                self._get_log(self.x_acc_log, _str, "xacc")
                self.judge_imu(self.x_acc_list, self.label_xacc,"acc")
                
                #peak_peak = max(self.x_acc_list)-min(self.x_acc_list)
                #std = np.std(self.x_acc_list)
                #self.label_xacc.setText("xacc:%.6f std:%.6f" % (peak_peak,std))    
                #if peak_peak>0.05 or std>0.03:
                #    self.label_xacc.setPalette(self.pe)
                #else:
                #    self.label_xacc.setPalette(self.pe_black)

                if len(self.x_gyro_list)<self.test_num_ui:
                    self.x_gyro_list.append(float(_str["xgyro"]))
                else:
                    self.x_gyro_list = self.x_gyro_list[1:]+[float(_str["xgyro"])] 
                self.judge_imu(self.x_gyro_list, self.label_xgyro,"gyro")
                self._get_log(self.x_gyro_log, _str, "xgyro")
                #self.label_xgyro.setText("xgyro:%.6f std:%.6f" % ((max(self.x_gyro_list)-min(self.x_gyro_list)),np.std(self.x_gyro_list)))    

                #self.label_pitch.setText("yacc"+_str["yacc"])
                if len(self.y_acc_list)<self.test_num_ui:
                    self.y_acc_list.append(float(_str["yacc"]))
                else:
                    self.y_acc_list = self.y_acc_list[1:]+[float(_str["yacc"])] 
                self.judge_imu(self.y_acc_list, self.label_yacc,"acc")
                self._get_log(self.y_acc_log, _str, "yacc")
                #self.label_yacc.setText("yacc:%.6f std:%.6f" % ((max(self.y_acc_list)-min(self.y_acc_list)),np.std(self.y_acc_list)))    


                if len(self.y_gyro_list)<self.test_num_ui:
                    self.y_gyro_list.append(float(_str["ygyro"]))
                else:
                    self.y_gyro_list = self.y_gyro_list[1:]+[float(_str["ygyro"])] 
                self.judge_imu(self.y_gyro_list, self.label_ygyro,"gyro")
                self._get_log(self.y_gyro_log, _str, "ygyro")
                #self.label_ygyro.setText("ygyro:%.6f std:%.6f" % ((max(self.y_gyro_list)-min(self.y_gyro_list)),np.std(self.y_gyro_list)))    



                #self.label_yaw.setText("zacc"+_str["zacc"])
                if len(self.z_acc_list)<self.test_num_ui:
                    self.z_acc_list.append(float(_str["zacc"]))
                else:
                    self.z_acc_list = self.z_acc_list[1:]+[float(_str["zacc"])] 
                self.judge_imu(self.z_acc_list, self.label_zacc,"acc")
                self._get_log(self.z_acc_log, _str, "zacc")
                #self.label_zacc.setText("zacc:%.6f std:%.6f" % ((max(self.z_acc_list)-min(self.z_acc_list)),np.std(self.z_acc_list)))    


                if len(self.z_gyro_list)<self.test_num_ui:
                    self.z_gyro_list.append(float(_str["zgyro"]))
                else:
                    self.z_gyro_list = self.z_gyro_list[1:]+[float(_str["zgyro"])] 
                self.judge_imu(self.z_gyro_list, self.label_zgyro,"gyro")
                self._get_log(self.z_gyro_log, _str, "zgyro")
                #self.label_zgyro.setText("zgyro:%.6f std:%.6f" % ((max(self.z_gyro_list)-min(self.z_gyro_list)),np.std(self.z_gyro_list)))    

                if len(self.x_mag_list)<self.test_num_ui:
                    self.x_mag_list.append(float(_str["xmag"]))
                else:
                    self.x_mag_list = self.x_mag_list[1:]+[float(_str["xmag"])] 
                self.judge_imu(self.x_mag_list, self.label_xmag,"mag")
                self._get_log(self.x_mag_log, _str, "xmag")

                if len(self.y_mag_list)<self.test_num_ui:
                    self.y_mag_list.append(float(_str["ymag"]))
                else:
                    self.y_mag_list = self.y_mag_list[1:]+[float(_str["ymag"])] 
                self.judge_imu(self.y_mag_list, self.label_ymag,"mag")
                self._get_log(self.y_mag_log, _str, "ymag")

            
                if len(self.z_mag_list)<self.test_num_ui:
                    self.z_mag_list.append(float(_str["zmag"]))
                else:
                    self.z_mag_list = self.z_mag_list[1:]+[float(_str["zmag"])] 
                self.judge_imu(self.z_mag_list, self.label_zmag,"mag")
                self._get_log(self.z_mag_log, _str, "zmag")

            if _str["message"] == "ATTITUDE":
                self.label_roll.setText(_str["roll"])
                self.label_pitch.setText(_str["pitch"])
                self.label_yaw.setText(_str["yaw"])
            
             
    burn_app=QtGui.QApplication(sys.argv)  
    burnshow=BurnWindow()  
    #sys.exit(burn_app.exec_())
    #burnshow.show()
    #main()
    class CalcApi(object):
        def calc(self, text):
	    """based on the input text, return the int result"""
            try:
                result = real_calc(text)
		return result
                #return sum(text)
	    except Exception as e:
		return e
        def echo(self, text):
            """echo any text"""
            return text
        def rand(self):
            #return datetime.datetime.now()
            result = mpstate.uiqueue.get()
            #print result
            return str(result)

    import zerorpc
    def parse_port():
        return '4243'

    def main():
	addr = 'tcp://127.0.0.1:' + parse_port()
	s = zerorpc.Server(CalcApi())
	s.bind(addr)
	print('start running on {}'.format(addr))
	s.run()

    main()

    class MyWindow(QtGui.QMainWindow,Ui_MainWindow):  
        def __init__(self):  
            super(MyWindow,self).__init__()  
            self.setupUi(self)  
    	
      
        def offboard(self):
            print ('start test')
            print (self.lineEdit.text())
            #process_stdin('offboard')
            process_stdin('p_mode')
        def position(self):
            print ('start test')
            print (self.lineEdit.text())
            #process_stdin('offboard')
            process_stdin('p_mode')
        def altitude(self):
            print ('start test')
            print (self.lineEdit.text())
            #process_stdin('offboard')
            process_stdin('a_mode')
        def manual(self):
            print ('start test')
            print (self.lineEdit.text())
            #process_stdin('offboard')
            process_stdin('m_mode %s' %str(self.verticalSlider.value()))
        def takeoff(self):
            process_stdin('takeoff3')
        def hold(self):
            process_stdin('h %s'%str(self.verticalSlider.value()))
        def front(self):
            process_stdin('x %s'%str(self.verticalSlider.value()))
        def back(self):
            process_stdin('x %s'%str(self.verticalSlider.value()*(-1)))
        def left(self):
            process_stdin('y %s'%str(self.verticalSlider.value()*(-1)))
        def right(self):
            process_stdin('y %s'%str(self.verticalSlider.value()))
        def up(self):
            #print self.verticalSlider.value()
            #process_stdin('z %s'%str(int(self.verticalSlider.value()+200)))
            process_stdin('z 350')
            #process_stdin('z %s'%str(self.verticalSlider.value()*(-1)))
        def down(self):
            #process_stdin('z %s'%str(int(self.verticalSlider.value()-200)))
            process_stdin('z -200')
            #process_stdin('z %s'%str(self.verticalSlider.value()))
        def yaw(self):
            process_stdin('yaw')
        def turn_left(self):
            process_stdin('yaw %s' % str(self.verticalSlider.value()))
        def turn_right(self):
            process_stdin('yaw %s' % str(self.verticalSlider.value()*(-1)))
        def land(self):
            process_stdin('land2')
        def download_log(self):
            process_stdin('log download latest %s.bin'%self.lineEdit_2.text())
        def disarm(self):
            process_stdin('land2')
            process_stdin('disarm')
        def arm(self):
            process_stdin('arm throttle')
        def st(self):
            process_stdin('st')
    #myshow=MyWindow()  
    

    # use main program for input. This ensures the terminal cleans
    # up on exit
    while (mpstate.status.exit != True):
        try:
            if opts.daemon:
                time.sleep(0.1)
                
            else:
                input_loop()
        except KeyboardInterrupt:
            if mpstate.settings.requireexit:
                print("Interrupt caught.  Use 'exit' to quit MAVProxy.")

                #Just lost the map and console, get them back:
                for (m,pm) in mpstate.modules:
                    if m.name in ["map", "console"]:
                        if hasattr(m, 'unload'):
                            try:
                                m.unload()
                            except Exception:
                                pass
                        reload(m)
                        m.init(mpstate)

            else:
                mpstate.status.exit = True
                sys.exit(1)
                #sys.exit(burn_app.exec_())
                print "aaaaaaaa"

    if opts.profile:
        yappi.get_func_stats().print_all()
        yappi.get_thread_stats().print_all()


    
    #this loop executes after leaving the above loop and is for cleanup on exit
    for (m,pm) in mpstate.modules:
        if hasattr(m, 'unload'):
            print("Unloading module %s" % m.name)
            m.unload()
    sys.exit(1)
    #sys.exit(burn_app.exec_())
    #burn_app.exec_()

