# My Study Goals

This file drives `rank.py` — every course gets scored against it. Be specific
and honest. The model reads the whole thing; a vague answer produces noisy
scores. Bullet points are fine; full sentences are better when nuance matters.

## Career goal

> What do you want to be doing professionally in 3–5 years?
> Be concrete enough that a stranger could tell two paths apart, e.g.
> "ML research scientist at a deep-tech startup, focus on probabilistic
> programming" rather than "tech".

I want to work in quantitative finance, unsure what career path. I am interested in quantitatively modelling something, like macro related stuff would be cool to try and model or work on. Anything a hedge fund does is interesting to me, anything in consulting / investment banking is not. There are multiple paths in the quant world, like at a market maker, quant dev or quant research etc.

Macro quant work would be one that is really interesting to me and i could specialize in.

Derivatives are interesting, but I am not sure if that is what I want to do. However, for a quant, I consider it important to still know the basics, regardless of exact career path.

Most interesting for me would be to work for a couple years on something at a real quant shop, gather experience, and then start my own shop with the experience + other stuff. I am broadly interested in a lot of stuff, and I believe broad interest is important to have, and broad knowledge of many topics.

## Topics I want to go deep on (in priority order)

1. Mathematical finance, all the hard tooling that are provided there related to statistics, maths etc.
2. Probability, and stochastic processes.
3. Statistics and hard tooling that are provided by anything stats related, i haven't had this much
4. Machine learning, priority with the kind that is most important for quants.
5. Econometrics
6. Time series analysis (couple courses)
7. Portfolio maths deep dive, asset pricing.
8. Numerical methods
9. Hardware part of software engineering if available somewhere.
10. One course in networking. 

## Topics I am NOT interested in

1. language courses
2. management / leadership
3. anything super super soft. finance from business school is ok, but nothing softer than that.
4. philosophy of x, agile/project management etc.

## My current level

1. bsc cs, comfortable with all the topics in there
2. most important stuff of maths bsc done, going to go to maths msc
3. bsc finance, continuing with msc in finance, some portion of it done

haven't done too much of
1. statistics
2. econometrics
3. financial maths (yet)
4. time series maths
5. bayesian probability

## Degree(s) and credit budget

What degrees am I working toward, and how many ECTS can Claude
actually choose from? Be specific about each degree: total credits,
what's already locked / done, and how much is still flexible.

- **Aalto MSc Finance** (120 op total). Most of the structure is
  already selected:
  - Elective studies: 41 op (4 done, 3 selected — locked).
  - Thesis: 30 op.
  - Freely chosen (vapaasti valittavat): max 42 op, currently 21 op
    locked-in.
  - **Open for Claude to choose: ~20 op in vapaasti.**

- **HY MSc Mathematics** (120 op total).
  - Thesis: 30 op (separate from coursework).
  - Coursework: 90 op available.
  - Mandatory inside that: Probability Theory I (MAST31701, 5 op) +
    Probability Theory II (MAST31702, 5 op) = 10 op.
  - **Open for Claude to choose: 80 op of HY coursework.**

Total flexible across both degrees: ~100 op of new course choices,
plus 60 op of thesis work.

## Universities I can take courses at

Aalto + HY (University of Helsinki). Both via active SISU study right.
Cross-faculty registration within HY (e.g. MSc Math student taking
ECOM-* courses from MSc Economics) is possible with advisor approval —
assume the advisor will sign off on quant-relevant macro courses.

Cooperation-network courses from other Finnish universities (Hanken,
Jyväskylä, LUT, Tampere, Aalto-Hanken etc.) should be excluded by
default — keep the catalog HY/Aalto-owned only. Surface specific
cooperation-network courses as alternates only if you can't find an
HY/Aalto equivalent for a topic the user explicitly wants.

## Faculties / topic areas to exclude entirely

Auto-exclude (no prompting needed):

- All humanities, theology, law, medicine, dentistry, veterinary,
  pharmacy, biological/environmental sciences, agriculture/forestry,
  educational sciences, language centres, art / design / architecture
