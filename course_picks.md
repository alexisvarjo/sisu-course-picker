# Course Picks — HY Math MSc + Aalto Finance MSc

Selection rationale anchored in course `content`/`outcomes` (not names).
Target: quant career with leaning toward quant-macro modelling.

Catalog: `data/courses_filtered.jsonl` (re-crawled with 18-month staleness
and broadened code-prefix queries; filtered to HY + Aalto only,
relevant faculties only, doctoral programmes excluded).

---

## Aalto MSc Finance

### Locked plan (per current SISU)

| Code | Course | ECTS | Status |
|---|---|---|---|
| FIN-E0311 | Advanced Investments | 6 | selected |
| ~~28E00900~~ | ~~Fixed Income~~ | ~~6~~ | **dropped — overlap with MAST31908 + BSc fixed income + FRM Derivatives chain** |
| 28E34600 | Portfolio Management | 6 | done |
| 28E35700 | Capstone: Alternative Investments | 6 | done |
| FIN-E0313 | Advanced Econometrics for Financial Markets | 6 | done |
| TU-E2211 | Financial Risk Management with Derivatives 1 | 5 | done |
| 28L30111 | Theoretical Asset Pricing | 6 | selected |
| 28L30211 | Empirical Asset Pricing | 6 | **moved from vapaasti to elective studies** — replaces 28E00900 in the elective-studies bucket, keeping it at 41 op |
| FIN.thes | Master's thesis | 30 | — |
| ~~FIN-E0310~~ | ~~Advances in Financial Technology~~ | ~~6~~ | **dropped — see below** |
| TU-E2221 | Financial Risk Management with Derivatives 2 | 5 | done (vapaasti) |
| TU-E2231 | Machine Learning in Financial Risk Management | 5 | done (vapaasti) |
| ~~ELEC-C7241~~ | ~~Computer Networks~~ | ~~5~~ | **dropped (doors 1–6 pass)** — opens no door 1–6; your CS BSc already covers most of it. Replaced by CS-E407524. |
| CS-E407524 | Special Course in ML/DS/AI D: Causal Inference | 5 | **replaces ELEC-C7241** in vapaasti — Pearl DAGs, do-calculus, counterfactuals. Zero overlap with HY convex-opt; strengthens doors 2/3/6 (factor/alt-data/experimentation). |

### Note on dropping 28E00900 Fixed Income

Substantial overlap with what you already have:
- **MAST31908 Quantitative finance** (HY): "Mathematical models of interest-rate
  instruments and derivatives" — covers the math-finance side of fixed income.
- **BSc fixed income & derivatives module** — practitioner side.
- **TU-E2211 + TU-E2221** FRM Derivatives 1 & 2 (done) — interest-rate
  derivatives angle.
- **MAST31710 Stochastic analysis II** — SDE foundation for term-structure /
  HJM-type models.

Marginal value of 28E00900 on top of all that is small. Replaced in the
elective-studies bucket by 28L30211 (moved from vapaasti).

### Note on the vapaasti networking → causal-inference swap

The doors 1–6 pass de-prioritizes networking entirely (it was door 10 in
`goals.md`, explicitly outside the 1–6 set). FIN-E0310 was dropped; the slot
went briefly to ELEC-C7241 (networking) and is now reallocated to **CS-E407524
Causal Inference**.

Why not an Aalto optimization course in this slot: the HY side already gets the
full convex-opt sequence (MAST31036 + MAST31041). Aalto's MS-E2122 Nonlinear
Optimization overlaps heavily with MAST31041 (convex sets, duality, KKT); the
more differentiated MS-E2160 (Stochastic & Robust Optimization) requires
MS-E2121/MS-E2122 as a prereq — a two-course chain there's no room for. Causal
inference is the cleaner non-redundant addition for doors 2/3/6.

Vapaasti stays at 40 ECTS (ELEC-C7241 –5, CS-E407524 +5), under the 42 cap.
**Caveat:** CS-E407524 is a *Special Course* (3–5 op) and runs irregularly —
confirm it's offered in 2027–2028 before locking; fallback is to absorb the
–5 ECTS as thesis-ramp breathing room (vapaasti → 35, still legal).

