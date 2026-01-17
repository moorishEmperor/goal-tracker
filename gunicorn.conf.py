import os

# Internal interface 
"""
Internet → Render's Load Balancer (public IP:443/80) 
          ↓
          Render's Internal Routing
          ↓
          Your App (0.0.0.0:10000) ← Internal only
"""
bind = f"0.0.0.0:{os.environ.get('PORT', '1000')}"
workers = 2
worker_class = "sync"
timeout = 120
accesslog = "-"
errorlog = "-"
loglevel = "info"