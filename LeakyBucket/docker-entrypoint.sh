#!/bin/sh
set -e

echo "Waiting for Redis to be ready..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "Redis is ready!"

# Set PYTHONPATH to include project root and app directory
export PYTHONPATH="/LeakyBucket:/LeakyBucket/app:$PYTHONPATH"

# Run tests based on environment variable
RUN_TESTS=${RUN_TESTS:-"false"}
TEST_TYPE=${TEST_TYPE:-"all"}

if [ "$RUN_TESTS" = "true" ]; then
    echo "Running tests..."

    cd /LeakyBucket/app

    case "$TEST_TYPE" in
        "unit")
            echo "Running unit tests only..."
            uv run pytest ../tests/unit/ -v --tb=short || true
            ;;
        "integration")
            echo "Running integration tests only..."
            uv run pytest ../tests/integration/ -v --tb=short || true
            ;;
        "security")
            echo "Running security tests only..."
            uv run pytest ../tests/security-abuse/ -v --tb=short || true
            ;;
        "all")
            echo "Running all tests..."
            uv run pytest ../tests/ -v --tb=short || true
            ;;
        *)
            echo "Unknown TEST_TYPE: $TEST_TYPE"
            echo "Available options: unit, integration, security, all"
            exit 1
            ;;
    esac

    # Always continue regardless of test results
    echo "Tests completed. Continuing with application startup..."
else
    echo "Tests skipped (RUN_TESTS=false)"
fi

# Start the application - ALWAYS start regardless of test results
cd /LeakyBucket/app
echo "Starting application..."
exec uv run uvicorn app.main:app --port 8000 --host 0.0.0.0