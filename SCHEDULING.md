# Schoology Scraper - Scheduling Configuration

## Overview

The Schoology Grade Scraper supports flexible scheduling via the `SCRAPE_TIMES` environment variable, allowing you to define exactly when grade checks should occur.

## Configuration

### Environment Variable
```bash
# In .env file
SCRAPE_TIMES=08:00,20:00
```

**Format**: 24-hour time format, comma-separated for multiple times per day

### Examples

```bash
# Daily at 9 PM only
SCRAPE_TIMES=21:00

# Twice daily (morning and evening)
SCRAPE_TIMES=08:00,20:00

# Three times daily
SCRAPE_TIMES=07:00,13:00,19:00

# Every 6 hours
SCRAPE_TIMES=00:00,06:00,12:00,18:00

# Business hours monitoring
SCRAPE_TIMES=08:30,12:30,17:30

# Custom times with minutes
SCRAPE_TIMES=07:15,15:45,22:30
```

## Deployment Methods

### 1. Continuous Docker Service (Recommended)
```bash
# Start persistent monitoring
docker compose up -d

# The container runs continuously and executes at scheduled times
# No external cron needed
```

**How it works:**
- Container stays running 24/7
- Built-in scheduler calculates sleep duration until next run
- Executes grade scraping at exact times specified
- Automatically restarts if container crashes

### 2. External Cron (Alternative)
```bash
# For external scheduling control
0 21 * * * cd /path/to/project && docker compose run --rm --profile manual schoology-scraper
```

**When to use:**
- Integration with existing cron systems
- More complex scheduling requirements
- System-level scheduling preferences

## Scheduler Implementation

### How Time Calculation Works
1. **Parse times** from `SCRAPE_TIMES` environment variable
2. **Calculate next run** by finding the closest upcoming time
3. **Sleep precisely** until that moment arrives
4. **Execute scraper** then repeat the cycle

### Smart Features
- **Automatic rollover**: If current time has passed today's schedule, moves to tomorrow
- **Precise timing**: No interval drift - runs at exact specified times
- **Error resilience**: Failed runs don't affect the schedule
- **Logging**: Comprehensive logging of schedule calculations and execution

### Logs
- **Scheduler logs**: `logs/scheduler.log`
- **Application logs**: `logs/application.log`
- **Change tracking**: `logs/grade_changes.log`

## Benefits Over Interval-Based Scheduling

| Feature | Timestamp Scheduling | Interval Scheduling |
|---------|---------------------|-------------------|
| **Precision** | Exact times (8:00 AM sharp) | Approximate (8:03 AM after 3min scrape) |
| **Predictability** | Always same times daily | Drifts over time |
| **Flexibility** | Any times, any frequency | Fixed intervals only |
| **User-friendly** | "8am and 8pm" intuitive | "every 720 minutes" confusing |

## Monitoring

### Check Status
```bash
# View live logs
docker compose logs -f

# Check if container is running
docker compose ps

# View recent scheduler decisions
tail -f logs/scheduler.log
```

### Health Checks
The scheduler includes built-in health monitoring:
- **Process check**: Verifies scheduler is running
- **Timeout protection**: 30-minute limit per scrape
- **Automatic restart**: Container restarts on failure

## Troubleshooting

### Common Issues

**Container not running:**
```bash
docker compose ps
# If exited, check logs: docker compose logs
```

**Wrong times:**
```bash
# Verify environment variable
docker compose exec schoology-scheduler env | grep SCRAPE_TIMES
```

**Timezone concerns:**
```bash
# Scheduler uses container's local time
# Times are interpreted in the container's timezone
```

### Debug Mode
```bash
# View detailed scheduler logs
docker compose logs schoology-scheduler
```

## Migration from Cron

### From External Cron
1. Remove cron entry: `crontab -e`
2. Update `SCRAPE_TIMES` to match your cron schedule
3. Start continuous service: `docker compose up -d`

### Cron to Timestamp Mapping
```bash
# Old cron: 0 21 * * * (daily at 9 PM)
SCRAPE_TIMES=21:00

# Old cron: 0 */6 * * * (every 6 hours)
SCRAPE_TIMES=00:00,06:00,12:00,18:00

# Old cron: 0 8,20 * * * (8 AM and 8 PM)
SCRAPE_TIMES=08:00,20:00
```