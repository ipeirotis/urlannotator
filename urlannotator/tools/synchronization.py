from tenclouds.lock.rwlock import FileRWLock


class RWSynchronize247(object):

    def __init__(self, template_name):
        self.lock = FileRWLock(template_name + '_general_lock')
        self.rwlock = FileRWLock(template_name + '_rw_lock')

    def reader_lock(self):
        """
        Locks the reader.
        """
        self.rwlock.reader_acquire()

    def reader_release(self):
        """
        Releases reader instance locks.
        """
        self.rwlock.reader_release()

    def modified_lock(self):
        """
        Locks the modified instance.
        """
        self.lock.writer_acquire()

    def modified_release(self, func=None, switch=True, *args, **kwargs):
        """
        Returns modified instance's lock.

        :param switch: perform instances switch writer :=: reader
        """
        if switch:
            self._switch_with_lock(func, *args, **kwargs)
        self.lock.writer_release()

    def switch(self, func=None, *args, **kwargs):
        """
        Cold switch. Aquires all locks and runs switch. In result whole
        template 24/7 instance is blocked for switch time.
        """
        self.lock.writer_acquire()
        self._switch_with_lock(func, *args, **kwargs)
        self.lock.writer_release()

    def _switch_with_lock(self, func=None, *args, **kwargs):
        """
        Hot switch. Use only when you hold the modified lock.
        """
        self.rwlock.writer_acquire()
        if func:
            func(*args, **kwargs)
        self.rwlock.writer_release()
