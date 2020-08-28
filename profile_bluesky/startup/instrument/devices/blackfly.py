
"""
Point Grey Blackfly area detector

note: this is one of the easiest area detector setups in Ophyd
"""

__all__ = [
    'blackfly_det',
    'blackfly_optical',
    'blackfly_radiography',
    ]

from ..session_logs import logger
logger.info(__file__)

from ophyd import AreaDetector
from ophyd import PointGreyDetectorCam
from ophyd import SingleTrigger, ImagePlugin
from ophyd.areadetector import ADComponent

from .area_detector_common import _validate_AD_FileWriter_path_
from .area_detector_common import area_detector_EPICS_PV_prefix
from .area_detector_common import DATABROKER_ROOT_PATH
from .area_detector_common import EpicsDefinesHDF5FileNames
from .area_detector_common import EpicsDefinesJpegFileNames


ORIGINAL_CAMERA = 'PointGrey BlackFly'                      # 9idFLY1:
OPTICAL_CAMERA = 'PointGrey BlackFly Optical'               # 9idFLY2:
RADIOGRAPHY_CAMERA = 'PointGrey BlackFly Radiography'       # 9idFLY:


# path for image files (as seen by EPICS area detector writer plugin)
# path seen by detector IOC
PATH_BASE = "/share1/USAXS_data/test/blackfly_optical"
WRITE_IMAGE_FILE_PATH = PATH_BASE + "/%Y/%m/%d/"
# path seen by databroker
READ_IMAGE_FILE_PATH = WRITE_IMAGE_FILE_PATH

_validate_AD_FileWriter_path_(WRITE_IMAGE_FILE_PATH, DATABROKER_ROOT_PATH)
_validate_AD_FileWriter_path_(READ_IMAGE_FILE_PATH, DATABROKER_ROOT_PATH)


class MyPointGreyDetector(SingleTrigger, AreaDetector):
    """PointGrey Black Fly detector(s) as used by 9-ID-C USAXS"""

    cam = ADComponent(PointGreyDetectorCam, "cam1:")
    image = ADComponent(ImagePlugin, "image1:")


class MyPointGreyDetectorHDF5(MyPointGreyDetector):
    """Variation to write image as HDF5"""

    hdf1 = ADComponent(
        EpicsDefinesHDF5FileNames,
        suffix = "HDF1:",
        root = DATABROKER_ROOT_PATH,
        write_path_template = WRITE_IMAGE_FILE_PATH,
        read_path_template = READ_IMAGE_FILE_PATH,
        )


class MyPointGreyDetectorJPEG(MyPointGreyDetector):
    """Variation to write image as JPEG"""

    jpeg1 = ADComponent(
        EpicsDefinesJpegFileNames,
        suffix = "JPEG1:",
        root = DATABROKER_ROOT_PATH,
        write_path_template = WRITE_IMAGE_FILE_PATH,
        read_path_template = READ_IMAGE_FILE_PATH,
        )


try:
    nm = ORIGINAL_CAMERA
    prefix = area_detector_EPICS_PV_prefix[nm]
    blackfly_det = MyPointGreyDetector(
        prefix, name="blackfly_det",
        labels=["camera", "area_detector"])
except TimeoutError as exc_obj:
    msg = f"Timeout connecting with {nm} ({prefix})"
    logger.warning(msg)
    blackfly_det = None


try:
    nm = OPTICAL_CAMERA
    prefix = area_detector_EPICS_PV_prefix[nm]
    blackfly_optical = MyPointGreyDetectorJPEG(
        prefix, name="blackfly_optical",
        labels=["camera", "area_detector"])
    blackfly_optical.read_attrs.append("jpeg1")
except TimeoutError as exc_obj:
    msg = f"Timeout connecting with {nm} ({prefix})"
    logger.warning(msg)
    blackfly_optical = None


try:
    nm = RADIOGRAPHY_CAMERA
    prefix = area_detector_EPICS_PV_prefix[nm]
    blackfly_radiography = MyPointGreyDetectorHDF5(
        prefix, name="blackfly_radiography",
        labels=["camera", "area_detector"])
    blackfly_radiography.read_attrs.append("hdf1")
except TimeoutError as exc_obj:
    msg = f"Timeout connecting with {nm} ({prefix})"
    logger.warning(msg)
    blackfly_radiography = None
