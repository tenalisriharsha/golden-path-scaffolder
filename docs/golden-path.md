# The golden path, and why this tool looks the way it does

"Golden path" is what platform teams call the paved road: the one way of
building a service that is fully supported, fast to start on, and already
correct for the things every service eventually needs — health checks,
metrics, a container image, CI, and a deployment target. Teams that don't
have one end up with N services built N different ways, each missing a
different subset of "obvious in hindsight" operational basics. This tool is
a small, self-contained version of the generator a platform team would build
to give every new service the same paved road on day one.

Every choice below is a default, not a mandate — `goldpath new` is not
trying to prevent someone from doing something else. It's trying to make
sure nobody *forgets* to do the standard thing, by making the standard thing
the zero-effort thing.

## Why a real health check, not a stub

Every generated service exposes `GET /healthz` (`app/main.py` for FastAPI,
`cmd/server/main.go` for Go) that returns a real 200 with a JSON body, wired
from the very first line of the entrypoint. It's not a placeholder to fill
in later, because "add a health check" is exactly the kind of task that gets
deferred until an on-call engineer needs one at 2am and it isn't there. The
path itself (`health_path` in `flavors.py`, currently `/healthz` for both
flavors) is flavor metadata rather than a hardcoded string, so it stays
consistent between the app code, the Kubernetes probes, and the README —
one source of truth instead of three places that can drift out of sync.

## Why the probes are wired to that same health check

`k8s/deployment.yaml`'s `livenessProbe` and `readinessProbe` both point at
`{{ health_path }}` on the named `http` container port — the same path the
app itself defines, the same port the `Service` forwards to. A generated
service is deployable to Kubernetes without anyone hand-editing YAML to
figure out what port or path is correct: the manifest generation and the
app generation share one template context (`build_context` in
`scaffold.py`), so they cannot disagree.

## Why a non-root, minimal runtime image

The FastAPI Dockerfile is a two-stage build: dependencies compile in a
`python:3.12-slim` builder stage, then only the installed packages and app
code copy into a fresh slim stage running as a non-root `appuser`. The Go
Dockerfile goes further — `distroless/static-debian12`, a runtime image
with no shell, no package manager, nothing but the compiled binary. Neither
of these is exotic; they're standard container hardening that every
production image should have and that's tedious enough to configure by hand
that services often ship without it. Baking it into the template means the
tradeoff (a slightly less debuggable container, in exchange for a
meaningfully smaller attack surface) is made once, correctly, by the
platform, rather than re-litigated per service.

## Why a request counter ships by default

Both flavors wire a `<service>_requests_total` Prometheus counter (labeled
`path`, `method`, `status_code`) into the request-handling middleware
before the developer writes a single route of their own, and expose it on
`GET /metrics`. Request rate and error rate are the first two things anyone
asks when a service misbehaves, and they're useless if instrumentation was
never added. Making the metric's name a template variable
(`service_slug`) rather than a fixed string is what lets
`grafana/dashboard.json` reference it directly — the dashboard queries
literally the same counter the app emits, so "the dashboard is empty" isn't
a possible failure mode for a service that hasn't been customized yet.

## Why Kubernetes manifests ship even though `--no-k8s` exists

The default is to generate `k8s/deployment.yaml`, `k8s/service.yaml`, and
`grafana/dashboard.json` alongside the app, because most teams adopting a
scaffolder like this *are* deploying to Kubernetes, and a manifest that's
already wired to the right probe path and port is worth more than a manifest
written from scratch under deadline pressure and copy-pasted from a
different service (where the probe path quietly stays `/health` after the
app's route was renamed to `/healthz`). `--no-k8s` exists for the teams that
aren't on that platform — the flag is there so the tool doesn't force an
assumption on everyone, but the *default* encodes what the common case
actually needs. This is also the one option in the tool that both skips
whole files (`scaffold.py` checks `relative.parts[0] in _K8S_DIRS` before
writing anything under `k8s/` or `grafana/`) and changes rendered content
elsewhere (each flavor's `README.md` wraps its "Deploy to Kubernetes" and
"Observability" sections in `{% if with_k8s %}`) — one flag, two different
mechanisms for "this doesn't apply here."

## Why the template engine has no expression language

`engine.py` supports exactly two things: `{{ variable }}` substitution and
`{% if variable %}...{% endif %}` conditionals, both strict — an undefined
variable or an unbalanced tag is an error, not a silently empty string.
There's no filters, no loops, no arithmetic, and that's deliberate. A
golden-path template's job is to be predictable: reading a `.yaml` or `.py`
file in the template tree should tell you almost exactly what the generated
file will look like, with no logic to trace through. The moment a template
needs real expressiveness, that's a sign the logic belongs in
`scaffold.py` (as Python, where it's testable and readable) rather than in
template syntax invented to avoid writing Python. `build_context()` is
where flavor-specific decisions get made; the templates just interpolate
the results.

## Why both flavors' platform assets are byte-identical

`k8s/deployment.yaml`, `k8s/service.yaml`, and `grafana/dashboard.json` are
the same files (modulo template variables) in both the `fastapi/` and
`go/` template trees. The image tag convention, probe wiring, resource
request/limit shape, and the `<service>_requests_total` metric name aren't
language-specific decisions — they're platform conventions that should hold
regardless of what's running inside the container. Keeping them identical
is what makes it possible to add a third flavor later without inventing a
new deployment convention: a new flavor gets the same `k8s/` and
`grafana/` subtree essentially for free, because "how this platform expects
a service to be deployed" is decoupled from "what language the service is
written in."

## Why the CLI is a plain function, not a subprocess-only script

`main(argv: list[str] | None = None) -> int` in `cli.py` takes an argument
list and returns an exit code — it never calls `sys.exit()` internally and
never reaches for global state. That's what let the test suite exercise
every CLI path (`goldpath list`, `goldpath new`, `--no-k8s`, error cases)
by calling `main()` directly and asserting on its return value and captured
output, without spawning a subprocess per test. A scaffolder that's
supposed to model good engineering practice should itself be built in a way
that's fast and easy to test.
