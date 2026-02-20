# Portfolio Command Center Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a full Portfolio tab to the dashboard — trade CRUD, live P/L, technical health signals (HOLD/CAUTION/EXIT), and a position-sizing modal.

**Architecture:** Trades persist in a new SQLite `trades` table. The GET endpoint enriches each trade at read-time with a fresh yfinance fetch (EMA8/20, CCI, current price). The frontend adds a tab switcher between SCANNER and PORTFOLIO views; the Portfolio tab is a new full-width component with an Add Trade modal.

**Tech Stack:** Python / FastAPI / aiosqlite / yfinance / pandas, React 18 / Tailwind / IBM Plex Mono

---

### Task 1: database.py — trades table + CRUD

**Files:**
- Modify: `swing-trading-dashboard/backend/database.py`

Add DDL, extend `init_db`, add `add_trade`, `get_trades`, `close_trade`.

---

### Task 2: main.py — 3 trade endpoints + live enrichment

**Files:**
- Modify: `swing-trading-dashboard/backend/main.py`

Endpoints: POST /api/trades, GET /api/trades, DELETE /api/trades/{id}.
Enrichment: current price, P/L $, P/L %, EMA8, EMA20, health signal.

---

### Task 3: api.js — trade API functions

**Files:**
- Modify: `swing-trading-dashboard/frontend/src/api.js`

Add `fetchTrades`, `addTrade(body)`, `closeTrade(id)`.

---

### Task 4: PortfolioTab.jsx — new full-width component

**Files:**
- Create: `swing-trading-dashboard/frontend/src/components/PortfolioTab.jsx`

Dense trade table, health badges, live P/L coloring, Add Trade modal,
position-sizing calculator (Risk $200 → auto-calc quantity).

---

### Task 5: App.jsx — tab switching

**Files:**
- Modify: `swing-trading-dashboard/frontend/src/App.jsx`

Add `activeTab` state ('scanner' | 'portfolio'). Tab nav bar between
header and body. Render PortfolioTab when portfolio tab is active.
