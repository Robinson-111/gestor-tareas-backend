import time

from rest_framework.throttling import ScopedRateThrottle


class TokenBucketRateThrottle(ScopedRateThrottle):
    """
    Rate limit con token bucket.

    Reemplaza la ventana fija de `ScopedRateThrottle`, permitiendo bursts
    controlados: el bucket arranca con `capacity` tokens y se rellena a
    `refill_rate` tokens por segundo.

    - capacity: tokens disponibles en el burst inicial.
    - refill_rate: tokens por segundo que se agregan al bucket.
    """

    capacity = 10
    refill_rate = 10
    bucket_wait = 0.0

    def allow_request(self, request, view):
        self.scope = getattr(view, self.scope_attr, None)
        if not self.scope:
            return True

        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        capacity = (
            float(self.num_requests) if self.num_requests else float(self.capacity)
        )
        refill_rate = (
            float(self.num_requests) / float(self.duration)
            if self.duration
            else float(self.refill_rate)
        )
        self.capacity = capacity
        self.refill_rate = refill_rate

        key = self.get_cache_key(request, view)
        state = self.cache.get(key)
        tokens_now = float(state.get('tokens')) if state else capacity
        updated_at = float(state.get('updated_at')) if state else time.monotonic()
        tokens = min(capacity, tokens_now + (time.monotonic() - updated_at) * refill_rate)

        bucket_state = {'tokens': tokens, 'updated_at': time.monotonic()}
        self.cache.set(key, bucket_state, self.duration)

        if tokens < 1:
            self.bucket_wait = max(0.0, (1 - tokens) / refill_rate) if refill_rate > 0 else 3600.0
            return False

        bucket_state['tokens'] = tokens - 1
        self.cache.set(key, bucket_state, self.duration)
        self.bucket_wait = 0.0
        return True

    def wait(self):
        return self.bucket_wait
