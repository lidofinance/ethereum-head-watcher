import logging
import os

import yaml

from src import variables
from src.keys_source.base_source import BaseSource, NamedKey

logger = logging.getLogger()


class FileSource(BaseSource):
    def __init__(self):
        self.keys_file_modification_time = 0

    def update_keys(self):
        """
        Returns True if keys file was changed and keys were updated
        """
        mtime = os.path.getmtime(variables.KEYS_FILE_PATH)
        if self.keys_file_modification_time == mtime:
            return None
        user_keys = {}
        with open(variables.KEYS_FILE_PATH, "r") as f:
            content = yaml.safe_load(f)
            for m_index, _module in enumerate(content.values(), 1):
                for o_index, operator_keys in enumerate(_module):
                    for key in operator_keys['keys']:
                        user_keys[key] = NamedKey(
                            key=key,
                            operatorIndex=o_index,
                            operatorName=operator_keys['name'],
                            moduleIndex=m_index,
                        )
        self.keys_file_modification_time = mtime
        return user_keys
