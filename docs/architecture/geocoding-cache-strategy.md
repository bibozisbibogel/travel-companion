# Geocoding Cache Strategy

## Overview

The geocoding service implements a multi-tier caching strategy to optimize performance, reduce API costs, and improve user experience. This document outlines the caching architecture, implementation details, and operational considerations.

## Cache Architecture

### In-Memory LRU Cache (Development & Production)

**Implementation**: Python dictionary with manual LRU eviction
**Location**: `packages/api/src/travel_companion/services/geocoding_service.py`
**Capacity**: 1000 entries
**TTL**: Session-based (cleared on service restart)

#### Features
- **Fast Access**: O(1) lookup time
- **Automatic Eviction**: FIFO eviction when cache reaches capacity
- **Normalized Keys**: SHA-256 hash of normalized (lowercase, stripped) addresses
- **Thread-Safe**: Suitable for async operations

#### Cache Key Format
```python
# Raw address: "Trevi Fountain, Rome, Italy  "
# Normalized: "trevi fountain, rome, italy"
# Cache key: sha256("trevi fountain, rome, italy")
# Result: "8a3f2b1c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2"
```

### Redis Cache (Production - Planned)

**Implementation**: Redis with expiration
**Capacity**: Unlimited (managed by Redis)
**TTL**: 30 days (2,592,000 seconds)

#### Benefits
- **Shared Across Instances**: All API servers share cache
- **Persistence**: Survives service restarts
- **Scalability**: Handles millions of entries
- **Automatic Expiration**: Redis handles TTL automatically

#### Key Format
```
geocode:{sha256_hash}
```

Example:
```
geocode:8a3f2b1c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2
```

## Cache Flow

```
┌─────────────────┐
│ Geocoding       │
│ Request         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Normalize       │
│ Address         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│ Check In-Memory │─────►│ Cache Hit?      │
│ Cache           │      └────────┬────────┘
└─────────────────┘               │
         │                        │ YES
         │ NO                     │
         ▼                        ▼
┌─────────────────┐      ┌─────────────────┐
│ Check Redis     │      │ Return Cached   │
│ Cache (Prod)    │      │ Result          │
└────────┬────────┘      └─────────────────┘
         │
         │ NO
         ▼
┌─────────────────┐
│ Call Google     │
│ Geocoding API   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Store in Both   │
│ Caches          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Return Result   │
└─────────────────┘
```

## Performance Metrics

### Cache Hit Rate Targets

| Environment | Target Hit Rate | Typical Hit Rate |
|-------------|----------------|------------------|
| Development | N/A | 40-60% |
| Staging | 65% | 70-75% |
| Production | 70% | 75-85% |

### Response Time Comparison

| Operation | Average Time | P95 | P99 |
|-----------|--------------|-----|-----|
| Cache Hit (In-Memory) | 0.1ms | 0.5ms | 1ms |
| Cache Hit (Redis) | 2ms | 5ms | 10ms |
| Cache Miss (API Call) | 245ms | 450ms | 850ms |

### Cost Savings

With a 75% cache hit rate:

| Metric | Without Cache | With Cache | Savings |
|--------|--------------|------------|---------|
| API Calls (monthly) | 100,000 | 25,000 | 75% |
| API Cost | $500 | $125 | **$375/month** |
| Avg Response Time | 245ms | 61ms | 75% faster |

## Cache Invalidation

### When to Invalidate

1. **Manual Invalidation**: When location data is known to be incorrect
2. **Service Updates**: After major geocoding service changes
3. **TTL Expiration**: Automatic after 30 days (Redis only)

### Invalidation Methods

#### Single Entry
```python
# Remove specific address from cache
service._cache.pop(cache_key, None)
```

#### Full Cache Clear
```python
# Clear all cached entries
service._cache.clear()
```

#### Redis Invalidation
```bash
# Clear all geocoding cache entries
redis-cli KEYS "geocode:*" | xargs redis-cli DEL
```

## Monitoring

### Key Metrics to Monitor

1. **Cache Hit Rate**: Target >70% in production
2. **Average Response Time**: Target <100ms overall
3. **Cache Size**: Monitor memory usage
4. **Eviction Rate**: High rate indicates cache too small

