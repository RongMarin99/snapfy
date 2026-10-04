import urllib.parse
import re
import httpx

def sanitize_url(url: str) -> str:
    if not url:
        return ""
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(url).strip())
    try:
        parsed = urllib.parse.urlparse(cleaned)
        safe_path = urllib.parse.quote(parsed.path, safe="/:[]")
        safe_query = urllib.parse.quote(parsed.query, safe="=&%+!*,;:@$-_.~'/[]")
        return urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc,
            safe_path,
            parsed.params,
            safe_query,
            parsed.fragment
        ))
    except Exception:
        return urllib.parse.quote(cleaned, safe=":/%?&=#+[]@!$'()*;,~-")

def test_breakage():
    url = "https://manifest.googlevideo.com/api/manifest/hls_playlist/expire/1791045416/ei/yNrAav2SH_Ty4-EPnLjT6Aw/ip/203.144.92.99/id/1b6d81545d14f970/itag/616/source/youtube/requiressl/yes/ratebypass/yes/pfa/1/wft/1/sgovp/clen%3D21889716%3Bdur%3D50.466%3Bgir%3Dyes%3Bitag%3D356%3Blmt%3D1788536759963876/rqh/1/hls_chunk_host/rr3---sn-j5hbnh-2oie.googlevideo.com/xpc/EgVo2aDSNQ%3D%3D/cps/206/met/1791023816,/mh/3c/mm/31,29/mn/sn-j5hbnh-2oie,sn-npoe7ndr/ms/au,rdu/mv/m/mvi/3/pl/24/rms/au,au/pcm2/yes/initcwndbps/708875/bui/AWzQHwqWEscPpa5KQlO-FXNiGLxHY8afOx404cnMFLJCyqEwJ4flgqnVX-SZxT4KCRVD54iPgK2-5eCW/spc/I-rgIZGEl8clScpuEvL3j1SQ_OWkEraHF2YDkTTqbPpxFnQ8x-JT8aPzNk7IlgM/vprv/1/playlist_type/DVR/dover/13/txp/440C234/mt/1791023373/fvip/4/short_key/1/keepalive/yes/fexp/51565116,52112905,52184226,52250513/sparams/expire,ei,ip,id,itag,source,requiressl,ratebypass,pfa,wft,sgovp,rqh,xpc,pcm2,bui,spc,vprv,playlist_type/sig/AE0s2JYwRgIhAL_lyq6wkC7wLE_O9DkRrdFm4leWgRoI-P3b9vRGMvWHAiEAw9JJvX8yYxQ4yo3khhnjGPtKl8WFCDg5K1PdqL8CElw%3D/lsparams/hls_chunk_host,cps,met,mh,mm,mn,ms,mv,mvi,pl,rms,initcwndbps/lsig/APaTxxMwRgIhAPhVFm-_XGeIPODQxpcTOeoCnMSh-OheG9hzxcPpjXqkAiEA2f6AvmdrhVCpdrFPPRSZaUq3C6b2OGH8elErB-c1KLs%3D/playlist/index.m3u8"
    
    sanitized = sanitize_url(url)

    print("Original URL len:", len(url))
    print("Sanitized URL len:", len(sanitized))
    print("Are URLs equal?", url == sanitized)

    r_orig = httpx.get(url)
    print("Fetch Original URL Status:", r_orig.status_code)

    r_san = httpx.get(sanitized)
    print("Fetch Sanitized URL Status:", r_san.status_code)

if __name__ == "__main__":
    test_breakage()
