
"""
Install a NeXus file writer for uascan raw data files
"""

# TODO: needs a newFile function, similar to instrument.framework.callbacks.newSpecFile()

__all__ = [
    "nxwriter",
    ]

# from ..session_logs import logger
from instrument.session_logs import logger
logger.info(__file__)

from .nxwriter_usaxs import NXWriterUascan
from ..framework import RE, callback_db

nxwriter = NXWriterUascan()
callback_db['nxwriter'] = RE.subscribe(nxwriter.receiver)
