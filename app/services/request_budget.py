"""One consultation deadline shared by interpretation, generation and review."""
from contextvars import ContextVar
import time

deadline=ContextVar('consultation_deadline',default=None)

def timeout(maximum=45):
    end=deadline.get()
    remaining=maximum if end is None else min(maximum,end-time.monotonic())
    if remaining<=0:raise TimeoutError('Consultation request deadline exceeded')
    return remaining
