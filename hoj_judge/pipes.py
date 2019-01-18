import contextlib
import io
import logging
import os
import queue
import tempfile
import threading


'''
Inspired from https://codereview.stackexchange.com/a/17959/188792.
'''

class LogThread(threading.Thread):
    # default pipe buffer size is 16 pages
    buffer_size = 4096 * 16

    def __init__(self, file, is_stderr=False, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.daemon = False

        self.file = file
        self.fdr = -1
        self.fdw = -1
        self._start_offset = self.file.seek(0, io.SEEK_CUR)
        self._offset = self._start_offset
        self._is_ready = threading.Event()
        self._is_ready2 = threading.Event()
        self._action_queue = queue.Queue(1)
        self._tag_map = {}
        self._active_tag = None
        self._max_size = None
        self.__fake_file = None

        self.start()

    @property
    def fake_file(self):
        # TODO: should throw if fdw is not available
        if self.__fake_file is None:
            f = lambda: None
            f.fileno = lambda: self.fdw
            f._read = self._read
            self.__fake_file = f
        return self.__fake_file

    @fake_file.deleter
    def fake_file(self):
        self.__fake_file = None

    def run(self):
        # main loop; use a tag once at a time
        while True:
            task = self._action_queue.get()
            if task is None:
                break
            self._active_tag, self._max_size = task

            # (1) create a pipe
            self.fdr, self.fdw = os.pipe()
            reader = os.fdopen(self.fdr)

            self._is_ready.set()

            # print(f'mark w/ tag {tag}')

            # (2) blocking read until write end is closed
            # line buffered, meh
            len_read = 0

            while True:
                bufsize = self.__class__.buffer_size
                if self._max_size is None:
                    sz = bufsize
                else:
                    sz = min(bufsize, self._max_size - len_read)
                if sz < 0:
                    # sz < 0, refusing to read
                    break
                buf = reader.read(sz)
                if not buf:  # EOF
                    break
                if sz == 0:  # not EOF yet, which means exceeding the max_size limit
                    break
                szr = len(buf)
                len_read += szr
                rem_read = -1 if self._max_size is None else (self._max_size - len_read)
                # print(f' [{buf}]... get {szr} bytes, remaining = {rem_read}')
                self.file.write(buf)

            reader.close()
            self._action_queue.task_done()
            self._is_ready2.set()

    def mark(self, tag, max_size=None):
        if self._active_tag is not None:
            raise Exception('Pipe is still in use. Call LogThread.mark_end() first before starting another task.')
        self._action_queue.put((tag, max_size))
        # (1) block until the read end of the pipe is ready for writing
        self._is_ready.wait()
        self._is_ready.clear()

    def mark_end(self):
        # make it flush
        os.close(self.fdw)
        self.fdw = -1
        del self.fake_file
        # (2) block until all data is read from the pipe
        self._is_ready2.wait()
        self._is_ready2.clear()

        # clean up; record and update the offs/len
        tag = self._active_tag
        self._active_tag = None
        new_offset = self.file.seek(0, os.SEEK_CUR)
        self._tag_map[tag] = (self._offset, new_offset - self._offset)
        self._offset = new_offset

    def close(self):
        self._action_queue.put(None)

    # workaround for getting the content from the buffer last used;
    # note that reading while the file is in use causes freaking race conditions
    def _read(self, size=None):
        self.file.seek(self._offset, os.SEEK_SET)
        return self.file.read(size)


class LogPipe(object):
    def __init__(self, file_stdout, file_stderr, *, thread_class=LogThread):
        object.__init__(self)
        self.thr_stdout = thread_class(file_stdout, name='LogPipe-stdout')
        self.thr_stderr = thread_class(file_stderr, name='LogPipe-stderr', is_stderr=True)

    def allocatePipes(self, tag, max_stdout=None, max_stderr=None):
        self.thr_stdout.mark(f'{tag}-STDOUT', max_stdout)
        f_stdout = self.thr_stdout.fake_file
        self.thr_stderr.mark(f'{tag}-STDERR', max_stderr)
        f_stderr = self.thr_stderr.fake_file
        return (f_stdout, f_stderr)

    @contextlib.contextmanager
    def pipe(self, *args, **kwargs):
        yield self.allocatePipes(*args, **kwargs)
        self.flush()

    def flush(self):
        self.thr_stdout.mark_end()
        self.thr_stderr.mark_end()

    def readFromPipe(self, tag, size=None, is_stderr=False):
        thr_target = self.thr_stderr if is_stderr else self.thr_stdout
        tag_real = f'{tag}-STDERR' if is_stderr else f'{tag}-STDOUT'
        offs, leng = thr_target._tag_map[tag_real]
        thr_target.file.seek(offs, os.SEEK_SET)
        if size is None:
            size = leng
        return thr_target.file.read(size)

    def close(self):
        self.thr_stdout.close()
        self.thr_stderr.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()
