import posix_ipc
import memcache
import threading
import weakref

from tenclouds.lock.rwlock import RWLock

memcache_client = memcache.Client(['127.0.0.1:11211'], debug=0)


_posix_sem_prefix = 'urlannotator'


class _POSIXSemProxy(object):
    """
        Proxies access to posix_ipc.Semaphore. Closes underlying semaphore on
        finalization.
    """
    def __init__(self, name):
        self.name = name
        self.semaphore = posix_ipc.Semaphore(
            name='/%s-%s' % (_posix_sem_prefix, name),
            flags=posix_ipc.O_CREAT,
            initial_value=1,
        )
        self.semaphore.unlink()

    def acquire(self):
        self.semaphore.acquire()

    def release(self):
        self.semaphore.release()

    def close(self):
        self.semaphore.close()

    def __del__(self, *args, **kwargs):
        # Swallow all possible exception. We can't really do anything to help
        # current situation if it occurs.
        try:
            self.semaphore.close()
        except:
            pass


class POSIXLockCache(object):
    """
        Manages a POSIXSemProxy cache so that there is always one
        instance for every different lock used inside process's scope.

        Internally contains a weak value reference dictionary which points at
        every currently spawned lock. Locks which are contained inside
        non-cyclic structure are finalized instantly (thus removed from the
        cache automatically).

        This class is thread-safe, but not process-safe because the OS itself
        does provide it in IPC.
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.cache = {}

    def _del_item(self, item):
        """
            Thread-safely remove an item from cache.

            :param item: weak ref to deleted item.

            This method is used as a callback when creating a weak ref to a
            lock. Shouldn't be used explicitly.
        """
        with self.lock:
            # Acquire shared ref
            posix_sem = item()

            # If we are too late and the item is already gone, there is nothing
            # we can do about that. Consequent calls to get the lock will
            # result in creation of a new one, so the cache entry won't take up
            # unused cache space in that case.
            if posix_sem is None:
                return

            self.cache.pop(posix_sem.name, None)

    def _add_lock(self, name):
        """
            Creates and adds a lock to the cache. This is not thread-safe.

            :param name: name of the lock to create and add
        """
        lock = _POSIXSemProxy(name=name)
        ref = weakref.ref(lock, self._del_item)
        self.cache[name] = ref
        return lock

    def get_lock(self, name):
        """
            Thread-safely gets a lock from the cache. In case of cache miss - a
            new lock is created with that name.

            :param name: name of desired lock
            :rtype: a shared reference to lock
        """
        with self.lock:
            ref = self.cache.get(name, None)

            # Cache miss
            if ref is None:
                return self._add_lock(name=name)

            # At this point, if we are holding the object, it won't go away.
            lock = ref()

            # Cache miss - ref is here, object is gone.
            if lock is None:
                return self._add_lock(name=name)

            return lock


_posix_lock_cache = POSIXLockCache()


class POSIXLock(object):
    """
        A lock implemented with posix_ipc.Semaphore. Closes underlying
        semaphore when garbage collected. This object acts as a singleton
        proxy in process's scope for underlying semaphore guaranteeing that
        when finalized, the semaphore will be properly closed.

        Instances of this class can be used with `with` statements.
    """
    def __init__(self, name):
        self.name = name
        global _posix_lock_cache
        self.lock = _posix_lock_cache.get_lock(name=name)

    def acquire(self):
        self.lock.acquire()

    def release(self):
        self.lock.release()

    def __enter__(self):
        self.acquire()

    def __exit__(self, value, *args, **kwargs):
        self.release()


class POSIXLightSwitch(object):
    """
        Simple Readers/Writers counter using POSIX lock and memcache to store
        counter's value.
    """
    cache_timeout = 60 * 60 * 12  # 12 hours

    def __init__(self, name):
        self.name = name
        self.mutex = POSIXLock(name='%s-%s' % (name, 'switchcounter'))

    def acquire(self, lock):
        """
            Increases counter's value by 1, and acquires lock argument if
            previous counter's value was 0.
        """
        self.mutex.acquire()
        counter = memcache_client.get(self.name)
        if counter is None:
            memcache_client.add(self.name, 0, time=self.cache_timeout)
            counter = 0

        memcache_client.set(self.name, counter + 1,
            time=self.cache_timeout)
        if counter == 0:
            self.mutex.release()
            lock.acquire()
        else:
            self.mutex.release()

    def release(self, lock):
        """
            Decreases counter's value by 1, and releases lock argument if
            counter is 0.
        """
        with self.mutex:
            counter = memcache_client.get(self.name)
            if counter is None:
                counter = 1

            memcache_client.set(self.name, counter - 1,
                time=self.cache_timeout)
            if counter == 1:
                lock.release()


class POSIXRWLock(RWLock):
    """ RWLock implemented with posix_ipc.Semaphore and file switch.
    """

    def __init__(self, name, lock_dir='/tmp/10c/locks'):
        self.__read_switch = POSIXLightSwitch('%s-%s' % (name, 'read'))
        self.__write_switch = POSIXLightSwitch('%s-%s' % (name, 'write'))

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
        self.lock = POSIXLock(name=template_name + '_general_lock')
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
        self.lock.acquire()

    def modified_release(self, func=None, switch=True, *args, **kwargs):
        """
        Returns modified instance's lock.

        :param switch: perform instances switch writer :=: reader
        """
        if switch:
            try:
                self._switch_with_lock(func, *args, **kwargs)
            finally:
                self.lock.release()
                return
        self.lock.release()

    def switch(self, func=None, *args, **kwargs):
        """
        Cold switch. Aquires all locks and runs switch. In result whole
        template 24/7 instance is blocked for switch time.
        """
        with self.lock:
            self._switch_with_lock(func, *args, **kwargs)

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
