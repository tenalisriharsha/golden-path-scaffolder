// {{ service_name }} — HTTP service entrypoint.
package main

import (
	"encoding/json"
	"log"
	"net/http"
	"strconv"

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
	status int
}

func (r *statusRecorder) WriteHeader(status int) {
	r.status = status
	r.ResponseWriter.WriteHeader(status)
}

func countRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)
		requestsTotal.WithLabelValues(r.URL.Path, r.Method, strconv.Itoa(rec.status)).Inc()
	})
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
