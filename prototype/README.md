# prototype: 기술 검증 시험

수업용 키트를 만들기 전에 "이게 정말 되나?"를 확인한 작은 시험 3개입니다. 키트 자체가 아닙니다.
처음 보는 말은 [용어 풀이](../docs/00_glossary.md)를 보세요.

## 시험 목록

| 파일 | 무엇을 확인하나 | 필요한 것 |
|---|---|---|
| `tests/t1_web.py` | 에이전트가 웹을 검색하고 위키백과를 읽어 요약하나 (Tavily MCP) | Node, `npx` |
| `tests/t2_fs.py` | 에이전트가 가짜 파일 10개를 스스로 계획해서 실제로 옮기나 | 없음 (임시 폴더 사용) |
| `tests/t3_met.py` | 미술관 API에서 공공 도메인 작품을 찾아 추천하나 | 인터넷 |
| `tests/common.py` | 모델 연결, 429/503 재시도, 결과 정리 (세 시험이 같이 씀) | — |

## 준비

1. Python 3.12와 `uv`(또는 pip)를 설치합니다.
2. 필요한 패키지를 설치합니다.

   ```bash
   pip install "aisuite[openai,anthropic,mcp]==0.2.0" requests
   ```

   extras(대괄호 안 이름)는 [확인 필요]입니다. 안 되면 `pip install aisuite==0.2.0 openai anthropic mcp requests`.
3. 시험 1을 돌리려면 Node를 설치하고 Tavily 서버를 미리 한 번 받아 둡니다.

   ```bash
   npx -y tavily-mcp@latest --help
   ```
4. 키를 **환경 변수로만** 넣습니다. 파일에 적지 마세요.

   | 모델 | 넣을 값 |
   |---|---|
   | Gemini (시험에서 쓴 방식) | `GEMINI_API_KEY=...`, `MODEL=openai:gemini-3.5-flash` |
   | Anthropic (아직 시험 안 함) | `ANTHROPIC_API_KEY=...`, `MODEL=anthropic:<모델 ID>` |
   | Tavily (선택) | `TAVILY_API_KEY=...` |

## 실행

```bash
cd prototype/tests
export GEMINI_API_KEY=...        # Windows PowerShell: $env:GEMINI_API_KEY="..."
export MODEL=openai:gemini-3.5-flash
python t1_web.py
python t2_fs.py
python t3_met.py
```

## 결과 읽는 법

| 출력 | 뜻 |
|---|---|
| `call 1 ('tavily_search', ...)` | 에이전트가 고른 도구와 넘긴 값 |
| `[429] 23초 기다리는 중` | 호출 한도에 걸려 기다렸다 다시 시도 |
| `moves 10` | 실제로 옮긴 파일 수 |
| `time 41.7s` | 걸린 시간 |

## 알아 둘 것

| 내용 | 이유 |
|---|---|
| 도구는 오류를 던지지 않고 `"error: ..."` 글을 돌려줍니다 | aisuite는 도구 안 오류를 다시 던져서 루프 전체가 멈춥니다 |
| Gemini는 `gemini:`가 아니라 OpenAI 호환 주소로 부릅니다 | `gemini:` 방식은 도구 호출 때 400 오류가 납니다 |
| 무료 Gemini 키로는 자주 429가 납니다 | 3.8 Flash 하루 20회, 3.5/3.6 Flash 분당 5회 |
| 시험 2는 임시 폴더만 씁니다 | 내 진짜 파일은 건드리지 않습니다. 삭제 도구는 없습니다 |

시험 결과: [logs/2026-10-17_test_log.md](../logs/2026-10-17_test_log.md)
