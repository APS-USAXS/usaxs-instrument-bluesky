print(__file__)

"""
tune the guard slits

Instead of using tunable axes, implement as device-based tuning plans

SPEC code from usaxs_gslit.mac:

#
# file gslit.mac
# J Kirchman 2012-03-28
#
# Guard Slit SPEC macros
#
# Decription: to optimize the location of the guard slits 
#
# User Macros: 
#    gslit_scan: scan and find optimal guard slit positions
# Internal Macros:
#
# Modification History:
# 2012-03-28 JAK -> created
# 2012-06-25 JIL, modified and added some global parameters for easier tuning. 
# 2013-04-11 JIL, added custom USAXS tuning procedure. Parameters are in the USAXS_conf.mac 
# 2013-04-18 JIL, modified to set also values of motors in real mm units not to confuse users. 
# 2015-02-25 JIL, added tune_GslitCenter needed for energy changes
# 2016-07-08 JIL, Jeff's changes to tune rectangular beam. 


# Guard slits tuning procedure for USAXS instrument...

def tune_Gslits '
    tune_GslitsCenter
    tune_GslitsSize
'

def tune_GslitsSize '
     useModeUSAXS
     waitmove; get_angles
     set_SAXS_Slits 
     waitmove
     openTiFilterShutter 
#     insertCCDfilters
     set_Filters_For_Transm
     DCMfeedbackOFF
     autorange_UPDI0I00
     USAXS_tune_guardSlits 
     closeTiFilterShutter
     local HslitVal
     local VslitVal
     HslitVal=epics_get("9idcLAX:GSlit1H:size.VAL")
     VslitVal=epics_get("9idcLAX:GSlit1V:size.VAL")
     epics_put("9idcLAX:SAXS:SAXS_hgslit_ap",HslitVal)
     epics_put("9idcLAX:SAXS:SAXS_vgslit_ap",VslitVal)
     printf ("Set V Slit=%f and  H SLit =%f\n", VslitVal, HslitVal);
     DCMfeedbackON
'


def tune_GslitsCenter '{
  #
  # tune_GslitCenter uses start and finish in a "epics_ascan"
  #
 
  oldtitle = TITLE
  TITLE = sprintf("tuning USAXS Gslit center %s", \'$1\')
  epics_put ("9idcLAX:sampleTitle", TITLE)
  comment "%s" TITLE

  NO_BEAM_THRESHOLD = 1000

  epics_put ("9idcLAX:userName",    USER)
  epics_put ("9idcLAX:userDir",     CWD)
  epics_put ("9idcLAX:USAXS:specFile",    DATAFILE)
  epics_put ("9idcLAX:USAXS:specScan",    SCAN_N+1)
  epics_put ("9idcLAX:USAXS:scanMacro",   "tune_GslitCenter")
  epics_put ("9idcLAX:USAXS:timeStamp",   date())

     useModeUSAXS
     waitmove; get_angles
     set_SAXS_Slits 
     waitmove
     openTiFilterShutter 
     set_Filters_For_Transm
     sleep(0.1)
     epics_put ("9idcLAX:USAXS:state", sprintf("%s", "autoranging the PD"))
     autorange_UPDI0I00                      ; # after this the I0, I00 and UPD are in manual mode...
     get_angles      # spec seems to be loosing track of motor positions when moved from css/python
     epics_put ("9idcLAX:USAXS:state", TITLE)
    
    tune_usaxs_motor gslity -1 1 50 0.2

    tune_usaxs_motor gslitx -2 2 20 0.2     
     
    #epics_dscan "9idcLAX:GSlit1V:center.VAL" "9idcLAX:GSlit1V:center.VAL" -1 1 40 0.3
    #if (pl_MAX > 4 * pl_MIN) {
    #  epics_put ("9idcLAX:GSlit1V:center.VAL", pl_COM)
    # sbMessage = sprintf("setting Gslits center to %g", pl_COM)
    #  comment "%s" sbMessage
    #  tune_ok = 1
    #} else {
    #  sbMessage = sprintf("Could not tune motor %s, no clear peak resolved", motor_mne($1))
    #  comment "%s" sbMessage
    #  tune_ok = 0
    #}
    epics_put (sprintf("9idcUSX:%s:mode",PDstring), "2")
  TITLE = oldtitle
  closeTiFilterShutter
  #ct 0.1
}'


#------------------------------------------------------------------------------
# turn on/off user defined macros inside standard scan macros for gslit tuning
#------------------------------------------------------------------------------
def gslit_tune_on '{
    cdef("user_prescan_head","_user_prescan_head_gst","gst","0x10")
    cdef("user_scan_loop","_user_scan_loop_gst","gst","0x10")
    cdef("user_scan_tail","_user_scan_tail_gst","gst","0x10")
}'

def gslit_tune_off '{
    cdef("user_prescan_head","","gst","delete")
    cdef("user_scan_loop","","gst","delete")
    cdef("user_scan_tail","","gst","delete")
}' 


#------------------------------------------------------------------------------
# Internal macros 
#------------------------------------------------------------------------------
def _user_prescan_head_gst '{
    # Setup storage array for gslit beam intensity and position data
    GSLIT_CURR_PNT = 0
    GSLIT_I = 0  
    GSLIT_X = 0
}'

def _user_scan_loop_gst '{
    # Collect gslit data for analysis later
    GSLIT_I[GSLIT_CURR_PNT] = S[DET]
    waitmove
    get_angles
    GSLIT_X[GSLIT_CURR_PNT++] = A[GSLIT_MOTOR]
}'

def _user_scan_tail_gst '{
    # Examine data points accumulated, find centroid and variance
    # Abort tuning if data is not reliable enough
    gslit_y[500]
    gslit_sum_y = 0
    gslit_sum_xy = 0
    gslit_sum_xxy = 0
  

    GSLIT_width = 0
    if (GSLIT_CURR_PNT < 10) {
         printf ("Not enough data points taken (%d) to tune guard slits\n", GSLIT_CURR_PNT);
         exit;
    } 
      
    # Calculate sums of "y", "xy" and "xxy" which will be needed for x_bar and variance
    for (i=0 ; i < GSLIT_CURR_PNT ; i++) {
        if (i==0) {gslit_y[i] = 0} else {gslit_y[i]=(GSLIT_I[i-1]-GSLIT_I[i])/(GSLIT_X[i-1]-GSLIT_X[i])}
        gslit_sum_y += gslit_y[i]
        gslit_sum_xy += (GSLIT_X[i]*gslit_y[i])
        gslit_sum_xxy += (GSLIT_X[i]*GSLIT_X[i]*gslit_y[i])
    }
    GSLIT_x_bar = gslit_sum_xy/gslit_sum_y
    variance = gslit_sum_xxy/gslit_sum_y - (GSLIT_x_bar * GSLIT_x_bar)
    GSLIT_width = 2 * sqrt(fabs(variance))

    if (GSLIT_DEBUG) {
        printf ("x_bar = %f\nvariance = %f\nwidth = %f\n",GSLIT_x_bar,variance,GSLIT_width)
        #for (i=0 ; i < GSLIT_CURR_PNT ; i++) {
        #    printf("GSLIT_I[%d]=%f  GSLIT_X[%d]=%f\n",i,GSLIT_I[i], i, GSLIT_X[i])
        #}
    }

    # Sanity check the result before moving motor
    x_end = GSLIT_X[GSLIT_CURR_PNT-1]
    x_start = GSLIT_X[0]
#    if ((GSLIT_x_bar > GSLIT_X[GSLIT_CURR_PNT-1]) || (GSLIT_x_bar < GSLIT_X[0])){
    if (((GSLIT_x_bar>x_start)&&(GSLIT_x_bar>x_end)) || \
       ((GSLIT_x_bar<x_start)&&(GSLIT_x_bar<x_end))) {
        printf("x_bar was calculated outside of the motor\'s travel.\n");
        printf("Tuning result is unusable, guard motor %s will not be tuned.\n",motor_mne(GSLIT_MOTOR))
        exit
    }

    # TODO - Need to find intensity threshold before implementing this 

    if (fabs(GSLIT_I[0]-GSLIT_I[GSLIT_CURR_PNT-1]) < 500) {
        printf("Not enough intensity change from first to last point.\n")
        printf("Did the guard slit move far enough to move into/out of the beam?\n")
        printf("Tuning result is unusable, guard motor %s will not be tuned.\n",motor_mne(GSLIT_MOTOR))
        exit
    }
    

    # Check if movement was from blocked to unblocked or vice versa
    if (GSLIT_I[0] < GSLIT_I[GSLIT_CURR_PNT]) {
        GSLIT_width = GSLIT_width
    } else {
        GSLIT_width = -1 * GSLIT_width
    }
    
    #A[GSLIT_MOTOR] = GSLIT_x_bar + GSLIT_width

    #move_em ; waitmove ; get_angles
    #printf("Guard slit motor %s has been tuned to %f.\n", motor_mne(GSLIT_MOTOR),GSLIT_x_bar + GSLIT_width)
}'


#------------------------------------------------------------------------------
# External macros 
#------------------------------------------------------------------------------
def USAXSgslit_init '{
    global array GSLIT_I[500]
    global array GSLIT_X[500]
    global GSLIT_CURR_PNT
    global GSLIT_MOTOR
    global GSLIT_DEBUG
    global GSLIT_x_bar GSLIT_width
    
    GSLIT_DEBUG = 1
}'


def USAXSgslit_tune '
  if ($# != 5) {
    printf("Usage: USAXSgslit_tune %s\n",\
       "motor start finish intervals time")
    exit
  } 
    motor = $1; start = $2; finish = $3
    intervals = int($4); ctime = $5
    GSLIT_MOTOR = $1

    USAXSgslit_init
    gslit_tune_on
   
    ascan $1 start finish intervals ctime

    gslit_tune_off   

    # center is in GSLIT_x_bar
    # motor offset to position is in GSLIT_width
    # new motor position is GSLIT_x_bar + GSLIT_width
    #printf("Guard slit motor %s has been tuned to %f.\n", motor_mne(GSLIT_MOTOR),A[GSLIT_MOTOR])

'


#------------------------------------------------------------------------------
# The macro which actually tunes the system
#------------------------------------------------------------------------------

def USAXS_tune_guardSlits '

    local __startPos
    local __endPos
    local __ScalingFactor
    chk_beam_off
    global ORIG_TOP_POS ORIG_BOT_POS ORIG_INB_POS ORIG_OUT_POS 
    
    global SAXS_GSlitsScaleFct
    global SAXS_GSlitVStepIn, SAXS_GSlitVStepOut
    global SAXS_GSlitHStepIn, SAXS_GSlitHStepOut


    USAXSgslit_init
    
    # set scaling factor to make guards looser
    __ScalingFactor = SAXS_GSlitsScaleFct

    # define proper counters and set the geometry... 
    plotselect upd2
    counters cnt_num(I0) cnt_num(upd2)
   
    # grab current motor positons
    waitmove; getangles
    ORIG_TOP_POS = A[gsltop]
    ORIG_BOT_POS = A[gslbot]
    ORIG_OUT_POS = A[gslout]
    ORIG_INB_POS = A[gslinb]
    print "top", "bottom", "Outboard", "Inboard"
    print ORIG_TOP_POS, ORIG_BOT_POS, ORIG_OUT_POS, ORIG_INB_POS 
    
    # Now move all guard slit motors back a bit
    A[gsltop] = ORIG_TOP_POS + SAXS_GSlitVStepOut
    A[gslbot] = ORIG_BOT_POS - SAXS_GSlitVStepOut
    A[gslout] = ORIG_OUT_POS + SAXS_GSlitHStepOut
    A[gslinb] = ORIG_INB_POS - SAXS_GSlitHStepOut
    move_em; waitmove
    autorange_UPDI0I00

    # if scan is aborted, return motors to original positions    
    rdef _cleanup3 \'
        print "Returning the guard slit motors to original pre-tune positions"
        A[gsltop] = ORIG_TOP_POS
        A[gslbot] = ORIG_BOT_POS
        A[gslout] = ORIG_OUT_POS
        A[gslinb] = ORIG_INB_POS
        move_em; waitmove
        gslit_tune_off 
     \'

    print "And now we can tune all of the guard slits"
 
    print "*** Tuning top guard slits first"
    __startPos = ORIG_TOP_POS + SAXS_GSlitVStepIn
    __endPos = ORIG_TOP_POS - SAXS_GSlitVStepOut
    printf ("Scanning from %f to %f\n", __startPos, __endPos)
    USAXSgslit_tune gsltop __startPos __endPos 60 0.25
    __gsltop_value = __ScalingFactor * fabs(GSLIT_width)   
    __gsltop_tune = GSLIT_x_bar   
    printf("Gslit motor %s will be tuned to %f.\n", motor_mne(GSLIT_MOTOR),__gsltop_tune);
    printf ("GSLIT_width=%f  GSLIT_x_bar=%f\n", GSLIT_width, GSLIT_x_bar);
    #Comment ("GSLIT_width=%f  GSLIT_x_bar=%f\n", GSLIT_width, GSLIT_x_bar);
    # Move back to scan rest of slits
    A[gsltop] = ORIG_TOP_POS + SAXS_GSlitVStepOut
    move_em; waitmove
   

    print "*** Tuning bottom guard slits next"
    __endPos = ORIG_BOT_POS + SAXS_GSlitVStepOut
    __startPos = ORIG_BOT_POS - SAXS_GSlitVStepIn
    printf ("Scanning from %f to %f\n", __startPos, __endPos)
    USAXSgslit_tune gslbot __startPos __endPos 60 0.25
    __gslbot_value = __ScalingFactor * fabs(GSLIT_width)   
    __gslbot_tune = GSLIT_x_bar
    printf("Gslit motor %s will be tuned to %f.\n", motor_mne(GSLIT_MOTOR),__gslbot_tune)
    printf ("GSLIT_width=%f  GSLIT_x_bar=%f\n", GSLIT_width, GSLIT_x_bar);
    #Comment "GSLIT_width=%f  GSLIT_x_bar=%f\n", GSLIT_width, GSLIT_x_bar
    # Move back to scan rest of slits
    A[gslbot] = ORIG_TOP_POS - SAXS_GSlitVStepOut
    move_em; waitmove

 
    print "*** Tuning outboard guard slits first"
    __startPos = ORIG_OUT_POS + SAXS_GSlitHStepIn
    __endPos = ORIG_OUT_POS - SAXS_GSlitHStepOut
    printf ("Scanning from %f to %f\n", __startPos, __endPos)
    USAXSgslit_tune gslout __startPos __endPos 60 0.25
    __gslout_value = __ScalingFactor * fabs(GSLIT_width)   
    __gslout_tune = GSLIT_x_bar   
    printf("Gslit motor %s will be tuned to %f.\n", motor_mne(GSLIT_MOTOR),__gslout_tune);
    printf ("GSLIT_width=%f  GSLIT_x_bar=%f\n", GSLIT_width, GSLIT_x_bar);
    #Comment ("GSLIT_width=%f  GSLIT_x_bar=%f\n", GSLIT_width, GSLIT_x_bar);
    # Move back to scan rest of slits
    A[gslout] = ORIG_OUT_POS + SAXS_GSlitHStepOut
    move_em; waitmove

    print "*** Tuning inboard guard slits next"
    __endPos = ORIG_INB_POS + SAXS_GSlitHStepOut
    __startPos = ORIG_INB_POS - SAXS_GSlitHStepIn
    printf ("Scanning from %f to %f\n", __startPos, __endPos)
    USAXSgslit_tune gslinb __startPos __endPos 60 0.25
    __gslinb_value = __ScalingFactor * fabs(GSLIT_width)   
    __gslinb_tune = GSLIT_x_bar
    printf("Gslit motor %s will be tuned to %f.\n", motor_mne(GSLIT_MOTOR),__gslinb_tune)
    printf ("GSLIT_width=%f  GSLIT_x_bar=%f\n", GSLIT_width, GSLIT_x_bar);
    #Comment ("GSLIT_width=%f  GSLIT_x_bar=%f\n", GSLIT_width, GSLIT_x_bar);
    # Move back to scan rest of slits
    A[gslinb] = ORIG_INB_POS - SAXS_GSlitHStepOut
    move_em; waitmove


    # Tuning is done, now move the motors to the center of the beam found
    A[gsltop] = __gsltop_tune
    A[gslbot] = __gslbot_tune
    A[gslout] = __gslout_tune
    A[gslinb] = __gslinb_tune
    move_em; waitmove
    gslit_tune_off 
    # redefine the motor positions so the centers are 0
    set gsltop 0   
    set gslbot 0   
    set gslout 0   
    set gslinb 0   

    # center of the slits is set to 0, now move the motors to the width found above, use average of the individual blade values.
    A[gsltop] = (__gsltop_value + __gslbot_value) / 2
    A[gslbot] = -1*(__gsltop_value + __gslbot_value) / 2
    A[gslout] = (__gslout_value + __gslinb_value) / 2
    A[gslinb] = -1*(__gslout_value + __gslinb_value) / 2
    move_em; waitmove

    # sync the slits software
    epics_put("9idcLAX:GSlit1H:sync.PROC",1)
    epics_put("9idcLAX:GSlit1V:sync.PROC",1)

    # normal cleanup macro for ^C usage
    rdef _cleanup3 \'\'

'

"""