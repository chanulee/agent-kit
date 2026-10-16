# (d) 한글 NFD 파일명 + 공백
import unicodedata
from common import run
import kit
names=[unicodedata.normalize("NFD","졸업 전시 포스터 최종.png"),"과제 2 (수정본).pdf","my file v2 .txt"]
kit.reset(names)
a,c,_=run([{"role":"user","content":"이 폴더 파일을 종류별 폴더(이미지/문서)로 apply_move로 옮기고 결과를 한국어로 한 줄 보고."}],[kit.list_files,kit.apply_move],max_turns=6)
print(c,"\n",a); print("트리:",kit.tree())
