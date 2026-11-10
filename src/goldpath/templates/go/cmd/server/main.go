// {{ service_name }} — HTTP service entrypoint.
package main

import (
	"encoding/json"
	"log"
	"net/http"
	"strconv"
	"strings"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var requestsTotal = promauto.NewCounterVec(
	prometheus.CounterOpts{
		Name: "{{ service_slug }}_requests_total",
		Help: "Total HTTP requests handled by {{ service_name }}.",
	},
	[]string{"path", "method", "status_code"},
)

type statusRecorder struct {
	http.ResponseWriter
	status      int
	wroteHeader bool
}

func (r *statusRecorder) WriteHeader(status int) {
	if r.wroteHeader {
		return
	}
	r.wroteHeader = true
	r.status = status
	r.ResponseWriter.WriteHeader(status)
}

func (r *statusRecorder) Write(b []byte) (int, error) {
	if !r.wroteHeader {
		r.WriteHeader(http.StatusOK)
	}
	return r.ResponseWriter.Write(b)
}

func countRequests(mux *http.ServeMux) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		routeLabel := routePattern(mux, r)
		defer func() {
			if err := recover(); err != nil {
				if !rec.wroteHeader {
					rec.status = http.StatusInternalServerError
					http.Error(rec, "internal server error", http.StatusInternalServerError)
				} else {
					log.Printf("panic after response started: %v", err)
				}
			}
			requestsTotal.WithLabelValues(routeLabel, r.Method, strconv.Itoa(rec.status)).Inc()
		}()
		mux.ServeHTTP(rec, r)
	})
}

// routePattern returns the matched route template (e.g. "/users/{id}") rather
// than the raw request path, so unmatched paths don't create unbounded metric
// cardinality. Unmatched requests are labeled "other".
func routePattern(mux *http.ServeMux, r *http.Request) string {
	_, pattern := mux.Handler(r)
	if pattern == "" {
		return "other"
	}
	if idx := strings.IndexByte(pattern, ' '); idx != -1 {
		pattern = pattern[idx+1:]
	}
	return pattern
}

func health(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]string{
		"status":  "ok",
		"service": "{{ service_name }}",
	})
}

func newMux() *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("GET {{ health_path }}", health)
	mux.Handle("GET /metrics", promhttp.Handler())
	return mux
}

func main() {
	log.Printf("{{ service_name }} listening on :{{ port }}")
	log.Fatal(http.ListenAndServe(":{{ port }}", countRequests(newMux())))
}
