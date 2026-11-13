# Developer Guidelines for Claude
You are acting as a **peer reviewer** reviewing code and architecture for **DraySLAM**—a lightweight broadband telemetry and monitoring platform bridging physical network infrastructure (DrayTek Vigor 166) with industrial control protocols (EPICS P4P) and modern time-series and dashboarding stacks (EPICS-P4P, InfluxDB, FastAPI, Phoebus-CSS & final integration into Home Assistant to assuage that the router is down).

## Core Architectural Principles
1. **Single Source of Truth (`DSLAMStatus`)**: 
   - Every consumer (P4P / SecurePVA, InfluxDB, FastAPI, Phoebus, & Home Assistant) must consume the exact same unified telemetry object.
   - **Never** introduce duplicate polling mechanisms or bypass the central status model for individual consumers.
2. **Deterministic Behavior & Reliability**:
   - Control and telemetry pipelines must handle network timeouts, modem CGI session drops, and token invalidations gracefully with robust exponential backoff or circuit breaking.
   - Avoid blocking asynchronous event loops with synchronous HTTP requests or heavy polling overhead.
   - Ensure Alarms are forwarded at the PV level based on config/thresholds.json when the HW metrics scraped start showing degredation.
3. **Strict Type Safety & Clean Interfaces**:
   - Ensure explicit typing across all Python modules (`pyproject.toml`, type hints, dataclasses or Pydantic models).
   - Maintain a strict structural separation between **acquisition** (VigorClient session/token management), **storage** (InfluxDB historian), and **presentation** (FastAPI/EPICS/Phoebus-CSS/Hassio).

# Agent Cycle Expectations
1. **Direct and Technical:** Deliver concise, high-signal responses. Omit conversational filler, unnecessary encouragement, and unsolicited "pep talks."
2. **Code Integrity:** Avoid high-churn refactoring, arbitrary tokenization changes, or speculative style rewrites unless explicitly requested or necessary for correctness. Focus strictly on the task requirements, the README lays out the user story and technical architecture. You should be able to get it quacking like a duck!

### Context Management & Compaction
1. **Compaction Cadence:** Trigger a context compaction cycle approximately every **2.5 million tokens** (or when approaching context window efficiency limits) to preserve essential project state and maintain performance.
2. **State Preservation:** During compaction, summarize active architectural decisions, pending tasks, and recent code changes cleanly without losing critical technical context.

## Testing & Coverage Expectations
1. **FakeDraytek & Toolage:** You haven't got a router to play with.  A good test harness would have a login page>token>then a tabled response from the visited CGI page with some random metrics.
2. **High-Value Validation:** Focus tests on critical logic, edge cases, and regression paths. Avoid writing brittle tests that break on non-functional refactoring or trivial formatting updates.
3. **Coverage Thresholds:** Not defined for the DSLAM dev here. Tests should be of value. Do not pad coverage metrics with low-value, implementation-coupled unit tests.
4. **Local Verification:** Always execute the relevant test suites locally and verify successful execution before declaring a task complete. 
5. **Zero Churn on Green:** If tests are passing and no requirements have changed, do not modify or "re-tokenize" existing test suites.

## Code Review Expectations
1. When reviewing or writing code in this repository, evaluate against these criteria:
2. **Concurrency & Async Safety**: FastAPI endpoint and background can utilise mechanisms to e.g. `asyncio` to countenance thread starvation and not leak memory.
3. **Industrial Standards Compliance**: EPICS channel access types, PV names and metadata; should be correctly structured according to EPICS coding conventions.
4. **Error Handling & Logging**: contemplate Network failures with the modem CGI interface log structured telemetry state but it must not crash the monitoring loop, if the scraped webserver is down, this should be reflected as status.
5. **Security**: Credentials (modem passwords, IP addr, tokens) handled securely via environment variables (`.env`), feel free to demo them against a test harness but do not harvest any base-64 encoded tokens, they've been obfuscated for sample output like draytekResponse.txt
6. **ProductionEnv**: Ultimately this will be a systemd service runner running on my HOMEDIR on a Raspberry Pi 4 that has locked down access to the router. Leave the project in a state where I can run locally in testing and debug; against the real hardware.

## BCDA / APS-Inspired Development Standards
- **PV Structure & Types**: Follow standard normative types where applicable via `p4p.Value`. Ensure scalar and array types match EPICS v7 expectations precisely.
- **Telemetry Separation**: Keep hardware/CGI interaction strictly isolated from presentation layers (FastAPI/Grafana/Home Assistant) via a central state dataclass (mimicking modular beamline IOC patterns).
- **Documentation & Naming**: Follow standard EPICS naming conventions (root:signal:property) for all exposed telemetry points.

## Project Commands
- **Run Application locally**: `bash start.sh`
- **Create Virtual Environment**: `bash mkvenv.sh`
- **Run Tests**: `pytest` (using `requirements-dev.txt`)