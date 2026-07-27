import sys
import os
sys.path.insert(0, os.path.abspath("."))

import httpx
import asyncio

async def test_vod3():
    manifest_url = "https://vod3.cf.dmcdn.net/sec2(RVF6eb6mH_KN7Ls34pU-R5CDtUHB7yxPEGvYif6yJ0yMq-hTARS2gWHP_UXKqiMFovy2rAPEX10iALTIM6wJ3krtvtb8hogvPjkwsmxu8EApXV_6xSeH2vfSBoHK_aia3qjceVMLupQmhY5Ek3QLguuSqrXnJjvOV0FnybjK6qjcuBOedYLLbSfJ1dXiStcUOR8zeSUgP5gjRzswdqJPrg)/video/fmp4/631247526/h264_aac_hq_vert/1/manifest.m3u8"
    base_cdn = manifest_url.rsplit('/', 1)[0]
    out_file = os.path.abspath("Dailymotion_Real_Downloaded_Video.mp4")

    print("Fetching vod3 manifest:", manifest_url[:80])
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        r = await client.get(manifest_url)
        print("Manifest Status:", r.status_code)
        lines = [line.strip() for line in r.text.splitlines() if line.strip()]
        seg_names = [l for l in lines if not l.startswith("#")]
        print(f"Found {len(seg_names)} segments!")

        init_mp4_url = f"{base_cdn}/init.mp4"
        init_res = await client.get(init_mp4_url)
        print(f"init.mp4 Status: {init_res.status_code} | Size: {len(init_res.content)} bytes")

        with open(out_file, "wb") as outfile:
            if init_res.status_code == 200:
                outfile.write(init_res.content)
            
            for i, seg in enumerate(seg_names[:25], 1):  # Download first 25 segments as test
                seg_url = f"{base_cdn}/{seg}"
                seg_res = await client.get(seg_url)
                if seg_res.status_code == 200:
                    outfile.write(seg_res.content)
                    print(f"Downloaded seg {i}/{len(seg_names)} -> {len(seg_res.content)} bytes")

        print(f"SUCCESS! Output MP4 File written: {out_file} | Size: {os.path.getsize(out_file)/(1024*1024):.2f} MB")

asyncio.run(test_vod3())
