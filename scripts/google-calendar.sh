#!/bin/bash
# Download and/or extract events from Google Calendar ICS

CAL_FILE="${HOME}/.calendar.ics"
BASHRC="${HOME}/.bashrc"

usage() {
    echo "Usage: $0 [download|events]"
    echo "  download  - Download calendar from Google"
    echo "  events    - Show today's events"
    echo "  events YYYY-MM-DD - Show events for specific date"
    exit 1
}

download_calendar() {
    eval "$(grep -E '^GOOGLE_CAL' "$BASHRC")"
    curl -sL -o "$CAL_FILE" "${GOOGLE_CAL_BASE_URL}/${GOOGLE_CAL_SECRET}"
    echo "Calendar updated: $CAL_FILE"
}

show_events() {
    local date_arg="${1:-$(date +%Y%m%d)}"
    cat "$CAL_FILE" | tr '\r' '\n' | awk -v today="$date_arg" '
/^BEGIN:VEVENT$/ {capture=1; sum=""; ds=""}
/^END:VEVENT$/ {
    if (capture && ds ~ today) {
        gsub(/[^0-9]/, "", ds)
        if (length(ds) >= 8) {
            h=substr(ds,9,2); m=substr(ds,11,2)
            if (h=="00" && m=="00") print "All day:", sum
            else print h":"m, sum
        } else {
            print "All day:", sum
        }
    }
    capture=0
}
capture && /^DTSTART.*:/ {ds=$0}
capture && /^SUMMARY.*:/ {sum=$0; sub(/^SUMMARY[^:]*: */,"",sum)}
' | grep -v "^$"
}

case "${1:-}" in
    download) download_calendar ;;
    events) show_events "$2" ;;
    *) usage ;;
esac