### Vapaasti valittavat — 25 ECTS to fill

| Code | Course | ECTS | Why |
|---|---|---|---|
| MAST32007 | Time series analysis I (HY, cross-reg) | 5 | ARMA, weak/strong stationarity, model selection, estimation. |
| ELEC-E8106 | Bayesian Filtering and Smoothing D | 5 | EKF / UKF / particle filters / SMC / MCMC for nonlinear non-Gaussian state-space — toolkit for online estimation and DSGE. |
| CS-E4825 | Probabilistic Machine Learning D | 5 | Mixture models, EM, Bayesian networks, latent linear models, variational inference. |
| CS-E4891 | Deep Generative Models D | 5 | Monte Carlo, divergences, VAEs, deep state-space, diffusion, GANs. Concrete generative-modelling toolkit (synthetic market data, scenario generation, score-based stochastic-vol). |
| MS-C1350 | Partial Differential Equations (Aalto) | 5 | Laplace / heat / wave equations, separation of variables, Fourier techniques. Bachelor-level applied PDE — no ODE-prereq overhead like HY's MAST30172/3. Direct payoff for MAST31710 (SDE → PDE bridge via Itô formula) and MAST31908 (interest-rate models). |

**Aalto vapaasti new picks: 25 ECTS.** Combined with locked/swapped vapaasti
(CS-E407524 causal inference + TU-E2221 done + TU-E2231 done = 15) → vapaasti
total **40 ECTS**, under max 42.

---

## HY MSc Mathematics — 90 ECTS

### Mandatory probability — 10 ECTS

| Code | Course | ECTS | Why |
|---|---|---|---|
| MAST31701 | Probability theory I | 5 | Measure-theoretic foundations of probability, independence, LLN, characteristic functions, CLT, Gaussian measures, recurrence/transience of random walks. |
| MAST31702 | Probability theory II | 5 | Discrete-time Markov chains, Poisson process, conditional expectation, martingales. |

### Stochastic analysis (Itô calculus) — 10 ECTS

| Code | Course | ECTS | Why |
|---|---|---|---|
| MAST31706 | Stochastic analysis I | 5 | Stochastic integration with respect to martingales and processes with finite variation; continuous martingales and processes with jumps. The Itô calculus course. |
| MAST31710 | Stochastic analysis II | 5 | Stochastic differential equations and applications. |

### Mathematical finance — 5 ECTS

| Code | Course | ECTS | Why |
|---|---|---|---|
| MAST31908 | Quantitative finance | 5 | Mathematical models of interest-rate instruments and derivatives. |

### Time series — 5 ECTS

| Code | Course | ECTS | Why |
|---|---|---|---|
| MAST32008 | Time series analysis II | 5 | Multivariate VAR; specification, estimation, evaluation, hypothesis testing, forecasting. (TS I is in Aalto vapaasti.) |

### Quant macro (HY MSc Economics, cross-faculty) — 15 ECTS

Shrunk 25 → 15 in the doors 1–6 pass. Kept the methodologically transferable
core (411 + 412 — SVAR / state-space / DSGE estimation, useful across doors
1–4) and one signature macro-depth course (R319) so door 1 still reads as
"theory, not just methods". Dropped ECOM-R318 (HANK — narrowest course for
industry; appears almost only in central-bank research) and ECOM-434 (Money &
Monetary Policy — institutional/textbook, no methodological firepower).

| Code | Course | ECTS | Why |
|---|---|---|---|
| ECOM-411 | Applied Macroeconometrics 1 | 5 | VAR / SVAR foundations + DSGE intro. **MSc-level.** Transfers to factor regime / rates models (doors 1–4). |
| ECOM-412 | Applied Macroeconometrics 2 | 5 | DSGE empirical implementation, structural VAR depth, validation of DSGE via VAR. |
| ECOM-R319 | Advanced Macroeconomics 3: Monetary Policy Models | 5 | Monetary-policy DSGEs — the single signature macro-depth course; without it door 1 weakens to "methods, not theory". |

### Optimization — 10 ECTS  *(new in doors 1–6 pass)*

