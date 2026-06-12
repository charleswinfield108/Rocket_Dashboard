package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"

	"github.com/jackc/pgx/v5/pgxpool"
)

type config struct {
	port    string
	dataDir string
}

func parseConfig() config {
	var portFlag string
	flag.StringVar(&portFlag, "port", "", "listen port (overrides PORT env var, default 8081)")
	flag.Parse()

	port := portFlag
	if port == "" {
		port = os.Getenv("PORT")
	}
	if port == "" {
		port = "8081"
	}

	dataDir := os.Getenv("DATA_DIR")
	if dataDir == "" {
		// Binary lives at platform/api/; CSVs are two directories up at <repo>/data/.
		// filepath.Abs resolves this relative to the process working directory, which
		// is platform/api/ when invoked with "go run ." or from the built binary there.
		dataDir = filepath.Join("..", "..", "data")
	}

	abs, err := filepath.Abs(dataDir)
	if err != nil {
		log.Fatalf("cannot resolve data directory %q: %v", dataDir, err)
	}

	return config{port: port, dataDir: abs}
}

type server struct {
	cfg config
	db  *pgxpool.Pool

	// Loaded at startup from CSV files. All maps are keyed by ElevatingDevicesNumber
	// (exposed as "id" in JSON), except ordersByInsp which is keyed by InspectionNumber.
	elevators         map[int]*elevatorRow
	elevatorIDs       []int // stable insertion order for deterministic pagination
	inspByElev        map[int][]*inspectionRow
	ordersByInsp      map[int][]*orderRow
	ordersByElev      map[int][]*orderRow
	predictions       map[int]*predictionRow
	predictionsLoaded bool
}

func (s *server) routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/health", s.handleHealth)
	mux.HandleFunc("GET /api/elevators", s.handleListElevators)
	mux.HandleFunc("GET /api/elevators/{id}", s.handleGetElevator)
	mux.HandleFunc("GET /api/elevators/{id}/inspections", s.handleGetInspections)
	mux.HandleFunc("GET /api/elevators/{id}/risk", s.handleGetRisk)
	mux.HandleFunc("GET /api/fleet/stats", s.handleFleetStats)
	mux.HandleFunc("GET /api/fleet/alerts", s.handleFleetAlerts)
	return jsonMiddleware(mux)
}

// jsonMiddleware sets Content-Type: application/json on every response,
// including errors, before the handler writes its status or body.
func jsonMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		next.ServeHTTP(w, r)
	})
}

func main() {
	cfg := parseConfig()

	if _, err := os.Stat(cfg.dataDir); err != nil {
		log.Fatalf("data directory not found at %q — set DATA_DIR to override", cfg.dataDir)
	}

	dbCfg, err := parseDBConfig()
	if err != nil {
		log.Fatalf("DB configuration error: %v", err)
	}
	pool, err := openDB(dbCfg)
	if err != nil {
		log.Fatalf("cannot connect to database: %v", err)
	}
	defer pool.Close()

	srv := &server{cfg: cfg, db: pool}
	if err := srv.loadData(); err != nil {
		log.Fatal(err)
	}

	log.Printf("loaded: %d elevators, %d inspection groups, %d order groups",
		len(srv.elevators), len(srv.inspByElev), len(srv.ordersByElev))
	if !srv.predictionsLoaded {
		log.Printf("predictions.csv not found — GET /api/elevators/{id}/risk returns 503 until Task 6 generates it")
	}

	addr := fmt.Sprintf(":%s", cfg.port)
	log.Printf("elevator fleet API listening on %s (data: %s)", addr, cfg.dataDir)

	if err := http.ListenAndServe(addr, srv.routes()); err != nil {
		log.Fatal(err)
	}
}
