""" Module for useful logging functionality. """
from os import path
from pathlib import Path
from types import SimpleNamespace
import logging

class Logger:
    """Implements log handling."""
    def __init__(self, name='python', base_dir=path.dirname(path.abspath(__file__)), verbosity=1):
        """Initialize the logger."""
        Path(f'{base_dir}/log').mkdir(parents=True, exist_ok=True)

        self.lvl = SimpleNamespace(**logging._nameToLevel)
        # Setup logging
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.lvl.DEBUG)

        # Setup logging to log.txt file
        self._fh = logging.handlers.TimedRotatingFileHandler(f'{base_dir}/log/{name}.log',
                                                             when='d', interval=30,
                                                             backupCount=12)
        self._fh.setLevel(self.lvl.DEBUG)

        # Setup logging to stdout based on verbosity
        verbosity = self.lvl.CRITICAL - (verbosity * 10)
        self._ch = logging.StreamHandler()
        self._ch.setLevel(verbosity)

        # Format the output message
        self.formatter = logging.Formatter(fmt='%(asctime)s %(name)s: %(levelname)s: %(message)s',
                                           datefmt='%b %d %H:%M:%S')
        self._fh.setFormatter(self.formatter)
        self._ch.setFormatter(self.formatter)

        # Setup the logging handler
        self.logger.addHandler(self._fh)
        self.logger.addHandler(self._ch)

    def log(self, msg, lvl=20):
        """Log a message based on the level passed.

        Args:
            lvl (int): The message level to log Default=20 (INFO).
            msg (str): The message to log.
        """
        self.logger.log(lvl, f'{msg}')
