# agent-kit: 디자인 전공생을 위한 에이전트 워크숍 키트

이 저장소는 디자인 전공 3·4학년 학생들이 AI 에이전트가 어떻게 움직이는지 직접 만들어 보며 이해하는 워크숍 키트입니다.

수업 앞의 2시간 동안은 모두 같은 에이전트 하나(`agents/my-agent`)를 키웁니다. 처음에는 말만 하는 챗봇에서 시작해서 성격, 도구, 스킬, 승인, MCP, 팀을 한 단계씩 붙이고, 마지막에는 폴더를 정리하고 미술관 작품으로 전시회 페이지를 만드는 에이전트가 됩니다. 단계마다 설정 파일에 한 줄이 늘고, 그 줄은 화면의 부품 창에서 켜거나 파일을 직접 고쳐서 바꿉니다.

뒤의 2시간에는 이 부품들을 바꿔 끼워서 각자의 에이전트를 만들어 봅니다.

**수업에서 순서대로 따라 할 때는 [GUIDE.md](GUIDE.md)를 봅니다.** 준비부터 6단계까지, 각 단계에서 무엇을 켜고 무엇을 말해 보는지, 처음 보는 개념은 무엇인지 차례로 적어 두었습니다. 이 README는 키트 전체를 한눈에 보기 위한 안내입니다.

## 빠르게 시작하기

