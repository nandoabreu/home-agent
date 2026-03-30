# Project Configuration

## Language Settings

- **Conversa**: pt-BR (Brazilian Portuguese)
- **Code, documents, settings, commit messages**: en-GB (British English)

## Action Confirmation Guidelines

- Always confirm with the user before taking any action
- Always propose the action plan before executing
- When sending an email, confirm the recipients before proceeding
- When modifying a calendar, be explicit about:
  - The number of insertions
  - Whether it is an individual event or a series
- Especially dangerous commands like `rm` require explicit confirmation before execution

## Development Guidelines

- Write code in en-GB
- Write documentation in en-GB
- Write commit messages in en-GB
- Use British English spelling (e.g., "colour" not "color", "centre" not "center")

## Google Calendar Integration

User has Google Calendar with iCal export. Configuration in `~/.bashrc`:

- `GOOGLE_CAL_BASE_URL` - Base URL for Google iCal
- `GOOGLE_CAL_SECRET` - Private calendar secret address

### How to use:

1. **Download/Update calendar:**
   ```bash
   source ~/.bashrc
   curl -sL -o ~/.calendar.ics "${GOOGLE_CAL_BASE_URL}/${GOOGLE_CAL_SECRET}"
   ```
   Or use: `/home/repos/home-agent/scripts/google-calendar.sh download`

2. **Get events for a date:**
   ```bash
   # Today's events
   /home/repos/home-agent/scripts/google-calendar.sh events
   
   # Specific date (YYYYMMDD)
   /home/repos/home-agent/scripts/google-calendar.sh events 20260325
   ```

3. **Manual awk parsing (alternative):**
   ```bash
   TODAY=$(date +%Y%m%d)  # or specific date
   cat ~/.calendar.ics | tr '\r' '\n' | awk -v today="$TODAY" '
   /^BEGIN:VEVENT$/ {capture=1; sum=""; ds=""}
   /^END:VEVENT$/ {
       if (capture && ds ~ today) {
           gsub(/[^0-9]/, "", ds)
           if (length(ds) >= 8) {
               h=substr(ds,9,2); m=substr(ds,11,2)
               if (h=="00" && m=="00") print "All day:", sum
               else print h":"m, sum
           } else { print "All day:", sum }
       }
       capture=0
   }
   capture && /^DTSTART.*:/ {ds=$0}
   capture && /^SUMMARY.*:/ {sum=$0; sub(/^SUMMARY[^:]*: */,"",sum)}
   '
   ```

### Important:
- Always include `/` between BASE_URL and SECRET when concatenating
- The ICS file contains `\r\n` line endings, use `tr '\r' '\n'` before awk
- Calendar file stored at `~/.calendar.ics`
