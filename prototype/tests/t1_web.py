import kit
from common import run
ans,calls,dt=run([{"role":"user","content":"Search for Van Gogh Sunflowers, read the Korean Wikipedia article, summarize in 3 Korean sentences with source URL"}],[kit.web_search,kit.web_read])
for i,c in enumerate(calls,1): print("call",i,c)
print(f"time {dt:.1f}s web_calls={len(kit.WEB_CALLS)}\n",ans); kit.close_web()
