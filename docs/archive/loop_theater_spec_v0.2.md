# Loop Theater 사양 초안 (v0.2에서 발췌)

> 예전 설계안 `design_2plus2.md`의 C절만 남겼습니다. 지금 기준은 `docs/03_requirements.md`의 THR 요구사항입니다. "Stage"는 지금의 L1~L4 단계에 해당합니다.

## C. 시각화 도구 「Loop Theater」 사양 (오늘 밤 제작)

### C.1 목적

프로젝터 화면에서 **"지금 에이전트가 무엇을 하고 있는지"**를 한 장면으로 보여 줍니다. 매 Stage마다 같은 화면을 쓰고, 새 Stage에서 새 칸이 켜지는 구조라 학생이 구조를 누적해서 익힙니다.

### C.2 화면 구성

```
┌──────────────────────────── 상단: 실행 정보 (trace_id · 모델 · 턴 3/8 · 토큰 · 비용 · 경과시간) ───────────────┐
│ ① 슬롯 다이어그램 (A.2 그림)  │ ② 턴 타임라인 (가운데, 가장 큼)              │ ③ 흐름 그래프 (S5부터)      │
│  지금 활성 슬롯에 불이 켜짐   │  턴1: 🧠 LLM 호출 → 🔧 search_items(...)      │  mermaid, 현재 노드 강조     │
│  (감각/루프/도구/컬렉션/…)    │        → 결과 {found:1}                       │                              │
│                               │  턴2: 🧠 → ⚠ 승인 요청 update_item → ✅      │ ④ 상태 패널                 │
│                               │  턴3: 🧠 → 📚 load_skill(card-writer)        │  컬렉션 항목 수, 프로필,     │
│                               │        → 💾 collection.write                  │  로드된 스킬, 도구 목록      │
├───────────────────────────────┴───────────────────────────────────────────────┴──────────────────────────────┤
│ ⑤ "LLM이 실제로 보는 것" (선택한 model.send의 messages 배열, 역할별 색)   │ ⑥ 렌더 미리보기 (카드 HTML iframe) │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### C.3 이벤트 형식 (JSONL, 한 줄 = 이벤트 1개)

aisuite 0.2.0 트레이스 형식을 그대로 따르고 사용자 정의 이벤트 타입만 추가합니다. 그러면 aisuite `Runner`가 만든 트레이스도 같은 화면에서 볼 수 있습니다.

- [소스 확인] aisuite `TraceEvent.to_dict()` 필드: `record_type="trace_event"`, `schema_version="2026-05-15"`, `event_id`, `event_type`, `timestamp`(UTC ISO), `trace_id`, `span_id`, `parent_span_id`, `parent_run_id`, `group_id`, `run_name`, `agent_name`, `tags`, `metadata`, `data`.
- [소스 확인] aisuite 기본 이벤트 타입: `run.started|completed|failed`, `model.send|response|error`, `tool.allowed|denied|started|completed|failed`.
- 추가 타입(우리 루프가 발생): `turn.started`, `sense.input`, `memory.read`, `memory.write`, `collection.write`, `skill.listed`, `skill.loaded`, `mcp.connected`, `graph.node.entered`, `graph.edge`, `approval.requested`, `approval.resolved`, `reflection.draft`, `reflection.critique`, `reflection.revised`, `render.output`, `run.max_turns`.
- 모든 사용자 정의 이벤트는 `data.slot`에 ①~⑨ 슬롯 이름을 넣습니다. 슬롯 다이어그램은 이 값만 보고 불을 켭니다.

예:
```json
{"record_type":"trace_event","schema_version":"2026-05-15","event_type":"collection.write","trace_id":"trace_ab12","timestamp":"2026-10-17T05:12:03Z","agent_name":"todaydex","data":{"slot":"collection","turn":3,"op":"update","item_id":"cat-001","diff":{"episodes":"+1"}}}
```

### C.4 기능 목록

MUST (오늘 밤 반드시)

1. **라이브 테일**: `logs/trace.jsonl`에 줄이 추가되면 1초 안에 화면에 반영합니다(SSE 또는 500ms 폴링).
2. **턴 단위 그룹핑**: 턴마다 카드 1장(LLM 호출 → 도구 호출들 → 결과). 도구 인자/결과는 접어 두고 클릭하면 펼칩니다.
3. **슬롯 다이어그램 강조**: 최근 이벤트의 `data.slot`에 해당하는 칸을 1.5초간 강조합니다. 쓰인 적 있는 칸은 옅게 유지해서 "이번 실행에서 쓴 부품"이 보이게 합니다.
4. **흐름 그래프 현재 노드 강조**: `graph.node.entered`가 오면 mermaid 노드 색을 바꾸고 지나온 경로를 표시합니다.
5. **승인 이벤트를 눈에 띄게**: approval.requested는 노란 배너, 결과는 ✅/❌.
6. **리플레이 모드**: 저장된 JSONL을 불러와 ←/→ 키로 한 이벤트씩 앞뒤로 넘깁니다. API가 죽거나 와이파이가 끊겨도 수업이 됩니다.
7. **프로젝터 모드**: 큰 글씨(최소 18px), 한국어 라벨, 다크/라이트 전환.
8. **오프라인 동작**: mermaid.js 등 모든 JS를 로컬 파일로 넣습니다(CDN 금지).

SHOULD (시간 되면)

1. **"LLM이 보는 것" 패널**: model.send의 messages 배열을 역할별 색으로 보여 주고, 직전 호출과 비교해 새로 추가된 메시지를 강조합니다(S1, S4 설명에 효과가 큽니다).
2. 턴별 토큰/지연/추정 비용, 실행 합계.
3. **스텝 모드(브레이크)**: Theater에서 "다음" 버튼을 누를 때까지 루프가 도구 실행 전에 기다립니다(루프가 `logs/step.lock` 파일이나 HTTP 엔드포인트를 확인). 루프를 "느리게 보여 주기"용입니다.
4. 두 실행 비교(reflection on/off, 스킬 on/off).
5. 렌더 미리보기 iframe(`render.output`의 파일 경로).
6. aisuite `Runner` 트레이스(LocalTraceSink 파일) 불러오기 호환.

COULD

- 학생 PC에서 각자 실행(3~4시간차 디버깅용), 실행을 GIF/영상으로 내보내기.

### C.5 기술 선택 (권장)

- 서버: **파이썬 표준 라이브러리만** 사용(`http.server` + SSE 엔드포인트 `/events`가 JSONL을 tail). 설치할 것이 없습니다. 실행: `python viz/server.py --trace logs/trace.jsonl --port 8790`.
- 화면: 단일 `viz/index.html` + 순수 JS(빌드 도구 없음) + 로컬 `mermaid.min.js`. Cursor로 오늘 밤 2~3시간 안에 만들 수 있는 크기입니다.
- 이벤트 발생: `agent/trace.py`의 `emit(event_type, **data)`가 aisuite `TraceEvent` 형식 dict를 JSONL로 append합니다. aisuite `LocalTraceSink`/`HttpTraceSink`와 형식이 같아서 Runner 비교 실습(S1 끝)의 트레이스도 같은 파일에 넣을 수 있습니다. [확인 필요: Runner에 `trace_sinks=[LocalTraceSink("logs/trace.jsonl")]`를 넘겼을 때 실제로 기록되는지 실행 확인]

**대안/보험: aisuite 내장 뷰어** [소스 확인, 실행 안 함]

- aisuite 0.2.0에는 로컬 트레이스 뷰어가 들어 있습니다: `python -m aisuite.agents.viewer --trace-file .aisuite/runs.jsonl --port 8765`. 1.5초마다 `/api/runs`를 폴링하고, `POST /api/events`로 라이브 이벤트를 받습니다(`HttpTraceSink(endpoint=".../api/events")`).
- 주의: `LocalTraceSink` 기본 경로는 `.aisuite/events.jsonl`, 뷰어 기본 경로는 `.aisuite/runs.jsonl`로 서로 다릅니다. 같은 경로를 명시해야 합니다.
- 한계: 런(run) 목록, 메시지, 도구 타임라인 중심입니다. 슬롯 다이어그램, 그래프 노드 강조, 메모리/스킬 이벤트는 없습니다(사용자 정의 이벤트 타입이 어떻게 표시되는지 [확인 필요]). 그래서 **오늘 밤 Loop Theater MUST 1~3이 안 되면 이 뷰어로 진행**하고, 슬롯 다이어그램은 슬라이드로 대체합니다.

### C.6 오늘 밤 제작 순서 (우선순위)

1. `agent/trace.py` + Stage 1 루프에서 이벤트가 찍히는지 확인 (30분)
2. Theater: 라이브 테일 + 턴 카드 (MUST 1, 2) (60분)
3. 슬롯 다이어그램 강조 (MUST 3) (30분)
4. 리플레이 모드 + 단계별 녹화 트레이스 `viz/replays/stage0~6.jsonl` (MUST 6) (30분)
5. 흐름 그래프 강조, 승인 배너 (MUST 4, 5) (30분)
6. SHOULD 1 ("LLM이 보는 것") (시간 남으면)
