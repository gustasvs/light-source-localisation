import json
import pygame as pg
import numpy as np
from scipy.optimize import minimize
from itertools import combinations
import serial
import serial.tools.list_ports

import re


from settings import *

def estimate_source(sensors, sliders):
    # centres and readings -----------------------------------------------
    positions = [(s.x + s.width//2, s.y + s.height//2) for s in sensors]
    readings  = np.array([sl.value for sl in sliders], dtype=float)
    logs      = np.log(readings + EPS)                 # avoid log(0)

    # initial guess -------------------------------------------------------
    x0, y0 = np.mean([p[0] for p in positions]), np.mean([p[1] for p in positions])

    # objective using all unordered pairs --------------------------------
    pairs = list(combinations(range(len(positions)), 2))

    def error(pt):
        x, y = pt
        total = 0.0
        for i, j in pairs:
            di = np.hypot(x - positions[i][0], y - positions[i][1]) + EPS
            dj = np.hypot(x - positions[j][0], y - positions[j][1]) + EPS
            lhs = logs[i] - logs[j]
            rhs = 2.0 * (np.log(dj) - np.log(di))
            total += (lhs - rhs) ** 2
        return total

    res = minimize(error, (x0, y0))
    return tuple(map(int, res.x))

class Map:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.map = pg.Surface((width, height))
        self.map.fill(map_bg_color)
        self.rect = self.map.get_rect()

    def draw(self, screen):
        screen.blit(self.map, (0, 0))

    def update(self):
        pass

class Sensor:
    def __init__(self, x, y, width, height, active=False, sensor_id=None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.rect = pg.Rect(x, y, width, height)
        self.active = active
        self.id = sensor_id

    def draw(self, screen):
        color = map_sensor_active_color if self.active else map_sensor_inactive_color
        pg.draw.circle(screen, color, (self.x + self.width // 2, self.y + self.height // 2), self.width // 2)

        if self.id is not None:
            font = pg.font.Font(None, 28)
            label = font.render(str(self.id), True, (255, 255, 255))
            screen.blit(label, label.get_rect(center=(self.x + self.width // 2, self.y - self.height * 1.5)))


class SensorSlider:
    def __init__(self, sensor):
        self.sensor = sensor
        # self.value = (max_val - min_val) // 2
        self.value = 10
        self.width = 200
        self.height = 10
        self.bar_rect = pg.Rect(sensor.x - (self.width / 2) + 10,
                                 sensor.y + 40, self.width, self.height)

    def draw(self, screen, debug_mode, C):
        pg.draw.rect(screen, (150, 150, 150), self.bar_rect)
        # Calculate slider_x based on value (left to right)
        slider_x = self.bar_rect.x + int((self.value - MIN_SENSOR_STRENGTH) / (MAX_SENSOR_STRENGTH - MIN_SENSOR_STRENGTH) * self.width)
        pg.draw.rect(screen, (255, 100, 100), (slider_x - 4, self.bar_rect.y - 2, 8, self.height + 4))

        if debug_mode:
            center_x = self.sensor.x + self.sensor.width // 2
            center_y = self.sensor.y + self.sensor.height // 2

            # raw inverse-sqrt distance proxy
            inv_sqrt = 1.0 / np.sqrt(self.value + 1e-9)

            # pixel scale ‘C’ computed once per frame and passed in
            radius   = int(C * inv_sqrt)
            pg.draw.circle(screen, (15, 105, 205),
                        (center_x, center_y), radius, 3)


    def handle_event(self, event):
        expadedHitbox = self.bar_rect.inflate(20, 20)
        isColliding = hasattr(event, "pos") and expadedHitbox.collidepoint(event.pos)

        if event.type == pg.MOUSEBUTTONDOWN and isColliding:
            self.update_value(event.pos[0])
        elif event.type == pg.MOUSEMOTION and hasattr(event, "buttons") and event.buttons[0] and isColliding:
            self.update_value(event.pos[0])

    def update_value(self, x_pos):
        rel_x = max(self.bar_rect.x, min(x_pos, self.bar_rect.x + self.width))
        ratio = (rel_x - self.bar_rect.x) / self.width
        self.value = int(MIN_SENSOR_STRENGTH + ratio * (MAX_SENSOR_STRENGTH - MIN_SENSOR_STRENGTH))

class AddSensorButton:
    def __init__(self, x, y, width, height):
        self.rect = pg.Rect(x, y, width, height)
        self.color = (0, 55, 0)

    def draw(self, screen):
        pg.draw.rect(screen, self.color, self.rect)
        font = pg.font.Font(None, 36)
        text = font.render("Add Sensor", True, (255, 255, 255))
        text_rect = text.get_rect(center=self.rect.center)
        screen.blit(text, text_rect)

    def handle_event(self, event, sensors, sliders):
        if event.type == pg.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            new_sensor = Sensor(150, 150, 20, 20)
            sensors.append(new_sensor)
            sliders.append(SensorSlider(new_sensor))

class ToggleDebugModeButton:
    def __init__(self, x, y, width, height):
        self.rect = pg.Rect(x, y, width, height)
        self.active_color = (0, 255, 0)
        self.inactive_color = (0, 55, 0)
        self.cooldown_color = (100, 100, 100)
        self.current_color = self.inactive_color
        self.last_toggle_time = 0
        self.cooldown_ms = 500
        self.debug_enabled = True

    def draw(self, screen):
        now = pg.time.get_ticks()
        elapsed = now - self.last_toggle_time
        progress = min(elapsed / self.cooldown_ms, 1.0)

        if progress < 1.0:
            # Interpolate color between cooldown and target color
            target = self.active_color if self.debug_enabled else self.inactive_color
            r = int(self.cooldown_color[0] + (target[0] - self.cooldown_color[0]) * progress)
            g = int(self.cooldown_color[1] + (target[1] - self.cooldown_color[1]) * progress)
            b = int(self.cooldown_color[2] + (target[2] - self.cooldown_color[2]) * progress)
            self.current_color = (r, g, b)
        else:
            self.current_color = self.active_color if self.debug_enabled else self.inactive_color

        pg.draw.rect(screen, self.current_color, self.rect)
        font = pg.font.Font(None, 36)
        text = font.render("Toggle Debug", True, (255, 255, 255))
        text_rect = text.get_rect(center=self.rect.center)
        screen.blit(text, text_rect)

    def handle_event(self, event):
        current_time = pg.time.get_ticks()
        if (
            event.type == pg.MOUSEBUTTONDOWN
            and self.rect.collidepoint(event.pos)
            and current_time - self.last_toggle_time > self.cooldown_ms
        ):
            self.debug_enabled = not self.debug_enabled
            self.last_toggle_time = current_time
            return self.debug_enabled
        return self.debug_enabled
    
class ToggleDrawModeButton:
    def __init__(self, x, y, width, height):
        self.rect = pg.Rect(x, y, width, height)
        self.active_color = (255, 255, 0)
        self.active_text_color = (0, 0, 0)
        self.inactive_color = (55, 55, 0)
        self.inactive_text_color = (255, 255, 255)
        self.cooldown_color = (100, 100, 100)
        self.current_color = self.inactive_color
        self.last_toggle_time = 0
        self.cooldown_ms = 500
        self.draw_enabled = False

    def draw(self, screen):
        now = pg.time.get_ticks()
        elapsed = now - self.last_toggle_time
        progress = min(elapsed / self.cooldown_ms, 1.0)

        if progress < 1.0:
            # Interpolate color between cooldown and target color
            target = self.active_color if self.draw_enabled else self.inactive_color
            r = int(self.cooldown_color[0] + (target[0] - self.cooldown_color[0]) * progress)
            g = int(self.cooldown_color[1] + (target[1] - self.cooldown_color[1]) * progress)
            b = int(self.cooldown_color[2] + (target[2] - self.cooldown_color[2]) * progress)
            self.current_color = (r, g, b)
        else:
            self.current_color = self.active_color if self.draw_enabled else self.inactive_color

        pg.draw.rect(screen, self.current_color, self.rect)
        font = pg.font.Font(None, 36)
        text = font.render("Pencil mode", True, 
                           self.active_text_color if self.draw_enabled else self.inactive_text_color)
        text_rect = text.get_rect(center=self.rect.center)
        screen.blit(text, text_rect)

    def handle_event(self, event):
        current_time = pg.time.get_ticks()
        if (
            event.type == pg.MOUSEBUTTONDOWN
            and self.rect.collidepoint(event.pos)
            and current_time - self.last_toggle_time > self.cooldown_ms
        ):
            self.draw_enabled = not self.draw_enabled
            self.last_toggle_time = current_time
            return self.draw_enabled
        return self.draw_enabled

class SensorToggleSwitch:
    def __init__(self, sensor, offset_x=40, offset_y=-10):
        self.sensor = sensor
        self.width = 20
        self.height = 40
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.rect = pg.Rect(0, 0, self.width, self.height)
        self.cooldown_ms = 300
        self.last_toggle_time = 0
        self.active_color = (0, 200, 0)
        self.inactive_color = (100, 0, 0)
        self.cooldown_color = (100, 100, 100)
        self.current_color = self.inactive_color

    def update_position(self):
        self.rect.topleft = (
            self.sensor.x + self.offset_x,
            self.sensor.y + self.offset_y
        )

    def draw(self, screen):
        self.update_position()
        now = pg.time.get_ticks()
        elapsed = now - self.last_toggle_time
        progress = min(elapsed / self.cooldown_ms, 1.0)

        target_color = self.active_color if self.sensor.active else self.inactive_color
        r = int(self.cooldown_color[0] + (target_color[0] - self.cooldown_color[0]) * progress)
        g = int(self.cooldown_color[1] + (target_color[1] - self.cooldown_color[1]) * progress)
        b = int(self.cooldown_color[2] + (target_color[2] - self.cooldown_color[2]) * progress)
        self.current_color = (r, g, b)

        temp_surface = pg.Surface((self.width, self.height), pg.SRCALPHA)
        color_with_alpha = (*self.current_color, int(255 * 0.3))
        temp_surface.fill(color_with_alpha)
        screen.blit(temp_surface, self.rect.topleft)
        pg.draw.rect(screen, (255, 255, 255), self.rect, 1)

    def handle_event(self, event):
        now = pg.time.get_ticks()
        if (
            event.type == pg.MOUSEBUTTONDOWN
            and self.rect.collidepoint(event.pos)
            and now - self.last_toggle_time > self.cooldown_ms
        ):
            self.sensor.active = not self.sensor.active
            self.last_toggle_time = now


class LightPoint:
    def __init__(self, x, y, strength):
        self.x = x
        self.y = y
        self.center_width = 10
        self.pulse_start_time = pg.time.get_ticks()
        self.cycle_duration = 3500

    def update(self, new_x, new_y, new_strength):
        self.x = new_x
        self.y = new_y

    def draw(self, screen):
        color = (255, 255, 0)
        pg.draw.circle(screen, color, (self.x, self.y), self.center_width)

        # Pulsing rings
        now = pg.time.get_ticks()
        elapsed = (now - getattr(self, "pulse_start_time", now)) % self.cycle_duration
        num_rings = 4
        max_radius = 50
        for i in range(num_rings):
            # Each ring is offset in time
            t = ((elapsed + i * (self.cycle_duration / num_rings)) % self.cycle_duration) / self.cycle_duration
            radius = int(20 + t * max_radius)
            alpha = int(120 * (1 - t))
            if alpha <= 0:
                continue
            ring_surf = pg.Surface((radius * 2, radius * 2), pg.SRCALPHA)
            pg.draw.circle(ring_surf, (255, 255, 0, alpha), (radius, radius), radius, 4)
            screen.blit(ring_surf, (self.x - radius, self.y - radius))

def main():
    pg.init()
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    pg.display.set_caption("Sensor Map")
    clock = pg.time.Clock()

    # -- PREVIOUS MAP STATE LOADING --
    try:
        if SENSOR_MODE:
            sensors, sliders = [], []
            draw_surf = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
            # small block for strokes on sensor mode
            try:
                with open('state.json') as f:
                    state = json.load(f)
                strokes = state['strokes']
                # redraw saved strokes
                for stroke in strokes:
                    for i in range(1, len(stroke)):
                        pg.draw.line(draw_surf, (200,200,200), stroke[i-1], stroke[i], 2)
            except FileNotFoundError:
                strokes = []
        
        else:
            with open('state.json') as f:
                state = json.load(f)
            sensors = [Sensor(**d) for d in state['sensors']]
            sliders = []
            for s, d in zip(sensors, state['sliders']):
                sl = SensorSlider(s)
                sl.value = d['value']
                sliders.append(sl)
            draw_surf = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
            strokes = state['strokes']
            # redraw saved strokes
            for stroke in strokes:
                for i in range(1, len(stroke)):
                    pg.draw.line(draw_surf, (200,200,200), stroke[i-1], stroke[i], 2)

    except FileNotFoundError:
        # fallback to defaults
        sensors = [Sensor(100,100,20,20,True),
                   Sensor(200,200,20,20,True),
                   Sensor(300,100,20,20,True)]
        sliders = [SensorSlider(s) for s in sensors]
        draw_surf = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        strokes = []
    m = Map(WIDTH, HEIGHT)
    m.map.fill(map_bg_color)

    # -- VARIABLES --

    # responsible for displaying things like erm.. the circles of influence for sensors
    debug_mode = True
    # enables user to draw the scenery / room design on the map
    draw_mode = True 
    draw_mode = False
    current = []
    dragged_sensor = None
    running = True

    # -- PYGAME OBJECTS AND STUFF --

    sliders = [SensorSlider(s) for s in sensors]
    add_sensor_button = AddSensorButton(10, 10, 200, 50)
    toggle_debug_button = ToggleDebugModeButton(WIDTH - 20 - 200, 10, 200, 50)
    toggle_draw_button = ToggleDrawModeButton(WIDTH - 20 - 200, 70, 200, 50)
    sensor_toggles = [SensorToggleSwitch(s) for s in sensors]
    light_point = LightPoint(0, 0, 0)

    # -- RECIEVER -- 

    ports = serial.tools.list_ports.comports()
    print("Ports: ", ports)
    for p in ports:
        print(p.device)


    try:
        # ser = serial.Serial('COM3', 38400, timeout=0)
        # print("Serial port COM3 opened successfully.")
        ser = serial.Serial('/dev/ttyUSB0', 38400, timeout=0)
        print("Serial port /dev/ttyUSB0 opened successfully.")  
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        print("Running basic mode.")
        ser = None

    
    serial_buffer = ""
    while running:
        # -- READ DATA FROM THE MOTES --
        if ser:
            serial_buffer += ser.read(ser.in_waiting or 1).decode('ascii', 'ignore')
            while '<START>' in serial_buffer and '<END>' in serial_buffer:
                start = serial_buffer.find('<START>') + len('<START>')
                end   = serial_buffer.find('<END>', start)
                if end == -1:
                    break

                frame = serial_buffer[start:end]     # e.g. "DEBUG_INFO=SENSOR_DATA, ID=17, Light=645, Seq=3"
                serial_buffer = serial_buffer[end + len('<END>'):]

                pattern = re.search(
                    r'DEBUG_INFO=([^,]+),\s*ID=(\d+),\s*Light=(\d+)(?:,\s*Seq=(\d+))?',
                    frame
                )
                if not pattern:
                    continue

                debug_info = pattern.group(1)               # string: SINK_DATA / SENSOR_DATA
                sender_id  = int(pattern.group(2))
                light      = int(pattern.group(3))
                seq        = pattern.group(4)
                seq        = int(seq) if seq is not None else None

                print(f"Received {debug_info} from mote {sender_id}: "
                    f"Light={light}" + (f", Seq={seq}" if seq is not None else ""))

                # update sliders only for sensor frames
                # if debug_info == "SENSOR_DATA":
                sensor = next((s for s in sensors if s.id == sender_id), None)
                if sensor is None:
                    sensor = Sensor(150, 150, 20, 20, True, sender_id)
                    sensors.append(sensor)
                    sliders.append(SensorSlider(sensor))
                    sensor_toggles.append(SensorToggleSwitch(sensor))

                # update slider value
                for sl in sliders:
                    if sl.sensor.id == sender_id:
                        sl.value = light



        # -- HANDLE VARIOUS EVENTS

        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

            draw_mode = toggle_draw_button.handle_event(event)
            
            if draw_mode:
                if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    current = [event.pos]
                elif event.type == pg.MOUSEMOTION and getattr(event, "buttons", (0,))[0]:
                    current.append(event.pos)
                    if len(current) > 1:
                        pg.draw.line(draw_surf, (200,200,200), current[-2], current[-1], 2)
                elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
                    if current:
                        strokes.append(current)
                        current = []
                
                elif event.type == pg.KEYDOWN and event.key == pg.K_z and (event.mod & pg.KMOD_CTRL):
                    if strokes:
                        strokes.pop()
                        # clear surface and redraw remaining strokes
                        draw_surf.fill((0,0,0,0))
                        for stroke in strokes:
                            for i in range(1, len(stroke)):
                                pg.draw.line(draw_surf, (200,200,200), stroke[i-1], stroke[i], 2)
            
                continue  # Skip the rest of the button / key handling loop if in draw mode

            if event.type == pg.MOUSEBUTTONDOWN:
                for s in sensors:
                    if s.rect.collidepoint(event.pos):
                        dragged_sensor = s
            elif event.type == pg.MOUSEBUTTONUP:
                dragged_sensor = None
            elif event.type == pg.MOUSEMOTION and dragged_sensor:
                dragged_sensor.x, dragged_sensor.y = event.pos
                dragged_sensor.rect.topleft = event.pos
                for slider in sliders:
                    if slider.sensor == dragged_sensor:
                        slider.bar_rect.topleft = (dragged_sensor.x - (slider.width / 2) + 10,
                                                   dragged_sensor.y + 40)

            for slider in sliders:
                slider.handle_event(event)

            
            add_sensor_button.handle_event(event, sensors, sliders)
            debug_mode = toggle_debug_button.handle_event(event)
            if len(sensor_toggles) < len(sensors):
                sensor_toggles.append(SensorToggleSwitch(sensors[-1]))

            for toggle in sensor_toggles:
                toggle.handle_event(event)

        active_sensors = [s for s in sensors if s.active]
        if len(active_sensors) >= 2:
            estimated_pos = estimate_source(active_sensors, sliders)
            # pg.draw.circle(screen, (255, 205, 0), estimated_pos, 8)
            light_point.update(estimated_pos[0], estimated_pos[1], MAX_SENSOR_STRENGTH)

        # -- DRAW --

        m.draw(screen)
        screen.blit(draw_surf, (0,0))
        for s in sensors:
            s.draw(screen)
        raw_radii = [1/np.sqrt(sl.value + 1e-9) for sl in sliders]
        reference_median_raw = np.median(raw_radii) or 1.0

        dists = [np.hypot(s.x + s.width//2 - estimated_pos[0],
                  s.y + s.height//2 - estimated_pos[1]) for s in sensors]

        # 3. Matching pixel scale:  C = mean( d_i * √R_i )
        C = np.mean([d * np.sqrt(sl.value + 1e-9)
                    for d, sl in zip(dists, sliders)])

        # 4. Draw sliders with that single scale
        for sl in sliders:
            sl.draw(screen, debug_mode, C)

        for toggle in sensor_toggles:
            toggle.draw(screen)
        add_sensor_button.draw(screen)
        toggle_debug_button.draw(screen)
        toggle_draw_button.draw(screen)

        light_point.draw(screen)

        pg.display.flip()
        clock.tick(60)


    # -- SAVE STATE --
    data = {
        'sensors': [
            {'x': s.x, 'y': s.y, 'width': s.width,
             'height': s.height, 'active': s.active}
            for s in sensors
        ],
        'sliders': [{'value': sl.value} for sl in sliders],
        'strokes': strokes
    }
    with open('state.json', 'w') as f:
        json.dump(data, f)

    pg.quit()

if __name__ == "__main__":
    main()