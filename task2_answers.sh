#!/usr/bin/env bash
# PAM Ops Engineer Task 2 - Log Analysis
# All commands are run inside the Docker container via SSH or docker exec.
# Log file: /opt/local/logs/server.log.gz
# Usage: bash task2_answers.sh
#   (requires the pam-ops Docker container to be running)

CONTAINER="pam-ops-container"
LOG="/opt/local/logs/server.log.gz"

echo "=== Task 2: Log Analysis ==="
echo ""

# ---------------------------------------------------------------------------
# Q1: Count of GetTemporaryAuthenticationTokenRequest
# ---------------------------------------------------------------------------
echo "1) Count of GetTemporaryAuthenticationTokenRequest:"
docker exec "$CONTAINER" bash -c "zcat $LOG | grep -c 'GetTemporaryAuthenticationTokenRequest'"
echo ""

# ---------------------------------------------------------------------------
# Q2: Count of LoginRequests per minute
# ---------------------------------------------------------------------------
echo "2) LoginRequest count per minute:"
docker exec "$CONTAINER" bash -c "
  zcat $LOG \
    | grep 'LoginRequest-' \
    | grep -oP '\d{4}-\d{4}' \
    | sort \
    | uniq -c \
    | awk '{print \$1, \$2}'
"
echo ""

# ---------------------------------------------------------------------------
# Q3: All request types that had 'JSON OUT:' and their counts
# ---------------------------------------------------------------------------
echo "3) Requests with JSON OUT: (count + name):"
docker exec "$CONTAINER" bash -c "
  zcat $LOG \
    | grep 'JSON OUT:' \
    | grep -oP '[A-Za-z]+Request-\d+' \
    | sort \
    | uniq -c \
    | sort -rn \
    | awk '{print \$1, \$2}'
"
echo ""

# ---------------------------------------------------------------------------
# Q4: For id=149418 — extract obj=, ipAddress=, customData=[KV(5, playerCode= and flow= in one line
# ---------------------------------------------------------------------------
echo "4) Values for request id=149418:"
docker exec "$CONTAINER" bash -c "
  zcat $LOG \
    | grep 'id=149418,' \
    | perl -ne '
        \$obj = \$1 if /obj=([^,]+)/;
        \$ip  = \$1 if /ipAddress=([^,)]+)/;
        \$kv5 = \$1 if /customData=\[KV\(5, ([^\)]+)\)/;
        \$pc  = \$1 if /playerCode=([^,]+)/;
        \$fl  = \$1 if /flow=([^)]+)\)/;
        END { print \"\$obj, \$ip, \$kv5, \$pc, \$fl\n\" }
      '
"
echo ""

# ---------------------------------------------------------------------------
# Bonus: Sum of all duration= values (in milliseconds)
# ---------------------------------------------------------------------------
echo "Bonus) Total duration (ms) of all requests:"
docker exec "$CONTAINER" bash -c "
  zcat $LOG \
    | grep -oP 'duration=\K\d+' \
    | paste -sd+ \
    | bc
"
