## Plan: Backend E2E Tests

Add a comprehensive e2e test suite to the FastAPI backend using pytest + httpx.AsyncClient + ASGITransport. No external server is started — tests run in-process. Real compositor is used (no mocking). Includes two bug fixes surfaced during planning.

**Phases (5 total)**

1. **Phase 1: Test Infrastructure + Bug Fix**
   - **Objective:** Bootstrap shared fixtures, reset stores between tests, fix broken analytics import
   - **Files/Functions to Modify/Create:**
     - `be/tests/__init__.py` (create)
     - `be/tests/conftest.py` (create)
     - `be/src/services/analytics.py` (fix import: `from models.analytics` → `from src.models.analytics`)
   - **Tests to Write:**
     - Verify `pytest --collect-only` succeeds (no import errors)
   - **Steps:**
     1. Fix broken import in `be/src/services/analytics.py`
     2. Create `be/tests/__init__.py`
     3. Create `be/tests/conftest.py` with fixtures: `app_client`, `reset_stores` (autouse), `avatar_bytes`, `screenshot_bytes`
     4. Run `pytest --collect-only` — confirm no errors
     5. Lint with ruff

2. **Phase 2: Overlay Endpoint Tests**
   - **Objective:** Cover `POST /overlay` — happy path, validation, file size limits, MIME type rejection
   - **Files/Functions to Modify/Create:**
     - `be/tests/test_overlay.py` (create)
     - `be/src/routers/overlay.py` (add explicit 415 rejection for non-image MIME types)
   - **Tests to Write:**
     - `test_overlay_success`
     - `test_overlay_missing_avatar`
     - `test_overlay_missing_screenshot`
     - `test_overlay_avatar_too_large`
     - `test_overlay_screenshot_too_large`
     - `test_overlay_non_image_content_type`
   - **Steps:**
     1. Write tests (they should fail)
     2. Run tests — confirm failure
     3. Add MIME type validation to `be/src/routers/overlay.py`
     4. Run tests — confirm pass
     5. Lint with ruff

3. **Phase 3: Job Status Tests**
   - **Objective:** Cover `GET /jobs/{job_id}` — polling with real compositor (15 s timeout / 0.5 s interval)
   - **Files/Functions to Modify/Create:**
     - `be/tests/test_jobs.py` (create)
   - **Tests to Write:**
     - `test_get_job_pending` — immediately after submit → status is `pending` or `processing`
     - `test_get_job_completed` — poll until `completed`; verify `output_url` ends with `.png`
     - `test_get_job_not_found` — unknown job_id → 404
     - `test_get_job_failed_graceful` — corrupt image bytes → poll until `failed`, no crash
   - **Steps:**
     1. Write tests (they should fail)
     2. Run tests — confirm failure
     3. Write minimal code to pass (polling helper in conftest if needed)
     4. Run tests — confirm pass
     5. Lint with ruff

4. **Phase 4: Save & Stats Tests**
   - **Objective:** Cover `POST /save` and `GET /stats` — validation and aggregation correctness
   - **Files/Functions to Modify/Create:**
     - `be/tests/test_save.py` (create)
     - `be/tests/test_stats.py` (create)
   - **Tests to Write:**
     - `test_save_success`
     - `test_save_rating_too_low`
     - `test_save_rating_too_high`
     - `test_save_negative_processing_time`
     - `test_save_unknown_job_id`
     - `test_stats_empty`
     - `test_stats_aggregation`
   - **Steps:**
     1. Write tests (they should fail)
     2. Run tests — confirm failure
     3. Write minimal code to pass (store state fixes if needed)
     4. Run tests — confirm pass
     5. Lint with ruff

5. **Phase 5: Full E2E Flow Test**
   - **Objective:** One test covering the complete user journey end-to-end with real compositing
   - **Files/Functions to Modify/Create:**
     - `be/tests/test_e2e_flow.py` (create)
   - **Tests to Write:**
     - `test_full_user_journey` — upload avatar1.png + avatar2.png → poll until completed → POST /save rating 5 → GET /stats → assert all values consistent
   - **Steps:**
     1. Write test (it should fail)
     2. Run test — confirm failure
     3. Write minimal code to pass (fix any integration gaps)
     4. Run test — confirm pass
     5. Lint with ruff

**Open Questions (resolved)**
1. Real compositor, no mocking — all job polling tests use 15 s timeout / 0.5 s interval
2. Screenshot fixture reads `test_assets/avatar2.png`; avatar fixture reads `test_assets/avatar1.png`
3. Non-image MIME type → explicit 415 rejection added to `/overlay` router
