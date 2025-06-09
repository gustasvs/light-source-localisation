import json
import pygame as pg
import numpy as np
from scipy.optimize import minimize

from settings import *

def estimate_source(sensors, sliders):
    # TODO instead of weighting based of the light intensity we can use the RSI value ( we cannot lol)
    positions = []
    distances = []

    for sensor, slider in zip(sensors, sliders):
        x = sensor.x + sensor.width // 2
        y = sensor.y + sensor.height // 2
        positions.append((x, y))
        # greater the value of the slider means it recieves brighter signal
        distances.append(MAX_SENSOR_STRENGTH + 10 - slider.value)

    x0 = np.mean([p[0] for p in positions])
    y0 = np.mean([p[1] for p in positions])

    def error_func(point):
        
        total_error = 0
        for pos, distance in zip(positions, distances):
            measured = np.linalg.norm(np.array(point) - np.array(pos))
            residual = measured - distance

            normalized_distance = distance / MAX_SENSOR_STRENGTH
            weight = np.log(1 + (1 - normalized_distance))

            total_error += (residual ** 2) * weight

        return total_error

    result = minimize(error_func, [x0, y0])
    return tuple(map(int, result.x))

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
    def __init__(self, x, y, width, height, active=False):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.rect = pg.Rect(x, y, width, height)
        self.active = active

    def draw(self, screen):
        color = map_sensor_active_color if self.active else map_sensor_inactive_color
        pg.draw.circle(screen, color, (self.x + self.width // 2, self.y + self.height // 2), self.width // 2)

class SensorSlider:
    def __init__(self, sensor):
        self.sensor = sensor
        # self.value = (max_val - min_val) // 2
        self.value = 10
        self.width = 200
        self.height = 10
        self.bar_rect = pg.Rect(sensor.x - (self.width / 2) + 10,
                                 sensor.y + 40, self.width, self.height)

    def draw(self, screen, debug_mode):
        pg.draw.rect(screen, (150, 150, 150), self.bar_rect)
        # Calculate slider_x based on value (left to right)
        slider_x = self.bar_rect.x + int((self.value - MIN_SENSOR_STRENGTH) / (MAX_SENSOR_STRENGTH - MIN_SENSOR_STRENGTH) * self.width)
        pg.draw.rect(screen, (255, 100, 100), (slider_x - 4, self.bar_rect.y - 2, 8, self.height + 4))

        if debug_mode:
            center_x = self.sensor.x + self.sensor.width // 2
            center_y = self.sensor.y + self.sensor.height // 2
            radius = MAX_SENSOR_STRENGTH + 10 - self.value

            pg.draw.circle(screen, (100, 100, 255), (center_x, center_y), radius, 1)


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
        self.debug_enabled = False

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


def main():
    pg.init()
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    pg.display.set_caption("Sensor Map")
    clock = pg.time.Clock()

    try:
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

        m = Map(WIDTH, HEIGHT)
        m.map.fill(map_bg_color)
    except FileNotFoundError:
        # fallback to defaults
        m = Map(WIDTH, HEIGHT)
        m.map.fill(map_bg_color)
        sensors = [Sensor(100,100,20,20,True),
                   Sensor(200,200,20,20,True),
                   Sensor(300,100,20,20,True)]
        sliders = [SensorSlider(s) for s in sensors]
        draw_surf = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        strokes = []

    # responsible for displaying things like erm.. the circles of influence for sensors
    debug_mode = True

    # enables user to draw the scenery / room design on the map
    draw_mode = True 

    sliders = [SensorSlider(s) for s in sensors]

    add_sensor_button = AddSensorButton(10, 10, 200, 50)
    toggle_debug_button = ToggleDebugModeButton(WIDTH - 20 - 200, 10, 200, 50)
    toggle_draw_button = ToggleDrawModeButton(WIDTH - 20 - 200, 70, 200, 50)

    sensor_toggles = [SensorToggleSwitch(s) for s in sensors]


    draw_mode = False
    current = []
    dragged_sensor = None
    running = True
    while running:
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

        m.draw(screen)
        screen.blit(draw_surf, (0,0))   # show pencil drawing
        for s in sensors:
            s.draw(screen)
        for slider in sliders:
            slider.draw(screen, debug_mode)
        for toggle in sensor_toggles:
            toggle.draw(screen)
        add_sensor_button.draw(screen)
        toggle_debug_button.draw(screen)
        toggle_draw_button.draw(screen)

        active_sensors = [s for s in sensors if s.active]
        if len(active_sensors) >= 2:
            estimated_pos = estimate_source(active_sensors, sliders)
            pg.draw.circle(screen, (255, 205, 0), estimated_pos, 8)

        pg.display.flip()
        clock.tick(60)


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