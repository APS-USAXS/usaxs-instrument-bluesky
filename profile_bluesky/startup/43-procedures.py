print(__file__)

"""
USAXS mode change procedures

see: https://subversion.xray.aps.anl.gov/spec/beamlines/USAXS/trunk/macros/local/usaxs_commands.mac
"""


logger = logging.getLogger(os.path.split(__file__)[-1])


def DCMfeedbackON():
    """plan: could send email"""
    yield from bps.mv(monochromator.feedback.on, MONO_FEEDBACK_ON)
    monochromator.feedback.check_position()


def insertScanFilters():
    """plan: insert the EPICS-specified filters"""
    yield from bps.mv(
        pf4_AlTi.fPosA, terms.USAXS.scan_filters.Al.value,    # Bank A: Al
        pf4_AlTi.fPosB, terms.USAXS.scan_filters.Ti.value,    # Bank B: Ti
    )


def insertRadiographyFilters():
    """plan: insert the EPICS-specified filters"""
    yield from bps.mv(
        pf4_AlTi.fPosA, terms.USAXS.img_filters.Al.value,    # Bank A: Al
        pf4_AlTi.fPosB, terms.USAXS.img_filters.Ti.value,    # Bank B: Ti
    )


def confirm_instrument_mode(mode_name):
    """
    True if instrument is in the named mode

    Parameter

    mode_name (str) :
        One of the strings defined in ``UsaxsSaxsModes``
    """
    expected_mode = UsaxsSaxsModes[mode_name]
    return terms.SAXS.UsaxsSaxsMode.value == expected_mode


def mode_USAXS():
    # plc_protect.stop_if_tripped()
    yield from user_data.set_state_plan("Moving USAXS to USAXS mode")
    yield from bps.mv(
        ccd_shutter,        "close",
        ti_filter_shutter,  "close",
    )
    yield from DCMfeedbackON()
    retune_needed = False

    if not confirm_instrument_mode("USAXS in beam"):
        mode_now = terms.SAXS.UsaxsSaxsMode.get(as_string=True)
        logger.info("Found UsaxsSaxsMode = {}".format(mode_now))
        logger.info("Moving to proper USAXS mode")
        yield from move_WAXSOut()
        yield from move_SAXSOut()
        yield from move_USAXSIn()
        retune_needed = True

    logger.info("Preparing for USAXS mode ... please wait ...")
    yield from bps.mv(
        # set scalar to autocount mode for USAXS
        scaler0.count_mode, SCALER_AUTOCOUNT_MODE,

        # put detector stage in position
        # TODO: redundant with move_USAXSIn() above?
        d_stage.x, terms.USAXS.diode.dx.value,
        d_stage.y, terms.USAXS.diode.dy.value,
    )
    # yield from bps.sleep(0.1)   # TODO: still needed?

    if not ccd_shutter.is_closed:
        logger.info("!!!CCD shutter failed to close!!!")
        # TODO: logging?
    else:
        # mono_shutter.open()

        # print("Change TV input selector to show image in hutch")
        # print("Turn off BLUE switch on CCD controller")
        yield from insertScanFilters()
        yield from bps.mv(ccd_shutter, "close")

        logger.info("Prepared for USAXS mode")
        yield from user_data.set_state_plan("USAXS Mode")
        ts = str(datetime.datetime.now())
        yield from bps.mv(
            user_data.time_stamp, ts,
            user_data.macro_file_time, ts,
            user_data.scanning, 0,
        )

    if retune_needed:
        # don't tune here
        # Instead, set a signal to be caught by the plan in the RunEngine
        yield from bps.mv(terms.USAXS.retune_needed, True)


def mode_SBUSAXS():
    pass

mode_SBUSAXS = mode_USAXS       # really the same thing, at least for now

def mode_SAXS():
    # plc_protect.stop_if_tripped()
    yield from user_data.set_state_plan("Moving USAXS to SAXS mode")
    yield from bps.mv(
        ccd_shutter,        "close",
        ti_filter_shutter,  "close",
    )

    if not confirm_instrument_mode("SAXS in beam"):
        mode_now = terms.SAXS.UsaxsSaxsMode.get(as_string=True)
        logger.info("Found UsaxsSaxsMode = {}".format(mode_now))
        logger.info("Moving to proper SAXS mode")
        yield from move_WAXSOut()
        yield from move_USAXSOut()
        yield from move_SAXSIn()

    logger.info("Prepared for SAXS mode")
    #insertScanFilters
    yield from user_data.set_state_plan("SAXS Mode")
    ts = str(datetime.datetime.now())
    yield from bps.mv(
        user_data.time_stamp, ts,
        user_data.macro_file_time, ts,
        user_data.scanning, 0,
    )


