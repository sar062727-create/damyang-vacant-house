"""
빈집 개별 데이터(405건) + 읍면별 시설 점수(12개) + 인구·유동인구 + 용도별 점수 합치기
- 입력1: damyang_geocoded.csv (빈집 405건, 위치주소·위도·경도)
- 입력2: eupmyeon_facilities.csv (읍면 12개, 시설 개수·이름 목록)
- 출력: damyang_final.csv (빈집 405건 각각에 용도별 점수가 모두 붙은 최종 파일)

v3에서 바뀐 점:
- "주거 vs 관광·숙박" 둘 중 하나만 추천하던 방식을 버리고,
  주거 / 카페·소품샵 / 게스트하우스·펜션 / 식당·베이커리 4개 용도 점수를
  전부 계산해서 동등하게 나열한다. 사용자가 하려는 용도에 맞는 점수를
  직접 확인할 수 있게 하기 위함.
- 점수는 0~100 사이로 정규화해서, 카테고리 간 비교가 쉽게 만든다.
"""

import pandas as pd

HOUSES_CSV = "damyang_geocoded.csv"
FACILITIES_CSV = "eupmyeon_facilities.csv"
OUTPUT_CSV = "damyang_final.csv"

# 담양군 통계시스템(https://www.damyang.go.kr) 공개 읍면별 인구현황, 공공누리 제4유형
EUPMYEON_POPULATION = {
    "담양읍": 15532,
    "수북면": 4817,
    "대전면": 4341,
    "창평면": 3686,
    "고서면": 3076,
    "봉산면": 2744,
    "금성면": 2655,
    "무정면": 2549,
    "월산면": 2419,
    "대덕면": 1870,
    "용면": 1813,
    "가사문학면": 1195,
}


def normalize(series):
    """0~100 사이로 min-max 정규화."""
    lo, hi = series.min(), series.max()
    if hi == lo:
        return series * 0
    return (series - lo) / (hi - lo) * 100


def compute_floating_population_index(df):
    """유동인구 수준(추정) 계산 — 관광명소·카페밀도 기반 군내 상대 등급 + 순위."""
    attraction_norm = normalize(df["관광명소수"])
    cafe_norm = normalize(df["카페밀도"])
    raw_score = attraction_norm * 0.5 + cafe_norm * 0.5

    rank = raw_score.rank(ascending=False, method="min").astype(int)
    total = len(df)

    def to_grade(score):
        if score >= 66:
            return "상"
        elif score >= 33:
            return "중"
        else:
            return "하"

    grade = raw_score.apply(to_grade)
    rank_label = rank.astype(str) + f"/{total}위"
    return grade, rank_label, raw_score


def compute_usage_scores(df):
    """용도별(주거/카페·소품샵/게스트하우스·펜션/식당·베이커리) 점수를 각각 0~100으로 계산.
    각 용도가 중요하게 보는 지표에 가중치를 다르게 줘서 원점수를 만들고,
    그 다음 12개 읍면 사이에서 0~100으로 정규화한다 (담양군 내 상대 비교)."""
    school_n = normalize(df["학교수"])
    mart_n = normalize(df["마트수"])
    cvs_n = normalize(df["편의점수"])
    attraction_n = normalize(df["관광명소수"])
    park_n = normalize(df["공원수"])
    cafe_density_n = normalize(df["카페밀도"])
    population_n = normalize(df["인구수"])
    floating_n = df["유동인구원점수"]  # 이미 0~100로 정규화되어 있음
    # '조용함'은 유동인구가 적을수록 높은 점수 (역방향)
    quietness_n = 100 - floating_n

    residential = (
        school_n * 0.30 + mart_n * 0.25 + cvs_n * 0.20 + population_n * 0.25
    )
    cafe_shop = (
        cafe_density_n * 0.40 + attraction_n * 0.25 + floating_n * 0.35
    )
    guesthouse = (
        attraction_n * 0.45 + park_n * 0.30 + quietness_n * 0.25
    )
    restaurant = (
        floating_n * 0.35 + attraction_n * 0.25 + population_n * 0.20 + mart_n * 0.20
    )

    return pd.DataFrame({
        "주거점수": residential.round(1),
        "카페소품샵점수": cafe_shop.round(1),
        "게스트하우스펜션점수": guesthouse.round(1),
        "식당베이커리점수": restaurant.round(1),
    })