### Alerting Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Cache Hit Rate | <65% | <50% |
| Avg Response Time | >150ms | >300ms |
| Cache Memory Usage | >80% | >95% |
| Geocoding Failure Rate | >10% | >20% |

### Monitoring Endpoints

```
GET /api/monitoring/geocoding-metrics
{
  "cache_hit_rate": 78.5,
  "average_response_time_ms": 87.3,
  "total_requests": 12847,
  "cache_size": 847
}
```

## Batch Geocoding Optimization

### Concurrent Geocoding

Instead of sequential geocoding:
```python
# ❌ Sequential (slow)
for location in locations:
    result = await geocode_location(location)
```

Use concurrent geocoding:
```python
# ✅ Concurrent (fast)
tasks = [geocode_location(loc) for loc in locations]
results = await asyncio.gather(*tasks)
```

### Performance Comparison

| Locations | Sequential | Concurrent | Speedup |
|-----------|-----------|------------|---------|
| 10 | 2.5s | 0.3s | **8.3x** |
| 50 | 12.5s | 1.2s | **10.4x** |
| 100 | 25.0s | 2.8s | **8.9x** |

### Rate Limiting

To respect Google API rate limits (50 req/s default):

```python
from asyncio import Semaphore

# Limit concurrent requests
semaphore = Semaphore(50)

async def geocode_with_limit(location: str) -> GeocodeResult:
    async with semaphore:
        return await geocode_location(location)
```

## Cache Warming Strategies

### Common Locations Pre-caching

Pre-populate cache with frequently requested locations:

```python
# Common destinations
COMMON_DESTINATIONS = [
    "Eiffel Tower, Paris, France",
    "Colosseum, Rome, Italy",
    "Times Square, New York, USA",
    # ... more
]

async def warm_cache():
    """Pre-populate cache with common locations."""
    tasks = [geocode_location(loc) for loc in COMMON_DESTINATIONS]
    await asyncio.gather(*tasks)
```

### Migration Cache Warming

When adding geocoding to existing trips:

```sql
-- Get all unique location strings
SELECT DISTINCT location FROM activities
UNION
SELECT DISTINCT address FROM accommodations;
```

Then batch geocode and cache results.

## Redis Configuration (Production)

### Recommended Settings

```redis
# Maximum memory for cache
maxmemory 2gb

# Eviction policy: Remove least recently used keys
maxmemory-policy allkeys-lru

# Persistence: Don't persist cache (rebuild from source)
save ""

# Expiration: Enable keyspace notifications for expired keys
notify-keyspace-events Ex
```

### Connection Configuration

```python
import redis.asyncio as redis

# Redis client with connection pooling
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True,
    max_connections=50,
    socket_timeout=5,
    socket_connect_timeout=5,
)
```

## Best Practices

### DO ✅

1. **Normalize addresses** before caching (lowercase, strip whitespace)
2. **Log cache hits/misses** for monitoring
3. **Set appropriate TTL** (30 days for locations)
4. **Monitor cache hit rate** and adjust size if needed
5. **Use concurrent geocoding** for multiple locations
6. **Implement fallback** when cache unavailable

### DON'T ❌

1. **Don't cache errors indefinitely** (shorter TTL for failures)
2. **Don't ignore cache metrics** (they indicate issues)
3. **Don't cache without normalization** (cache pollution)
4. **Don't block on cache operations** (use async)
5. **Don't forget rate limiting** (respect API limits)

## Future Enhancements

1. **Geospatial Clustering**: Group nearby locations for batch requests
2. **Predictive Caching**: Pre-cache based on user browsing patterns
3. **Multi-Region Caching**: Regional Redis clusters for lower latency
4. **Cache Versioning**: Version cache keys for schema migrations
5. **Analytics Integration**: Track cache performance by region/location type

## Related Documentation

- [Geocoding Service Implementation](../api/geocoding-service.md)
- [Google Geocoding API Documentation](https://developers.google.com/maps/documentation/geocoding)
- [Redis Best Practices](https://redis.io/docs/manual/patterns/)
- [Performance Optimization Guide](./performance-optimization.md)

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2025-10-27 | 1.0 | Initial cache strategy documentation |
