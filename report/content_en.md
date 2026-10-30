---
title: Explainable Machine Learning-Based Nowcasting of Fog and Low Visibility at Ankara Esenboğa Airport
authors: Ata Sakik
abstract: Fog is the main meteorological cause of delays, diversions and cancellations at Ankara Esenboğa International Airport (LTAC), where more than half of all fog observations require CAT II/III approach procedures. This study presents the first machine-learning nowcasting system for low visibility at LTAC. Using 21.8 years (2005–2026) of quality-controlled METAR/SPECI reports, fog (prevailing visibility below 1000 m) and ILS-oriented runway visual range categories are predicted 1, 3 and 6 h ahead from 77 predictors that describe the current state, tendencies, boundary-layer memory and the solar cycle. Logistic regression, random forest, XGBoost, LightGBM and multi-task GRU/LSTM networks were trained chronologically, calibrated and verified on four independent fog seasons (2022–2026) against persistence, climatology and the official METAR TREND forecast. All models significantly outperform persistence at every lead time: the best critical success index is 0.73, 0.47 and 0.34 at 1, 3 and 6 h, compared with 0.65, 0.32 and 0.13 for persistence, and at 1 h LightGBM exceeds the TREND forecast by 0.105 (95% confidence interval 0.075–0.140). Gradient boosting is best at 1 h, whereas recurrent networks give the highest probabilistic skill at 3–6 h. SHAP analysis reveals a physically consistent shift from the current humidity and visibility state at 1 h to boundary-layer moisture memory and the time to sunrise at 6 h. The calibrated models are deployed in an open-source web application that issues tiered warnings, explains every forecast and verifies itself in real time.
keywords: Aviation meteorology, explainable artificial intelligence, fog, gradient boosting, low-visibility procedures, nowcasting, recurrent neural networks, runway visual range.
footnote: This manuscript was prepared as the term project of the YMH453 Machine Learning course, Department of Software Engineering, Ankara University, in the 2026–2027 fall semester. The data set, source code, trained models and web application are openly available at https://github.com/AtaSakik/esenboga-fog-nowcasting.
 A. Sakik is a fourth-year undergraduate student with the Department of Software Engineering, Ankara University, Ankara, Türkiye (student no. 25290085; e-mail: atasakik0077@hotmail.com).
header: YMH453 MACHINE LEARNING — TERM PROJECT, ANKARA UNIVERSITY, 2026
bio: Ata Sakik|is a fourth-year undergraduate student in Software Engineering at Ankara University, Ankara, Türkiye. Research interests include machine learning, explainable artificial intelligence and their application to aviation meteorology and operational forecasting systems.
---
# Introduction

Fog reduces the horizontal visibility near the ground below 1000 m and is one of the most disruptive weather phenomena for aviation [@gultepe2007; @haeffelin2010]. When visibility or runway visual range (RVR) falls below the minima of the available instrument landing system (ILS) category, an airport must activate low-visibility procedures, reduce its arrival rate or close, which propagates delays, diversions and cancellations through the network [@dalmau2025]. Ankara Esenboğa International Airport (LTAC), the main gateway of the Turkish capital, is particularly exposed: about 89% of its fogs occur between October and February, most of them reduce RVR below 350 m and roughly three quarters are radiation fogs [@camalan2010]; for 2011–2020 about 800 fog hours were recorded and a single episode in December 2019 lasted almost three days [@koyuncu2022].

Despite this operational relevance, the published work on Esenboğa is climatological and synoptic. Çamalan et al. [@camalan2010] analysed 2000–2009 observations and explicitly recommended the development of fog prediction models, and Koyuncu et al. [@koyuncu2022] combined a decadal analysis with a synoptic case study. To the best of our knowledge, no machine-learning (ML) forecast of fog or low visibility has been developed for LTAC. Internationally, statistical and ML nowcasts of fog and low-visibility-procedure states have shown clear skill over persistence at airports such as Vienna [@kneringer2019; @dietz2019a; @dietz2019b] and in many other locations [@alves2025; @salcedo2025], but few studies compare data-driven forecasts with the official aerodrome forecasts under an identical information horizon, and few explain what the models have learnt in physical terms.

This study closes these gaps for LTAC. Its contributions are:

1) a 21.8-year quality-controlled METAR/SPECI data set (2005–2026) whose fog statistics reproduce the published climatology of the airport, released openly together with all code;

