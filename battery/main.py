import os
import shutil
import subprocess
import sys
import time
import uuid

from tqdm import tqdm
from collections import deque
from datetime import datetime
from threading import Semaphore, Thread

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

FEW_EPS = 1000
MANY_EPS = 10000
PROPORTIONS = [0.25, 0.5, 0.75]  # [0.0, 0.25, 0.5, 0.75, 1.0]
REPETITIONS = 30  # 5
AVFS = [1]
MAX_SIMULTANEOUS_PROCESSES = 8

NETWORKS_PARAMS = {
    # 'Anaheim': {'k': 16, 'lambda': 0.999, 'mu': 0.999, 'eps': MANY_EPS},
    'Anaheim': {'k': 16, 'lambda': 0.995, 'mu': 0.995, 'eps': FEW_EPS},
    'BBraess_1_2100_10_c1_2100': {'k': 3, 'lambda': 0.98, 'mu': 0.98, 'eps': FEW_EPS},
    'BBraess_3_2100_10_c1_900': {'k': 8, 'lambda': 0.99, 'mu': 0.99, 'eps': FEW_EPS},
    'BBraess_5_2100_10_c1_900': {'k': 4, 'lambda': 0.99, 'mu': 0.99, 'eps': FEW_EPS},
    'BBraess_7_2100_10_c1_900': {'k': 4, 'lambda': 0.99, 'mu': 0.99, 'eps': FEW_EPS},
    'Braess_1_4200_10_c1': {'k': 3, 'lambda': 0.99, 'mu': 0.99, 'eps': FEW_EPS},
    'Braess_2_4200_10_c1': {'k': 5, 'lambda': 0.99, 'mu': 0.99, 'eps': FEW_EPS},
    'Braess_3_4200_10_c1': {'k': 7, 'lambda': 0.99, 'mu': 0.99, 'eps': FEW_EPS},
    'Braess_4_4200_10_c1': {'k': 9, 'lambda': 0.99, 'mu': 0.99, 'eps': FEW_EPS},
    'Braess_5_4200_10_c1': {'k': 11, 'lambda': 0.99, 'mu': 0.99, 'eps': FEW_EPS},
    'Braess_6_4200_10_c1': {'k': 13, 'lambda': 0.99, 'mu': 0.99, 'eps': FEW_EPS},
    'Braess_7_4200_10_c1': {'k': 15, 'lambda': 0.99, 'mu': 0.99, 'eps': FEW_EPS},
    # 'Eastern-Massachusetts': {'k': 16, 'lambda': 0.999, 'mu': 0.999, 'eps': MANY_EPS},
    'Eastern-Massachusetts': {'k': 16, 'lambda': 0.995, 'mu': 0.995, 'eps': FEW_EPS},
    'OW': {'k': 8, 'lambda': 0.99, 'mu': 0.99, 'eps': FEW_EPS},
}

USE_ONLY_NETWORKS = None  # ['Anaheim', 'Eastern-Massachusetts']
EXCLUDE_NETWORKS = ['Anaheim', 'Eastern-Massachusetts']


def get_networks_to_use():
    for network in NETWORKS_PARAMS.keys():
        only_pass = USE_ONLY_NETWORKS is None or network in USE_ONLY_NETWORKS
        exclude = EXCLUDE_NETWORKS is not None and network in EXCLUDE_NETWORKS
        if only_pass and not exclude:
            yield network


FOLDER = r'C:\Users\Tim\Documents\Git\marl-route-choice'
SCRIPT = os.path.join(FOLDER, 'proof_of_concept.py')
LOGS_DIR = os.path.abspath(os.path.join('.', 'output', 'results_' + datetime.now().strftime('%Y-%m-%d_%Hh%Mm%Ss')))
PARAMS = 'aamas20 --alg ala18 --logs-dir {logs_dir} --net {net} --k {k} --episodes {epi} --user-proportion ' \
         '{user_prop} --fixed-participation --obligatory-toll-percentile {obl_percent} --avf {avf} ' \
         '--decay-alpha {decay_alpha} --decay-eps {decay_epsilon}'
NETWORKS = None  # deprecated
LARGE_NETWORKS = ['SF']  # deprecated
EPISODES_LARGE = 10000  # deprecated
DECAY_RATE_LARGE = 0.9999  # deprecated
EPISODES = 1000  # deprecated
DECAY_RATE = 0.995  # deprecated


# PROPORTIONS = [i / 10.0 for i in range(0, 11)]
# PROPORTIONS_TO_PERCENTILES = {prop: ([0.0] if prop != 0.0 else [i / 10.0 for i in range(0, 11)]) for prop in
#                               PROPORTIONS if prop != 1.0}
# PROPORTIONS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
# PROPORTIONS = [0.1, 0.3, 0.5, 0.7, 0.9]


def generate_proportions():
    for x in PROPORTIONS:
        yield x, 0.0
    for y in filter(lambda a: a not in [0.0, 1.0], PROPORTIONS):
        yield 0.0, y
    # for x in PROPORTIONS:
    #     for y in PROPORTIONS:
    #         if (x, y) in [(0, 0), (1, 0)] or (y == 0 < x < 1) or (x == 0 < y < 1):
    #             yield x, y
    # for x in PROPORTIONS:
    #     if x == 0.0:
    #         for y in PROPORTIONS:
    #             if y == 1.0:
    #                 break
    #             yield x, y
    #     else:
    #         yield x, 0.0
    pass


