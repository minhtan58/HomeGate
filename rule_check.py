from pydispatch import dispatcher
import threading
from .dbsync import DbInterface

def dispatch_signal(signal=dispatcher.Any, sender=dispatcher.Anonymous,
                    *arguments, **named):
    '''
    Dispatch signal with exception proof
    '''
    LOGGER.debug('Dispatch %s', signal)
    try:
        dispatcher.send(signal, sender, *arguments, **named)
    except Exception:
        LOGGER.error('Exception dispatching signal %s', signal)
        LOGGER.error(traceback.format_exc())
class Rule_Check(object):
    """docstring forRule_Check."""

    def __init__(self):
        self._dblistener = DbInterface()
        # dispatcher.connect(self.door_reminder_status, DOOR_REMINDER_CHECK)
        self._door_reminder = None

    def start_auto_check_rule(self):
        '''Automation check one minutes'''
        print("Check rule automation" ,self._dblistener.check_rule_timer())
        self._door_reminder = threading.Timer(1, self.start_auto_save)
        self._door_reminder.setDaemon(True)
        self._door_reminder.start()
    def door_reminder_status(self,channel_door):
        pass
    def door_reminder_check(self):
        '''Automation check one minutes'''
        while 1:
              print("Check rule automation" ,self._dblistener.check_door_open())
              self._door_reminder = threading.Timer(10, self.door_reminder_check)
              self._door_reminder.setDaemon(True)
              self._door_reminder.start()


    def stop_door_reminder_check(self):
        if self._door_reminder:
            self._door_reminder.cancel()
if __name__ == '__main__':
    d = Rule_Check()
    d.door_reminder_check()