2) a benchmark of six model families—logistic regression, random forest, XGBoost, LightGBM, GRU and LSTM—for fog and ILS-category forecasts at 1, 3 and 6 h, with probability calibration, a class-imbalance ablation and day-block bootstrap significance tests against persistence, climatology and the official METAR TREND (and the TAF in an operational window);

3) an ordinal formulation of the RVR/ILS-category forecast and a dedicated analysis of fog onsets and dissipations, the events that matter most for operations;

4) a SHAP-based explanation that connects the learnt relationships to fog physics and shows how the dominant predictors change with lead time; and

5) an open-source web-based early-warning application that runs the identical pipeline on live METARs, issues tiered warnings with explanations and verifies its own forecasts in real time.

The remainder of the paper is organised as follows. Section II reviews related work, Section III describes the airport and the data, Section IV the methodology, Section V the results, and Section VI discusses implications and limitations; Section VII concludes.

# Related Work

## Fog Physics and Esenboğa

Fog forms when the near-surface air becomes saturated through radiative cooling, advection of moist air or moistening by evaporation, and dissipates through solar heating, mixing or drying [@gultepe2007]. Field campaigns such as ParisFog showed that the life cycle of radiation fog is controlled by a delicate balance of radiative cooling, turbulence, aerosols and surface moisture [@haeffelin2010], which explains why numerical weather prediction still struggles with fog [@gultepe2007; @herman2016]. At Esenboğa, Çamalan et al. [@camalan2010] found that radiation fog accounts for 75% of the fog days of 2000–2009 and that most fog observations fall into the CAT III range (RVR < 350 m), and Koyuncu et al. [@koyuncu2022] related a prolonged December 2019 event to a persistent anticyclone and a strong low-level inversion.

## Statistical and Machine-Learning Nowcasting at Airports

Early data-driven approaches used artificial neural networks for fog at Canberra [@fabbian2007], for ceiling and visibility at US airports [@marzban2007] and for probabilistic visibility forecasts [@bremnes2007]. Herman and Schumacher [@herman2016] post-processed reforecasts to improve fog and visibility guidance for aviation. For Vienna International Airport, Kneringer et al. [@kneringer2019] nowcast ordered low-visibility-procedure states with ordered logistic regression up to 2 h ahead, and Dietz et al. showed that tree-based models [@dietz2019a] and boosting [@dietz2019b] improve such forecasts for different planning horizons. Guijo-Rubio et al. [@guijo2018] treated fog-induced low visibility as an ordinal classification problem, and Castillo-Botón et al. [@castillo2022] compared regression and classification formulations of many ML methods. Deep learning approaches range from deep networks for airport visibility [@zhu2017] and climatological visibility forecasting [@ortega2023] to the three-dimensional convolutional FogNet [@kamangir2021]. Recent reviews [@alves2025; @salcedo2025] confirm the potential of these methods but highlight inconsistent verification practices, rare comparisons with official forecasts and the limited transferability of models between sites [@cerda2025].

## Explainable AI and Forecast Verification

Explainability is essential for the acceptance of ML forecasts by forecasters [@mcgovern2019]. SHAP values [@lundberg2017] provide additive, locally accurate attributions that can be computed exactly for tree ensembles [@lundberg2020]. Aerodrome forecasts are verified with categorical scores derived from contingency tables [@jolliffe2012; @wilks2019]; because TAFs and TRENDs contain change groups, they are best interpreted as ranges of forecast conditions [@mahringer2008]. The present study combines these strands—calibrated ML, ordinal ILS categories, explicit comparison with the official forecasts and SHAP explanations—in a single, operationally deployed system for an airport that had no data-driven fog forecast.

# Study Area and Data

## Esenboğa Airport and Its Fog Climate

Ankara Esenboğa International Airport (40.13° N, 32.99° E) lies on a plateau about 28 km north-east of the city centre at an elevation of 953 m. Its continental climate combines long winter nights, frequent anticyclonic stagnation, snow cover and moist boundary layers after frontal precipitation—conditions that favour radiative cooling and fog [@camalan2010; @koyuncu2022]. Fig. @fig:clim summarises the fog climate in the data set used here. Fog is almost exclusively a cold-season phenomenon: 94.6% of all half-hourly observations with a prevailing visibility below 1000 m fall between October and February, with frequencies of 4.3% in December and 3.7% in January and practically none from June to September. Within the day, fog is most frequent around sunrise (08 LT, 2.8%) and least frequent at 15 LT. The 819.5 fog hours we count for 2011–2020 agree closely with the approximately 800 h reported for that decade by Koyuncu et al. [@koyuncu2022], and the share of fog observations with RVR ≤ 350 m (55.5%) confirms the finding of Çamalan et al. [@camalan2010] that most fogs require CAT III operations. The 537 fog episodes are short—median 2 h—but the 90th percentile reaches 9 h and the longest lasted 35.5 h, so the operational problem is dominated by the timing of onsets and dissipations. The annual number of fog hours has decreased markedly: from about 130 h per year in 2005–2012 to about 50 h per year in 2020–2025.

