"""
담양군 읍면별 주변 시설 조회 스크립트 (v2)
- 입력: eupmyeon_centers.csv (12개 읍면의 대표 위도/경도)
- 출력: eupmyeon_facilities.csv (읍면별 카테고리 개수 + 밀도 + 용도 점수)

v1에서 바뀐 점:
1. "공원"을 관광명소(AT4)에서 분리해서 따로 센다 (키워드 검색만, 카테고리 코드 없음)
2. 카페는 개수 대신 "밀도"(㎢당 카페 수)로 계산해서, 검색 반경이 같아도
   실제로 카페가 몰려있는 동네인지 더 정확히 구분한다
3. 점수 계산에서 관광명소 가중치를 낮춰서, 모든 읍면이 관광 쪽으로
   쏠리던 문제(v1 결과)를 완화한다

사용법:
1. 아래 KAKAO_API_KEY 에 본인의 REST API 키를 넣는다.
2. python geocode_facilities.py 실행
3. 같은 폴더에 eupmyeon_facilities.csv 가 생성된다.
"""

import time
import math
import requests
import pandas as pd

KAKAO_API_KEY = "84f2e7c1a69f6d5985c4ffc64ace3ba2"  # <-- 본인 키로 교체

INPUT_CSV = "eupmyeon_centers.csv"
OUTPUT_CSV = "eupmyeon_facilities.csv"
RADIUS_M = 3000  # 검색 반경 (미터)
SEARCH_AREA_KM2 = math.pi * (RADIUS_M / 1000) ** 2  # 반경 3km 원의 면적 ≈ 28.27 km²

# 카카오 공식 카테고리 코드 + 키워드 검색용 검색어
# 카테고리 코드가 없는 항목(공원)은 code를 None으로 두고 키워드만으로 검색한다
CATEGORIES = {
    "학교수": ("SC4", "학교"),
    "편의점수": ("CS2", "편의점"),
    "마트수": ("MT1", "마트"),
    "관광명소수": ("AT4", "관광명소"),
    "카페수": ("CE7", "카페"),
    "공원수": (None, "공원"),
}


def count_category(lat, lon, category_code, keyword, api_key, return_names=False):
    """특정 좌표 반경 내 카테고리+키워드 장소 개수를 반환 (최대 45건까지 정확, 그 이상은 45로 표기).
    return_names=True 면 (개수, 장소이름목록) 튜플을 반환한다."""
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {
        "query": keyword,
        "x": lon,
        "y": lat,
        "radius": RADIUS_M,
        "page": 1,
        "size": 15,
    }
    if category_code:
        params["category_group_code"] = category_code

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        total = data.get("meta", {}).get("total_count", 0)
        if return_names:
            names = [d["place_name"] for d in data.get("documents", [])]
            return total, names
        return total
    except Exception as e:
        print(f"  [오류] ({lat},{lon}) {keyword}: {e}")
        return (None, []) if return_names else None


def compute_scores(row):
    """v2 점수화 규칙.
    - 주거적합점수: 학교·마트·편의점 개수를 그대로 합산 (동네 생활 인프라)
    - 관광숙박적합점수: 관광명소는 가중치를 낮추고(0.5), 공원과 카페 밀도를 더해서
      '조용한 자연 근처'와 '카페 상권'을 함께 반영
    이 가중치는 임의로 정한 첫 버전 규칙이라, 실제 데이터를 보면서 계속 조정하면 됨."""
    school = row["학교수"] or 0
    mart = row["마트수"] or 0
    cvs = row["편의점수"] or 0
    attraction = row["관광명소수"] or 0
    park = row["공원수"] or 0
    cafe_density = row["카페밀도"] or 0

    residential = school * 3 + mart * 2 + cvs * 1
    tourism = attraction * 0.5 + park * 2 + cafe_density * 5

    return pd.Series({"주거적합점수": round(residential, 1), "관광숙박적합점수": round(tourism, 1)})


def main():
    df = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
    print(f"{len(df)}개 읍면에 대해 시설 조회 시작 (반경 {RADIUS_M}m, 면적 {SEARCH_AREA_KM2:.1f}km²)")

    for col in CATEGORIES:
        df[col] = None

    for i, row in df.iterrows():
        eup = row["읍면"]
        lat, lon = row["위도"], row["경도"]
        print(f"[{i+1}/{len(df)}] {eup} 조회 중...")
        for col, (code, keyword) in CATEGORIES.items():
            count = count_category(lat, lon, code, keyword, KAKAO_API_KEY)
            df.at[i, col] = count
            time.sleep(0.15)

    # 카페 밀도 = 카페 개수 / 검색 면적(km²)
    df["카페밀도"] = df["카페수"].apply(lambda c: round((c or 0) / SEARCH_AREA_KM2, 2))

    score_df = df.apply(compute_scores, axis=1)
    df = pd.concat([df, score_df], axis=1)

    df["추천용도"] = df.apply(
        lambda r: "주거" if r["주거적합점수"] >= r["관광숙박적합점수"] else "관광·숙박(게스트하우스/카페)",
        axis=1,
    )

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n완료: {OUTPUT_CSV} 저장")
    print(df[["읍면", "학교수", "마트수", "편의점수", "관광명소수", "공원수", "카페수", "카페밀도",
               "주거적합점수", "관광숙박적합점수", "추천용도"]].to_string())

    # 확인용: 담양읍의 관광명소 목록을 실제로 출력 (죽녹원 등이 어떻게 잡히는지 확인)
    print("\n--- 담양읍 관광명소 목록 (반경 3km 이내, 상위 15개) ---")
    damyang_row = df[df["읍면"] == "담양읍"].iloc[0]
    _, names = count_category(
        damyang_row["위도"], damyang_row["경도"], "AT4", "관광명소", KAKAO_API_KEY, return_names=True
    )
    for n in names:
        print(f"  - {n}")


if __name__ == "__main__":
    main()
