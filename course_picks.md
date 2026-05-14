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
| 28E00900 | Fixed Income | 6 | selected (see note) |
| 28E34600 | Portfolio Management | 6 | done |
| 28E35700 | Capstone: Alternative Investments | 6 | done |
| FIN-E0313 | Advanced Econometrics for Financial Markets | 6 | done |
| TU-E2211 | Financial Risk Management with Derivatives 1 | 5 | done |
| 28L30111 | Theoretical Asset Pricing | 6 | selected |
| FIN.thes | Master's thesis | 30 | — |
| ~~FIN-E0310~~ | ~~Advances in Financial Technology~~ | ~~6~~ | **swap → networking, see below** |
| 28L30211 | Empirical Asset Pricing | 6 | selected (vapaasti) |
| TU-E2221 | Financial Risk Management with Derivatives 2 | 5 | done (vapaasti) |
| TU-E2231 | Machine Learning in Financial Risk Management | 5 | done (vapaasti) |
| ELEC-C7241 | Computer Networks | 5 | **replaces FIN-E0310** — packet switching, TCP/IP, routing, performance evaluation. Your one networking course. |

### Note on Fixed Income (28E00900)

Recommend **keep**. Term-structure modelling is core quant tooling. If swap:
`31E00910` Applied Microeconometrics I (6 ECTS).

### Note on the FIN-E0310 / ELEC-C7241 swap

Net –1 ECTS in vapaasti (6 → 5), giving you 1 ECTS of extra room (max 42).
ELEC-C7241 is the canonical single networking course at Aalto.

### Vapaasti valittavat — 20 ECTS to fill

| Code | Course | ECTS | Why |
|---|---|---|---|
| MAST32007 | Time series analysis I (HY, cross-reg) | 5 | ARMA, weak/strong stationarity, model selection, estimation. |
| ELEC-E8106 | Bayesian Filtering and Smoothing D | 5 | EKF / UKF / particle filters / SMC / MCMC for nonlinear non-Gaussian state-space — toolkit for online estimation and DSGE. |
| CS-E4825 | Probabilistic Machine Learning D | 5 | Mixture models, EM, Bayesian networks, latent linear models, variational inference. |
| CS-E4891 | Deep Generative Models D | 5 | Monte Carlo, divergences, VAEs, deep state-space, diffusion, GANs. Concrete generative-modelling toolkit with quant uses (synthetic market data, scenario generation, score-based stochastic-vol). |

**Aalto vapaasti total: 20 ECTS.**

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

### Quant macro (HY MSc Economics, cross-faculty) — 25 ECTS

| Code | Course | ECTS | Why |
|---|---|---|---|
| ECOM-411 | Applied Macroeconometrics 1 | 5 | VAR / SVAR foundations + DSGE intro. **MSc-level.** |
| ECOM-412 | Applied Macroeconometrics 2 | 5 | DSGE empirical implementation, structural VAR depth, validation of DSGE via VAR. |
| ECOM-R318 | Advanced Macroeconomics 4: Heterogeneous Agent Models | 5 | HANK with applications to taxation, social insurance, pensions. |
| ECOM-R319 | Advanced Macroeconomics 3: Monetary Policy Models | 5 | Monetary-policy DSGEs — central-bank-flavoured macro modelling. |
| ECOM-434 | Money and Monetary Policy | 5 | Institutional / applied side of monetary economics; complements R319's DSGE-flavoured view. |

### Stochastic + applied quant — 5 ECTS

| Code | Course | ECTS | Why |
|---|---|---|---|
| MAST30142 | Stochastic Methods of Energy Markets | 5 | Electricity & gas market modelling, energy-derivative pricing, post-2008 regulatory environment. Applied stochastic finance with a macro/commodities flavour. |

### Math foundations — 5 ECTS

| Code | Course | ECTS | Why |
|---|---|---|---|
| MAST30170 | Functional Analysis I | 5 | Banach/Hilbert/operators. Directly load-bearing for the Stochastic Analysis sequence (martingales in L^2, operator theory for stochastic integration). Addresses the prereq-risk flag from earlier drafts in coursework rather than self-study. |

### Statistics + Bayesian — 25 ECTS

| Code | Course | ECTS | Why |
|---|---|---|---|
| MAT22013 | Statistical inference IIA | 5 | MSc-level estimation/testing theory. |
| MAST32006 | High-dimensional statistics | 5 | FDR, q-values, penalized regression, variable selection — directly applicable to factor models and risk attribution. |
| MAST32001 | Computational statistics | 5 | Numerical methods, density estimation, MC, MCMC, approximate Bayesian inference. |
| MAT22005 | Bayesian inference | 5 | Posteriors, multiparameter models, R + Stan workflow. |
| MAST32004 | Advanced Bayesian Inference | 5 | Marginal likelihood, decision theory, model comparison, CV / info criteria. |

**HY total: 10 + 10 + 5 + 5 + 25 + 5 + 5 + 25 = 90 ECTS.** ✓

---

## Decisions made this round

