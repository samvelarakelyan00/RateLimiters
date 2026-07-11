#!/bin/sh
set -e

echo "Waiting for Redis to be ready..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "Redis is ready!"

export PYTHONPATH="/LeakyBucket:/LeakyBucket/app:$PYTHONPATH"

RUN_TESTS=${RUN_TESTS:-"false"}
TEST_TYPE=${TEST_TYPE:-"all"}

if [ "$RUN_TESTS" = "true" ]; then
    echo "Running tests..."
    cd /LeakyBucket/app

    # Initialize counters
    TOTAL_TESTS=0
    TOTAL_PASSED=0
    TOTAL_FAILED=0
    TOTAL_XFAILED=0
    TOTAL_ERRORS=0

    # Function to parse pytest output and extract results (BusyBox compatible)
    parse_test_results() {
        local output="$1"

        # Extract numbers using grep with basic regex (no -P)
        # BusyBox grep uses -E for extended regex, but we'll use basic regex
        local passed=$(echo "$output" | grep -oE '[0-9]+ passed' | tail -1 | grep -oE '[0-9]+')
        local failed=$(echo "$output" | grep -oE '[0-9]+ failed' | tail -1 | grep -oE '[0-9]+')
        local xfailed=$(echo "$output" | grep -oE '[0-9]+ xfailed' | tail -1 | grep -oE '[0-9]+')
        local errors=$(echo "$output" | grep -oE '[0-9]+ errors' | tail -1 | grep -oE '[0-9]+')

        # Default to 0 if not found
        passed=${passed:-0}
        failed=${failed:-0}
        xfailed=${xfailed:-0}
        errors=${errors:-0}

        TOTAL_PASSED=$((TOTAL_PASSED + passed))
        TOTAL_FAILED=$((TOTAL_FAILED + failed))
        TOTAL_XFAILED=$((TOTAL_XFAILED + xfailed))
        TOTAL_ERRORS=$((TOTAL_ERRORS + errors))

        # Count total tests in this group
        local group_total=$((passed + failed + xfailed + errors))
        TOTAL_TESTS=$((TOTAL_TESTS + group_total))
    }

    case "$TEST_TYPE" in
        "unit")
            echo "=== UNIT TESTS ==="
            output=$(uv run pytest ../tests/unit/ -v --tb=short 2>&1 || true)
            echo "$output"
            parse_test_results "$output"
            ;;
        "integration")
            echo "=== INTEGRATION TESTS ==="
            output=$(uv run pytest ../tests/integration/ -v --tb=short 2>&1 || true)
            echo "$output"
            parse_test_results "$output"
            ;;
        "security")
            echo "=== SECURITY TESTS ==="
            output=$(uv run pytest ../tests/security-abuse/ -v --tb=short 2>&1 || true)
            echo "$output"
            parse_test_results "$output"
            ;;
        "concurrency")
            echo "=== CONCURRENCY TESTS ==="
            output=$(uv run pytest ../tests/concurrency/ -v --tb=short 2>&1 || true)
            echo "$output"
            parse_test_results "$output"
            ;;
        "all")
            echo "Running all tests in isolated groups..."

            # Run each test group separately
            echo ""
            echo "=== UNIT TESTS ==="
            output=$(uv run pytest ../tests/unit/ -v --tb=short 2>&1 || true)
            echo "$output"
            parse_test_results "$output"

            echo ""
            echo "=== INTEGRATION TESTS ==="
            output=$(uv run pytest ../tests/integration/ -v --tb=short 2>&1 || true)
            echo "$output"
            parse_test_results "$output"

            echo ""
            echo "=== SECURITY TESTS ==="
            output=$(uv run pytest ../tests/security-abuse/ -v --tb=short 2>&1 || true)
            echo "$output"
            parse_test_results "$output"

            echo ""
            echo "=== CONCURRENCY TESTS ==="
            output=$(uv run pytest ../tests/concurrency/ -v --tb=short 2>&1 || true)
            echo "$output"
            parse_test_results "$output"
            ;;
        *)
            echo "Unknown TEST_TYPE: $TEST_TYPE"
            exit 1
            ;;
    esac

    # Display final summary
    echo ""
    echo "========================================"
    echo "          TEST SUMMARY"
    echo "========================================"
    echo "Total Tests:  $TOTAL_TESTS"
    echo "Passed:       $TOTAL_PASSED"
    echo "Failed:       $TOTAL_FAILED"
    echo "XFailed:      $TOTAL_XFAILED"
    echo "Errors:       $TOTAL_ERRORS"
    echo "----------------------------------------"
    if [ $TOTAL_FAILED -eq 0 ] && [ $TOTAL_ERRORS -eq 0 ]; then
        echo "✅ ALL TESTS PASSED!"
    else
        echo "❌ Some tests failed!"
    fi
    echo "========================================"
    echo ""

    echo "Tests completed. Continuing with application startup..."
else
    echo "Tests skipped (RUN_TESTS=false)"
fi

cd /LeakyBucket/app
echo "Starting application..."
exec uv run uvicorn app.main:app --port 8000 --host 0.0.0.0