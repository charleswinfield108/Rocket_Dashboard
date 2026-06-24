# AND-107 Source Citations

## Overview

The operations team needs to trust the chatbot's answers. Every response that uses data or documents must cite where the information came from.

## Requirements

- **Database responses** must cite the source table and relevant record (e.g., "Source: inspections table, elevator 12345").
- **Document responses** must cite the source document and section (e.g., "Source: Hydraulic Elevator Maintenance Procedures, Section 3.2").
- **Incident narrative responses** must cite the incident ID and date.
- **Citations must be accurate:** if the chatbot references a source, that source must exist and contain the claimed information. The chatbot must not fabricate citations or attribute information to a document that does not contain it.
- **When no source exists:** the chatbot must say so rather than citing a source it cannot verify.