- **Swapped FIN-E0310 (Advances in Financial Technology, 6) → ELEC-C7241 (Computer Networks, 5)** in Aalto vapaasti — your one networking course.
- **Considered then rejected CS-E4690 Programming Parallel Supercomputers (Aalto, 5)** — covers MPI / distributed-memory HPC. Real value for HFT/market-making engineering and at-scale Monte Carlo, but the actual HFT toolkit (kernel bypass, FPGAs, lock-free C++, microsecond budgets) isn't taught at Aalto anyway. CS-E4580 (already done) covers the higher-leverage multicore + GPU half. The MPI/HPC mental model can be picked up from a book + weekend project at lower cost than 5 ECTS.
- **Dropped MAST31036 + MAST31041 Convex Analysis & Optimization I + II (10 ECTS)** — practical optimization content can be picked up from CVXPY tutorials + Boyd's free EE364A material. Made room for ECOM-434 + MAST30170.
- **Added ECOM-434 Money and Monetary Policy (5)** — institutional / applied complement to ECOM-R319's DSGE-flavoured monetary policy.
- **Added MAST30170 Functional Analysis I (5)** — addresses the prereq risk for the Stochastic Analysis sequence in coursework instead of self-study.
- **Dropped MAST31910 Financial Economics (10 ECTS)** — content (arbitrage pricing, equilibrium, CAPM) heavily overlaps with `28L30111` Theoretical Asset Pricing, `FIN-E0311` Advanced Investments, and the existing FRM Derivatives chain on the Aalto side.
- **Dropped MATR326 Tools of HPC (5)** — materials-science-flavoured, and you've already done Aalto's Programming Parallel Computers. No second HPC needed.
- **Dropped MAST30172 + MAST30173 Partial Differential Equations I + II (10)** — would also require Differentiaaliyhtälöt I + II (10 ECTS ODE prereqs you don't currently have), making it a 20 ECTS commitment to unlock 10 ECTS of PDE. For quant macro and applied quant, PDEs at this depth are not core. Black-Scholes-PDE intuition can be picked up from Shreve / Björk or via the Stochastic Analysis sequence; the heavy PDE machinery is mainly for academic math-finance research.
- **Dropped MAST30132 Real and Fourier Analysis + MAST30170 Functional Analysis I (10)** — both were primarily justified as PDE prereqs. Without PDE, neither is essential. Probability Theory I gives you the measure-theoretic foundations the stochastic analysis sequence needs.
- **Added per your picks**: MAST30142 (Energy Markets), MAST31036/41 (Convex Opt I+II), ECOM-R319 (Monetary Policy DSGEs), MAST32006 (High-Dim Stats), MAST32004 (Adv Bayesian), MAT22013 (Stat Inf IIA).

## Sequencing notes

- **MAST31701 → MAST31702** must come early; everything stochastic depends on them.
- **MAST31702 → MAST31706 → MAST31710** — stochastic analysis sequence after Probability Theory II.
- **MAT22005 → MAST32004 → MAST32001** — Bayesian basics → advanced → computational.
- **MAT22013 → MAST32006** — classical inference before high-dim.
- **ECOM-411 → ECOM-412** — Applied Macroeconometrics 1 is prereq for 2.
- **ECOM-R318 / R319 / R321** — typically run alternating years; check schedule.
- **MAST31036 → MAST31041** — convex optimization I before II.
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
| MAST31036 | Convex analysis and optimization I | 5 | Line-search methods, gradient/Newton/conjugate-gradient/Levenberg-Marquardt. Dropped this round to make room for ECOM-434 + MAST30170. CVXPY tutorials + Boyd's free EE364A material covers the practical need. |
| MAST31041 | Convex analysis and optimization II | 5 | Continuation; same comment. |
| MAST30172 / 30173 | Partial differential equations I / II | 5 + 5 | Only if you invest in academic math-finance research and accept the ODE prereq overhead. |
| MAST30132 | Real and Fourier Analysis | 5 | Add only if FA I + Probability Theory I together don't feel like enough analysis foundation for the stochastic analysis sequence. |
| MAST31802 | Risk theory | 10 | If you want insurance / credit-risk angle (actuarial). |
| MAST31806 | Advanced risk theory | 5 | Lighter follow-on to MAST31802. |
| MAST32017 | Nonparametric Inference | 5 | Distribution-free methods. Borderline for inclusion — your stats block is already 25 ECTS. Add only if you specifically want this content. |
| ECOM-R321 | Advanced Econometrics 3: Macroeconometrics | 5 | Heavy overlap with MAST32008 + ECOM-411 — generally redundant given current plan. |
| ECOM-410 | Applied Macroeconomics | 5 | Lighter quantitative-macro intro; ECOM-411/412 cover the meaty material. |
| MAT12004 | Statistical inference I | 5 | Bachelor-level basics; mostly review for someone with your math BSc. |

## Open issues

- Cross-faculty for ECOM-* (HY MSc Math student in MSc Economics courses) — confirm advisor approval.
- Cross-degree credit for MAST32007 in Aalto vapaasti — confirm Aalto programme coordinator.
- Once locked, write into `schedule.yaml` and run `python schedule.py` for prereq-ordering validation.
