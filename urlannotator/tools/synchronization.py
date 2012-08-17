import posix_ipc

from tenclouds.lock.rwlock import RWLock, _FileLightSwitch


class POSIXLock(object):
    """
        A lock implemented with posix_ipc.Semaphore. DOESN'T CLOSE underlying
        semaphore on close/destroy. You MUST do it manually.
    """
    def __init__(self, name):
        self.semaphore = posix_ipc.Semaphore(
            name='/%s' % name,
            flags=posix_ipc.O_CREAT,
            initial_value=1,
        )

    def acquire(self):
        self.semaphore.acquire()

    def release(self):
        self.semaphore.release()

    def close(self):
        self.semaphore.unlink()

    def __enter__(self):
        self.acquire()

    def __exit__(self, value, *args, **kwargs):
        self.release()


class ContextPOSIXLock(object):
    """
        Provides a context manager wrapper for POSIXLock. CLOSES
        underlying semaphore on exit. Use it only if you are sure no other
        thread is using this semaphore. (Process-safe)
    """
    def __init__(self, name):
        self.lock = POSIXLock(name=name)

    def __enter__(self):
        self.lock.acquire()

    def __exit__(self, *args, **kwargs):
        self.lock.release()
        self.lock.close()


class POSIXRWLock(RWLock):
    """ RWLock implemented with posix_ipc.Semaphore and file switch.
    """

    def __init__(self, name, lock_dir='/tmp/10c/locks'):
        self.__read_switch = _FileLightSwitch(name, lock_dir, 'read')
        self.__write_switch = _FileLightSwitch(name, lock_dir, 'write')

        self.__no_readers = POSIXLock(
            name='%s-%s' % (name, 'no_readers'),
        )
        self.__no_writers = POSIXLock(name='%s-%s' % (name, 'no_writers'))
        self.__readers_queue = POSIXLock(
            name='%s-%s' % (name, 'readers_queue'),
        )

    def reader_acquire(self):
        with self.__readers_queue:
            with self.__no_readers:
                self.__read_switch.acquire(self.__no_writers)

    def reader_release(self):
        self.__read_switch.release(self.__no_writers)

    def writer_acquire(self):
        self.__write_switch.acquire(self.__no_readers)
        self.__no_writers.acquire()

    def writer_release(self):
        self.__no_writers.release()
        self.__write_switch.release(self.__no_readers)


class RWSynchronize247(object):

    def __init__(self, template_name):
        self.lock = POSIXRWLock(name=template_name + '_general_lock')
        self.rwlock = POSIXRWLock(name=template_name + '_rw_lock')

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
            try:
                self._switch_with_lock(func, *args, **kwargs)
            finally:
                self.lock.writer_release()
                return
        self.lock.writer_release()

    def switch(self, func=None, *args, **kwargs):
        """
        Cold switch. Aquires all locks and runs switch. In result whole
        template 24/7 instance is blocked for switch time.
        """
        self.lock.writer_acquire()
        try:

            self._switch_with_lock(func, *args, **kwargs)

        finally:
            self.lock.writer_release()

    def _switch_with_lock(self, func=None, *args, **kwargs):
        """
        Hot switch. Use only when you hold the modified lock.
        """
        self.rwlock.writer_acquire()

        try:

            if func:
                func(*args, **kwargs)

        finally:
            self.rwlock.writer_release()
