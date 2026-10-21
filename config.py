"""
MRI pTx RF phase calibration configuration.
"""
# ==========================================
# 1. Instrument connection
# ==========================================
SCOPE_IP = "192.168.8.2"
VISA_ADDRESS = f"TCPIP0::{SCOPE_IP}::inst0::INSTR"
VISA_BACKEND = "@py"
VISA_TIMEOUT_MS = 30000
# ==========================================
# 2. RF measurement
# ==========================================
RF_FREQUENCY_HZ = 400e6
REFERENCE_CHANNEL = 1
RF_CHANNEL = 2
TOTAL_RF_CHANNELS = 8
# ==========================================
# 3. Acquisition settings
# ==========================================
# Desired sample rate for validation.
# Actual sample rate must be queried from scope.
TARGET_SAMPLE_RATE_HZ = 5e9
# Scope horizontal acquisition record length.
RECORD_LENGTH = 10000
# Number of points transferred per channel.
MAX_TRANSFER_POINTS = 10000
# Horizontal scale in seconds per division.
# For 10,000 points at 5 GS/s, aim for 2 us
# total duration. On a 10-division screen:
HORIZONTAL_SCALE_S = 200e-9
# False: do not change scope horizontal settings.
# True: apply scale and record length via SCPI.
AUTO_CONFIGURE_HORIZONTAL = True
ACQUISITION_TIMEOUT_S = 15.0
MIN_SAMPLES_PER_CYCLE = 10
# ==========================================
# 4. Trigger settings
# ==========================================
TRIGGER_SOURCE_CHANNEL = REFERENCE_CHANNEL
TRIGGER_LEVEL_V = 0.0
TRIGGER_SLOPE = "RISE"
TRIGGER_MODE = "NORMAL"
# ==========================================
# 5. Analysis settings
# ==========================================
MIN_FIT_R_SQUARED = 0.98
FREQUENCY_SEARCH_RANGE_HZ = 1e6
# Hard Pulse plateform arrange
FIT_START_S = 0.2e-6
FIT_END_S = 0.7e-6
# ==========================================
# 6. Data output
# ==========================================
RESULTS_DIR = "results"