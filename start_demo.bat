@echo off
REM ============================================================
REM  MO TOAN BO HE THONG DEMO PHONG VAN - bam dup la chay
REM  Cua so 1: RAG API (port 8000)   - backend kien thuc
REM  Cua so 2: RAG UI  (port 8501)   - chat RAG
REM  Cua so 3: AGENT UI (port 8502)  - chat Agent (demo chinh)
REM ============================================================

set AGENT_DIR=%~dp0
set RAG_DIR=%~dp0..\RAG_project

echo [1/3] Mo RAG API (port 8000)...
start "RAG API :8000" cmd /k "cd /d %RAG_DIR% && .venv\Scripts\activate && uvicorn api.main:app --port 8000"

echo     ... cho API khoi dong 15 giay (load model + warmup)
timeout /t 15 /nobreak >nul

echo [2/3] Mo RAG UI (port 8501)...
start "RAG UI :8501" cmd /k "cd /d %RAG_DIR% && .venv\Scripts\activate && streamlit run ui/app.py --server.port 8501"

echo [3/3] Mo AGENT UI (port 8502)...
start "AGENT UI :8502" cmd /k "cd /d %AGENT_DIR% && .venv\Scripts\activate && streamlit run app.py --server.port 8502"

echo.
echo ============================================================
echo  XONG! Cac dia chi demo:
echo    Agent (demo chinh):  http://localhost:8502
echo    RAG chat:            http://localhost:8501
echo    Swagger API:         http://localhost:8000/docs
echo  Dong cua so nao thi service do tat.
echo ============================================================
pause