The single biggest gap in the prior plan. Optimization is the one technical
area where a transcript line reads materially stronger than self-study, and it
touches doors 2/3/5 directly (portfolio construction, factor-model fitting,
risk parity, mean-variance under constraints). Replaces the dropped MAST30142
(Stochastic Methods of Energy Markets — commodities-specific, an exotic
specialization counter to the broad-optionality goal).

| Code | Course | ECTS | Why |
|---|---|---|---|
| MAST31036 | Convex analysis and optimization I | 5 | Line-search, 1D Newton/secant, gradient/Newton/conjugate-gradient, Levenberg–Marquardt, least-squares / Kaczmarz, NN applications. The numerical-methods half. |
| MAST31041 | Convex analysis and optimization II | 5 | Convex sets, separating/supporting hyperplanes, conjugate functions, LP/QP, geometric programming, **Lagrange duality, KKT, sensitivity** — the machinery you'd actually deploy. Needs MAST31036. |

### Math foundations — 5 ECTS

| Code | Course | ECTS | Why |
|---|---|---|---|
| MAST30170 | Functional Analysis I | 5 | Banach/Hilbert/operators. Directly load-bearing for the Stochastic Analysis sequence (martingales in L^2, operator theory for stochastic integration). Addresses the prereq-risk flag from earlier drafts in coursework rather than self-study. |

### Statistics + Bayesian — 30 ECTS

Extended +5 in the doors 1–6 pass with MAST32017 — cheap range extension
(rank/sign methods, distribution-free inference) that increases robustness
across doors 2/3/5/6, especially for alt-data / messy-distribution work.

| Code | Course | ECTS | Why |
|---|---|---|---|
| MAT22013 | Statistical inference IIA | 5 | MSc-level estimation/testing theory. |
| MAST32006 | High-dimensional statistics | 5 | FDR, q-values, penalized regression, variable selection — directly applicable to factor models and risk attribution. |
| MAST32001 | Computational statistics | 5 | Numerical methods, density estimation, MC, MCMC, approximate Bayesian inference. |
| MAT22005 | Bayesian inference | 5 | Posteriors, multiparameter models, R + Stan workflow. |
| MAST32004 | Advanced Bayesian Inference | 5 | Marginal likelihood, decision theory, model comparison, CV / info criteria. Underpins DSGE-style model comparison (doors 1, 6). |
| MAST32017 | Nonparametric Inference | 5 | Sign/rank estimates, Hodges–Lehmann, distribution-free CIs/tests, nonparametric ANOVA alternatives. Robustness layer for doors 2/3/5/6. |

**HY total: 10 + 10 + 5 + 5 + 15 + 10 + 5 + 30 = 90 ECTS.** ✓
(prob 10 · stoch 10 · math-fin 5 · TS 5 · macro 15 · optimization 10 ·
math-foundations 5 · stats+Bayesian 30)

---

## Sequencing notes

- **MAST31701 → MAST31702** must come early; everything stochastic depends on them.
- **MAST31702 → MAST31706 → MAST31710** — stochastic analysis sequence after Probability Theory II.
- **MAT22005 → MAST32004 → MAST32001** — Bayesian basics → advanced → computational.
- **MAT22013 → MAST32006** — classical inference before high-dim.
- **ECOM-411 → ECOM-412** — Applied Macroeconometrics 1 is prereq for 2.
- **ECOM-R319** — Advanced Macro courses typically run alternating years; check schedule.
- **MAST31036 → MAST31041** — convex optimization I before II (formal sequence prereq).
- **MAST31908** — usable after Probability Theory II + a bit of Stochastic Analysis I.

## Risk flag (largely addressed)

The Stochastic Analysis sequence (MAST31706 / MAST31710) leans on
functional-analytic machinery (L^2 martingales, operator theory). MAST30170
(Functional Analysis I) is now in the plan to cover this. Real Analysis +
Fourier (MAST30132) is *not* — characteristic functions and Fourier
material from Probability Theory I + the L^p material from FA I should
suffice. If MAST31706 still feels rough mid-course, self-studying Folland
or Kreyszig chapters on L^p spaces and Sobolev embeddings is the lighter
cover for what's missing.

## Alternates / swap pool

