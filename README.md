# Collect StatsD post it to PRTG

Collect [StatsD](https://github.com/etsy/statsd) data and periodically
post it into a [PRTG](https://www.paessler.com/prtg) [advanced data sensor]
(https://www.paessler.com/manuals/prtg/http_push_data_advanced_sensor).
The application currently knows how to convert counters and timers with
a sample rate of 1.0.
