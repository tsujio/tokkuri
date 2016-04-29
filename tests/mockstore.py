# -*- coding: utf-8 -*-

# Configurable dummy methods
SAVE = DEFAULT_SAVE = lambda id, vars: None
LOAD = DEFAULT_LOAD = lambda id: {'key1': 'string', 'key2': 123}


class MockStore(object):
    """Mock session store class"""

    # Remember method call history until the next initialization
    initargs = ()
    calls = []

    def __init__(self, timeout, config):
        MockStore.initargs = (timeout, config)
        MockStore.calls = []

    def save(self, id, vars):
        MockStore.calls.append(('save', id, vars))
        SAVE(id, vars)

    def load(self, id):
        MockStore.calls.append(('load', id))
        return LOAD(id)
