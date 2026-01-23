# SnorkelAI Support Ticket: cracked256 Task Evaluation Failure

## Summary
Task submission `cracked256` passes all validation in our GitHub Actions CI pipeline (20-minute runtime) but fails in SnorkelAI's CodeBuild environment with S3 "NoSuchKey" errors, indicating builds never started execution.

## Submission Details
- **Task Name**: cracked256
- **Submission Package**: cracked256-snorkel-submission.zip (14KB)
- **Package Contents**: Dockerfile, generate_data.py, task.toml, solution/, tests/
- **Expected Runtime**: 15-20 minutes (oracle + NOP tests pass in our CI)

## Failure Symptoms

### From Provided Logs

**Build 1 (6938dff1)**: ✅ Success (orchestrator)
- Completes in 0.3 seconds
- Output: "Phases found in YAML: 0"
- No actual commands executed
- Interpretation: Setup/orchestration build that queues parallel jobs

**Builds 2-3**: ❌ Connection Closed
- IDs: 9ffa69c9, f00288fd
- Error: "Connection closed"
- Interpretation: Container crashed during initialization

**Builds 4-13**: ❌ NoSuchKey S3 Errors
- IDs: 6f0c9793, ac19a578, f168eebe, b75908b5, 3959ae74, c20b984e, ceac9589, 74a0b05e, 4196f062, 32125162
- Error: "NoSuchKey when calling GetObject"
- Interpretation: Builds failed before writing logs to S3 (never started execution)

### Pattern Analysis
- **Total builds**: 13 (likely 1 orchestrator + 5 GPT evals + 5 Claude evals + 2 infrastructure)
- **Success rate**: 1/13 (orchestrator only)
- **Critical failure**: 12 builds never executed, suggesting Docker image access/build failure

## Our CI Pipeline (Working)

### GitHub Actions Configuration
```yaml
- Docker registry: ghcr.io (GitHub Container Registry)
- Authentication: GitHub token (automatic)
- Image strategy: Pull pre-built OR build from Dockerfile
- Build timeout: 27 minutes (task.toml: build_timeout_sec = 1600)
- Runtime timeout: 15 minutes (900 seconds for oracle test)
- Result: ✅ All tests pass
```

### Image Availability
- **Public GHCR Image**: `ghcr.io/holynakamoto/terminus-tasks/task-cracked256:main`
- **Visibility**: Public (no authentication required)
- **Build cache**: Also public at `:buildcache` tag

### Dockerfile Build Process
```dockerfile
FROM python:3.11.11-slim
WORKDIR /app
COPY generate_data.py /app/generate_data.py
RUN python3 /app/generate_data.py && rm /app/generate_data.py
CMD ["tail", "-f", "/dev/null"]
```

**Build characteristics**:
- Base image: python:3.11.11-slim (~150MB)
- Build-time data generation: ~30 seconds
- Generates password hashes (PBKDF2, max 10,000 iterations)
- Total build time: ~2-3 minutes
- Final image size: ~180MB

## Questions for SnorkelAI

### 1. Docker Image Strategy
**Q**: How does CodeBuild access task Docker images?
- Does it pull from GHCR automatically?
- Does it authenticate to public registries?
- Should we provide images via AWS ECR instead?
- Or does it build from Dockerfile in the submission package?

**Our hypothesis**: CodeBuild cannot access our GHCR images (authentication issue or network restriction) and cannot build from Dockerfile (timeout or configuration issue).

### 2. Build Timeout Configuration
**Q**: How is `task.toml`'s `build_timeout_sec` interpreted?
```toml
[environment]
build_timeout_sec = 1600.0  # 27 minutes
cpus = 1
memory_mb = 4096
storage_mb = 10240
```

- Does this apply to Docker build phase?
- Does this apply to the entire CodeBuild job?
- What's the actual timeout before CodeBuild terminates?

**Our concern**: If CodeBuild tries to build from Dockerfile but has a shorter timeout than 1600 seconds, it might terminate before `generate_data.py` completes.

### 3. S3 NoSuchKey Error Root Cause
**Q**: What causes "NoSuchKey" errors in build logs?

The error pattern suggests builds failed at container initialization, before any commands could execute or logs could be written to S3.

Possible causes:
- Docker image pull failure (GHCR authentication)
- Docker image build failure (timeout during `generate_data.py`)
- Container resource exhaustion (13 parallel builds overwhelming available resources)
- Buildspec configuration error (no commands defined?)

**Request**: Can you provide CloudWatch logs or build metadata for these failed builds?
- Build IDs: 9ffa69c9, f00288fd, 6f0c9793, ac19a578, etc.
- Container initialization logs
- Docker pull/build logs
- Any error messages before S3 log upload

### 4. Buildspec Investigation
**Q**: What commands are defined in the buildspec.yml?

The successful orchestrator build shows:
```
Phases found in YAML: 0
```