# TODO: revert to generate_proportions() if I want to test u again
PROPORTIONS_AND_PERCENTILES = [(0.0, p) for p in PROPORTIONS]  # list(generate_proportions())

started_tasks_bar = None
completed_tasks_bar = None


def make_params(network, user_prop, obl_percent, logs_dir, avf, k):
    return {
        'net': network,
        'k': k,
        'user_prop': user_prop,
        'obl_percent': obl_percent,
        'logs_dir': logs_dir,
        'epi': EPISODES_LARGE if network in LARGE_NETWORKS else EPISODES,
        'avf': avf,
        'decay': DECAY_RATE_LARGE if network in LARGE_NETWORKS else DECAY_RATE,
    }


def run_experiment(params, process_queue):
    args = '{} {} {}'.format(sys.executable, SCRIPT, PARAMS.format(**params))
    # timestamp = str(uuid.uuid4())  # datetime.now().strftime('%Y-%m-%d_%Hh%Mm%Ss')
    # filepath = '{}\\{}'.format(params['logs_dir'], timestamp)
    # args = ['echo "adabo" > %s_.txt' % filepath, 'echo "inakos" > %s.csv' % filepath]
    # print 'RUN >>', args
    # started_tasks_bar.update(1)
    # started_tasks_bar.set_postfix_str('$ %s' % args)
    del params['logs_dir']
    completed_tasks_bar.set_postfix(params)
    process_queue.append(subprocess.Popen(args, shell=True))
    # process_queue.extend([subprocess.Popen(arg, shell=True) for arg in args])


capacity_sem = Semaphore(value=MAX_SIMULTANEOUS_PROCESSES)
timestamp_sem = Semaphore(value=1)
tqdm_sem = Semaphore(value=0)


def runner(exec_queue, process_queue):
    while len(exec_queue) > 0:
        capacity_sem.acquire()
        timestamp_sem.acquire()
        run_experiment(exec_queue.pop(), process_queue)


def tqdm_run(total):
    for _ in range(total):
        tqdm_sem.acquire()
        yield None


class ResultsHandler(FileSystemEventHandler):
    def __init__(self):
        FileSystemEventHandler.__init__(self)

    def on_created(self, event):
        path = event.src_path
        if path.endswith('.csv'):
            # print 'FINISHED EXECUTION', path
            completed_tasks_bar.update(1)
            # completed_tasks_bar.set_postfix_str('Completed! %s' % path)
            capacity_sem.release()
            # tqdm_sem.release()
        elif path.endswith('_.txt'):
            # print 'TIMESTAMP ACQUIRED', path
            # started_tasks_bar.set_postfix_str('\nTimestamp freed: %s' % path)
            timestamp_sem.release()


def retrieve_all_networks(allow_large=True):
    netdir = os.path.join(FOLDER, 'networks')
    for filename in os.listdir(netdir):
        if filename.endswith('.net'):
            netname = filename.split('.net')[0]
            if os.path.isfile(os.path.join(netdir, netname + '.routes')) and (
                    allow_large or netname not in LARGE_NETWORKS):
                yield netname


def main():
    global started_tasks_bar, completed_tasks_bar
    process_queue = deque()
    exec_queue = deque()

    # for net in retrieve_all_networks(allow_large=False) if NETWORKS is None else NETWORKS:
    for _ in range(REPETITIONS):
        for avf in AVFS:
            for prop, percent in PROPORTIONS_AND_PERCENTILES:
                for net in get_networks_to_use():
                    logs_dir = os.path.join(LOGS_DIR, net)

                    if not os.path.exists(logs_dir):
                        os.makedirs(logs_dir)
                        observer = Observer()
                        observer.schedule(ResultsHandler(), path=logs_dir, recursive=False)
                        observer.start()

                    exec_queue.append({
                        'net': net,
                        'k': NETWORKS_PARAMS[net]['k'],
                        'user_prop': float(prop),
                        'obl_percent': float(percent),
                        'logs_dir': logs_dir,
                        'epi': NETWORKS_PARAMS[net]['eps'],
                        'avf': avf,
                        'decay_alpha': NETWORKS_PARAMS[net]['lambda'],
                        'decay_epsilon': NETWORKS_PARAMS[net]['mu'],
                    })
                    # exec_queue.extend([make_params(net, float(prop), float(percent), logs_dir, float(avf)) for prop, percent in
                    #                    PROPORTIONS_AND_PERCENTILES for avf in AVFS])

    # TODO: remove this later, it's temporary
    # eq = []
    # for params in exec_queue:
    #     if params['obl_percent'] == 0.0 and params['user_prop'] in [0.1, 0.3, 0.7, 0.9]:
    #         eq.append(params)
    # exec_queue = eq

    os.chdir(FOLDER)
    n_runs = len(exec_queue)
    # started_tasks_bar = tqdm(total=n_runs, position=0, desc='Queued')
    completed_tasks_bar = tqdm(total=n_runs, position=0, desc='Progress')
    # main_run = Thread(target=runner, args=(exec_queue, process_queue))
    # main_run.start()

    # for _ in tqdm(tqdm_run(n_runs), total=n_runs):
    #     pass

    # main_run.join()

    runner(exec_queue, process_queue)

    while len(process_queue) > 0:
        process_queue.pop().wait()

    # started_tasks_bar.close()
    completed_tasks_bar.close()


if __name__ == '__main__':
    main()