![page](climatology.png){#fig:clim} Fog climate of LTAC, 2005–2026 (prevailing visibility < 1000 m). (a) Annual number of fog hours; the shaded decade 2011–2020 is the period analysed by Koyuncu et al. (b) Monthly frequency of fog in the half-hourly observations. (c) Frequency by month and local hour (UTC+3).

## Observations and Official Forecasts

The study uses the routine half-hourly METARs (issued at HH:20 and HH:50 UTC) and special SPECI reports of January 2005–October 2026. Original report texts were retrieved from the Iowa Environmental Mesonet (IEM) [@iem]. Older IEM holdings also contain reports reconstructed from the NCEI Integrated Surface Database; as these lack RVR and TREND groups and carry visibility in statute-mile steps, they were discarded and the resulting gaps were filled with original texts from the Ogimet archive [@ogimet]. Every METAR includes the forecaster's 2-h TREND forecast (NOSIG, BECMG or TEMPO groups), which serves as the official very-short-range forecast. Terminal aerodrome forecasts (TAFs; 24-h validity, issued four times a day) are available from the NOAA Aviation Weather Center data service [@awc] for the most recent 30 days only, because the historical TAF archive could not be accessed reliably; they are therefore evaluated in the operational period.

All reports were decoded with a purpose-built WMO FM 15/FM 51 decoder [@wmo306] that extracts prevailing and minimum visibility, the RVR of every runway, present and recent weather, cloud layers and vertical visibility, temperature, dew point, QNH and the TREND/TAF change groups; it also repairs frequent keying errors (e.g., "NO SIG", "Q1 015"). Quality control removed NIL and malformed reports, applied physical range checks and a dew-point consistency check, and removed isolated spikes in temperature, dew point and pressure. Table @tab:data summarises the resulting data set.

{{table:data_summary|col}}{#tab:data}

## Analysis Grid and Predictands

The reports were mapped onto a regular 30-min grid aligned with the routine observation times. The state at grid time $t$ is the latest report issued within $(t-29\,\mathrm{min},\,t]$, so SPECIs between routine times are honoured but no value is ever interpolated or carried forward; 99.7% of the 382 607 grid slots contain an observation.

Two predictands are defined at the valid time $t+h$ for lead times $h \in \{1, 3, 6\}$ h. The binary fog event is a prevailing visibility below 1000 m, the ICAO/WMO fog threshold [@icao_annex3]. The ILS category is an ordinal variable based on the minimum RVR reported over all runways: class 0 for RVR ≥ 550 m (CAT I or better), class 1 for 350 ≤ RVR < 550 m (CAT II) and class 2 for RVR < 350 m (CAT III). These boundaries follow the categories used for LTAC by Çamalan et al. [@camalan2010] and the ICAO guidance on all-weather operations and RVR reporting [@icao_doc9365; @icao_doc9328]; current CAT II minima allow RVR down to 300 m, so the 350-m boundary is slightly conservative. RVR is reported only when visibility or RVR is below 1500 m; slots without an RVR group and with visibility ≥ 1500 m are therefore class 0, and in the 0.06% of low-visibility slots with a missing RVR the prevailing visibility is used as a conservative proxy.

# Methodology

Fig. @fig:arch shows the data flow from the archives to the verified forecasts and to the operational application.

![page](architecture.png){#fig:arch} Data flow of the study and of the operational early-warning application. The web application reuses the decoder, quality control, feature pipeline and calibrated models of the offline study, which guarantees identical offline and online forecasts.

## Problem Formulation

For every grid time $t$ with an observation, a model $f_h$ estimates the probability

$$ p_{h}(t)=P\left(y(t+h)=1\mid \mathbf{x}(t)\right) $$ {#eq:prob}

where $\mathbf{x}(t)$ is a feature vector computed exclusively from reports issued at or before $t$. Warnings are issued when $p_{h}(t)$ exceeds a threshold $\tau_{h}$. The ILS category is forecast with the ordinal decomposition of Frank and Hall [@frank2001]: two binary models estimate $P_{550}=P(\mathrm{RVR}<550\,\mathrm{m})$ and $P_{350}=P(\mathrm{RVR}<350\,\mathrm{m})$, from which the class probabilities $1-P_{550}$, $P_{550}-P_{350}$ and $P_{350}$ follow, with $P_{350}\le P_{550}$ enforced.

## Feature Engineering

The 77 predictors are summarised by group in Table @tab:feat. They describe (i) the current state—visibility, RVR, temperature $T$, dew point $T_{d}$, dew-point depression $T-T_{d}$, relative humidity from the Magnus formula [@alduchov1996], wind components, a calm flag, QNH, ceiling, cloud base and cover; (ii) present weather (fog, shallow or patchy fog, mist, haze, drizzle, rain, snow); (iii) 1-, 3- and 6-h tendencies, in particular the nocturnal cooling and the drying or moistening of the surface layer; (iv) memory terms such as the cooling since the 12-h temperature maximum, the fractions of fog, mist, precipitation and snow over the previous 6–72 h and the time since the last fog; and (v) calendar and astronomical terms, including the solar elevation and the time to sunrise at both the issue and the valid time, computed with the NOAA solar-position equations [@spencer1971]. The valid-time astronomical terms are deterministic and therefore legitimately known in advance.

{{table:features|col}}{#tab:feat}

## Models

Logistic regression (LR) with standardised, median-imputed inputs [@cox1958] is the statistical baseline. Random forests (RF) [@breiman2001] and the gradient-boosting libraries XGBoost [@chen2016] and LightGBM [@ke2017] represent tree ensembles; both boosting libraries handle missing values natively, and their hyper-parameters were tuned with 30 trials of the tree-structured Parzen estimator in Optuna [@akiba2019], maximising the validation PR-AUC with early stopping. RF and LR used small validation grids. Temporal patterns are learnt by recurrent networks with long short-term memory (LSTM) [@hochreiter1997] and gated recurrent units (GRU) [@cho2014]. One multi-task network reads the last 12 h (24 grid steps) of 22 standardised state variables plus a presence mask, concatenates its final hidden state with memory and valid-time features, and predicts all nine tasks (three targets × three lead times) through a two-layer head. The masked, positively re-weighted binary cross-entropy was minimised with AdamW [@loshchilov2019] and early stopping on the mean validation PR-AUC, and six architectures were compared on the validation seasons. All models were implemented with scikit-learn [@pedregosa2011] and PyTorch [@paszke2019]; the selected settings are listed in the Appendix.

## Class Imbalance and Calibration

Fog occupies only 1.0% of the observations and RVR < 350 m only 0.6%. Four strategies were compared for LR and LightGBM [@he2009]: no correction, class weighting, SMOTE oversampling [@chawla2002] and random undersampling. Because re-weighting and resampling distort predicted probabilities, every model is recalibrated with either no mapping, Platt scaling [@platt1999] or isotonic regression [@zadrozny2002]; the method is selected by leave-one-season-out cross-validation of the Brier score within the validation seasons [@niculescu2005] and then refitted on the whole validation set. The warning threshold $\tau_{h}$ maximises the critical success index (CSI) on the validation set; since $F_{1}=2\,\mathrm{CSI}/(1+\mathrm{CSI})$, the same threshold also maximises $F_{1}$.

## Training Protocol and Leakage Control

The data were split chronologically and season-aligned (Table @tab:split): training 01/2005–06/2019, validation 07/2019–06/2022 (three fog seasons) and test 07/2022–06/2026 (four fog seasons); the period from July 2026 onwards is reserved for the operational evaluation. A random split would leak information because consecutive half-hourly samples of one fog episode are nearly identical [@kaufman2012]. All tuning, calibration and threshold decisions used the validation seasons only, and the test seasons were evaluated once. Automated tests verify that every feature at time $t$ is unchanged when all reports after $t$ are deleted and that a target never re-uses the observation at $t$.

{{table:splits|col}}{#tab:split}

## Reference Forecasts

Persistence forecasts the currently observed state for $t+h$. Climatology is the conditional event frequency for the calendar month and UTC hour of the valid time in the training period and is the reference of the Brier skill score. The TREND appended to the METAR issued at $t$ is evaluated for $h \le 2$ h, and the TAF forecast for $t+h$ is taken from the latest TAF issued at or before $t$, so that the forecaster's information horizon equals that of the models. TREND and TAF contain change groups and are therefore converted into a visibility range at the valid time [@mahringer2008]: the prevailing reading uses the base forecast, FM groups and completed BECMG changes, and the worst-case reading additionally takes the lower end of BECMG transitions and of TEMPO and PROB30/40 groups. A fog forecast is issued when the reading is below 1000 m.

## Verification

With $a$ hits, $b$ false alarms, $c$ misses and $d$ correct negatives, the categorical scores are [@jolliffe2012; @wilks2019]

$$ \mathrm{POD}=\frac{a}{a+c},\quad \mathrm{FAR}=\frac{b}{a+b},\quad \mathrm{CSI}=\frac{a}{a+b+c} $$ {#eq:pod}

$$ \mathrm{HSS}=\frac{2(ad-bc)}{(a+c)(c+d)+(a+b)(b+d)} $$ {#eq:hss}

where the Heidke skill score (HSS) measures accuracy relative to random chance [@heidke1926; @doswell1990]. Probabilistic forecasts are assessed with the area under the precision–recall curve (PR-AUC), which is informative for rare events [@saito2015; @davis2006], the area under the ROC curve, and the Brier score and its skill score [@brier1950; @murphy1973]

$$ \mathrm{BS}=\frac{1}{N}\sum_{i=1}^{N}(p_{i}-o_{i})^{2},\qquad \mathrm{BSS}=1-\frac{\mathrm{BS}}{\mathrm{BS}_{\mathrm{clim}}} $$ {#eq:bs}

For the ILS categories the ranked probability score [@epstein1969]

$$ \mathrm{RPS}=\frac{1}{K-1}\sum_{k=1}^{K}\left(F_{k}-O_{k}\right)^{2} $$ {#eq:rps}

with cumulative forecast and observed distributions $F_{k}$ and $O_{k}$ ($K=3$) is averaged over the test set and expressed as a skill score (RPSS) against the month–hour class climatology. Because half-hourly samples are strongly autocorrelated, 95% confidence intervals are obtained with a block bootstrap that resamples whole days [@kunsch1989; @wilks1997], and differences between forecasts are tested with paired resamples of the same days (2000 resamples for the categorical scores and 300 for PR-AUC and BSS).

## Explainability

The LightGBM models are explained with SHAP values [@lundberg2017], computed exactly for trees with TreeSHAP [@lundberg2020]. For a forecast with log-odds $g(\mathbf{x})$ the contributions $\phi_{j}$ satisfy local accuracy,

$$ g(\mathbf{x})=\phi_{0}+\sum_{j=1}^{M}\phi_{j} $$ {#eq:shap}

where $\phi_{0}$ is the expected model output and $\phi_{j}$ is the Shapley value of feature $j$ [@shapley1953]. Global importance is summarised by the mean absolute SHAP value on a test sample containing all fog cases and 6000 random non-fog cases, and dependence plots relate the contributions to the physical drivers of fog [@mcgovern2019].

## Early-Warning Application

The operational system is a FastAPI web application (Fig. @fig:app). Every ten minutes it downloads the METARs of the last 7 days from the NOAA Aviation Weather Center (with IEM as fallback), runs exactly the same decoding, quality-control, gridding and feature code as the offline study, and publishes calibrated fog probabilities for 1–6 h, an ILS-category outlook for 1, 3 and 6 h, an alert level and the leading SHAP contributions. Because TreeSHAP values are additive, the 77 contributions are also summed into ten plain-language factor groups (e.g., humidity, wind, time of day) so that non-specialist users can read the explanation. The alert is red when fog is observed or the 1–2-h probability exceeds its threshold, orange when only the 3–6-h forecasts exceed their thresholds, and yellow (watch) when any probability exceeds half of its threshold. Every forecast is stored and automatically verified once its valid time has passed, which provides a genuinely real-time verification record. A serverless public instance runs the same cycle every 30 min on GitHub Actions and publishes the dashboard at https://atasakik.github.io/esenboga-fog-nowcasting/. Because the GitHub scheduler often delays or skips runs, each run also computes the forecasts for the issue times skipped during roughly the previous three days from the reports observed up to those times (including any later corrections), each with its full 96-h feature history; these catch-up forecasts are verified like the others but reported separately from the real-time record.

# Results

## Overall Skill

Table @tab:main lists the scores of all forecasts on the four test seasons. At 1 h all ML models clearly outperform persistence; LightGBM attains the best CSI (0.729) and HSS (0.842) and a Brier skill score of 0.739, against a CSI of 0.652 for persistence. The margin grows with lead time: at 3 h the best CSI is 0.472 (LSTM) against 0.321 for persistence, and at 6 h 0.340 (LSTM) against 0.129. Persistence even becomes worse than climatology at 3 and 6 h (negative BSS), whereas all ML models keep a BSS between 0.26 and 0.32 at 6 h. The ROC areas exceed 0.98 for every model because of the many easy non-fog cases, so the PR curves in Fig. @fig:pr are the more informative view: at 1 h the six models are nearly indistinguishable, while at 3 and 6 h the recurrent networks dominate a large part of the curve and achieve the highest PR-AUC (GRU: 0.685 and 0.517).

{{table:main_results|page}}{#tab:main}

![page](pr_curves.png){#fig:pr} Precision–recall curves of the fog forecasts on the test seasons (PR-AUC in brackets). Markers show the deterministic reference forecasts.

The day-block bootstrap (Table @tab:ci) confirms that the improvements are robust: the paired CSI and HSS differences between each of the six models and persistence are significantly positive at all three lead times—for LightGBM, for example, ΔCSI = 0.077 [0.052, 0.104] at 1 h, 0.146 [0.105, 0.188] at 3 h and 0.168 [0.099, 0.234] at 6 h. The skill decays smoothly with lead time (Fig. @fig:lead), and the relative CSI gain of LightGBM over persistence increases from 12% at 1 h to 45% at 3 h and 130% at 6 h. The improvement is not limited to a favourable year: every model beats persistence in each of the four test seasons and at every lead time (Table @tab:season).

{{table:bootstrap_ci|col}}{#tab:ci}

{{table:per_season|col}}{#tab:season}

![col](leadtime.png){#fig:lead} CSI and HSS of LightGBM and persistence as a function of lead time on the test seasons, with the METAR TREND forecast at 1 h. Shading: 95% day-block bootstrap intervals computed at 1, 3 and 6 h (interpolated in between).

## Comparison with the Official TREND and TAF

The TREND forecast is available for every test METAR. On identical cases (Table @tab:trend), the prevailing reading of the TREND reaches CSI 0.623 and HSS 0.767 at 1 h and the worst-case reading 0.622 and 0.765, slightly below persistence (0.652 and 0.788). In other words, the official 2-h forecast rarely adds information beyond the current observation: TREND groups most often announce improvements, while new fog formation is seldom anticipated. LightGBM improves on the TREND by ΔCSI = 0.105 [0.075, 0.140] and ΔHSS = 0.076 [0.053, 0.103], both significant. In the 30-day TAF window available at the time of writing (29 September–30 October 2026; about 1 420 forecasts per lead time), no fog occurred; neither the TAF—under either reading—nor LightGBM issued a fog forecast, so both were free of false alarms, while the worst-case TAF reading announced mist below 5 km in about 8% of the cases. A fog-season TAF comparison is therefore left to the live verification.

{{table:trend|col}}{#tab:trend}

## Fog Onsets and Dissipations

Onsets and dissipations are where a nowcast creates operational value, because persistence cannot predict either. Fig. @fig:onset shows the fraction of the 48 test-season onsets (fog after at least 2 h without fog) and 44 dissipations that were correctly forecast. Dissipations are captured well: at 1 h XGBoost forecasts 45% of them correctly (persistence: 0%), and at 6 h the GRU reaches 86% (persistence: 68%). Onsets remain the hardest problem: at the CSI-optimal thresholds the models capture 2–21% of the onsets, compared with 0–4% for persistence. The tiered alert design mitigates this limitation: at the watch level ($\tau_{h}/2$) LightGBM flags 25%, 21% and 38% of the onsets 1, 3 and 6 h ahead, while the CSI decreases only from 0.729 to 0.692, from 0.467 to 0.435 and from 0.297 to 0.271.

![col](onset_dissipation.png){#fig:onset} Fraction of fog onsets (left) and dissipations (right) in the test seasons that were correctly forecast at the CSI-optimal thresholds.

## ILS-Category Forecasts

Table @tab:rvr and Fig. @fig:rvr summarise the ordinal RVR forecasts. All ML models achieve a positive ranked probability skill score at every lead time—0.636 (LightGBM) at 1 h, 0.407 (XGBoost) at 3 h and 0.281 (LSTM) at 6 h—whereas persistence falls from 0.427 to −0.166 and −0.695. For CAT III conditions (RVR < 350 m) LightGBM reaches CSI 0.578 at 1 h and the GRU 0.371 at 3 h (persistence: 0.521 and 0.225). The confusion matrices show that CAT III is recognised well (76% of the cases at 1 h), whereas the intermediate CAT II class is the most difficult, being frequently confused with its neighbours; this is expected for a narrow transitional band of RVR.

{{table:rvr|col}}{#tab:rvr}

![page](rvr_confusion.png){#fig:rvr} Confusion matrices of the LightGBM ILS-category forecasts on the test seasons (counts and row-normalised fractions).

## Class Imbalance and Calibration

The imbalance ablation (Table @tab:imb) shows that class weighting, SMOTE and undersampling do not improve the ranking quality reliably—for LR they even lower the validation PR-AUC from 0.759 to 0.720–0.747—but they severely degrade the raw probabilities: class weighting increases the validation Brier score of LR tenfold (from 0.0026 to 0.0261). Recalibration removes most of this damage, but the simplest option, no resampling followed by calibration, is as good as or better than the alternatives; it was therefore used for all final models. The reliability curves of the calibrated forecasts follow the diagonal closely at all lead times (Fig. @fig:rel). This is not trivial: the fog frequency of the test seasons (0.64%) is only half that of the training period (1.24%), and calibrating on the most recent seasons adapted the probabilities to this change.

{{table:imbalance|col}}{#tab:imb}

![col](reliability.png){#fig:rel} Reliability diagram of the calibrated LightGBM (solid) and GRU (dashed) fog forecasts on the test seasons; bins with fewer than 15 forecasts are omitted.

## Explainability

The SHAP analysis reveals a physically coherent picture. At 1 h the forecast is dominated by the current state—relative humidity, minimum and prevailing visibility and dew-point depression (Fig. @fig:shapbar)—which together carry 78% of the total attribution (Fig. @fig:groups). As the lead time increases, the share of the current state falls to 41% at 6 h, while the astronomical and calendar terms rise from 6% to 28% and boundary-layer memory from 6% to 21%.

![page](shap_bar.png){#fig:shapbar} Mean absolute SHAP values of the fifteen most important predictors of the LightGBM fog models at 1, 3 and 6 h.

![col](shap_groups.png){#fig:groups} Share of the total mean absolute SHAP value per predictor group and lead time.

At 6 h the 6-h maximum relative humidity, the relative humidity, the dew-point depression and the temperature lead the ranking, followed by the time since sunrise at the valid time, the night length and the time to sunrise (Fig. @fig:bee): high humidity, small dew-point depressions, low temperatures and long nights push the forecast towards fog, whereas valid times after sunrise push it away—the signature of radiation fog.

![col](shap_beeswarm_6h.png){#fig:bee} SHAP values of the twelve most important predictors of the 6-h model; colour shows the percentile rank of the predictor value.

The dependence plots (Fig. @fig:dep) reproduce textbook fog physics: dew-point depressions of 2 °C or less raise the log-odds by up to +1.4, whereas depressions of 4 °C or more lower them; calm and light winds (≤ 3 kt) favour fog, while winds of 4–10 kt suppress it through mechanical mixing; a 6-h maximum relative humidity above about 93% strongly favours fog; and once the sun is more than about 15° above the horizon at the valid time the contribution turns negative, reflecting dissipation by solar heating.

![page](shap_dependence.png){#fig:dep} SHAP dependence of the 3-h fog model on the dew-point depression, wind speed, solar elevation at the valid time and 6-h maximum relative humidity, coloured by an interacting variable.

## Case Study: 17–18 December 2022

Fig. @fig:case shows a two-stage episode from the test period. Fog persisted until about 10 UTC on 17 December, cleared during the afternoon and formed again at 16:50 UTC, lasting until 03:50 UTC on 18 December with RVR mostly between 200 and 400 m. At 16:20 UTC, when the visibility was still 1200 m, the 3-h model issued a fog probability of 0.82 (threshold 0.33), i.e., a correct warning for the re-formation. Its SHAP explanation (Fig. @fig:local) attributes the forecast to the falling minimum visibility (+1.74), the RVR of 650 m (+0.96), the dew-point depression of 1 °C (+0.88) and a relative humidity of 93% (+0.88)—exactly the cues an experienced forecaster would use. The 1-h forecasts track the episode closely, and the 3- and 6-h forecasts raise the probability during the evening and anticipate the persistence of the fog through the night; after sunrise all lead times correctly forecast the dissipation, with the longer lead times reacting later.

![page](case_study.png){#fig:case} Observed visibility and RVR at LTAC on 17–18 December 2022 with the LightGBM fog probabilities issued 1, 3 and 6 h before each valid time.

![col](shap_waterfall.png){#fig:local} SHAP explanation of the 3-h forecast issued at 16:20 UTC on 17 December 2022 (visibility 1200 m; fog formed 30 min later).

## Operational Performance

The deployed application (Fig. @fig:app) was verified in two ways. First, a replay of the operational period after the test set (July–October 2026) through the web-application code yielded 5 727–5 737 forecasts per lead time (Table @tab:live); no fog occurred in this warm-season period and the system issued no fog warning at any lead time, i.e., it produced no false alarms. Second, a parity check rebuilt the features at 40 random times from only the reports observed up to that time, exactly as the live system does, and reproduced the batch probabilities to machine precision (maximum difference 0.0 over 240 comparisons). The live logger started on 29 October 2026, at the beginning of the 2026/27 fog season, and its automatically verified record is updated continuously during the semester.

![col](app_screenshot.png){#fig:app} The web-based early-warning application. Left: plain-language status over a runway scene drawn from the observed visibility, and the fog probabilities for the next 6 h against their warning thresholds. Right: the driving factors of the selected hour (SHAP values summed into plain-language groups) and the ILS-category outlook.

{{table:live|col}}{#tab:live}

# Discussion

The results show that a purely observation-based nowcast can add substantial skill to both persistence and the official TREND at Esenboğa. Three aspects deserve emphasis. First, the best model depends on the lead time: at 1 h the tree ensembles, which exploit sharp thresholds in the current state, are best, whereas at 3–6 h the recurrent networks extract more from the 12-h history and achieve the best probabilistic scores. An operational system could therefore combine boosting at the shortest lead times with recurrent networks beyond 2 h. Second, the SHAP analysis confirms that the models learn the physics of radiation fog—saturation, weak mixing and the diurnal radiative cycle—rather than spurious correlations, which supports forecaster trust [@mcgovern2019] and agrees with the dominance of radiation fog at LTAC [@camalan2010]. Third, the comparison with the TREND shows that the official 2-h forecast is essentially persistence, so even modest data-driven guidance can improve the very-short-range service.

The study has limitations. It uses point observations only; fog onsets, which depend on boundary-layer processes and advection that are not visible in a single METAR, remain hard to predict, and numerical weather prediction, satellite or ceilometer data would likely improve them [@herman2016; @kamangir2021]. The historical TAF archive could not be obtained for the test seasons, so the TAF comparison is limited to a short, fog-free window; it will be completed with the live verification. Because only one airport is considered, transferability is not assessed [@cerda2025]. Finally, the decreasing frequency of fog over the 21 years implies non-stationarity; the season-aligned validation and calibration on recent seasons mitigated it, but periodic retraining will be necessary.

# Conclusion

This paper presented the first machine-learning nowcasting system for fog and low visibility at Ankara Esenboğa Airport. Built on 21.8 years of quality-controlled METAR/SPECI reports and verified on four independent fog seasons, all models significantly outperformed persistence, and LightGBM improved on the official METAR TREND by 0.105 in CSI at 1 h. Calibrated probabilities, ILS-category forecasts and SHAP explanations make the forecasts operationally interpretable, and the open-source web application delivers them in real time with continuous self-verification. Future work will add numerical-model and satellite predictors to improve onset detection, extend the TAF comparison over full fog seasons and transfer the approach to other Turkish airports.

# Appendix {-}

The hyper-parameters selected on the validation seasons are listed in Table @tab:hp. The complete data set, the decoder, training and evaluation scripts, the trained models, the figures in English and Turkish and the web application are available at https://github.com/AtaSakik/esenboga-fog-nowcasting; a single script reproduces every number in this paper.

{{table:hyperparams|col}}{#tab:hp}

# Acknowledgment {-}

The author thanks the Iowa Environmental Mesonet, Ogimet and the NOAA Aviation Weather Center for making their meteorological archives openly available, and the instructor of the YMH453 Machine Learning course for the guidance during this project.

# References {-}