This suggests no build phases are defined, which is unusual. In our GitHub Actions workflow, we explicitly:
```bash
# Build or pull Docker image
docker pull ghcr.io/holynakamoto/terminus-tasks/task-cracked256:main || \
  docker build -t task-cracked256 environment/

# Run solution and tests in container
docker run --rm -v solution:/solution -v tests:/tests task-cracked256 \
  bash -c 'bash /solution/solve.sh && pytest /tests/test_outputs.py'
```

**Request**: Can you share what's in the buildspec.yml used for evaluations? We need to understand what commands CodeBuild is attempting to execute.

### 5. Successful Reference Example
**Q**: Can you provide a reference submission that successfully evaluated?

We need to see:
- How the task package was structured
- Whether Dockerfile was included or images were pre-provided
- What a successful build log looks like
- Expected evaluation time and resource usage

This would help us understand the expected format and identify what's different about our submission.

### 6. Parallel Execution Limits
**Q**: Are there resource limits on parallel builds?

With 13 concurrent builds (5 GPT-5 evals + 5 Claude evals + infrastructure):
- Each requires 4GB RAM (per task.toml)
- Each requires Docker image (180MB)
- Total RAM needed: ~52GB

**Concern**: If CodeBuild has resource limits, parallel execution might fail due to memory exhaustion or rate limiting.

## Diagnostic Data

### Task Characteristics
- **Difficulty**: Hard
- **Category**: Security (password cracking)
- **Oracle runtime**: 8-12 minutes (PBKDF2 iterations)
- **CI_FAST_MODE**: Supported (reduces iterations for testing)
- **Dependencies**: Python 3.11, hashlib (stdlib only)

### Resource Requirements
```toml
cpus = 1
memory_mb = 4096
storage_mb = 10240
```

### Submission Package Structure
```
cracked256-snorkel-submission.zip (14KB)
└── cracked256/
    ├── environment/
    │   ├── Dockerfile
    │   └── generate_data.py
    ├── solution/
    │   └── solve.sh
    ├── tests/
    │   ├── test_outputs.py
    │   └── test.sh
    └── task.toml
```

### Alternative Approach: Pre-built Images

If CodeBuild cannot build from Dockerfile efficiently, we can provide:

1. **Public GHCR images** (already available):
   - `ghcr.io/holynakamoto/terminus-tasks/task-cracked256:main`
   - No authentication required
   - Updated automatically on push to main branch

2. **AWS ECR images** (if needed):
   - We can push to a public ECR repository
   - Specify ECR URI in task metadata

3. **Docker Hub images** (if needed):
   - Alternative public registry
   - Lower rate limits than GHCR

**Question**: Which registry does SnorkelAI's CodeBuild prefer?

## Comparison: Our Pipeline vs SnorkelAI

| Aspect | GitHub Actions (Working) | SnorkelAI CodeBuild (Failing) |
|--------|-------------------------|-------------------------------|
| **Image Source** | GHCR with GitHub token auth | Unknown |
| **Image Availability** | Public (no auth required) | Unknown if accessible |
| **Build Strategy** | Pull pre-built OR build locally | Unknown |
| **Build Timeout** | 27 minutes (task.toml) | Unknown |
| **Runtime Timeout** | 15 minutes (900s) | 30 minutes (task.toml) |
| **Parallel Jobs** | 2-3 (oracle, nop, static) | 13 (5+5+3) |
| **Resource Allocation** | 7GB RAM per runner | Unknown per build |
| **Log Storage** | GitHub artifacts (inline) | S3 (async, fails if build crashes) |
| **Result** | ✅ All tests pass | ❌ NoSuchKey errors |

## Requested Information from SnorkelAI

Please provide:

1. ✅ **CloudWatch logs** for failed builds (9ffa69c9, f00288fd, 6f0c9793, etc.)
2. ✅ **Buildspec.yml contents** - What commands are executed?
3. ✅ **Docker strategy** - Pull from registry or build from Dockerfile?
4. ✅ **Registry access** - Can CodeBuild pull from public GHCR?
5. ✅ **Resource limits** - Limits on parallel builds, memory, CPU?
6. ✅ **Timeout configuration** - How is task.toml's build_timeout_sec applied?
7. ✅ **Example successful submission** - Reference task package that works
8. ✅ **Error details** - Any error messages before "NoSuchKey"?

## Next Steps

### If Issue is Image Access:
1. Verify SnorkelAI can pull: `ghcr.io/holynakamoto/terminus-tasks/task-cracked256:main`
2. Alternative: Push to AWS ECR or Docker Hub
3. Alternative: Include pre-built image in submission (if format allows)

### If Issue is Build Timeout:
1. Increase CodeBuild timeout to match task.toml (1600 seconds)
2. Optimize generate_data.py (already minimal: ~30 seconds)
3. Use pre-built images instead of building

### If Issue is Resource Limits:
1. Reduce parallel execution (fewer concurrent evals)
2. Increase per-build resource allocation
3. Add retry logic for transient failures

## Contact Information
- **GitHub Repository**: holynakamoto/terminus-tasks
- **Task Path**: tasks/cracked256/
- **CI Logs**: https://github.com/holynakamoto/terminus-tasks/actions
- **Public Image**: ghcr.io/holynakamoto/terminus-tasks/task-cracked256:main

