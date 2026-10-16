# (a) 탐정 -> 큐레이터(SKILL.md) -> 승인 -> 실제 이동 -> 도슨트(Met+Tavily) -> gallery.html
import os
from common import run, STATS
import kit
FILES=["IMG_2031.jpg","Screenshot 1.png","과제3_최종.pdf","receipt_coupang.pdf","setup.dmg","sunflower_ref.jpg"]; kit.reset(FILES)
a1,c1,_=run([{"role":"system","content":"너는 탐정. 파일 목록만 보고 각 파일이 뭔지 한 줄씩 한국어로 추리해."},{"role":"user","content":"다운로드 폴더 추리해줘."}],[kit.list_files],max_turns=3)
print("탐정:",c1,"\n",a1)
skill=open("SKILL.md").read()
a2,c2,_=run([{"role":"system","content":"너는 큐레이터. list_files로 ID를 보고, 아래 규칙대로 apply_move(src=ID번호, dst=폴더/)로 하나씩 옮겨. 끝나면 한 줄 요약.\n"+skill},{"role":"user","content":"탐정 보고:\n"+(a1 or "")[:600]}],[kit.list_files,kit.apply_move],max_turns=10)
print("큐레이터:",[c[0] for c in c2],"\n",a2); print("트리:",kit.tree())
left=kit.unmoved(FILES); print("안 옮긴 파일(코드 확인):", left or "없음")
a3,c3,_=run([{"role":"system","content":"너는 도슨트. 사용자에게 묻지 말고 바로 met_search부터 호출해. met_search로 후보를 받고(필요하면 다른 키워드로 1번 더), 폴더 분위기에 가장 맞는 1점을 고르고, web_search로 그 작품 해설 근거를 1~2번 찾고, write_gallery에 고른 작품의 objectID, 고른 이유 한 줄(다른 후보 대비), 3문장 한국어 해설만 넣어 저장해. HTML은 쓰지 마. sources에는 이번에 web_search/web_read 결과로 실제로 받은 URL만 넣어. 제목·작가·연도·재료는 met_search가 준 Met 값만 써. 웹 자료에 그렇게 쓰여 있지 않으면 Met 연도와 다른 연도를 말하지 마."},{"role":"user","content":"정리된 폴더: "+", ".join(kit.tree())}],[kit.met_search,kit.web_search,kit.write_gallery],max_turns=8)
kit.close_web(); print("web_calls:",len(kit.WEB_CALLS),"met_calls:",len(kit.MET_CALLS),"seen_urls:",len(kit.SEEN_URLS)); print("도슨트:",c3,"\n",a3)
print("gallery exists:",os.path.exists("/workspace/workshop/tests/out/gallery.html"))
