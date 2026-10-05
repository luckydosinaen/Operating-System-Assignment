"""Sampel resource seluruh process tree, dengan metode sama untuk setiap kondisi."""

from threading import Event, Lock, Thread
from time import perf_counter

import psutil


class ResourceMonitor:
    def __init__(self, interval=0.05):
        self.parent = psutil.Process()
        self.interval = interval
        self.stop_event = Event()
        self.lock = Lock()
        self.samples = []
        self.child_cpu = {}
        self.origin = perf_counter()
        self.thread = Thread(target=self._poll, name="resource-sampler", daemon=True)

    def sample(self):
        # Lock mencegah snapshot manual dan snapshot monitor bertabrakan.
        with self.lock:
            parent_rss = self.parent.memory_info().rss / 1024**2
            tree_rss = parent_rss
            child_count = 0
            for child in self.parent.children(recursive=True):
                try:
                    key = (child.pid, child.create_time())
                    times = child.cpu_times()
                    self.child_cpu[key] = max(self.child_cpu.get(key, 0), times.user + times.system)
                    tree_rss += child.memory_info().rss / 1024**2
                    child_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            self.samples.append({"elapsed_s": max(0, perf_counter() - self.origin),
                                 "parent_rss_mib": parent_rss, "tree_rss_sum_mib": tree_rss,
                                 "child_processes": child_count})

    def _poll(self):
        while not self.stop_event.wait(self.interval):
            self.sample()

    def start(self):
        self.sample()
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join()

