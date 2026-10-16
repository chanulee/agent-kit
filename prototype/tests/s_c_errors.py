# (c) 도구 에러(없는 경로, Met 결과 없음)에도 루프가 안 죽는지
from common import run
import kit
kit.reset(["a.txt"])
a,c,_=run([{"role":"user","content":"1) read_file로 'nope/ghost.txt'를 읽어봐. 2) met_search로 'zxqvplm' 검색해봐. 3) 각 결과를 한국어로 보고해."}],[kit.read_file,kit.met_search],max_turns=5)
print(c,"\n",a)
