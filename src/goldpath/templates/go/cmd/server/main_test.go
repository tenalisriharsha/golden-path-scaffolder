package main

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestHealth(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "{{ health_path }}", nil)
	rec := httptest.NewRecorder()
	countRequests(newMux()).ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), `"service":"{{ service_name }}"`) {
		t.Fatalf("unexpected body: %s", rec.Body.String())
	}
}

func TestMetrics(t *testing.T) {
	handler := countRequests(newMux())

	healthReq := httptest.NewRequest(http.MethodGet, "{{ health_path }}", nil)
	handler.ServeHTTP(httptest.NewRecorder(), healthReq)

	metricsReq := httptest.NewRequest(http.MethodGet, "/metrics", nil)
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, metricsReq)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "{{ service_slug }}_requests_total") {
		t.Fatalf("expected metrics output to contain counter name, got: %s", rec.Body.String())
	}
}

func TestCounterIncrementsOnPanic(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /boom", func(w http.ResponseWriter, r *http.Request) {
		panic("boom")
	})
	handler := countRequests(mux)

	req := httptest.NewRequest(http.MethodGet, "/boom", nil)
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("expected status 500, got %d", rec.Code)
	}

	metricsReq := httptest.NewRequest(http.MethodGet, "/metrics", nil)
	metricsRec := httptest.NewRecorder()
	countRequests(newMux()).ServeHTTP(metricsRec, metricsReq)

	if !strings.Contains(metricsRec.Body.String(), `path="/boom"`) {
		t.Fatalf("expected metrics output to include /boom path, got: %s", metricsRec.Body.String())
	}
	if !strings.Contains(metricsRec.Body.String(), `status_code="500"`) {
		t.Fatalf("expected metrics output to include status_code 500, got: %s", metricsRec.Body.String())
	}
}
