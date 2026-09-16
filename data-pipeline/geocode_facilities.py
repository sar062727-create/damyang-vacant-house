"""
담양군 읍면별 주변 시설(학교·편의점·관광명소·카페) 개수 + 실제 이름 + 좌표 조회 스크립트 (v4)
- 입력: eupmyeon_centers.csv (12개 읍면의 대표 위도/경도)
- 출력: eupmyeon_facilities.csv (읍면별 카테고리 개수 + 밀도 + 용도 점수 + 대표 장소 이름/좌표)

v4에서 바뀐 점:
- 관광명소, 학교는 이름뿐 아니라 좌표(위도·경도)도 같이 저장한다.
  프론트엔드 카드의 미니 지도에서 실제 위치에 마커를 찍기 위함.
  좌표는 "이름1|위도1|경도1;;이름2|위도2|경도2" 형태의 문자열로 저장하고,
  프론트엔드에서 split해서 사용한다 (CSV 한 칸에 여러 장소를 담기 위한 방식).

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
NAME_SAMPLE_SIZE = 5  # 카드에 보여줄 대표 장소 이름/좌표 개수

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

# 이름+좌표까지 같이 저장할 카테고리 (카드 미니 지도에 실제로 마커로 찍을 것들)
CATEGORIES_WITH_NAMES = ["학교수", "관광명소수"]


def search_places(lat, lon, category_code, keyword, api_key):
    """특정 좌표 반경 내 카테고리+키워드 장소를 검색해서
    (개수, [(이름, 위도, 경도), ...]) 튜플을 반환한다."""
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
        places = [
            (d["place_name"], d["y"], d["x"])  # y=위도, x=경도 (카카오 응답 형식)
            for d in data.get("documents", [])
        ]
        return total, places
    except Exception as e:
        print(f"  [오류] ({lat},{lon}) {keyword}: {e}")
        return None, []


def encode_places(places, limit):
    """장소 목록을 '이름|위도|경도;;이름|위도|경도' 문자열로 인코딩.
    이름에 있을 수 있는 구분자 문자는 미리 제거해 파싱이 깨지지 않게 한다."""
    entries = []
    for name, lat, lon in places[:limit]:
        safe_name = name.replace("|", " ").replace(";;", " ")
        entries.append(f"{safe_name}|{lat}|{lon}")
    return ";;".join(entries)


def compute_scores(row):
    """규칙 기반 점수화.
    - 주거적합점수: 학교·마트·편의점 개수를 그대로 합산 (동네 생활 인프라)
    - 관광숙박적합점수: 관광명소는 가중치를 낮추고(0.5), 공원과 카페 밀도를 더해서
      '조용한 자연 근처'와 '카페 상권'을 함께 반영"""
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
    print(f"{len(df)}개 읍면에 대해 시설 조회 시작 (반경 {RADIUS_M}m)")

    for col in CATEGORIES:
        df[col] = None
    for col in CATEGORIES_WITH_NAMES:
        df[col.replace("수", "목록")] = None
        df[col.replace("수", "좌표")] = None

    for i, row in df.iterrows():
        eup = row["읍면"]
        lat, lon = row["위도"], row["경도"]
        print(f"[{i+1}/{len(df)}] {eup} 조회 중...")
        for col, (code, keyword) in CATEGORIES.items():
            count, places = search_places(lat, lon, code, keyword, KAKAO_API_KEY)
            df.at[i, col] = count
            if col in CATEGORIES_WITH_NAMES:
                name_col = col.replace("수", "목록")
                coord_col = col.replace("수", "좌표")
                names = [p[0] for p in places]
                df.at[i, name_col] = ", ".join(names[:NAME_SAMPLE_SIZE])
                df.at[i, coord_col] = encode_places(places, NAME_SAMPLE_SIZE)
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
    print(df[["읍면", "학교수", "학교목록", "관광명소수", "관광명소목록", "추천용도"]].to_string())
    print()
    print("좌표 인코딩 샘플 (담양읍 관광명소좌표):")
    sample = df[df["읍면"] == "담양읍"]["관광명소좌표"]
    if len(sample) > 0:
        print(sample.iloc[0])


if __name__ == "__main__":
    main()

