# 03. 요구사항: 에이전트 키트 (스타터 앱 + 엔진 + 공통 에이전트)

> 현재 공통 실습: 샘플은 사본 없이 저장소의 `sample_downloads/`에서 직접 사용합니다. **폴더 고르기 → 샘플 폴더 → 이 폴더 사용**으로 선택하며, 이동 결과·노트·갤러리도 같은 폴더에서 확인합니다. 아래 초기 설계의 사본 절차는 개인 폴더 사용에만 해당합니다. 현재 실행 안내는 [GUIDE 0-6](../GUIDE.md#0-6-화면과-실습-폴더)을 따릅니다.

> 처음 보는 말(에이전트, 루프, 도구, MCP, 스킬, API, 하네스 등)은 [용어 풀이](00_glossary.md)에 쉬운 예시와 함께 있습니다.
> 요구사항 = "키트가 무엇을 할 수 있어야 하나"를 적은 목록입니다. 인수 기준 = "이렇게 되면 완성"이라고 확인하는 방법입니다.

> 이 문서는 다음 단계에서 키트를 개발할 사람을 위한 기준입니다. 이전 초안(요구사항 v0.1, 저장소에 넣지 않음)의 Gradio, LangChain, 컬렉션 CRUD 중심 설계는 **대체되었습니다.**

## 0. 읽는 법

| 표기 | 뜻 |
|---|---|
| **MUST** | 수업 당일 반드시 동작해야 함 |
| **SHOULD** | 강하게 권장. 시간이 없으면 완성본 리플레이로 대신해도 수업은 됨 |
| **COULD** | 선택. 강사 시연이나 3~4시간차용 |
| [확인함] / [확인 필요] | 직접 실행해서 확인함 / 아직 안 함 |

ID 규칙: `APP` 스타터 앱, `THR` Loop Theater, `ENG` 엔진, `LV` 단계, `FS` 파일·사본, `HIL` 사람 승인, `WEB` 웹, `MET` 미술관, `DOC` 도슨트, `REN` 결과 화면, `STB` 스토리보드.

## 1. 범위 요약

| 만드는 것 | 설명 |
|---|---|
| 스타터 웹앱 | 왼쪽 채팅, 오른쪽 Loop Theater, 위쪽 단계 스위치와 도구 토글 |
| 엔진 | aisuite 0.2.0 위의 에이전트 루프, 도구, MCP, 스킬, 승인, 기록 |
| 공통 에이전트 | 탐정 → 큐레이터 → 도슨트 (「내 다운로드 폴더 전시회」) |
| 단계별 미션 | `levels/L1~L4` 미션 카드와 `levels/Lx_done/` 완성본 |
| 보조 스크립트 | 사본 만들기, 되돌리기, 오프라인 캐시 준비 |
| 인쇄물 | 3색 카드, 다이얼 스티커, A3 스토리보드 시트 |

## 2. 기능 요구사항

### 2.1 스타터 웹앱 (APP)

| ID | 우선 | 요구사항 | 인수 기준 |
|---|---|---|---|
| APP-01 | MUST | 명령 하나로 실행되고 브라우저가 열린다 | Mac과 Windows에서 `uv run app.py`(또는 동등한 명령) 한 번으로 `localhost`에 앱이 뜬다 |
| APP-02 | MUST | 왼쪽 채팅 창 | 메시지를 보내면 에이전트 답이 한국어로 표시된다. 진행 중에는 "생각 중" 상태가 보인다 |
| APP-03 | MUST | 상단 단계 스위치 L1~L4 | 스위치를 바꾸면 재시작 없이 다음 메시지부터 해당 단계로 동작한다(LV 요구사항 참고) |
| APP-04 | MUST | 도구 토글: 파일, 웹 검색, MCP, Met API | 토글을 끄면 그 도구가 LLM에 전달되는 도구 목록에서 빠진다. Theater 도구 패널 개수가 바뀐다 |
| APP-05 | MUST | 버튼 ↔ 파일 연결 보기 | 각 버튼 옆 "파일로 보기"를 누르면 그 설정이 들어 있는 파일과 줄(예: `config.yaml`의 `tools.web_search: true`)을 보여 준다 |
| APP-06 | MUST | 버튼과 파일은 같은 상태 | 버튼을 누르면 파일이 바뀌고, 파일을 직접 고치면(또는 Cursor가 고치면) 3초 안에 버튼 상태가 따라온다 |
| APP-07 | MUST | 승인 카드 | 승인이 필요한 행동은 채팅 창에 카드로 뜨고 ✅승인 / ❌거절 / ✏️수정 버튼이 있다(HIL 참고) |
| APP-08 | SHOULD | 💬 한마디 | 승인 카드에 자유 입력 칸이 있고, 입력하면 에이전트가 계획 전체를 다시 짠다 |
| APP-09 | MUST | 미션 카드 | 단계마다 미션 카드(목표, 해 볼 것 3개, 확인할 것)가 앱 안에 보인다 |
| APP-10 | MUST | 완성본으로 바꾸기 | "완성본으로" 버튼을 누르면 해당 단계의 `levels/Lx_done/` 설정으로 바뀐다. 학생 파일은 지우지 않고 백업한다 |
| APP-11 | MUST | 처음 상태로 되돌리기 | 설정을 처음 상태로 돌리는 버튼(또는 명령)이 있다 |
| APP-12 | SHOULD | 키 상태 표시 | 시작 화면에 어떤 키(모델, Tavily)가 잡혔는지 ✅/❌로 보인다. 키 값은 보이지 않는다 |

### 2.2 Loop Theater 시각화 (THR)

| ID | 우선 | 요구사항 | 인수 기준 |
|---|---|---|---|
| THR-01 | MUST | 실시간 반영 | 엔진 이벤트가 1초 안에 화면에 나타난다 |
| THR-02 | MUST | 턴 카드 | 턴마다 카드 1장: 🧠 LLM 판단 → 🔧 도구 호출(이름, 인자) → 결과. 인자와 결과는 접혀 있고 누르면 펼쳐진다 |
| THR-03 | MUST | 부품 강조 | 지금 쓰는 부품(뇌, 손, MCP, 스킬, 승인, 기억, 결과 화면)에 1.5초 불이 들어온다. 이번 실행에 쓴 부품은 옅게 남는다 |
| THR-04 | MUST | 에이전트 노드 강조 | L4에서 탐정·큐레이터·도슨트 노드 중 지금 일하는 노드가 강조되고 넘겨준 화살표가 보인다 |
| THR-05 | MUST | 노드 그래프는 보기 전용 | 그래프를 클릭해도 편집되지 않는다. 노드를 누르면 설명만 뜬다 |
| THR-06 | MUST | 승인 배너 | 승인 대기 중에는 노란 배너가 뜨고, 결과는 ✅/❌/✏️로 남는다 |
| THR-07 | MUST | 재시도 대기 보이기 | 429나 503이 오면 "요청 한도: 23초 기다리는 중" 카드와 카운트다운이 보인다 |
| THR-08 | MUST | 리플레이 | 저장된 `trace.jsonl`을 불러와 ←/→ 키로 한 이벤트씩 넘긴다. 인터넷 없이 동작한다 |
| THR-09 | MUST | 프로젝터 모드 | 버튼 하나로 큰 글씨(최소 18px)로 바뀐다. 라벨은 한국어 |
| THR-10 | MUST | 오프라인 자산 | 화면에 쓰는 코드·스타일·폰트를 모두 노트북 안에 넣어 둔다. 인터넷에서 불러오지 않는다 |
| THR-11 | SHOULD | "LLM이 보는 것" 패널 | 선택한 턴에 LLM에 보낸 메시지 목록을 역할별 색으로 보여 주고, 직전보다 늘어난 부분을 강조한다 |
| THR-12 | SHOULD | 컨텍스트 막대 | 턴마다 AI에게 보낸 글의 양(글자 수 또는 토큰 = AI가 글을 세는 단위)을 막대로 보여 준다. 스킬을 불러오면 막대가 커지는 것이 보인다 |
| THR-13 | SHOULD | 턴별 시간·토큰·추정 비용 | 각 턴 카드와 실행 합계에 표시 |
| THR-14 | COULD | 두 실행 비교 | 스킬 켬/끔 등 두 기록을 나란히 본다 |

### 2.3 엔진 (ENG)

| ID | 우선 | 요구사항 | 인수 기준 |
|---|---|---|---|
| ENG-01 | MUST | 에이전트 루프 + 턴 한도 | `config.yaml`의 `max_turns`(기본 8)를 넘으면 멈추고 "턴 한도 도달"을 채팅과 Theater에 남긴다 |
| ENG-02 | MUST | 모델은 설정 한 줄로 교체 | `model`과 `provider` 설정만 바꿔 Anthropic과 Gemini(OpenAI 호환 주소)가 둘 다 동작한다 |
| ENG-03 | MUST | 도구는 예외를 던지지 않는다 | 모든 도구는 실패 시 `"error: ..."` 문자열을 돌려준다. 도구 안 예외는 엔진의 감싸개가 잡아 문자열로 바꾼다. 실패 뒤에도 루프가 계속된다 [확인함: aisuite는 도구 예외를 다시 던져 루프가 끊김] |
| ENG-04 | MUST | 429/503 자동 재시도 | 서버가 알려 준 대기 시간(없으면 20초)만큼 기다렸다 최대 6회 재시도한다. 대기는 THR-07로 보인다 |
| ENG-05 | MUST | 페르소나 파일 | 에이전트마다 `persona.md`가 시스템 프롬프트가 된다. 파일만 고치면 다음 메시지부터 말투가 바뀐다 |
| ENG-06 | MUST | 스킬 로더 | `skills/*/SKILL.md`의 이름과 한 줄 설명만 시스템 프롬프트에 넣고, 본문은 LLM이 `load_skill(name)`을 부를 때만 넣는다. 이 순간이 Theater에 이벤트로 보인다 |
| ENG-07 | MUST | MCP 연결 | `mcp.json`에 켜 둔 서버를 시작할 때 연결하고 도구를 목록에 더한다. 연결 실패 시 앱은 나머지 도구로 계속 동작하고 실패 이유를 한국어로 보여 준다 |
| ENG-08 | MUST | 도구 허용 목록 | MCP 서버마다 쓸 도구를 이름으로 고른다(예: Tavily는 `tavily_search`, `tavily_extract`만) |
| ENG-09 | MUST | 기록 | 모든 이벤트를 `runs/<날짜시간>/trace.jsonl`에 남긴다(형식은 5.8). 키와 개인 파일 내용 전문은 남기지 않는다 |
| ENG-10 | MUST | 에이전트 넘겨주기 | L4에서 큐레이터 결과(`exhibit.json`)를 코드가 도슨트에게 넘긴다. 두 에이전트는 서로 다른 페르소나와 도구 목록을 쓴다 |
| ENG-11 | MUST | 고정 흐름(그래프) | L2와 장면 5의 정해진 순서(예: 탐색 → 계획 → 승인 → 실행 → 전시)를 코드로 정의하고, 지금 노드를 이벤트로 알린다 |
| ENG-12 | SHOULD | 스텝 모드 | Theater의 "다음" 버튼을 누를 때까지 도구 실행 전에 기다린다 |
| ENG-13 | COULD | 오즈의 마법사 모드 | `wizard_mode: llm`이면 LLM 대신 짝이 콘솔에서 답이나 도구 호출을 입력한다(3~4시간차 트랙 C) |

### 2.4 자율성 단계 (LV)

| ID | 우선 | 단계 | 동작 | 인수 기준 |
|---|---|---|---|---|
| LV-01 | MUST | L1 챗봇 | 도구 없이 LLM만 답한다 | "지금 몇 시야?"에 도구 호출이 0회다 |
| LV-02 | MUST | L2 고정 워크플로 | 코드가 `list_files → count_by_type → LLM 요약`을 항상 같은 순서로 돈다 | 질문이 바뀌어도 같은 3단계만 켜진다. "제일 큰 파일 3개?"에는 답하지 못한다 |
| LV-03 | MUST | L3 에이전트 + 승인 | LLM이 도구를 고르고 루프를 돈다. 쓰기 도구는 승인을 거친다 | 한 요청에서 도구 호출이 2회 이상 이어지고, `apply_move`는 승인 없이 실행되지 않는다 |
| LV-04 | MUST | L4 에이전트 둘 | 큐레이터와 도슨트가 나눠 일한다 | Theater에 두 에이전트 노드가 번갈아 켜지고 `exhibit.html`이 만들어진다 |
| LV-05 | MUST | 미션 완성본 | `levels/L1_done` ~ `L4_done`이 있다 | 각 완성본으로 바꾸면 그 단계 미션이 바로 성공한다 |

### 2.5 파일과 사본 폴더 (FS)

| ID | 우선 | 요구사항 | 인수 기준 |
|---|---|---|---|
| FS-01 | MUST | 사본 만들기 | 원본 폴더에서 **진짜로 복사**한다(날짜 유지). 위치 `~/agent-workshop/exhibit_copy/`. 최대 60개, 파일당 20MB |
| FS-02 | MUST | 복사 전 목록 고르기 | 복사할 목록을 먼저 보여 주고 학생이 뺄 파일을 고른다 |
| FS-03 | MUST | 민감 파일 기본 제외 | 이름에 신분증·여권·주민·통장·계좌·계약·성적·진단·영수증 등이 있거나 확장자가 `.env .pem .key .kdbx`이면 기본 제외한다 |
| FS-04 | MUST | 샘플 폴더 | 가상의 학생 다운로드 40개(재미있는 이름)를 기본 제공한다. 내 파일이 싫은 학생은 이것을 쓴다 |
| FS-05 | MUST | 읽기 도구 | `list_files`, `file_info`, `peek_file`. 엿보기는 텍스트·PDF 첫 페이지 앞 500자, 이미지는 크기·해상도만 |
| FS-06 | MUST | 계획 도구는 쓰지 않는다 | `propose_plan`은 `plan.json`만 만든다. 파일은 움직이지 않는다 |
| FS-07 | MUST | 이동 도구 | `apply_move`만 쓰기 도구다. 승인된 항목만 이동·이름 변경한다 |
| FS-08 | MUST | 사본 밖 거부 | 사본 폴더 밖 경로는 코드가 거부하고 `"error: 사본 폴더 밖"`을 돌려준다 |
| FS-09 | MUST | 덮어쓰기 금지 | 이름이 겹치면 `_2`, `_3`을 붙인다 |
| FS-10 | MUST | **삭제 도구 없음** | 키트 어디에도 파일을 지우는 도구가 없다. Cursor 규칙 파일에도 "삭제 기능 추가 금지"를 적는다 |
| FS-11 | MUST | 되돌리기 | 모든 이동을 `undo.json`에 남기고, 버튼(또는 `undo.py`)으로 원래대로 돌린다 |
| FS-12 | MUST | 원본은 건드리지 않음 | 어떤 단계에서도 원본 폴더에 쓰지 않는다 |
| FS-13 | MUST | 한글 파일명 NFC | 모든 파일명을 같은 유니코드 방식(NFC)으로 맞춘 뒤 비교하고, 새 이름도 이 방식으로 만든다. Mac은 한글을 자모로 쪼개 저장할 때가 있어서(NFD) 그냥 비교하면 같은 이름도 다르게 보인다 |
| FS-14 | SHOULD | 한 번에 여러 개 옮기기 | 승인된 항목을 도구 호출 한 번에 옮길 수 있다(10개 이동에 약 78초 걸린 것을 줄이기 위해) |

### 2.6 사람 승인 (HIL)

| ID | 우선 | 요구사항 | 인수 기준 |
|---|---|---|---|
| HIL-01 | MUST | 항목별 심사 | 계획표의 항목마다 승인/거절/수정을 고른다 |
| HIL-02 | MUST | 거절 존중 | 거절한 항목은 실행하지 않고, 에이전트가 비슷한 항목도 뺄지 되묻는다 |
| HIL-03 | MUST | 수정 존중 | 학생이 고친 이름·전시실이 그대로 쓰이고, 같은 패턴의 다른 항목에도 반영된 v2 계획이 나온다 |
| HIL-04 | MUST | v1→v2 차이 | v2 계획에서 바뀐 줄이 강조된다 |
| HIL-05 | MUST | 규칙을 스킬에 저장 | 실행이 끝나면 "방금 알려 주신 규칙을 `SKILL.md`에 추가할까요?"를 묻고, 승인하면 파일에 실제로 추가된다 |
| HIL-06 | MUST | 승인 목록은 설정에 | 어떤 도구가 승인을 거치는지 `config.yaml`의 `require_approval`에 적는다 |

### 2.7 웹 검색과 읽기 (WEB)

| ID | 우선 | 요구사항 | 인수 기준 |
|---|---|---|---|
| WEB-01 | MUST | Tavily MCP | `npx -y tavily-mcp@latest`로 연결하고 `tavily_search`, `tavily_extract`를 쓴다 [확인함: 키 없이도 동작] |
| WEB-02 | MUST | Tavily 키는 선택 | `TAVILY_API_KEY`가 있으면 넘기고, 없으면 키 없이 동작한다. 학생에게 무료 키(월 1,000 크레딧, 카드 불필요)를 권한다 |
| WEB-03 | MUST | 웹 읽기는 `tavily_extract` | 별도 Fetch MCP는 쓰지 않는다 |
| WEB-04 | MUST | 위키백과 | 해설 근거는 위키백과에서 읽는다. 위키백과 API를 직접 부를 때는 `User-Agent`를 넣는다 |
| WEB-05 | MUST | 출처 표시 | 웹에서 읽은 내용을 쓸 때 출처 URL을 함께 보여 준다 |
| WEB-06 | COULD | DuckDuckGo MCP 예비 | Tavily가 막힐 때만 쓰는 예비. 봇 차단으로 5회 중 2회 실패, 위키백과 읽기 불가 [확인함] |
| WEB-07 | COULD | Playwright 시연 | 강사 PC에서만. 학생 키트에는 넣지 않는다 |

### 2.8 미술관 (MET)

| ID | 우선 | 요구사항 | 인수 기준 |
|---|---|---|---|
| MET-01 | MUST | Met API v1.1 검색 | `GET .../public/collection/v1.1/search?q=<검색어>&hasImages=true&limit=<n>`을 쓴다. 옛 `/v1/search`는 쓰지 않는다 |
| MET-02 | MUST | 작품 정보 | `GET .../public/collection/v1/objects/<id>`에서 제목, 작가, 연도, 재료, 분류, 태그, 이미지, 링크를 가져온다 |
| MET-03 | MUST | 공공 도메인만 | `isPublicDomain`이 true이고 `primaryImageSmall`이 있는 것만 후보로 남긴다 |
| MET-04 | MUST | 미술관 웹페이지는 읽지 않음 | metmuseum.org 웹페이지는 봇 확인 화면으로 막힌다. 데이터는 API로만 가져온다 [확인함] |
| MET-05 | MUST | 캐시 | 결과를 `data/met_cache.json`에 저장하고 같은 검색어는 다시 부르지 않는다 |
| MET-06 | MUST | 오프라인 모드 | 강사가 미리 만든 검색어 30개 캐시만으로도 도슨트가 동작한다 |

### 2.9 도슨트 (DOC)

| ID | 우선 | 요구사항 | 인수 기준 |
|---|---|---|---|
| DOC-01 | MUST | D1 검색어 3개 | 전시실 요약(이름, 파일 수, 대표 파일명 5개, 확장자, 캡션)으로 영어 검색어 3개와 이유를 만든다. 파일 내용 원문은 보내지 않는다 |
| DOC-02 | MUST | D2 후보 | 검색어별로 Met 후보를 모아 최대 8점을 보여 준다 |
| DOC-03 | MUST | D3 고르기 | 제목·재료·태그를 비교해 1점을 고르고 이유 1문장을 쓴다 |
| DOC-04 | MUST | D4 해설 | 위키백과 문서를 읽어 2~3문장 해설과 출처 링크를 쓴다 |
| DOC-05 | MUST | 학생이 끼어들기 | 검색어 1개를 고치거나, 고른 작품을 다른 후보로 바꿀 수 있다. 바꾼 기록은 도슨트에게 돌아간다 |
| DOC-06 | COULD | 비전 비교 | 학생이 동의한 경우에만 대표 이미지 1장(축소본)과 후보 이미지를 비교한다. 동의 화면에 "이미지가 API로 전송됨"을 적는다 |

### 2.10 결과 화면 (REN)

| ID | 우선 | 요구사항 | 인수 기준 |
|---|---|---|---|
| REN-01 | MUST | 갤러리 HTML | `exhibit.html`에 전시실, 썸네일(이미지 파일만), 캡션, 닮은 명작(이미지 + 출처), 탐정의 추리가 들어간다 |
| REN-02 | MUST | 오프라인으로 열림 | 인터넷 없이 열린다(작품 이미지는 내려받아 두거나, 실패 시 제목 카드로 대체) |
| REN-03 | MUST | 템플릿은 한 파일 | 학생이 Cursor에게 "어두운 미술관 벽 느낌으로" 부탁하면 템플릿 한 파일만 바뀐다 |

### 2.11 스토리보드 (STB)

| ID | 우선 | 요구사항 | 인수 기준 |
|---|---|---|---|
| STB-01 | MUST | 템플릿 | 10문항 + 6컷 템플릿을 A3 PDF와 FigJam으로 제공한다(`docs/02` 6장) |
| STB-02 | MUST | 원리 추출 프롬프트 | 복사해서 쓰는 프롬프트를 키트에 넣는다 |
| STB-03 | COULD | `extract.py` | 같은 프롬프트로 `my_agent.json`과 `my_agent.mmd`를 만들고 Theater 그림에 표시한다 |

## 3. 비기능 요구사항

### 3.1 안전과 개인정보

| ID | 우선 | 요구사항 |
|---|---|---|
| NF-SAFE-01 | MUST | 쓰기는 사본 폴더 안에서만. 삭제 도구 없음. 덮어쓰기 금지. 되돌리기 가능 |
| NF-SAFE-02 | MUST | 첫 장면에서 "파일 이름과 앞부분이 클라우드 AI로 간다"고 화면과 말로 알린다 |
| NF-SAFE-03 | MUST | 외부 API(Met, Tavily)에는 검색어만 보낸다. 파일 내용 원문은 보내지 않는다 |
| NF-SAFE-04 | MUST | 이미지 비전은 기본 끔. 켤 때 동의를 받는다 |
| NF-SAFE-05 | MUST | 키는 환경 변수(`.env`)에서만 읽는다. `.env`는 `.gitignore`에 있다. 키는 화면·로그·trace에 찍지 않는다 |
| NF-SAFE-06 | MUST | 화면 공유와 갤러리 공개는 본인 동의만 |
| NF-SAFE-07 | MUST | Cursor 규칙 파일(`.cursor/rules/workshop.mdc`): 엔진 수정 금지, 삭제 기능 추가 금지, Met은 v1.1 검색 사용 |

### 3.2 크로스 플랫폼 (Mac / Windows)

| ID | 우선 | 요구사항 |
|---|---|---|
| NF-OS-01 | MUST | 폴더 경로는 파이썬의 `pathlib`로만 다룬다. Mac은 `/`, Windows는 `\`를 쓰는데 이 차이를 자동으로 처리해 준다 |
| NF-OS-02 | MUST | 다운로드 폴더 자동 찾기: `Path.home()/"Downloads"`, 없으면 폴더 선택. Windows는 OneDrive 아래 다운로드도 후보로 찾는다 [확인 필요] |
| NF-OS-03 | MUST | 한글 파일명은 NFC로 비교·생성 (FS-13) |
| NF-OS-04 | MUST | 설치 안내는 Mac과 Windows를 나란히 쓴다 |
| NF-OS-05 | MUST | Node가 필요한 MCP(Tavily)가 실패해도 앱은 동작한다. 웹 장면은 리플레이로 진행 |
| NF-OS-06 | SHOULD | 첫 실행 전 `npx -y tavily-mcp@latest`를 미리 한 번 받아 둔다(처음 실행할 때 나오는 설치 메시지가 연결을 깨는 문제를 막기 위해) |

### 3.3 비용과 호출 한도

| ID | 우선 | 요구사항 |
|---|---|---|
| NF-COST-01 | MUST | 기본 `max_turns: 8`, 파일 60개 제한, 목록은 이름·크기·날짜만, 엿보기 500자 |
| NF-COST-02 | MUST | 무료 Gemini 키는 수업용으로 쓰지 않는다(3.8 Flash 하루 20회, 3.5/3.6 분당 5회). 유료 키나 학생 Anthropic 키를 쓴다 |
| NF-COST-03 | MUST | 429/503 재시도와 대기 표시(ENG-04, THR-07) |
| NF-COST-04 | SHOULD | 학생 1인당 수업 중 비용 약 5달러 이내(목표). Theater에 추정 비용 표시 |
| NF-COST-05 | SHOULD | 강사 예비 키는 사용 한도를 걸어 둔다 |

### 3.4 오프라인과 장애 대비

| 상황 | 대비 (MUST) |
|---|---|
| 와이파이 끊김, API 장애 | Theater 리플레이로 강사 녹화본 진행(`replays/L1~L4.jsonl`) |
| Tavily 실패 | 리플레이. 예비로 DDG MCP(COULD) |
| Met API 실패 | 캐시만으로 동작(MET-06). 그래도 안 되면 도슨트는 캡션만 |
| MCP 연결 실패 | 나머지 도구로 계속(ENG-07) |
| 학생 설정이 망가짐 | 완성본으로 바꾸기(APP-10), 처음 상태로(APP-11) |
| 파일 사고 | 되돌리기(FS-11). 최악이면 사본을 다시 만듦(원본은 무사) |

### 3.5 성능과 설치

| ID | 우선 | 요구사항 | 참고 측정값 [확인함] |
|---|---|---|---|
| NF-PERF-01 | SHOULD | 웹 검색 + 읽기 + 요약 한 번 60초 이내 | 41.7초 |
| NF-PERF-02 | SHOULD | 10개 이동 계획 + 실행 60초 이내 | 약 78초(한 개씩 이동) → FS-14로 줄임 |
| NF-PERF-03 | SHOULD | Met 후보 찾기 + 추천 30초 이내 | 21초 |
| NF-INST-01 | MUST | 설치는 15분 이내. 사전 안내문(uv, Node, 키) 배포 |
| NF-INST-02 | MUST | 버전 고정(`uv.lock`). aisuite 0.2.0 |

### 3.6 언어와 접근성

| ID | 우선 | 요구사항 |
|---|---|---|
| NF-UX-01 | MUST | 화면 라벨, 오류 메시지, 미션 카드는 한국어. 짧은 문장 |
| NF-UX-02 | MUST | 오류는 "무슨 일인지 + 학생이 할 일" 두 줄로 보여 준다(예: "모델 키가 없습니다. `.env`에 키를 넣고 다시 실행하세요.") |
| NF-UX-03 | MUST | 프로젝터 모드(THR-09) |

## 4. 스타터 앱 화면과 설정 연결

### 4.1 버튼 ↔ 파일

| 화면의 버튼 | 바뀌는 파일 | 바뀌는 값 |
|---|---|---|
| 단계 L1~L4 | `config.yaml` | `level: L1` ~ `L4` |
| [파일] 도구 | `config.yaml` | `tools.files: true/false` |
| [웹 검색] 도구 | `config.yaml` → `mcp.json` | `tools.web_search`, `mcpServers.tavily.enabled` |
| [MCP] 도구 | `mcp.json` | 서버별 `enabled` |
| [Met API] 도구 | `config.yaml` | `tools.met: true/false` |
| 턴 한도 | `config.yaml` | `max_turns` |
| 대상 폴더 | `config.yaml` | `sandbox_path` |
| 에이전트 말투 | `agents/<이름>/persona.md` | 파일 본문 |
| 정리 규칙 | `skills/curator/SKILL.md` | 파일 본문 |

### 4.2 미션 카드 형식

| 칸 | 예시 (L3) |
|---|---|
| 목표 | 탐정이 내 폴더를 스스로 뒤지게 하기 |
| 해 볼 것 | ① 탐정 미션 실행 ② `max_turns`를 3으로 ③ [웹 검색] 켜고 처음 보는 파일 묻기 |
| 확인할 것 | 턴 카드가 몇 장 쌓였나? 도구 결과가 다음 선택을 바꿨나? |
| 막히면 | [완성본으로] 버튼 = `levels/L3_done/` |

## 5. 설정 파일 형식

> 이름과 필드는 제안입니다. 개발 중 바꿔도 되지만, **버튼과 파일이 1:1로 대응**한다는 원칙(APP-05, APP-06)은 지킵니다.

### 5.1 `config.yaml`

```yaml
level: L3                      # L1 | L2 | L3 | L4
model:
  provider: anthropic          # anthropic | gemini_openai
  name: "anthropic:<모델 ID>"   # [확인 필요] 수업용 Anthropic 모델 ID
  # Gemini 예: provider: gemini_openai
  #           name: "openai:gemini-3.8-flash"
  #           base_url: "https://generativelanguage.googleapis.com/v1beta/openai/"
max_turns: 8
sandbox_path: "~/agent-workshop/exhibit_copy"
tools:
  files: true
  web_search: true
  met: true
require_approval: [apply_move, save_skill_rule]
retry:
  on_status: [429, 503]
  max_attempts: 6
  default_wait_s: 20
vision:
  enabled: false               # 켜려면 동의 필요
ui:
  projector_mode: false
```

### 5.2 `.env.example` (값은 비워 둠)

```
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
TAVILY_API_KEY=        # 선택. 없으면 Tavily 키 없이 동작
```

### 5.3 `mcp.json`

```json
{
  "mcpServers": {
    "tavily": {
      "command": "npx",
      "args": ["-y", "tavily-mcp@latest"],
      "env_from": ["TAVILY_API_KEY"],
      "allow_tools": ["tavily_search", "tavily_extract"],
      "enabled": true
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "${sandbox_path}"],
      "enabled": false
    }
  }
}
```

`env_from`: 넘길 환경 변수 이름 목록. MCP 서버 프로세스에 `env`를 넘기면 PATH 등 기본 환경이 빠질 수 있으므로, 엔진이 현재 환경에 이 값만 더해서 넘깁니다 [확인 필요].

### 5.4 `persona.md`

```markdown
# 큐레이터
## 캐릭터
- 깐깐하지만 유머 있는 미술관 큐레이터. 반말 금지.
## 일하는 법
- 파일을 옮기기 전에 반드시 계획표를 먼저 보여 준다.
## 하지 않는 것
- 사본 폴더 밖은 보지 않는다. 파일을 지우자고 하지 않는다.
```

### 5.5 `SKILL.md`

```markdown
---
name: curator
description: 다운로드 파일을 전시실로 나누고 이름을 규칙대로 바꾸는 법
---
## 내 파일 이름 규칙
- 날짜_프로젝트_내용_버전 (예: 20261017_졸전_포스터_v03.png)
## 전시실 (4~6개)
- 스크린샷 방: ...
## 캡션 말투
- 미술관 캡션처럼 2문장, 약간 건방지게
## 승인에서 배운 규칙
- (HIL-05로 추가되는 칸)
```

### 5.6 `plan.json`

```json
{
  "plan_id": "p-20261017-1",
  "version": 2,
  "items": [
    {"id": 1, "src": "Screenshot 2026-10-01 at 3.12.44 PM.png",
     "dst": "스크린샷 방/20261001_스크린샷_01.png",
     "room": "스크린샷 방", "reason": "스크린샷 이름 패턴",
     "status": "approved", "changed_from_v1": false}
  ]
}
```

`status`: `pending | approved | rejected | edited`.

### 5.7 `undo.json`

```json
{"moves": [{"plan_id": "p-20261017-1", "item": 1, "from": "a.png", "to": "스크린샷 방/a.png", "at": "2026-10-17T14:05:00+09:00"}]}
```

### 5.8 `exhibit.json` (큐레이터 → 도슨트)

```json
{
  "owner_guess": "마감에 쫓기는 그래픽 디자인 전공생",
  "rooms": [
    {"name": "포스터 방", "files": ["..."], "caption": "...",
     "docent": {"keywords": ["poster", "typography", "sunflowers"],
                "pick": {"met_id": 436524, "title": "Sunflowers", "reason": "..."},
                "commentary": "...", "sources": ["https://ko.wikipedia.org/..."]}}
  ]
}
```

### 5.9 `trace.jsonl` 이벤트 (한 줄 = 이벤트 1개)

aisuite 0.2.0 트레이스 형식(`record_type`, `event_type`, `timestamp`, `trace_id`, `agent_name`, `data` 등)을 따르고, 아래 타입을 더합니다.

| 이벤트 | 언제 | `data`에 들어가는 것 |
|---|---|---|
| `turn.started` | 턴 시작 | `turn`, `agent` |
| `model.send` / `model.response` | LLM 호출 전후 | 메시지 수, 글자 수, 소요 시간 |
| `tool.started` / `tool.completed` / `tool.failed` | 도구 실행 | 도구 이름, 인자 요약, 결과 요약 |
| `retry.waiting` | 429/503 | 상태 코드, 대기 초, 시도 횟수 |
| `skill.loaded` | 스킬 본문 로드 | 스킬 이름, 글자 수 |
| `mcp.connected` / `mcp.failed` | MCP 연결 | 서버 이름, 도구 목록 또는 이유 |
| `graph.node.entered` | 흐름 노드 진입 | 노드 이름 |
| `agent.handoff` | 에이전트 넘겨주기 | 보낸 쪽, 받는 쪽, 파일 |
| `approval.requested` / `approval.resolved` | 승인 | 항목, 결과(승인/거절/수정/한마디) |
| `run.max_turns` | 턴 한도 | 턴 수 |
| `render.output` | 결과 파일 생성 | 파일 경로 |

모든 사용자 정의 이벤트는 `data.slot`(뇌, 손, MCP, 스킬, 승인, 기억, 결과 화면)을 넣습니다. Theater는 이 값으로 부품에 불을 켭니다.

## 6. 범위 밖

| 범위 밖 | 이유 |
|---|---|
| 코딩 에이전트(코드 실행 도구) | 수업 목표가 아님. 위험 |
| 파일 삭제 기능 | 안전 원칙 |
| 원본 폴더에 적용하는 스크립트 | 학생이 집에서 직접 판단 |
| 노드 그래프 편집기 | 보기 전용으로 충분 |
| LangChain / LangGraph | 이번 키트는 aisuite만 사용(`docs/05`) |
| 배포, 로그인, 다중 사용자 서버 | 각자 노트북에서 로컬 실행 |
| OAuth가 필요한 MCP(Spotify, Notion, Figma 원격 등) | 16명이 수업 중에 설정하기 어려움 |
| Fetch MCP | 새 버전 Node(22 이상)가 필요하고, 처음 실행할 때 설치 메시지가 연결을 깸 → `tavily_extract`로 대체 |
| metmuseum.org 웹페이지 읽기 | 봇 확인 화면으로 막힘 → API 사용 |
| 학생 PC에서 Playwright | 설치가 무겁고 불안정 → 강사 시연만 |
| 음성·이미지 생성 | 1~2시간차 범위 밖. 3~4시간차 개인 확장 |