## Appendix: Full Build Logs from SnorkelAI

```
=== Build CodeExecutionEnvironment:6938dff1-ccd2-4c20-a106-761bffeaab39 ===
[Container] 2026/01/22 23:28:03.574404 Running on CodeBuild On-demand
[Container] 2026/01/22 23:28:03.574422 Waiting for agent ping
[Container] 2026/01/22 23:28:03.776060 Waiting for DOWNLOAD_SOURCE
[Container] 2026/01/22 23:28:04.994410 Phase is DOWNLOAD_SOURCE
[Container] 2026/01/22 23:28:04.995752 CODEBUILD_SRC_DIR=/codebuild/output/src3805077359/src
[Container] 2026/01/22 23:28:04.996422 YAML location is /codebuild/readonly/buildspec.yml
[Container] 2026/01/22 23:28:04.999203 Setting HTTP client timeout to higher timeout for S3 source
[Container] 2026/01/22 23:28:04.999303 Processing environment variables
[Container] 2026/01/22 23:28:05.005414 Setting HTTP client timeout to higher timeout for S3 source
[Container] 2026/01/22 23:28:05.078681 Setting HTTP client timeout to higher timeout for S3 source
[Container] 2026/01/22 23:28:05.130090 Setting HTTP client timeout to higher timeout for S3 source
[Container] 2026/01/22 23:28:05.186805 Setting HTTP client timeout to higher timeout for S3 source
[Container] 2026/01/22 23:28:05.477481 No runtime version selected in buildspec.
[Container] 2026/01/22 23:28:05.534534 Moving to directory /codebuild/output/src3805077359/src
[Container] 2026/01/22 23:28:05.534559 Cache is not defined in the buildspec
[Container] 2026/01/22 23:28:05.582244 Skip cache due to: no paths specified to be cached
[Container] 2026/01/22 23:28:05.582568 Registering with agent
[Container] 2026/01/22 23:28:05.624116 Phases found in YAML: 0
[Container] 2026/01/22 23:28:05.624614 Phase complete: DOWNLOAD_SOURCE State: SUCCEEDED
[Container] 2026/01/22 23:28:05.624626 Phase context status code:  Message:
[Container] 2026/01/22 23:28:05.741880 Entering phase INSTALL
[Container] 2026/01/22 23:28:05.779523 Phase complete: INSTALL State: SUCCEEDED
[Container] 2026/01/22 23:28:05.779541 Phase context status code:  Message:
[Container] 2026/01/22 23:28:05.817129 Entering phase PRE_BUILD
[Container] 2026/01/22 23:28:05.818624 Phase complete: PRE_BUILD State: SUCCEEDED
[Container] 2026/01/22 23:28:05.818639 Phase context status code:  Message:
[Container] 2026/01/22 23:28:05.856065 Entering phase BUILD
[Container] 2026/01/22 23:28:05.857833 Phase complete: BUILD State: SUCCEEDED
[Container] 2026/01/22 23:28:05.857848 Phase context status code:  Message:
[Container] 2026/01/22 23:28:05.896003 Entering phase POST_BUILD
[Container] 2026/01/22 23:28:05.897948 Phase complete: POST_BUILD State: SUCCEEDED
[Container] 2026/01/22 23:28:05.897961 Phase context status code:  Message:
[Container] 2026/01/22 23:28:05.950236 Set report auto-discover timeout to 5 seconds
[Container] 2026/01/22 23:28:05.950274 Expanding base directory path:  .
[Container] 2026/01/22 23:28:05.953436 Assembling file list
[Container] 2026/01/22 23:28:05.953452 Expanding .
[Container] 2026/01/22 23:28:05.956683 Expanding file paths for base directory .
[Container] 2026/01/22 23:28:05.956699 Assembling file list
[Container] 2026/01/22 23:28:05.956703 Expanding **/*
[Container] 2026/01/22 23:28:05.960116 No matching auto-discover report paths found
[Container] 2026/01/22 23:28:05.960134 Report auto-discover file discovery took 0.009898 seconds
[Container] 2026/01/22 23:28:05.960145 Phase complete: UPLOAD_ARTIFACTS State: SUCCEEDED
[Container] 2026/01/22 23:28:05.960153 Phase context status code:  Message:

=== Build CodeExecutionEnvironment:9ffa69c9-64a9-4e3f-a4aa-69827a99725f ===
Error retrieving logs: Connection closed.

=== Build CodeExecutionEnvironment:f00288fd-dd25-4909-8989-04804aafcfe6 ===
Error retrieving logs: Connection closed.

=== Build CodeExecutionEnvironment:6f0c9793-bfdb-4a5b-a257-be018e804967 ===
Error retrieving logs: An error occurred (NoSuchKey) when calling the GetObject operation: The specified key does not exist.

[... 9 more NoSuchKey errors ...]
```

---

Thank you for investigating this issue. We believe the root cause is Docker image access/build failure, and providing CloudWatch logs or buildspec details would help us confirm and resolve this quickly.
