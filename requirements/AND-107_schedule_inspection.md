# AND-107 Schedule Inspection

## Overview

The chatbot can schedule an inspection when asked. Before writing anything to the database, the chatbot confirms the details with the user and waits for explicit approval.

## Required Flow

```
User:     "Schedule an inspection for elevator E12345 next Tuesday. Suspected hydraulic issue."
Chatbot:  "I'll schedule an inspection for elevator E12345 on Tuesday, June 23, 2026.
           Reason: suspected hydraulic issue. Priority: normal. Should I go ahead?"
User:     "Yes"
Chatbot:  "Done. Inspection scheduled for elevator E12345 on June 23, 2026."
```

## Requirements

- The chatbot must **confirm all details** (elevator ID, date, reason, priority) with the user before writing to the database.
- The chatbot must **wait for explicit user approval** ("Yes", "Go ahead", "Confirm", etc.) before taking action.
- If the user says no or changes the details, the chatbot must update accordingly and re-confirm before proceeding.
- The inspection record must be written to the database only after approval is received.
- If the elevator ID does not exist in the database, the chatbot must say so and not create the record.