# 각 용도 점수에 기여하는 지표들 — (지표 표시용 이름, 데이터 컬럼명, 가중치) 순.
# compute_usage_scores 의 가중치와 반드시 동일하게 맞춘다.
USAGE_FACTORS = {
    "주거점수": [
        ("학교 수", "학교수", 0.30),
        ("마트 수", "마트수", 0.25),
        ("인구 규모", "인구수", 0.25),
        ("편의점 수", "편의점수", 0.20),
    ],
    "카페소품샵점수": [
        ("카페 밀도", "카페밀도", 0.40),
        ("유동인구 수준", "유동인구원점수", 0.35),
        ("관광명소 수", "관광명소수", 0.25),
    ],
    "게스트하우스펜션점수": [
        ("관광명소 수", "관광명소수", 0.45),
        ("공원 수", "공원수", 0.30),
        ("한적함(낮은 유동인구)", "유동인구원점수", 0.25),
    ],
    "식당베이커리점수": [
        ("유동인구 수준", "유동인구원점수", 0.35),
        ("관광명소 수", "관광명소수", 0.25),
        ("인구 규모", "인구수", 0.20),
        ("마트 수", "마트수", 0.20),
    ],
}

USAGE_SCORE_COLS = ["주거점수", "카페소품샵점수", "게스트하우스펜션점수", "식당베이커리점수"]


def build_top_usage_reason(row):
    """4개 용도 점수 중 1위 용도를 찾아, 그 근거(기여 지표 상위 2개)를 문장으로 만든다.
    반환값: (1위 용도명, 근거 문장)"""
    scores = {col: row[col] for col in USAGE_SCORE_COLS}
    top_usage = max(scores, key=scores.get)

    factors = USAGE_FACTORS[top_usage]
    # 이 읍면에서 해당 지표가 정규화 기준 몇 위인지는 개별 계산이 필요 없고,
    # 가중치가 큰 상위 2개 지표를 근거로 제시한다 (그 용도 점수식에서 가장 중요한 요소이므로).
    top_factors = sorted(factors, key=lambda f: f[2], reverse=True)[:2]
    factor_desc = ", ".join(
        f"{label} {row[col]:,.0f}" if col != "유동인구원점수" else f"{label} 상위권"
        for label, col, _ in top_factors
    )
    usage_label = top_usage.replace("점수", "")
    reason = f"{usage_label} 점수가 가장 높습니다 ({factor_desc} 기준)"
    return usage_label, reason


def main():
    houses = pd.read_csv(HOUSES_CSV, encoding="utf-8-sig")
    facilities = pd.read_csv(FACILITIES_CSV, encoding="utf-8-sig")

    # 실제 인구수 매핑
    facilities["인구수"] = facilities["읍면"].map(EUPMYEON_POPULATION)

    # 유동인구 수준(추정) 계산 — 등급 + 군내 순위 + 원점수(용도 점수 계산에 재사용)
    grade, rank_label, floating_raw = compute_floating_population_index(facilities)
    facilities["유동인구수준(추정)"] = grade
    facilities["유동인구순위(추정)"] = rank_label
    facilities["유동인구원점수"] = floating_raw

    # 용도별 점수 계산
    usage_scores = compute_usage_scores(facilities)
    facilities = pd.concat([facilities, usage_scores], axis=1)

    # 1위 용도 + 근거 문장 생성
    top_usage_list = []
    top_reason_list = []
    for _, row in facilities.iterrows():
        usage_label, reason = build_top_usage_reason(row)
        top_usage_list.append(usage_label)
        top_reason_list.append(reason)
    facilities["1위용도"] = top_usage_list
    facilities["1위용도근거"] = top_reason_list

    # 빈집 주소에서 읍면 이름 추출
    houses["읍면"] = houses["위치주소(지번 비공개)"].str.extract(r"담양군 (\S+[읍면])")

    # 읍면 기준으로 합치기
    merge_cols = ["읍면", "인구수", "유동인구수준(추정)", "유동인구순위(추정)",
                  "관광명소수", "카페밀도", "학교수", "마트수", "편의점수",
                  "학교목록", "관광명소목록", "학교좌표", "관광명소좌표",
                  "주거점수", "카페소품샵점수", "게스트하우스펜션점수", "식당베이커리점수",
                  "1위용도", "1위용도근거"]
    merged = houses.merge(facilities[merge_cols], on="읍면", how="left")

    merged.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print(f"완료: {OUTPUT_CSV} 저장 (총 {len(merged)}건)")
    print()
    print("읍면별 용도 점수 및 1위 근거:")
    print(facilities[["읍면", "주거점수", "카페소품샵점수", "게스트하우스펜션점수", "식당베이커리점수", "1위용도", "1위용도근거"]]
          .sort_values("주거점수", ascending=False).to_string())
    print()
    print("결측 확인:", merged["주거점수"].isna().sum(), "건")


if __name__ == "__main__":
    main()
