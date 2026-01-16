import os

# Bind port 24 given by render 

bind = f"0.0.0.0:{os.environ.get('PORT', '1000')}"
workers = 2
worker_class = "sync"
timeout = 120
accesslog = "-"
errorlog = "-"
loglevel = "info"