자세한 설명은 [GUIDE.md의 0. 준비](GUIDE.md#0-준비)에 있습니다.

1. 키트를 내려받고(ZIP이면 압축을 풀고) Cursor에서 **File → Open Folder**로 `agent-kit` 폴더를 엽니다.
2. **Terminal → New Terminal**로 터미널을 열고 uv를 설치합니다. 설치가 끝나면 터미널을 닫았다가 새로 엽니다.
   - Mac: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
3. 키 두 개를 받습니다. 각자 자기 키를 사용하고 서비스 화면에서 사용량 조건을 확인합니다.
   - Z.ai: https://z.ai/model-api 에서 가입하고, https://z.ai/manage-apikey/apikey-list 에서 키를 만듭니다.
   - Tavily: https://app.tavily.com/home 에서 가입하고 `tvly-`로 시작하는 키를 복사합니다.
4. `cp .env.example .env`(Windows는 `copy .env.example .env`)로 `.env`를 만들고, `=` 뒤에 키를 붙여 넣습니다.
   - `ZAI_API_KEY`: Z.ai 키
   - `TAVILY_API_KEY`: Tavily 키. 키만 넣는 것을 권하고, Tavily MCP 주소(`https://mcp.tavily.com/mcp/?tavilyApiKey=...`) 전체를 넣어도 됩니다.
5. `uv run app.py`로 켭니다. 처음 한 번은 1~2분 걸립니다. 브라우저에 대시보드가 열리고, 위쪽의 "모델 ... 키 있음", "Tavily 키 있음"을 확인하고 대화창에 "안녕"을 보내 실제 답이 오는지 확인합니다. 키 표시는 인증 성공을 뜻하지 않습니다.
6. 공통 실습에서는 개인 다운로드를 쓰지 않습니다. 화면 위쪽의 **폴더 고르기 → 샘플 폴더 → 사본 만들기**를 누릅니다. 에이전트는 이 사본(실습 폴더)에서만 일합니다. 샘플 원본을 보존하므로 언제든 같은 시작 상태로 다시 만들 수 있습니다.
   - 사본 위치: Mac `~/agent-workshop/copy`, Windows `C:\Users\내이름\agent-workshop\copy`

끌 때는 터미널에서 Ctrl+C를 누릅니다.

## 화면

| 칸 | 무엇이 보이나 |
|---|---|
| 대화 (왼쪽) | 에이전트가 하는 말입니다. 승인 카드와 오류 카드(어느 단계에서, 무슨 일이, 무엇을 하면 되는지)도 여기에 뜹니다 |
| 루프 (가운데) | 에이전트가 하는 행동입니다. 턴마다 생각, 도구, 결과가 한 장씩 쌓입니다. 팀 실행에서는 에이전트마다 칸이 나뉘고, 그 사이에 넘겨주기가 보입니다 |
| 부품 (오른쪽) | 도구, 스킬, MCP, 승인, 루프 조절을 켜고 끄는 곳입니다. 체크하면 `agents/my-agent/agent.yaml`이나 `mcp.json`의 한 줄이 바뀝니다. 파일을 직접 고쳐도 몇 초 안에 화면이 따라 바뀝니다 |

실행·재시도·승인 대기 중에는 새 메시지 전송과 팀 실행이 막힙니다. 승인 카드는 계속 조작할 수 있습니다. 계획표의 ✏️는 목적지 폴더를 드롭다운으로 선택하며 파일 이름을 유지합니다.

위쪽의 **팀 실행** 버튼은 6단계에서 씁니다. 입력창에 요청을 적고 보내기 대신 팀 실행을 누릅니다. 나의 에이전트가 먼저 폴더를 정리하고, 미리 만들어 둔 도슨트가 이어서 갤러리를 만듭니다.

## 단계 요약

| 단계 | 붙이는 부품 | 켜는 것 | 말해 볼 문장 |
|---|---|---|---|
| 1 | 성격 | `persona.md`의 "성격·말버릇" 칸 고치기 | 내 폴더에 뭐가 있어? |
| 2 | 도구 | `list_files`, `peek_file`, `file_info` | 내 폴더를 보고 주인이 어떤 사람인지 추리해 줘. |
| 3 | 스킬 | `propose_plan`, 스킬 `curator` | 이 폴더를 정리할 계획을 세우고 저장해 줘. |
| 4 | 승인 | `move_files`와 그 옆 승인 칸 | 계획대로 옮겨 줘. |
| 5 | MCP | MCP의 Tavily, `web_search`, `web_read`, `write_file`과 승인 칸, 스킬 `research-note` | 요즘 타이포그래피 포스터 트렌드를 찾아서 리서치 노트로 남겨 줘. |
| 6 | API와 팀 | 팀 실행 버튼 | 이 샘플 폴더를 정리하고, 어울리는 미술관 작품으로 전시회를 열어 줘. |

GUIDE.md 각 단계에는 성공 확인과 접힌 Cursor 도움말·오류 질문 예시가 있습니다. 5단계 뒤에는 도구·스킬·MCP를 비교하는 5분 정리 시간이 있습니다.

단계별로 `agent.yaml`에 쌓이는 모습은 다음과 같습니다.

```yaml
# 2단계
tools: [list_files, peek_file, file_info]
# 3단계
tools: [list_files, peek_file, file_info, propose_plan]
skills: [curator]
# 4단계
tools: [list_files, peek_file, file_info, propose_plan, move_files]
ask_before: [move_files]
# 5단계 (mcp.json에서 tavily도 켭니다)
tools: [list_files, peek_file, file_info, propose_plan, move_files, web_search, web_read, write_file]
skills: [curator, research-note]
ask_before: [move_files, write_file]
```

## 폴더 지도

```
app.py                      대시보드를 켜는 파일입니다. 학생은 이것만 실행합니다
config.yaml                 누구와 대화할지(my-agent), 팀 짝(docent), 모델 이름, 사본 폴더 위치
mcp.json                    웹 검색(Tavily MCP)의 주소와 켜고 끄기
.env                        키를 적는 파일입니다. 저장소에 올라가지 않습니다. .env.example 이 견본입니다
GUIDE.md                    수업에서 따라 하는 단계별 안내

agents/my-agent/            학생이 키우는 에이전트입니다. 처음에는 말만 합니다
  agent.yaml                도구 목록, 스킬, 승인, 루프 조절
  persona.md                위는 기본 규칙(미리 적혀 있음), 아래는 성격·말버릇(학생이 씀)
agents/docent/              팀 실행용으로 미리 만들어 둔 도슨트입니다. 갤러리를 맡습니다

tools/                      도구입니다. 함수 하나가 할 수 있는 일 하나입니다
  files.py                  폴더 목록, 앞부분 보기, 파일 정보
  move.py                   정리 계획, 파일 옮기기, 되돌리기
  write.py                  마크다운 노트 만들기
  web.py                    웹 검색과 페이지 읽기. 접속 주소는 mcp.json 에서 읽습니다
  met.py                    메트로폴리탄 미술관 공개 API. 작품 정보와 갤러리 HTML은 코드가 채웁니다
  clock.py                  지금 시각
  gallery_template.html     갤러리 페이지의 모양

skills/curator/SKILL.md         폴더를 전시실로 나누는 규칙
skills/research-note/SKILL.md   리서치 노트의 구성(한 줄 요약, 핵심, 출처 표, 더 물어볼 질문)

engine/                     루프, 승인, 화면을 담당합니다. 수업 중에는 고치지 않습니다
sample_downloads/           연습용으로 만들어 둔 가상의 다운로드 폴더
tests/                      키 없이 도는 Python 시험: `uv run pytest`. 화면 로직: `node --test tests/dashboard.test.cjs`
docs/                       수업 설계 메모입니다
prototype/                  키트를 만들기 전에 돌렸던 기술 확인 스크립트
```

실행할 때마다 `runs/<시간>/trace.jsonl`에 루프 기록이 쌓입니다. 이 폴더는 저장소에 올라가지 않습니다.

## 안전장치

- 에이전트는 사본 폴더 안에서만 파일을 보고, 옮기고, 새로 만듭니다. 원본 폴더에는 쓰지 않습니다.
- 파일을 지우는 도구는 없습니다. 옮길 때 같은 이름이 있으면 덮어쓰지 않고 `_2`를 붙입니다.
- 옮긴 것은 **되돌리기** 버튼으로 원래 자리로 돌릴 수 있습니다. 옮기고 나서 비어 버린 폴더만 정리합니다. `write_file`로 만든 노트는 되돌리기로 지우지 않습니다.
- 에이전트가 파일을 볼 때 AI 서버로 가는 것은 파일 이름과 앞부분(글은 앞 500자, 그림은 크기)입니다. 그림 내용은 보내지 않습니다.
- 사본을 만들 때 통장, 여권, 계약처럼 민감해 보이는 이름과 20MB가 넘는 파일은 기본으로 빠집니다.
- 키는 `.env`에서만 읽고, 화면과 기록에는 가려서 남깁니다.

## 새 도구를 더하는 법

1. `tools/`에 파일을 만들거나, 있는 파일에 함수를 추가합니다.
2. 함수 바로 아래 설명(독스트링)은 영어로 적습니다. 모델이 이 설명을 읽고 언제 이 도구를 쓸지 고릅니다. 학생에게 보이는 오류 문장은 한국어로 적어도 됩니다.
3. 함수 위에 `@tool(group="기타")`를 붙입니다. `needs="TAVILY_API_KEY"`처럼 적으면, 그 키가 없을 때 도구가 이유와 함께 꺼집니다.
4. `agents/my-agent/agent.yaml`의 `tools:`에 함수 이름을 넣습니다. 화면의 체크박스와 같습니다.

파일을 지우는 도구는 만들지 않습니다. 도구가 실패하면 예외를 던지기보다 `error: 이유`로 시작하는 글을 돌려줍니다. 예외를 던져도 키트가 잡아서 글로 바꾸지만, 이유를 적어 주면 모델이 다른 방법을 고르기 쉽습니다.

예시 (`tools/weather.py`):

```python
from tools import tool

@tool(group="기타")
def get_weather(city: str) -> str:
    """Get today's weather for a city."""
    return "맑음, 21도"
```

## 용어

| 용어 | 뜻 |
|---|---|
| 모델 | 글을 읽고 글로 답하는 AI입니다. 이 키트에서는 Z.ai의 GLM을 씁니다 |
| 에이전트 | 목표를 받으면 할 일을 고르고, 도구로 해 보고, 결과를 보고 다음을 정하는 AI입니다 |
| 도구 | 에이전트가 부르는 함수입니다. 이 키트에서는 `tools/`에 있습니다 |
| 루프와 턴 | 고르기, 해 보기, 결과 보기를 반복하는 것이 루프이고, 그 한 바퀴가 턴입니다 |
| 스킬 | 필요할 때 읽어 오는 업무 매뉴얼입니다. `skills/<이름>/SKILL.md` |
| 승인 | 실행 전에 사람이 확인하는 자리입니다. `agent.yaml`의 `ask_before` |
| MCP | 남이 만든 도구를 연결하는 표준 방식입니다. 여기서는 `mcp.json`의 Tavily |
| API | 프로그램끼리 정보를 주고받는 창구입니다. 여기서는 미술관 공개 API(`tools/met.py`) |

더 자세한 풀이는 [docs/00_glossary.md](docs/00_glossary.md)에 있습니다.

## 지금 상태 (2026-10-17)

| 항목 | 상태 |
|---|---|
| 시험 | Python: `uv run pytest` / 화면 로직(Node.js 사용 가능 시): `node --test tests/dashboard.test.cjs` |
| 실제 실행 | Mac에서 Z.ai(GLM-4.5-Flash), Tavily, 미술관 API로 1단계부터 6단계까지 끝까지 돌려 보았습니다 |
| 걸리는 시간(실측) | 2단계 30~60초, 3단계 계획 30~90초(파일 39개), 4단계 거절 4초와 승인 17초, 5단계 50~90초, 팀 실행 80초 안팎 |
| 확인하지 못한 것 | Windows에서의 실제 실행, 16명이 같은 와이파이에서 동시에 쓰는 상황, Z.ai와 Tavily 가입 화면의 정확한 메뉴 이름 |

## 알려진 한계

- 모델이 늘 지시대로 움직이지는 않습니다. 짧고 애매하게 말하면(예: "정리 계획 짜줘") 계획을 대화창에 글로만 보여 주고 저장하지 않을 때가 있습니다. 원하는 것을 분명하게 다시 말하면 됩니다.
- MCP는 Tavily 한 곳만 연결되어 있습니다. `mcp.json`에 다른 서버를 적는 것만으로는 도구가 생기지 않고, `tools/`에 그 도구를 부르는 함수가 있어야 합니다.
- 팀 실행의 순서는 프로그램이 정합니다(나의 에이전트 다음 도슨트). 에이전트끼리 스스로 일을 나눠 맡는 방식은 들어 있지 않습니다.
- `docs/01`~`06`은 키트를 지금 구조로 바꾸기 전의 설계 메모라서, 예전 설명(L1~L4 스위치 등)이 남아 있습니다. 수업의 기준은 GUIDE.md와 이 README입니다.

## 문서

| 문서 | 내용 |
|---|---|
| [GUIDE.md](GUIDE.md) | 수업에서 따라 하는 단계별 안내 |
| [docs/00_glossary.md](docs/00_glossary.md) | 용어 풀이 |
| [docs/07_loop_dashboard_requirements.md](docs/07_loop_dashboard_requirements.md) | 루프, 대시보드, 요구사항, 수업 롤플레이 메모 |
| [docs/01_workshop_overview.md](docs/01_workshop_overview.md) 이하 | 수업 설계 초안(예전 설명이 섞여 있습니다) |
| [prototype/](prototype/README.md) | 키트 이전의 기술 확인 |

API 키와 `.env`는 이 저장소에 넣지 않습니다.
