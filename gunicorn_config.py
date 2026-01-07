"""
Gunicorn configuration file for production deployment.

This file configures Gunicorn for optimal performance and security.
"""
import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
backlog = 2048

# Worker processes
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests (helps prevent memory leaks)
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stderr
loglevel = os.environ.get('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'gym-manager'

# Server mechanics
daemon = False  # Don't daemonize (systemd will handle this)
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

def on_starting(server):
    """Called just before the master process is initialized."""
    print("Starting Gym Manager application...")

def on_reload(server):
    """Called to recycle workers during a reload."""
    print("Reloading Gym Manager application...")

def when_ready(server):
    """Called just after the server is started."""
    print(f"Gym Manager ready at {bind}")
    print(f"Workers: {workers}")

def on_exit(server):
    """Called just before exiting Gunicorn."""
    print("Shutting down Gym Manager application...")
