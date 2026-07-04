# 📖 HƯỚNG DẪN CHI TIẾT (Tiếng Việt — dành cho người mới)

> Project thứ 2 trong bộ demo phỏng vấn: **AI Agent** với LangGraph + MCP +
> Human-in-the-loop. Đây là trụ cột "AI Agents" trong CV — chủ đề bị hỏi
> nhiều thứ 2 sau RAG.

---

## 1. AI Agent là gì? (giải thích từ đầu)

Chatbot thường chỉ **trả lời** — nhận câu hỏi, sinh text, xong.
**Agent** thì **hành động**: nó có một bộ **tools** (công cụ) và tự quyết định
*gọi tool nào, theo thứ tự nào* để hoàn thành yêu cầu phức tạp.

Ví dụ yêu cầu: *"Tra cứu RRF là gì, tính 1/(60+1) + 1/(60+3), rồi lưu báo cáo."*
Một chatbot chịu chết. Agent thì:

1. **Plan**: "cần 3 bước — tra cứu → tính toán → lưu file"
2. Gọi tool `knowledge_search` → nhận kết quả
3. Gọi tool `calculator` → nhận kết quả
4. Gọi tool `save_report` → **dừng lại chờ con người duyệt** (vì ghi file là hành động nhạy cảm)
5. Tổng hợp câu trả lời cuối

Vòng lặp "suy nghĩ → gọi tool → nhận kết quả → suy nghĩ tiếp" chính là
**planner/executor loop** — trái tim của mọi agent.

## 2. Ba công nghệ chính trong project

| Công nghệ | Nó là gì | Trong project này |
|---|---|---|
| **LangGraph** | Framework dựng agent dạng **đồ thị trạng thái** (StateGraph): mỗi node là 1 bước (planner, tools), các cạnh quyết định đi đâu tiếp. Kiểm soát được, checkpoint được, pause/resume được — hơn hẳn vòng while tự viết. | `src/agent/graph.py` |
| **MCP** (Model Context Protocol) | Chuẩn mở (Anthropic đề xuất, cả ngành dùng) để **kết nối LLM với tools** qua một giao thức thống nhất — như "USB-C cho AI". Tool viết 1 lần, agent nào cũng cắm vào dùng được. | `mcp_server/server.py` là MCP server thật, agent kết nối qua MCP client |
| **Human-in-the-loop** | Hành động nhạy cảm (ghi file, gửi mail, thanh toán) phải được **con người duyệt** trước khi chạy. LangGraph `interrupt()` làm đồ thị **đứng lại giữa chừng**, chờ Approve/Reject rồi mới chạy tiếp. | Tool `save_report` bị gate; UI có nút ✅/❌ |

## 3. Từng file làm gì?

```
AI_AGENT_LANGGHAPH/
├── mcp_server/server.py    ← MCP SERVER (FastMCP): định nghĩa 4 tools
│                              • knowledge_search → gọi RAG API (project 1!)
│                              • calculator → tính toán an toàn bằng AST (không dùng eval)
│                              • get_current_time
│                              • save_report → ghi file (nhạy cảm, cần duyệt)
│
├── src/agent/
│   ├── config.py           ← Key DeepSeek, lệnh khởi động MCP server, guardrails
│   ├── graph.py            ← ⭐ LangGraph: planner ↔ tools, interrupt() cho HITL,
│   │                          giới hạn số vòng lặp (chống agent chạy vô hạn)
│   └── runtime.py          ← Cầu nối sync/async để Streamlit gọi được agent
│
├── app.py                  ← Streamlit chat: timeline từng bước + nút Approve/Reject
├── cli.py                  ← Bản chạy terminal (dự phòng khi demo)
├── requirements.txt        ← langgraph, langchain-openai, mcp, streamlit...
├── .env.example            ← Mẫu cấu hình key
└── reports/                ← Nơi agent lưu báo cáo (không commit)
```

**Luồng chạy một yêu cầu:**

```
User hỏi → planner (DeepSeek) nghĩ: "cần tool nào?"
   ├─ có tool_calls → tool executor chạy tool (qua MCP) → kết quả về planner → nghĩ tiếp
   │        └─ tool nhạy cảm? → interrupt() → CHỜ NGƯỜI DUYỆT → approve thì chạy
   └─ đủ thông tin → viết câu trả lời cuối → END
```

## 4. Cài đặt từng bước (Windows)

```powershell
# Bước 1-2: môi trường ảo (như project RAG)
python -m venv .venv
.venv\Scripts\activate

# Bước 3: cài thư viện (nhẹ, ~1 phút — không có PyTorch)
pip install -r requirements.txt

# Bước 4: cấu hình key
copy .env.example .env
# → mở .env, điền DEEPSEEK_KEY (bắt buộc — agent cần LLM để suy nghĩ)

# Bước 5 (nên làm): chạy RAG API của project 1 để tool knowledge_search có backend
# Mở terminal khác tại D:\profile\RAG_project:
#   .venv\Scripts\activate
#   uvicorn api.main:app --port 8000
# (Không chạy cũng được — tool sẽ báo offline và agent vẫn xử lý phần còn lại)
```

## 5. Chạy demo

