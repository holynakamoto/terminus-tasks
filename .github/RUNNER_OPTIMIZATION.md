# Recommended Runner Upgrades for Your Workflow

## Current Performance Analysis

Your workflow is bottlenecked by:
1. **Docker I/O** - building images from scratch every run
2. **LLM API latency** - waiting for GPT-5 / Claude responses
3. **Dependency installation** - repeated uv/harbor installs

## Recommended Third-Party Runners (2026)

### Best Options for Your Use Case:

#### 1. **BuildJet** (Recommended for Docker-heavy workflows)
- **Speed**: 3-5× faster than GitHub standard
- **Why**: NVMe storage + cached layers + better single-core perf
- **Cost**: ~$0.004/min (vs GitHub $0.008/min for standard Linux)
- **Setup**: Just change `runs-on: buildjet-4vcpu-ubuntu-2204`

```yaml
validate-oracle:
  runs-on: buildjet-4vcpu-ubuntu-2204  # 4 vCPU, 16 GB RAM, NVMe
  # Your existing steps unchanged
```

**Expected improvement:**
- Docker builds: 8 min → 2 min
- Oracle/NOP tests: 15 min → 4 min
- **Total savings: ~10-15 min per run**

#### 2. **WarpBuild** (Best cache performance)
- **Speed**: 2-4× faster
- **Why**: Intelligent cross-run caching, including Docker layers
- **Cost**: ~$0.005/min
- **Setup**: `runs-on: warp-ubuntu-latest-x64-4x`

```yaml
validate-difficulty-gpt:
  runs-on: warp-ubuntu-latest-x64-4x
```

**Expected improvement:**
- Cache hits make subsequent runs 70% faster
- First run: ~45 min → ~20 min (with warm cache)

#### 3. **Namespace** (Best for monorepo with many tasks)
- **Speed**: 4-8× faster on first boot, excellent caching
- **Why**: Pre-warmed environments, persistent volumes
- **Cost**: ~$0.006/min but often net cheaper due to speed
- **Setup**: `runs-on: namespace-profile-docker-8vcpu`

### GitHub Larger Runners (If already on Team/Enterprise)

If you're already paying for Team/Enterprise:

```yaml
validate-difficulty-gpt:
  runs-on: ubuntu-latest-8-cores  # 8 vCPU, 32 GB RAM
```

**Cost**: ~$0.064/min (more expensive but 2-3× faster)
**When worth it**: When time-to-feedback is critical

## Quick Cost-Benefit Analysis

### Current costs (GitHub standard runners):
- **PR**: ~30 min × $0.008 = **$0.24 per PR**
- **Main**: ~70 min × $0.008 = **$0.56 per merge**
- **Monthly** (10 PRs + 10 merges): ~**$96**

### With BuildJet 4-vCPU:
- **PR**: ~12 min × $0.004 = **$0.05 per PR** (80% faster, 79% cheaper)
- **Main**: ~25 min × $0.004 = **$0.10 per merge** (64% faster, 82% cheaper)
- **Monthly** (10 PRs + 10 merges): ~**$18** (**81% cost reduction + 5× faster**)

### With pre-built Docker images + BuildJet:
- **PR**: ~5 min × $0.004 = **$0.02 per PR** (94% faster!)
- **Main**: ~15 min × $0.004 = **$0.06 per merge** (79% faster)
- **Monthly**: ~**$9.60** (**90% cost reduction + 7-10× faster feedback**)

## Implementation Priority

### Phase 1 (This week - FREE):
✅ **Done**: Parallel jobs + skip difficulty on PRs
🔲 **Add**: Pre-build Docker images to GHCR (5 min setup, saves 5-10 min/run)
🔲 **Add**: Better Python dependency caching (already started with uv cache)

**Expected result**: 30 min → 15 min PRs, 70 min → 35 min main

### Phase 2 (Next week - paid runners):
🔲 **Try BuildJet** free trial (sign up at buildjet.com)
🔲 **Change** `runs-on:` in 3-4 slowest jobs
🔲 **Benchmark** and compare

**Expected result**: 15 min → 5 min PRs, 35 min → 12 min main

### Phase 3 (Optional - advanced):
🔲 **Custom runner image** with pre-installed harbor/terminal-bench/Docker
🔲 **Self-hosted runner** on AWS c7i.4xlarge with NVMe (if running >1000 builds/month)

## Immediate Next Steps

Want me to:
1. **Implement pre-built Docker image workflow** (free, 50% faster builds)
2. **Add BuildJet runner config** (requires signup but has free tier)
3. **Both** - compound the benefits for maximum speed

The pre-built images alone will cut your Docker overhead from ~8 min to ~30 seconds per task.
