import pandas as pd
import numpy as np

MAX_COUNT = 4

class DataSimulator:
    def __init__(self, excel_path):
        df = pd.read_excel(excel_path, sheet_name='data')
        self.sensor_ids = sorted(df['sensor_id'].unique())
        self.light_lists = [
            df[df['sensor_id'] == sensor]['light'].tolist() for sensor in self.sensor_ids
        ]

    def get_light_values(self, index):
        result = []
        active_sensor_count = 0
        for light_list in self.light_lists[:MAX_COUNT]:
            if index + 1200 < len(light_list):
                result.append(light_list[index + 1200])
                active_sensor_count += 1
            else:
                result.append(None)

        if active_sensor_count < 2:
            # randomly generate data if running out!
            result = [np.random.uniform(20, 30), np.random.uniform(30, 40)] + [None] * (MAX_COUNT - 2)
            return tuple(result)

        return tuple(result)