```powershell
streamlit run app.py      # giao diện web — trình duyệt tự mở
# hoặc:
python cli.py             # bản terminal
```

Thử câu "ăn tiền" (đủ cả 3 bước + human-in-the-loop):

> Search the knowledge base for what Reciprocal Rank Fusion is, then calculate
> 1/(60+1) + 1/(60+3), and save a short report titled "RRF summary".

Sẽ thấy: 🔧 gọi `knowledge_search` → 🔧 gọi `calculator` → ⚠️ **dừng chờ duyệt**
`save_report` → bấm ✅ Approve → report xuất hiện trong `reports/` → câu trả lời
cuối tóm tắt mọi bước. Bấm ❌ Reject thì agent lịch sự giải thích bị từ chối.

## 6. 🎯 Kịch bản demo phỏng vấn (5 phút)

1. **Mở sidebar** chỉ vào danh sách tools: *"Tools không hard-code trong agent —
   chúng được serve qua một MCP server thật, agent load qua MCP client. Đây là
   chuẩn công nghiệp để nối LLM với internal APIs."*
2. **Gõ câu multi-step ở trên** → chỉ vào timeline: *"Đây là planner/executor
   loop bằng LangGraph — model tự quyết định thứ tự tools, mỗi kết quả tool
   quay lại planner để quyết định bước kế."*
3. **Đến đoạn dừng chờ duyệt** → *"Hành động ghi file bị gate bằng LangGraph
   interrupt — đồ thị tự đứng lại, model KHÔNG thể bypass. Đây là
   human-in-the-loop mà production agent bắt buộc phải có."* → bấm Approve.
4. **Mở file report** trong `reports/` cho họ xem kết quả thật.
5. **Chốt hạ hệ sinh thái**: *"Tool knowledge_search đang gọi vào chính RAG API
   của project kia — 2 repo của em nối thành một hệ thống: RAG là knowledge
   layer, agent là orchestration layer."* (Muốn diễn sâu hơn: tắt RAG API, hỏi
   lại — agent báo knowledge base offline nhưng vẫn hoàn thành phần tính toán.)

## 7. Câu hỏi phỏng vấn thường gặp & cách trả lời

**Q: LangGraph khác gì LangChain?**
A: LangChain là bộ toolkit (models, tools, prompts). LangGraph xây trên đó để
dựng **agent có trạng thái** dạng đồ thị: node/edge tường minh, checkpoint,
pause/resume (interrupt), replay. Vòng lặp agent tự viết bằng while không có
mấy thứ đó.

**Q: ReAct và planner/executor khác gì?**
A: ReAct đan xen "Thought → Action → Observation" từng bước một — linh hoạt
nhưng dễ lạc đề với task dài. Planner/executor tách vai: lập kế hoạch rồi thực
thi từng bước có kiểm soát. Project này là planner/executor dạng vòng lặp: mỗi
kết quả tool quay về planner để re-plan.

**Q: MCP là gì, sao không viết tool thẳng vào code agent?**
A: MCP là chuẩn mở kết nối LLM ↔ tools qua giao thức thống nhất (stdio/HTTP).
Viết tool thẳng vào agent thì tool đó chết dính với agent đó; expose qua MCP
server thì tool viết 1 lần, mọi agent/client (kể cả Claude Desktop) đều dùng
được, có schema chuẩn, quản lý permission tập trung.

**Q: Làm sao chặn agent chạy vô hạn / phá hoại?**
A: Nhiều lớp: (1) cap số vòng lặp — quá hạn ép trả lời ngay; (2) human-in-the-loop
cho hành động nhạy cảm; (3) tool lỗi được catch trả về message thay vì crash;
(4) calculator dùng AST whitelist chứ không eval(); (5) recursion_limit của
LangGraph là chốt chặn cuối.

**Q: Multi-agent thật thì khác gì demo này?**
A: Cùng nguyên lý nhưng nhiều node planner chuyên biệt hơn (researcher, writer,
reviewer...) giao tiếp qua state chung hoặc message passing; thêm routing/
supervisor pattern. LangGraph hỗ trợ subgraph cho việc này — kiến trúc demo
mở rộng thẳng lên được.

**Q: Đưa lên production cần thêm gì?**
A: Observability (trace từng tool call — LangSmith/OpenTelemetry), eval suite
cho agent behavior, timeout + retry cho tool, auth cho MCP server, checkpoint
bền (Postgres thay MemorySaver), rate limiting và cost tracking.

## 8. Lỗi thường gặp

| Lỗi | Cách sửa |
|---|---|
| Agent báo knowledge base offline | Chạy RAG API: `cd ..\RAG_project` → `uvicorn api.main:app --port 8000` |
| `AuthenticationError` | Kiểm tra `DEEPSEEK_KEY` trong `.env` (chỉ chuỗi `sk-...`, không kèm chú thích) |
| Streamlit treo lúc khởi động | Lần đầu khởi động MCP server mất vài giây; F5 nếu quá 30s |
| `ModuleNotFoundError: agent` | Chạy từ sai thư mục — phải đứng ở thư mục gốc project |

---

Bộ đôi demo: **RAG_project** (knowledge layer) + **AI_AGENT_LANGGHAPH**
(orchestration layer). Chúc ông đậu phỏng vấn! 🚀
