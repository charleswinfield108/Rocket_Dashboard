package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

type dbConfig struct {
	host     string
	port     string
	name     string
	user     string
	password string
}

func parseDBConfig() (dbConfig, error) {
	cfg := dbConfig{
		host:     os.Getenv("DB_HOST"),
		port:     os.Getenv("DB_PORT"),
		name:     os.Getenv("DB_NAME"),
		user:     os.Getenv("DB_USER"),
		password: os.Getenv("DB_PASSWORD"),
	}
	if cfg.host == "" {
		return dbConfig{}, fmt.Errorf("DB_HOST is not set")
	}
	if cfg.name == "" {
		return dbConfig{}, fmt.Errorf("DB_NAME is not set")
	}
	if cfg.user == "" {
		return dbConfig{}, fmt.Errorf("DB_USER is not set")
	}
	if cfg.port == "" {
		cfg.port = "5432"
	}
	return cfg, nil
}

func (c dbConfig) dsn() string {
	return fmt.Sprintf(
		"host=%s port=%s dbname=%s user=%s password=%s sslmode=disable",
		c.host, c.port, c.name, c.user, c.password,
	)
}

// openDB builds a pgxpool, then verifies the connection with a ping.
// MaxConns=10: suits a read-heavy dashboard with up to 6 concurrent endpoint
// queries; increase for higher throughput.
// Fails hard (returns error) if the DB is unreachable — no fallback.
func openDB(cfg dbConfig) (*pgxpool.Pool, error) {
	poolCfg, err := pgxpool.ParseConfig(cfg.dsn())
	if err != nil {
		return nil, fmt.Errorf("parsing DB config: %w", err)
	}
	poolCfg.MaxConns = 10

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	log.Printf("DB: connecting to %s:%s/%s (pool maxConns=10)", cfg.host, cfg.port, cfg.name)
	pool, err := pgxpool.NewWithConfig(ctx, poolCfg)
	if err != nil {
		return nil, fmt.Errorf("opening DB pool (%s:%s/%s): %w", cfg.host, cfg.port, cfg.name, err)
	}

	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("DB ping failed (%s:%s/%s): %w", cfg.host, cfg.port, cfg.name, err)
	}

	log.Printf("DB: pool ready (%s:%s/%s)", cfg.host, cfg.port, cfg.name)
	return pool, nil
}

// GET /api/health — issues a live DB ping; returns 503 if unreachable.
func (s *server) handleHealth(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	if err := s.db.Ping(ctx); err != nil {
		s.writeError(w, http.StatusServiceUnavailable, "DB_UNAVAILABLE",
			"database ping failed: "+err.Error())
		return
	}
	s.writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "db": "connected"})
}
