# Engine Tuning & Trendline Detection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix Engine 1 recency bias with time-weighted KDE and add diagonal trendline detection with live chart rendering.

**Architecture:** Engine 1 gets weighted gaussian_kde (2× weight for last 90 days) + scipy find_peaks with lower prominence + proximity prioritization (3% = Primary). Engine 2 gets a new `detect_trendline()` helper and PATH C. The /api/chart endpoint includes trendline series data; TradingChart.jsx draws it as a bright-white line series.

**Tech Stack:** scipy (gaussian_kde weights, signal.find_peaks), numpy, pandas, lightweight-charts v4

---

### Task 1: engine1.py — Weighted KDE + find_peaks + Proximity
### Task 2: engine2.py — detect_trendline() + PATH C breakout
### Task 3: main.py — trendline in /api/chart response
### Task 4: TradingChart.jsx — render trendline + legend entry
### Task 5: SetupTable.jsx — TDL badge
