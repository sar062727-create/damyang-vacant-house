"""
담양군 빈집 데이터 지오코딩 스크립트
- 입력: damyang_raw.csv (405건, '위치주소(지번 비공개)' 컬럼에 리 단위 주소)
- 출력: damyang_geocoded.csv (위도/경도 컬럼 추가)

사용법:
1. 아래 KAKAO_API_KEY 에 본인의 REST API 키를 넣는다.
2. python geocode_damyang.py 실행
3. 같은 폴더에 damyang_geocoded.csv 가 생성된다.

주의:
- 카카오 로컬 API는 초당 호출 제한이 있어서, 요청 사이에 짧은 대기(time.sleep)를 둔다.
- 리 단위 주소는 카카오 주소 검색에서 정확히 안 잡힐 수 있어서,
  실패하면 "읍/면"까지만 잘라서 재시도하는 fallback을 넣었다.
"""

import time
import requests
import pandas as pd

KAKAO_API_KEY = "84f2e7c1a69f6d5985c4ffc64ace3ba2"  # <-- 본인 키로 교체

INPUT_CSV = "damyang_raw.csv"
OUTPUT_CSV = "damyang_geocoded.csv"
ADDR_COL = "위치주소(지번 비공개)"


def geocode_address(address: str, api_key: str):
    """카카오 주소 검색 API로 위도/경도를 반환. 실패하면 (None, None)."""
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {"query": address}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        docs = data.get("documents", [])
        if docs:
            lon = float(docs[0]["x"])  # 경도
            lat = float(docs[0]["y"])  # 위도
            return lat, lon
    except Exception as e:
        print(f"  [오류] {address}: {e}")

    return None, None


def geocode_with_fallback(address: str, api_key: str):
    """리 단위 주소가 안 잡히면, 읍/면 단위까지만 잘라서 재시도."""
    lat, lon = geocode_address(address, api_key)
    if lat is not None:
        return lat, lon, "정확(리 단위)"

    # "전라남도 담양군 담양읍 담주리" -> "전라남도 담양군 담양읍" 로 축소
    parts = address.split()
    if len(parts) >= 3:
        shorter = " ".join(parts[:3])
        lat, lon = geocode_address(shorter, api_key)
        if lat is not None:
            return lat, lon, "근사(읍면 단위)"

    return None, None, "실패"


def main():
    df = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
    unique_addrs = sorted(df[ADDR_COL].dropna().unique())
    print(f"고유 주소 {len(unique_addrs)}건 지오코딩 시작")

    results = {}
    for i, addr in enumerate(unique_addrs, 1):
        lat, lon, quality = geocode_with_fallback(addr, KAKAO_API_KEY)
        results[addr] = (lat, lon, quality)
        status = "OK" if lat is not None else "FAIL"
        print(f"[{i}/{len(unique_addrs)}] {status:4s} {quality:12s} {addr} -> ({lat}, {lon})")
        time.sleep(0.15)  # 초당 호출 제한 방지용 살짝 대기

    df["위도"] = df[ADDR_COL].map(lambda a: results.get(a, (None, None, None))[0])
    df["경도"] = df[ADDR_COL].map(lambda a: results.get(a, (None, None, None))[1])
    df["좌표정확도"] = df[ADDR_COL].map(lambda a: results.get(a, (None, None, None))[2])

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    ok = df["위도"].notna().sum()
    print(f"\n완료: 전체 {len(df)}건 중 {ok}건 좌표 매칭 성공")
    print(f"결과 저장: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
