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
