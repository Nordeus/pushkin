'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
from threading import Thread
from Queue import Queue as ThreadQueue
from multiprocessing import Process, Queue as ProcessQueue
from Queue import Full



class AbstractPool():
    """Abstraction of worker pool. Holds common code for concrete pools."""

    def __init__(self, name, num_workers, queue_limit):
        self.num_workers = num_workers
        self.name = name
        self.worker_list = [self.create_worker('{name}-{id}'.format(name=self.name, id=str(i))) for i in
                            range(num_workers)]
        self.task_queue = self.create_queue(queue_limit)

    def create_queue(self, queue_limit):
        """Instantiate queue used for communication with this pool."""
        raise Exception("Not implemented!")

    def create_worker(self, id):
        """Creates a worker for this pool."""
        raise Exception("Not implemented!")

    def process(self):
        """Called for each workers once."""
        raise Exception("Not implemented!")

    def limit_exceeded(self, task):
        """Called when queue limit is exceeded."""
        raise Exception("Not implemetned!")

    def start(self):
        """Starts workers."""
        for worker in self.worker_list:
            worker.daemon = True
            worker.start()

    def submit(self, task):
        """
        Used to submit a task to this pool.

        Returns false is queue size is exceeded.
        """
        try:
            self.task_queue.put_nowait(task)
            return True
        except Full:
            self.limit_exceeded(task)
            return False

    def queue_size(self):
        """Current items number in job queue. Estimated value."""
        return self.task_queue.qsize()


class ThreadPool(AbstractPool):
    """A pool of threads."""

    def __init__(self, name, num_workers, queue_limit):
        AbstractPool.__init__(self, name, num_workers, queue_limit)

    def create_queue(self, queue_limit):
        return ThreadQueue(queue_limit)

    def create_worker(self, name):
        return Thread(target=self.process, name=name)


class ProcessPool(AbstractPool):
    """A pool of threads."""

    def __init__(self, name, num_workers, queue_limit):
        AbstractPool.__init__(self, name, num_workers, queue_limit)

    def create_queue(self, queue_limit):
        return ProcessQueue(queue_limit)

    def create_worker(self, name):
        return Process(target=self.process, name=name)