- All language courses (Finnish, Swedish, English, German, etc.)
- All bachelor-level intro courses on topics already covered by my BSc
  (basic CS, basic calculus, intro programming)
- All doctoral programmes (I'm an MSc student — DPE-* etc.)
- HY Faculty of Social Sciences sub-programmes EXCEPT MSc Economics
  (philosophy, social research, politics/media, contemporary societies,
  global politics, etc. all out — Economics in)
- Aalto Department of Built Environment / Civil Engineering /
  Energy and Mechanical / Chemistry-Materials / Bioproducts (engineering
  schools whose content doesn't apply to quant)
- Aalto School of Business: Marketing, Accounting, Management Studies
  (keep Finance, Economics, parts of Information & Service Management)

Keep (override defaults):

- HY MSc Mathematics and Statistics (Faculty of Science) — primary
- HY MSc Computer Science / Data Science (Faculty of Science) — for
  applied ML / numerical methods
- HY MSc Economics (within Faculty of Social Sciences) — for the
  ECOM-* macro and econometrics courses
- Aalto School of Science (math, stat, CS, applied physics)
- Aalto School of Business: Department of Finance, Department of
  Economics
- Aalto School of Electrical Engineering (signals, ML, communications,
  one networking course)

## Practical constraints

no constraints except around 24 to 30 ects per period. i want to finish my finance MSC latest at 2028 spring, and maths msc can also be done at 2029 spring or earlier. 

## Anything else the scorer should know

It might pay off to do lots of maths from the msc before doing finance master's thesis. Then my idea is to investigate the same topic or nearby topic in both master's theses: in the university of helsinki one from a more theoretic perspective and in the aalto one more empirical view.

## Door-optimization preference (added 2026-05-16)

Strategy: **broad strong fundamentals now, specialize on the desk.** This is
the standard junior-hire profile for AQR / Two Sigma / DE Shaw / multi-manager
pods (Millennium, Citadel, BAM, Point72) and sell-side strats — strong math +
stats + coding + financial intuition, with the specialty taught in the first
12–18 months. Score for *optionality across many roles*, not depth in one.

Optimize course picks for doors **1–6**, explicitly de-prioritize **7–8**:

1. Systematic macro / rates research — primary strength
2. Buy-side research at multi-strat / quant funds
3. Stat-arb / systematic equity
4. Fixed income / rates quant (sell side)
5. Risk quant
6. Buy-side ML quant / alt data
7. *(de-prioritized)* HFT — closed by absence of demonstrable C++/low-latency
   work, not by coursework; not reachable via an EE degree either (HFT hires
   competitive-programming CS people, not EE PhDs). Out of scope here.
8. *(de-prioritized)* Exotic derivatives — needs more PDE + a PhD. Out of scope.

Concrete consequences applied to the plan (see `course_picks.md`):
- Optimization is the highest-value gap (transcript signal beats self-study;
  hits doors 2/3/5). Convex-opt sequence MAST31036 + MAST31041 added.
- Macro block trimmed 25 → 15 ECTS: keep the transferable methods core
  (ECOM-411/412 — SVAR/state-space/DSGE estimation, doors 1–4) + one
  signature depth course (ECOM-R319). Drop HANK (ECOM-R318) and Money &
  Monetary Policy (ECOM-434) as too narrow / too institutional for industry.
- Stats range extended cheaply: MAST32017 Nonparametric Inference.
- Drop niche / out-of-scope: MAST30142 (energy/commodities), ELEC-C7241
  (networking — was door 10, outside 1–6).
- Networking slot reallocated to causal inference (CS-E407524) for doors 2/3/6.

Not changed and why: macroeconometrics core (411+412), one signature macro
DSGE course (R319), full Bayesian+stats block, both ML courses
(CS-E4825/E4891), stoch-analysis + math-finance chain
(MAST31706/31710/31908), Bayesian filtering (ELEC-E8106) — each earns its
slot for ≥2 of doors 1–6.
