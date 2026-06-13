# ── builder ───────────────────────────────────────────────────────────────────
# Full Go toolchain only lives here; nothing from this stage leaks into runtime.
FROM golang:1.25-alpine AS builder

WORKDIR /build

# Copy module manifests first so dependency downloads are cached separately
# from source changes.
COPY platform/api/go.mod platform/api/go.sum ./
RUN go mod download

COPY platform/api/*.go ./

# CGO_ENABLED=0 produces a fully static binary (no libc dependency).
# -ldflags="-s -w" strips debug info and DWARF tables (~30% smaller binary).
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o api_server .

# ── runtime ───────────────────────────────────────────────────────────────────
# alpine (not scratch) so we have a shell available for Step 4 connectivity
# checks; can switch to scratch once the DB integration is verified.
FROM alpine AS runtime

RUN apk add --no-cache ca-certificates wget

WORKDIR /app

# Binary from builder — no Go toolchain included.
COPY --from=builder /build/api_server .

# CSV datasets the server loads at startup.
# DATA_DIR tells the binary where to find them (overrides the default ../../data
# path that assumes the binary is running from platform/api/ on the host).
COPY data/ /data/

ENV DATA_DIR=/data

EXPOSE 8081

ENTRYPOINT ["/app/api_server"]