def mode_WAXS():
    # plc_protect.stop_if_tripped()
    yield from user_data.set_state_plan("Moving USAXS to WAXS mode")
    yield from bps.mv(
        ccd_shutter,        "close",
        ti_filter_shutter,  "close",
    )

    if confirm_instrument_mode("WAXS in beam"):
        logger.debug("WAXS is in beam")
    else:
        mode_now = terms.SAXS.UsaxsSaxsMode.get(as_string=True)
        logger.info("Found UsaxsSaxsMode = {}".format(mode_now))
        logger.info("Moving to proper WAXS mode")
        yield from move_SAXSOut()
        yield from move_USAXSOut()
        yield from move_WAXSIn()

    # move SAXS slits in, used for WAXS mode also
    v_diff = abs(guard_slit.v_size.value - terms.SAXS.guard_v_size.value)
    h_diff = abs(guard_slit.h_size.value - terms.SAXS.guard_h_size.value)
    logger.debug("guard slits horizontal difference = %g" % h_diff)
    logger.debug("guard slits vertical difference = %g" % v_diff)

    if max(v_diff, h_diff) > 0.03:
        logger.info("changing Guard slits")
        yield from bps.mv(
            guard_slit.h_size, terms.SAXS.guard_h_size.value,
            guard_slit.v_size, terms.SAXS.guard_v_size.value,
        )
        # TODO: need completion indication
        #  guard_slit is calculated by a database
        #  support needs a handler that does this wait for us.
        yield from bps.sleep(0.5)           # TODO: needed now?

    v_diff = abs(usaxs_slit.v_size.position - terms.SAXS.v_size.value)
    h_diff = abs(usaxs_slit.h_size.position - terms.SAXS.h_size.value)
    logger.debug("USAXS slits horizontal difference = %g" % h_diff)
    logger.debug("USAXS slits vertical difference = %g" % v_diff)

    if max(v_diff, h_diff) > 0.02:
       logger.info("Moving Beam defining slits")
       yield from bps.mv(
           usaxs_slit.h_size, terms.SAXS.h_size.value,
           usaxs_slit.v_size, terms.SAXS.v_size.value,
       )
       yield from bps.sleep(2)     # wait for backlash, seems these motors are slow and spec gets ahead of them?

    logger.info("Prepared for WAXS mode")
    #insertScanFilters
    yield from user_data.set_state_plan("WAXS Mode")
    ts = str(datetime.datetime.now())
    yield from bps.mv(
        user_data.time_stamp, ts,
        user_data.macro_file_time, ts,
        user_data.scanning, 0,
    )


    """
  comment "Ready for Radiography mode"
  print "TV should now show Radiography CCD image. If not, check: TV on? Right TV input? Camera on (Blue button)?"
  print "Beam on? Shutters opened? Sample/holder out of beam? - if all is OK, try running preUSAXStune."
  print "preUSAXStune worked? Run useModeRadiography. Still not working? Call Jan, Ivan or Matt."
  print "But before calling - are you REALLY sure the sample is not blocking the beam? Move it out and try preUSAXStune again."
  epics_put ("9idcLAX:USAXS:timeStamp",   date())
  epics_put ("9idcLAX:USAXS:state",       "Radiography Mode")
  epics_put ("9idcLAX:USAXS:macroFileTime",      date())
  epics_put ("9idcLAX:USAXS:scanning",    0)
}'
    """


