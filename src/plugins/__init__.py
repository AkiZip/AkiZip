from . import sevenzip, system_job


def register_plugins(commands):
    sevenzip.register(commands)
    system_job.register(commands)
