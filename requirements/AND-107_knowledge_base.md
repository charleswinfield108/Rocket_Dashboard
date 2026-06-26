# AND-107 Knowledge Base (RAG Pipeline)

## Overview

The chatbot searches maintenance documentation and incident narratives to answer procedural and technical questions. This goes beyond what the system prompt can hold: the maintenance documents total 50-70 pages of detailed procedures, troubleshooting guides, and safety references.

**Implementation:** RAG pipeline using ChromaDB as the vector database.

## Knowledge Sources

### 1. Maintenance Documents (PDF files)

Six documents provided:
- Hydraulic Elevator Maintenance Procedures
- Traction Elevator Troubleshooting Guide
- Safety Code Quick Reference
- Inspection Types and What They Check
- Common Failure Modes by Elevator Type
- Emergency Response Protocols

### 2. Incident Narratives

Free-text narratives from the existing incidents dataset. Each incident record includes a narrative describing what happened (e.g., "Elevator-Flood on 13th floor ran down the stairs and through the elevators"). Approximately 2,400 incident narratives covering near-misses and incidents.

## Required Capabilities

- **Procedural questions:** Answer using content from maintenance documents (e.g., "What's the maintenance procedure for hydraulic pressure loss?")
- **Historical questions:** Answer "has this happened before?" questions using incident narrative data (e.g., "Have we seen flooding incidents in elevators?")
- **Semantic retrieval:** Retrieve relevant content even when the user's phrasing doesn't exactly match the document text. A technician asking "what do I do when hydraulic pressure drops?" should get the same content as one asking about "hydraulic pressure loss procedure."
- **Grounded responses:** If the chatbot cannot find relevant documentation, it must say so rather than inventing a procedure.

## Technical Implementation

- **Vector database:** ChromaDB
- **Pipeline:** Chunk documents → embed → store in ChromaDB → retrieve on query → inject into LLM context
