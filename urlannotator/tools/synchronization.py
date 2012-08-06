import new

from tenclouds.lock import FileLock


class RWSynchronize247(object):

    def __init__(self, template_name, reader_instance=None,
            writer_instance=None, synchronized_class=None, reader_functions=[],
            writer_functions=[], *args, **kwargs):
        """
        Our permanent (24/7) synchronize template can be initialized with custom
        class - synchronized_class or with instances of sync objects.
        """

        self.reader_instance = reader_instance or synchronized_class(*args,
            **kwargs)
        self.writer_instance = writer_instance or synchronized_class(*args,
            **kwargs)

        self.reader_functions = reader_functions
        self.writer_functions = writer_functions

        self.lock = FileLock(template_name + '_general_lock')
        self.rwlock = FileLock(template_name + '_rw_lock')

        # Dynamic add reader methods.
        for func_name in reader_functions:
            func = self._new_readers_function(func_name)
            self._new_method(func, func_name)

        # Dynamic add writer methods.
        for func_name in writer_functions:
            func = self._new_writer_function(func_name)
            self._new_method(func, func_name)

    def _new_readers_function(self, function_name):
        def func(self, *args, **kwargs):
            """
            Reading task. Read instance is used - aquire reader rwlock.
            """

            self.rwlock.acquire_shared_lock()
            res = getattr(self.reader_instance, function_name)(*args, **kwargs)
            self.rwlock.unlock()

            return res

        return func

    def _new_writer_function(self, function_name):
        def func(self, *args, **kwargs):
            """
            Writing task. Lock write instance.
            On default after training switch is performed. This can be disabled
            by passing template_switch=False in kwargs.
            """

            # Switch can be disabled.
            template_switch = True
            if 'template_switch' in kwargs:
                template_switch = kwargs['template_switch']
                kwargs.pop('template_switch')

            self.lock.acquire_exclusive_lock()
            res = getattr(self.writer_instance, function_name)(*args, **kwargs)
            if template_switch:
                self._switch_with_lock()
            self.lock.unlock()

            return res

        return func

    def _new_method(self, function, function_name):
        method = new.instancemethod(function, self, self.__class__)
        self.__dict__[function_name] = method

    def switch(self):
        """
        Cold switch. Aquires all locks and runs switch. In result whole
        template 24/7 instance is blocked for switch time.
        """

        self.lock.acquire_exclusive_lock()
        self._switch_with_lock()
        self.lock.unlock()

    def _switch_with_lock(self):
        """
        Hot switch. Use only when ensured that write instance is not used.
        F.e. when training task ends.
        """

        self.rwlock.acquire_exclusive_lock()
        (self.reader_instance, self.writer_instance) = (self.writer_instance,
            self.reader_instance)
        self.rwlock.unlock()