| Code | Course | ECTS | When you'd add it |
|---|---|---|---|
| MAST30132 | Real and Fourier Analysis | 5 | Add only if FA I + Probability Theory I together don't feel like enough analysis foundation for the stochastic analysis sequence. |
| ECOM-R318 | Adv Macro 4: Heterogeneous Agent Models | 5 | Dropped (doors 1–6 pass). Re-add only for a central-bank-research lean (door 7-ish), which this pass de-prioritizes. |
| ECOM-434 | Money and Monetary Policy | 5 | Dropped. Institutional/textbook; if needed later, Walsh or Galí over a weekend covers the relevant parts. |
| MAST30142 | Stochastic Methods of Energy Markets | 5 | Dropped. Re-add only for a real CTA/energy/commodities seat interest. |
| MS-E2160 | Stochastic Programming & Robust Optimization (Aalto) | 5 | Robust portfolio optimization. Needs MS-E2121/MS-E2122 first — only worth it if you add the Aalto opt chain. |

## Open issues

- Cross-faculty for ECOM-* (HY MSc Math student in MSc Economics courses) — confirm advisor approval.
- Cross-degree credit for MAST32007 in Aalto vapaasti — confirm Aalto programme coordinator.

## Schedule

Period-by-period plan written to `schedule.yaml` and validated:

```
2026-2027/I    27 cr  MAST31701, MAST30170, ECOM-411, FIN-E0311, 28L30111
2026-2027/II   26 cr  MAST31702, ECOM-412, CS-E4891, MAST32007, 28L30211
2026-2027/III  25 cr  MAST31706, MAST32006, MAST32008, MAST31036, MAT22005
2026-2027/IV   30 cr  MAST31710, ECOM-R319, MAST32004, MAST32001, MAT22013, MS-C1350
2027-2028/I    23 cr  MAST31908, MAST31041, MAST32017, CS-E407524, ELEC-E8106
                      (CS-E407524 is 3–5 op variable; validator counts min=3)
2027-2028/II    5 cr  CS-E4825                                    (light period; thesis ramps up)
2027-2028/III  thesis (Aalto FIN.thes — handled at programme level)
2027-2028/IV   thesis defence — Aalto MSc Finance complete
2028-2029/I    HY thesis writing
2028-2029/II   30 cr  MAST31000  (HY MSc Math thesis defence)
```

Period I/II of 2026–2027 are autumn-loaded with the two Aalto Asset
Pricing courses (28L30111 in I, 28L30211 in II — both autumn-only).
Spring IV is at the 30-cr ceiling because MS-C1350 lands there to support
the Stoch Anal II → SDE→PDE bridge. Math-finance chain
(MAST31701 → 31702 → 31706 → 31710 → 31908) and Bayesian chain
(MAT22005 → MAST32004) sequence correctly.

**Convex-opt placement (doors 1–6 pass):** MAST31036 takes the slot
ECOM-R318 vacated in 2026-2027/III; MAST31041 lands in 2027-2028/I (after
31036 — sequence prereq satisfied). The earlier-draft ask was "both before
period IV of 2026–2027"; that's infeasible without breaching the 30-cr cap
(periods I/II/IV of 2026–2027 are already at 27/26/30). 2027-2028/I is still
before any thesis period (earliest is Aalto FIN.thes in 2027-2028/III), so
the "apply the optimization machinery in the thesis if relevant" rationale
still holds. **Verification still owed:** confirm MAST31036/31041 actually
run in those terms against the live SISU teaching calendar — the catalog
carries validity periods only (`activityPeriods` is null), so this can't be
checked from `data/`.

`python schedule.py --schedule schedule.yaml --catalog data/courses.jsonl
--transcript data/transcript.json` reports **plan is consistent, no prereq
ordering violations**. The math-finance chain (MAST31701 → MAST31702 →
MAST31706 → MAST31710 → MAST31908) and the macroeconometrics chain
(ECOM-411 → ECOM-412) sequence correctly across periods.

### Catalog gotcha worth knowing

When you re-crawl the catalog later, `28L30111` and `28L30211` (Aalto
Theoretical / Empirical Asset Pricing) need `--staleness-cutoff none` to
survive — they have empty `activityPeriods` in the SISU API response and
the default staleness filter drops them silently. The current
`data/courses.jsonl` has them included from a targeted re-fetch.
