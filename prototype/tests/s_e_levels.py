# (e) L1 도구없음 vs L2 고정순서 vs L3 도구선택, 각 1회
from common import run, client, MODEL
import kit
kit.reset(["IMG_9.jpg","report.pdf"])
q="내 다운로드 폴더에 뭐 있어? 한 줄로."
r=client.chat.completions.create(model=MODEL,messages=[{"role":"user","content":q}]); print("L1:",r.choices[0].message.content)
r=client.chat.completions.create(model=MODEL,messages=[{"role":"user","content":q+"\n목록:\n"+kit.list_files()}]); print("L2(코드가 list_files 먼저 실행):",r.choices[0].message.content)
a,c,_=run([{"role":"user","content":q}],[kit.list_files,kit.read_file],max_turns=3); print("L3:",c,a)
