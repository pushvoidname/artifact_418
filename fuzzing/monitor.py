import os
import sys
import time
import subprocess
import psutil
import pywinauto
import win32api
import random
import win32evtlog
import argparse

# Common Configuration
TEST_DIR = os.path.join(os.getcwd(), 'test')

class BaseMonitor:
    """Base class for PDF reader monitoring"""
    
    # Should be overridden in child classes
    APP_PATH = ''
    PROCESS_NAME = ''
    APP_NAME_FOR_CRASH = ''
    DERIVED_PROCESSES = []
    EVENTLOG_FILTER_KEY = ''

    def __init__(self, fileName, timeOut=120):
        """Initialize common parameters"""
        self.status = 'init'
        self.fileName = fileName
        self.timeOut = timeOut
        self.popup = 0
        self.popup_avl = 0  # Special flag for Adobe AVL popups
        self.crash_key = ''
        self.pid = None
        self.app = None

    def log(self, info):
        """Log messages with timestamp"""
        t = time.strftime("%H:%M:%S", time.localtime())
        print(t + ' ' + info)

    def getPidsByName(self, pname):
        """Get process IDs by process name"""
        return [p.info['pid']
                for p in psutil.process_iter(attrs=['pid', 'name'])
                if p.info['name'] == pname]

    def closeProcess(self, pname):
        """Terminate processes by name"""
        try:
            list_ = [psutil.Process(i)
                     for i in self.getPidsByName(pname)]
            for p in list_:
                if p.is_running():
                    p.kill()
        except Exception as e:
            self.log(str(e))

    def clearDerived(self):
        """Clean up related processes (to be implemented in child classes)"""
        raise NotImplementedError

    def checkStart(self):
        """Check if target process started successfully"""
        pid_lst = self.getPidsByName(self.PROCESS_NAME)
        if len(pid_lst) > 0:
            self.pid = pid_lst[0]
            self.app = pywinauto.Application().connect(process=self.pid)
            self.status = 'running'
            self.log(f'checkStart - pid:{self.pid}')
            return True
        return False

    def openPDF(self):
        """Open target PDF file"""
        fpath = os.path.join(TEST_DIR, self.fileName) if len(
            TEST_DIR) > 0 else self.fileName
        cmd = f'{self.APP_PATH} {fpath}'
        self.log(f'Executing: {cmd}')
        subprocess.Popen(cmd, shell=True)
        
        for _ in range(10):
            time.sleep(1)
            if self.checkStart():
                return True
        return False

    def checkHalt(self):
        """Check if process halted normally"""
        if not self.app.is_process_running():
            self.status = 'halt'
            self.log('Check - Halt')
            return True
        return False

    def checkCrash(self):
        """Detect application crash through WerFault"""
        werfault_list = self.getPidsByName('WerFault.exe')
        if not werfault_list:
            return False

        # Verify crash is for our target application
        werfault_app = pywinauto.Application().connect(process=werfault_list[0])
        for win in werfault_app.windows():
            if self.APP_NAME_FOR_CRASH not in win.window_text():
                self.closeProcess('WerFault.exe')
                return False

        self.status = 'crash'
        self.log('Check - Crash')
        self.closeProcess('WerFault.exe')
        if self.app.is_process_running():
            self.app.kill()
        return True

    def checkPop(self):
        """Handle application popups (to be implemented in child classes)"""
        raise NotImplementedError

    def checkStatus(self, enter=0):
        """Main status checking logic"""
        if psutil.cpu_percent(interval=1.0) < 20:
            if not self.checkHalt():
                if not self.checkCrash():
                    if not self.checkPop():
                        if enter:
                            self.status = 'stop'
                            self.log('Check - Stop')
                        else:
                            self.log('Check - Low CPU usage')
                            time.sleep(2)
                            self.checkStatus(1)

    def checkMain(self):
        """Monitor main loop"""
        startTime = time.time()
        ret = False

        for _ in range(self.timeOut // 2):
            time.sleep(1)
            self.checkStatus()
            if self.status != 'running':
                ret = True
                break

        if not ret:
            self.status = 'hang'
            self.log('Check - Hang')

        self.log(f'End - Running time: {int(time.time() - startTime)}s')

    def writeResult(self):
        with open('runlog.txt', 'a') as f:
            f.write('%s %s %s\n' %
                    (self.fileName, self.status, str(self.popup)))
        return self.status

    def savePDF(self):
        """Save crash artifacts"""
        if self.status == 'finish':
            return

        save_dir = os.path.join('save', self.status)
        os.makedirs(save_dir, exist_ok=True)

        src = os.path.join(TEST_DIR, self.fileName)
        dst = os.path.join(save_dir, self.fileName)
        with open(src, 'rb') as f_src, open(dst, 'wb') as f_dst:
            f_dst.write(f_src.read())
        self.log(f'Saved - {self.status} - {self.fileName}')

    def closeReader(self):
        """Terminate target process"""
        if self.app.is_process_running():
            try:
                self.app.kill()
            except Exception as e:
                print(e)
                print("Kill with psutil")
                read_proc = psutil.Process(self.pid)
                read_proc.kill()

    def startUp(self):
        """Main execution flow"""
        try:
            if self.openPDF():
                self.checkMain()
            self.closeReader()    
        except Exception as e:
            self.status = 'error'
            self.log(str(e))
        finally:
            self.clearDerived()
            self.savePDF()


class AdobeMonitor(BaseMonitor):
    """Adobe Acrobat Reader specific implementation"""
    APP_PATH = r'"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe"'
    PROCESS_NAME = 'AcroRd32.exe'
    APP_NAME_FOR_CRASH = 'Adobe'
    DERIVED_PROCESSES = ['AcroRd32.exe', 'AdobeCollabSync.exe', 
                        'AdobeARM.exe', 'RdrCEF.exe']
    EVENTLOG_FILTER_KEY = 'acrord32'

    def clearDerived(self):
        """Clean up Adobe-related processes"""
        for proc in self.DERIVED_PROCESSES + ['WerFault.exe', 'splwow64.exe']:
            self.closeProcess(proc)

    def checkPop(self):
        """Handle Adobe-specific popups"""
        try:
            self.closeProcess("VMwareHostOpen.exe")

            # Focus main window
            for w in self.app.windows():
                if w.class_name() == 'AcrobatSDIWindow':
                    w.set_focus()
                    break

            win = self.app.top_window()
            cname = win.class_name()
            w_text = win.window_text()

            self.log(f"cname: {cname}, text: {w_text}")

            if cname != 'AcrobatSDIWindow':
                if cname == 'AVL_AVPopup':
                    # if w_text == "":
                    #     self.status = 'stop'
                    #     self.log('Check - stop on AVL_AVPopup')
                    #     return False
                    self._handle_avl_popup(win)
                else:
                    self._handle_generic_popup(win)
                return True  # Popup handled

            if win.window_text().startswith('Adobe Acrobat Reader (32-bit)'):
                self.status = 'finish'
                self.log('Check - close')
                try:
                    win.close()
                except Exception as e:
                    pass
                return True  # Popup handled

            return False  # No popup

        except Exception as e:
            self.log(f'Popup handling error: {str(e)}')
            pywinauto.keyboard.send_keys('{ESC}')
            pywinauto.mouse.click(coords=(973, 682))
            return True

    def _handle_avl_popup(self, win):
        """Handle AVL_AVPopup specific logic"""
        win.set_focus()
        all_wins = self.app.windows()
        target_win = all_wins[1] if len(all_wins) > 1 else win
        rect = target_win.rectangle()
        
        # Add random offset if needed
        x = rect.left + rect.width()//2 
        y = rect.top + rect.height()//2
        if self.popup_avl:
            x += random.randint(100, 200)
            y += random.randint(100, 200)

        pywinauto.mouse.click(coords=(x, y))
        self.popup_avl = 1

    def _handle_generic_popup(self, win):
        """Handle generic popups"""
        win.set_focus()
        if win.class_name() == '#32768':  # System menu
            pywinauto.keyboard.send_keys('%{a}')
        else:
            pywinauto.keyboard.send_keys('%{F4}')


class FoxitMonitor(BaseMonitor):
    """Foxit PDF Reader specific implementation"""
    APP_PATH = r'"C:\Program Files (x86)\Foxit Software\Foxit PDF Reader\FoxitPDFReader.exe"'
    PROCESS_NAME = 'FoxitPDFReader.exe'
    APP_NAME_FOR_CRASH = 'Foxit'
    DERIVED_PROCESSES = ['FoxitPDFReader.exe', 'OpenWith.exe']
    EVENTLOG_FILTER_KEY = 'foxit'

    def clearDerived(self):
        """Clean up Foxit-related processes"""
        for proc in self.DERIVED_PROCESSES + ['WerFault.exe', 'splwow64.exe']:
            self.closeProcess(proc)

    def checkPop(self):
        """Handle Foxit-specific popups"""
        try:
            self.closeProcess("VMwareHostOpen.exe")
            win = self.app.top_window()
            cname = win.class_name()
            w_text = win.window_text()

            self.log(f"cname: {cname}, text: {w_text}")
            
            if cname != 'classFoxitReader':
                win.set_focus()
                if cname == '#32768':
                    pywinauto.keyboard.send_keys('%{a}')
                elif cname == '#32770':
                    if w_text != "Foxit PDF Reader" and w_text != "Full Screen":
                        pywinauto.keyboard.send_keys('%{F4}')
                    else:
                        if random.random() <0.5:
                            if random.random() < 0.5:
                                pywinauto.keyboard.send_keys('{ENTER}')
                            else:
                                pywinauto.keyboard.send_keys('{RIGHT}')
                                pywinauto.keyboard.send_keys('{ENTER}')
                        else:
                            pywinauto.keyboard.send_keys('%{F4}')
                else: # cname.startswith('Afx:')
                    pywinauto.keyboard.send_keys('%{F4}')
                return True  # Popup handled

            if w_text == 'Start - Foxit PDF Reader':
                self.status = 'finish'
                self.log('Check - close')
                try:
                    win.close()
                except Exception as e:
                    pass
                return True  # Popup handled

            return False  # No popup

        except Exception as e:
            self.log(f'Popup handling error: {str(e)}')
            pywinauto.keyboard.send_keys('{ESC}')
            pywinauto.mouse.click(coords=(973, 682))
            return True
        

class XchangeMonitor(BaseMonitor):
    """Foxit PDF Reader specific implementation"""
    APP_PATH = r'"C:\Program Files\Tracker Software\PDF Editor\PDFXEdit.exe"'
    PROCESS_NAME = 'PDFXEdit.exe'
    APP_NAME_FOR_CRASH = 'Xchange'
    DERIVED_PROCESSES = ['PDFXEdit.exe', 'OpenWith.exe']
    EVENTLOG_FILTER_KEY = 'pdfxedit'

    def clearDerived(self):
        """Clean up Foxit-related processes"""
        for proc in self.DERIVED_PROCESSES + ['WerFault.exe', 'splwow64.exe']:
            self.closeProcess(proc)

    def checkHalt(self):
        """Override: Treat process halt as crash for Xchange"""
        if not self.app.is_process_running():
            self.status = 'crash'  # Mark as crash instead of halt
            self.log('Check - Process Halt (Saved as Crash)')
            return True
        return False

    def checkPop(self):
        """Handle Foxit-specific popups"""
        try:
            self.closeProcess("VMwareHostOpen.exe")
            win = self.app.top_window()
            cname = win.class_name()
            w_text = win.window_text()

            self.log(f"cname: {cname}, text: {w_text}")
            
            if not cname.startswith("PXE"):
                win.set_focus()
                if random.random() <0.1:
                    if random.random() < 0.8:
                        pywinauto.keyboard.send_keys('{ENTER}')
                    else:
                        pywinauto.keyboard.send_keys('{RIGHT}')
                        pywinauto.keyboard.send_keys('{ENTER}')
                else:
                    pywinauto.keyboard.send_keys('%{F4}')
                # if cname == '#32770' or cname.startswith('UIX:'):
                #     pywinauto.keyboard.send_keys('%{a}')
                # else:
                #     pywinauto.keyboard.send_keys('%{F4}')
                return True  # Popup handled

            if w_text == 'PDF-XChange Editor':
                self.status = 'finish'
                self.log('Check - close')
                try:
                    win.close()
                except Exception as e:
                    pass
                return True  # Popup handled

            return False  # No popup

        except Exception as e:
            self.log(f'Popup handling error: {str(e)}')
            pywinauto.keyboard.send_keys('{ESC}')
            pywinauto.mouse.click(coords=(973, 682))
            return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='JavaScript Fuzzing Monitor')
    parser.add_argument('-t', '--target', required=True,
                      help='Fuzz target: adobe, foxit, xchange')
    parser.add_argument('-i', '--input', required=True,
                      help='Fuzz target file name')
    args = parser.parse_args()
    if args.target == "adobe":
        # Adobe Test
        adobe_test = AdobeMonitor(args.input)
        adobe_test.startUp()
    elif args.target == "foxit":
        # Foxit Test
        foxit_test = FoxitMonitor(args.input)
        foxit_test.startUp()
    elif args.target == "xchange":
        # Xchange Test
        xchange_test = XchangeMonitor(args.input)
        xchange_test.startUp()
    else:
        print(f"Unknown target name {args.target}...")