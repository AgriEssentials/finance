import sys
import os

# Add backend directory to Python path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_dir)
os.environ['PYTHONPATH'] = backend_dir + os.pathsep + os.environ.get('PYTHONPATH', '')

# CRITICAL: Memory optimization - MUST be before any TensorFlow imports
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')  # Suppress TF logs
os.environ.setdefault('CUDA_VISIBLE_DEVICES', '')   # Force CPU-only
os.environ.setdefault('OMP_NUM_THREADS', '1')       # Single threaded for low memory
os.environ.setdefault('NUMEXPR_MAX_THREADS', '1')   # Limit parallel threads  
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')  # Single thread
os.environ.setdefault('MKL_NUM_THREADS', '1')       # Single thread

# Disable multiprocessing completely (causes memory bloat)
# Use single worker only
os.environ['WORKERS'] = '1'

# Now import and run
import uvicorn

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    workers = 1  # FORCED: Single worker only
    reload = os.getenv("APP_RELOAD", "false").lower() in {"1", "true", "yes"}

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        workers=workers,
        reload=reload,
        loop="asyncio"
    )
