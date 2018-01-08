print(__file__)
# Define some environment variables (for now)
import os
os.environ['PYEPICS_LIBCA'] = '/APSshare/epics/base-3.15.5/lib/linux-x86_64/libca.so'

# Make ophyd listen to pyepics.
from ophyd import setup_ophyd
setup_ophyd()

# Import matplotlib and put it in interactive mode.
import matplotlib.pyplot as plt
plt.ion()

# Make plots update live while scans run.
from bluesky.utils import install_qt_kicker
install_qt_kicker()

# Optional: set any metadata that rarely changes. in 60-metadata.py

# convenience imports
from ophyd.commands import *
from bluesky.callbacks import *
from bluesky.spec_api import *
from bluesky.global_state import gs, abort, stop, resume
from bluesky.plan_tools import print_summary
from time import sleep
import numpy as np
