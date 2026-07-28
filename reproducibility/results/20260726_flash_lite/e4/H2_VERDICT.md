# H2 Verdict (E4)

Condition (16): C_check^S < (ρ0 − ρ1) · C_rerun^L

## humaneval

- ρ0 (P[rerun needed w/o small check])     = **0.3500**
- ρ1 (P[rerun needed w/  small check])     = **0.0000**
- C_check^S (mean small-check cost, USD)   = **$0.000060**
- C_rerun^L (mean large rerun cost, USD)   = **$0.010822**
- Expected savings (ρ0−ρ1)·C_rerun^L       = **$0.003788**
- Net economic margin per task             = **$0.003728**
- Bootstrap 95% CI for net margin          = [$0.002042, $0.007685]
- Lower CI > 0 ⇒ H2 confirmed on this dataset: **True**

## swebench_lite

- ρ0 (P[rerun needed w/o small check])     = **0.7500**
- ρ1 (P[rerun needed w/  small check])     = **0.6000**
- C_check^S (mean small-check cost, USD)   = **$0.000122**
- C_rerun^L (mean large rerun cost, USD)   = **$0.014469**
- Expected savings (ρ0−ρ1)·C_rerun^L       = **$0.002170**
- Net economic margin per task             = **$0.002048**
- Bootstrap 95% CI for net margin          = [$-0.000104, $0.004650]
- Lower CI > 0 ⇒ H2 confirmed on this dataset: **False**


## Decision

**H2: NOT CONFIRMED**
