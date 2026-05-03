import os

class ConfigManager:
    def __init__(self):
        self.api_keys = {"news_api": "0cf53d3d3f554be09c9b20505aeeefb9"}
        self.scheduler_frequency = {
            "batch": 1800, # 30 mins
            "fast": 300    # 5 mins
        }
        self.feature_flags = {
            "enable_causal": True,
            "enable_ml": True,
            "enable_adaptive": True
        }

config = ConfigManager()
