# (b) 승인 콜백: 하나 거절, 하나 수정
from common import run
import kit
kit.reset(["IMG_1.jpg","IMG_2.jpg","memo.txt","invoice.pdf"])
def appr(s,d):
    if s=="memo.txt": return ("reject",d)
    if s=="IMG_1.jpg": return ("edit","사진/2026-10/IMG_1.jpg")
    return ("approve",d)
kit.APPROVER[0]=appr
a,c,_=run([{"role":"user","content":"이 폴더 파일들을 종류별 폴더로 apply_move로 정리해. 사람이 거절/수정하면 따르고, 끝나면 결과를 한국어로 요약."}],[kit.list_files,kit.apply_move],max_turns=8)
print([x for x in c],"\n",a); print("트리:",kit.tree())
