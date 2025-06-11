WIDTH = 1000
HEIGHT = 770

map_bg_color = (12, 12, 14)
map_sensor_inactive_color = (235, 64, 52)
map_sensor_active_color = (0, 255, 0)  # Green color for the active sensor

MAX_SENSOR_STRENGTH = 40
MIN_SENSOR_STRENGTH = 1e-6

# enable to clear sensors each run
SENSOR_MODE = False
SIMULATION_MODE = True

# constants

EPS = 1e-6
SENSOR_INACTIVE_TIMEOUT = 10 * 90
PAST_VALUE_SMOOTHING_WINDOW = 90