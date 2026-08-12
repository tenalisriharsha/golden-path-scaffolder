// {{ service_name }} — HTTP service entrypoint.
package main

import (
	"encoding/json"
	"log"
	"net/http"
)

func health(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]string{
		"status":  "ok",
		"service": "{{ service_name }}",
	})
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("GET {{ health_path }}", health)
	log.Printf("{{ service_name }} listening on :{{ port }}")
	log.Fatal(http.ListenAndServe(":{{ port }}", mux))
}
