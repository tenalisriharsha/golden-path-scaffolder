package main

import (
	"net/http"
	"net/http/httptest"
	"regexp"
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

func TestCounterMatchesClientStatusOnPartialWriteThenPanic(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /partial", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("partial body"))
		panic("boom after write")
	})
	handler := countRequests(mux)

	req := httptest.NewRequest(http.MethodGet, "/partial", nil)
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected client-visible status 200, got %d", rec.Code)
	}
	if rec.Body.String() != "partial body" {
		t.Fatalf("expected body to be untouched by the panic recovery, got: %q", rec.Body.String())
	}

	metricsReq := httptest.NewRequest(http.MethodGet, "/metrics", nil)
	metricsRec := httptest.NewRecorder()
	countRequests(newMux()).ServeHTTP(metricsRec, metricsReq)

	if !strings.Contains(metricsRec.Body.String(), `path="/partial"`) {
		t.Fatalf("expected metrics output to include /partial path, got: %s", metricsRec.Body.String())
	}
	for _, line := range strings.Split(metricsRec.Body.String(), "\n") {
		if strings.Contains(line, `path="/partial"`) {
			if !strings.Contains(line, `status_code="200"`) {
				t.Fatalf("expected status_code 200 for /partial, got metric line: %s", line)
			}
		}
	}
}

func TestMetricCardinalityBoundedForUnmatchedPaths(t *testing.T) {
	handler := countRequests(newMux())

	randomPaths := []string{
		"/users/12345",
		"/scan/wp-admin.php",
		"/api/v2/orders/abc-def-ghi",
		"/nonexistent-" + strings.Repeat("x", 40),
	}
	for _, p := range randomPaths {
		req := httptest.NewRequest(http.MethodGet, p, nil)
		handler.ServeHTTP(httptest.NewRecorder(), req)
	}

	metricsReq := httptest.NewRequest(http.MethodGet, "/metrics", nil)
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, metricsReq)

	pathLabel := regexp.MustCompile(`path="([^"]*)"`)
	counterName := "{{ service_slug }}_requests_total"
	leaked := map[string]bool{}
	for _, line := range strings.Split(rec.Body.String(), "\n") {
		if !strings.HasPrefix(line, counterName) {
			continue
		}
		match := pathLabel.FindStringSubmatch(line)
		if match == nil {
			continue
		}
		for _, p := range randomPaths {
			if match[1] == p {
				leaked[p] = true
			}
		}
	}

	if len(leaked) != 0 {
		t.Fatalf("unmatched request paths must not appear verbatim as metric labels (unbounded cardinality): %v", leaked)
	}
}