def mode_Radiography():
    """
    put in USAXS Radiography mode

    USAGE:  ``RE(mode_Radiography())``
    """
    
    yield from mode_USAXS()
    
    yield from bps.mv(
        monochromator.feedback.on, MONO_FEEDBACK_ON,
        mono_shutter, "open",
        ccd_shutter, "close",
    )
  
    yield from bps.mv(
        # move to ccd position 
        d_stage.x, terms.USAXS.ccd.dx.value,
        d_stage.y, terms.USAXS.ccd.dy.value,
        # make sure slits are in place
        usaxs_slit.v_size,  terms.SAXS.usaxs_v_size.value,
        usaxs_slit.h_size,  terms.SAXS.usaxs_h_size.value,
        guard_slit.v_size,  terms.SAXS.usaxs_guard_v_size.value,
        guard_slit.h_size,  terms.SAXS.usaxs_guard_h_size.value,
    )
    
    yield from insertRadiographyFilters()
    
    # when all that is complete, then ...
    ts = str(datetime.datetime.now())
    yield from bps.mv(
        ti_filter_shutter, "open",
        ccd_shutter, "open",
        user_data.time_stamp, ts,
        user_data.macro_file_time, ts,
        user_data.scanning, 0,
        )

    yield from user_data.set_state_plan("Radiography Mode")
    msg = """
    TV should now show Radiography CCD image. 
    
    But before calling - are you REALLY sure the sample is not blocking the beam? 
       Move sample out and try RE(tune_usaxs_optics()) again.

    If still no image on the CCD, check: 
    
    * TV on? Right TV input? 
    * Camera on (Blue button)?
    * Beam on? 
    * Shutters opened? 
    * Sample/holder out of beam? 
    
    - if all is OK, try running RE(tune_usaxs_optics()).
    tune_usaxs_optics worked? Run RE(mode_Radiography()). 
    
    Still not working? Call Jan, Ivan or Matt.
    """
    print(msg)


def mode_imaging():
    pass
    """
# /share1/USAXS_data/2019-02/USAXS_user_macros.mac
def useModeImaging 'useModeUSAXS'
    """
mode_imaging = mode_USAXS


def mode_OpenBeamPath():
    # plc_protect.stop_if_tripped()
    yield from user_data.set_state_plan("Moving USAXS to OpenBeamPath mode")
    yield from bps.mv(
        ccd_shutter,        "close",
        ti_filter_shutter,  "close",
    )

    if not confirm_instrument_mode("out of beam"):
        mode_now = terms.SAXS.UsaxsSaxsMode.get(as_string=True)
        logger.info("Found UsaxsSaxsMode = {}".format(mode_now))
        logger.info("Opening the beam path, moving all components out")
        yield from move_SAXSOut()
        yield from move_WAXSOut()
        yield from move_USAXSOut()
        yield from user_data.set_state_plan("USAXS moved to OpenBeamPath mode")


def measure_USAXS_Transmission():
    """
    measure the sample transmission in USAXS mode
    """
    # yield from user_data.set_state_plan("Measuring USAXS transmission")
    yield from user_data.set_state_plan("TODO: measure USAXS transmission")
    yield from bps.null()  # this is a no-op
    # TODO:
    
    """
# /home/beams/USAXS/spec/macros/local/usaxs_uascan.mac
def measure_USAXS_PinT '
  #global USAXS_MEASURE_PIN_TRANS
  local LocTRPinCts, LocTRI0Cts 
  StopIfPLCEmergencyProtectionOn
  epics_put ("9idcLAX:USAXS:state",       "Measuring USAXS transmission")
  if(USAXS_MEASURE_PIN_TRANS){
     useModeUSAXS
     waitmove; get_angles
     mv ay (USAXSPinT_AyPosition)
     waitmove; get_angles
     openTiFilterShutter 
     set_Filters_For_Transm
     autorange_I0I00amps
     ct USAXSPinT_MeasurementTime
     #check if we did not top the amplifiers, if yes, redo again...
     LocTRPinCts =  S[trd]
     LocTRI0Cts  = S[I0]
     if(((LocTRPinCts/USAXSPinT_MeasurementTime)>980000) || ((LocTRI0Cts/USAXSPinT_MeasurementTime)>980000)){
        autorange_I0I00amps
        ct USAXSPinT_MeasurementTime
     }
     closeTiFilterShutter
     mv_Al_filter 0
     mv ay AY0
     set_USAXSPinT_pinCounts   S[trd]    ##epics_get("9idcLAX:vsc:c0.S5")        
     set_USAXSPinT_pinGain    TRDRange   ##epics_get("9idcUSX:fem05:seq01:gain")
     set_USAXSPinT_I0Counts   S[I0]      ##epics_get("9idcLAX:vsc:c0.S2")   
     set_USAXSPinT_I0Gain     I0Range    ##epics_get("9idcUSX:fem02:seq01:gain")           
     printf ("Measured USAXS transmission values pinDiode cts =%f with gain %g and  I0 cts =%f with gain %g\n", USAXSPinT_pinCounts, USAXSPinT_pinGain, USAXSPinT_I0Counts,USAXSPinT_I0Gain);
     waitmove; get_angles
   }else{
     set_USAXSPinT_pinCounts  0        
     set_USAXSPinT_pinGain    0
     set_USAXSPinT_I0Counts   0   
     set_USAXSPinT_I0Gain     0                
     printf ("Did not measure USAXS transmission \n");
   }
'
    """
    
